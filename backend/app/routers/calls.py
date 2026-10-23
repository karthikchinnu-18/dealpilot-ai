from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..config import settings
from ..database import get_db
from ..models import (
    CallRecord,
    CallTranscript,
    EvidenceRecord,
    NegotiationSession,
    Offer,
    PurchaseRequest,
    Recommendation,
    Supplier,
)
from ..schemas import (
    CallRecordOut,
    CallStartRequest,
    CallTranscriptOut,
    EvidenceOut,
    NegotiationSessionOut,
    SupplierCallRequest,
)
from ..services.scoring_engine import ScoringEngine
from ..services.simulation_service import SimulationService
from ..services.telephony_service import telephony_service

router = APIRouter(prefix="/api", tags=["calls"])

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def update_negotiation_recommendation(db: Session, negotiation_id: str) -> Optional[Recommendation]:
    """
    Deterministically re-scores all available offers for this negotiation
    and updates the persisted Recommendation record.
    """
    req = db.query(PurchaseRequest).filter(PurchaseRequest.id == negotiation_id).first()
    if not req:
        return None

    all_offers_query = db.query(Offer).filter(Offer.negotiation_id == negotiation_id).all()
    all_offers = [
        {
            "id": o.id,
            "business_name": o.business_name,
            "total_price": o.total_price,
            "delivery_days": o.delivery_days,
            "evidence_status": o.evidence_status,
            "source_type": o.source_type,
            "is_simulated": o.is_simulated,
            "initial_offer": o.initial_offer,
            "terms": o.terms,
            "warranty": o.warranty,
            "missing_information": o.missing_information,
        }
        for o in all_offers_query
    ]

    scoring_res = ScoringEngine.evaluate_offers(
        offers=all_offers,
        budget=req.budget,
        deadline=req.deadline,
        priorities=req.priorities or ["best_value"],
        mandatory_conditions=req.mandatory_conditions or [],
    )

    rec_record = db.query(Recommendation).filter(Recommendation.negotiation_id == negotiation_id).first()
    if not rec_record:
        rec_record = Recommendation(negotiation_id=negotiation_id)
        db.add(rec_record)

    rec_record.recommended_offer_id = scoring_res.recommendation.get("id") if scoring_res.recommendation else None
    rec_record.recommended_supplier = scoring_res.recommended_supplier
    rec_record.final_price = scoring_res.final_price
    rec_record.total_cost = scoring_res.total_cost
    rec_record.currency = scoring_res.currency
    rec_record.discount_achieved = scoring_res.discount_achieved
    rec_record.baseline_savings = scoring_res.baseline_savings
    rec_record.baseline_reference = scoring_res.baseline_reference
    rec_record.delivery_days = scoring_res.delivery_days
    rec_record.warranty_terms = scoring_res.warranty_terms
    rec_record.payment_terms = scoring_res.payment_terms
    rec_record.score = scoring_res.score
    rec_record.score_breakdown = scoring_res.score_breakdown
    rec_record.reasons = scoring_res.reasons
    rec_record.pros_cons = scoring_res.pros_cons
    rec_record.next_best_offer = scoring_res.next_best_offer
    rec_record.missing_uncertain_info = scoring_res.missing_uncertain_info
    rec_record.ranked_offers = scoring_res.ranked_offers
    rec_record.note = scoring_res.note
    db.commit()
    db.refresh(rec_record)
    return rec_record


async def execute_call_for_single_supplier(
    db: Session,
    req: PurchaseRequest,
    supp: Supplier,
    mode: str = "simulated",
    user_confirmed: bool = True,
    session: Optional[NegotiationSession] = None,
    index: int = 0,
) -> Dict[str, Any]:
    """
    Executes a phone call to a single supplier (simulated or real via Twilio),
    extracts quotation, records evidence, and recalculates the recommendation.
    """
    if not user_confirmed:
        raise HTTPException(
            status_code=400,
            detail="User confirmation is required before placing outbound calls.",
        )

    if not session:
        session = NegotiationSession(
            negotiation_id=req.id,
            mode=mode,
            status="IN_PROGRESS",
            total_suppliers=1,
            completed_calls=0,
            failed_calls=0,
            offers_collected=0,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    req.status = "CALLING"

    if mode == "simulated":
        sim_res = SimulationService.run_simulated_call(
            session=session,
            request=req,
            supplier=supp,
            index=index,
        )
        call_rec: CallRecord = sim_res["call"]
        transcript: CallTranscript = sim_res["transcript"]
        offer: Optional[Offer] = sim_res["offer"]
        evidence_items: List[EvidenceRecord] = sim_res["evidence"]

        db.add(call_rec)
        db.flush()

        transcript.call_id = call_rec.id
        db.add(transcript)

        if offer:
            offer.call_id = call_rec.id
            db.add(offer)
            session.offers_collected += 1

        for ev in evidence_items:
            ev.call_id = call_rec.id
            if offer:
                ev.offer_id = offer.id
            db.add(ev)

        if call_rec.call_state == "COMPLETED":
            session.completed_calls += 1
        else:
            session.failed_calls += 1

        session.status = "COMPLETED"
        req.status = "COMPLETED"
        db.commit()

        # Update recommendation deterministically
        update_negotiation_recommendation(db, req.id)
        db.refresh(session)
        db.refresh(call_rec)
        return {"session": session, "call": call_rec, "offer": offer}

    else:
        # REAL MODE: Twilio outbound dispatch
        is_ready, reason = telephony_service.is_configured()
        if not is_ready:
            raise HTTPException(
                status_code=400,
                detail=f"Real calling is disabled: {reason} Configure TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER in settings to enable real calls.",
            )

        webhook_base = settings.webhook_base_url.rstrip("/")
        voice_url = f"{webhook_base}/api/telephony/twilio/voice?negotiation_id={req.id}"
        status_url = f"{webhook_base}/api/telephony/twilio/status"

        call_rec = CallRecord(
            session_id=session.id,
            negotiation_id=req.id,
            supplier_id=supp.id,
            provider="twilio",
            call_state="CALLING",
            is_simulated=False,
            last_event="Initiating outbound call via Twilio",
        )
        db.add(call_rec)
        db.flush()

        try:
            is_valid, formatted_phone, err = telephony_service.validate_phone_number(
                supp.country_code, supp.phone_number
            )
            to_phone = formatted_phone if is_valid else f"{supp.country_code}{supp.phone_number.replace(' ', '')}"
            twilio_res = await telephony_service.initiate_outbound_call(
                to_phone=to_phone,
                webhook_url=voice_url,
                status_callback_url=status_url,
            )
            call_rec.provider_call_sid = twilio_res.get("sid", "")
            call_rec.last_event = f"Call placed to {to_phone}. Twilio SID: {call_rec.provider_call_sid}"
        except Exception as e:
            call_rec.call_state = "FAILED"
            call_rec.failure_reason = str(e)
            session.failed_calls += 1

        db.commit()
        db.refresh(session)
        db.refresh(call_rec)
        return {"session": session, "call": call_rec, "offer": None}


@router.post("/negotiations/{negotiation_id}/suppliers/{supplier_id}/call")
async def call_single_supplier(
    negotiation_id: str,
    supplier_id: str,
    payload: SupplierCallRequest,
    db: Session = Depends(get_db),
):
    req = db.query(PurchaseRequest).filter(PurchaseRequest.id == negotiation_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Purchase request not found")

    supp = db.query(Supplier).filter(
        Supplier.id == supplier_id,
        Supplier.negotiation_id == negotiation_id,
    ).first()
    if not supp:
        raise HTTPException(status_code=404, detail="Supplier not found")

    res = await execute_call_for_single_supplier(
        db=db,
        req=req,
        supp=supp,
        mode=payload.mode,
        user_confirmed=payload.user_confirmed,
    )

    rec = db.query(Recommendation).filter(Recommendation.negotiation_id == negotiation_id).first()
    return {
        "success": True,
        "message": f"Call initiated to {supp.business_name} ({supp.country_code} {supp.phone_number}) in {payload.mode} mode.",
        "call_id": res["call"].id,
        "call_state": res["call"].call_state,
        "is_simulated": res["call"].is_simulated,
        "recommended_supplier": rec.recommended_supplier if rec else None,
        "best_deal_price": rec.final_price if rec else None,
    }


@router.post("/negotiations/{negotiation_id}/calls/start", response_model=NegotiationSessionOut)
async def start_calls(
    negotiation_id: str,
    payload: CallStartRequest,
    db: Session = Depends(get_db),
):
    req = db.query(PurchaseRequest).filter(PurchaseRequest.id == negotiation_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Purchase request not found")

    if not payload.user_confirmed:
        raise HTTPException(
            status_code=400,
            detail="Explicit user confirmation is mandatory before initiating any AI outbound calls.",
        )

    # Fetch eligible suppliers
    query = db.query(Supplier).filter(
        Supplier.negotiation_id == negotiation_id,
        Supplier.permission_status == "authorized",
    )
    if payload.supplier_ids:
        query = query.filter(Supplier.id.in_(payload.supplier_ids))
    suppliers = query.all()

    if not suppliers:
        raise HTTPException(
            status_code=400,
            detail="No eligible suppliers found. Add authorized suppliers with phone numbers first.",
        )

    # Real Calling Validation
    if payload.mode == "real":
        is_ready, reason = telephony_service.is_configured()
        if not is_ready:
            raise HTTPException(
                status_code=400,
                detail=f"Real calling is disabled: {reason} Configure TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER in settings to enable real calls.",
            )

    # Create Negotiation Session
    session = NegotiationSession(
        negotiation_id=negotiation_id,
        mode=payload.mode,
        status="IN_PROGRESS",
        total_suppliers=len(suppliers),
        completed_calls=0,
        failed_calls=0,
        offers_collected=0,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    req.status = "CALLING"

    # Execution Loop
    if payload.mode == "simulated":
        for i, supp in enumerate(suppliers):
            await execute_call_for_single_supplier(
                db=db,
                req=req,
                supp=supp,
                mode="simulated",
                user_confirmed=True,
                session=session,
                index=i,
            )

        session.status = "COMPLETED"
        req.status = "COMPLETED"
        update_negotiation_recommendation(db, negotiation_id)
        db.commit()
        db.refresh(session)
        return session

    else:
        # REAL MODE: Twilio outbound dispatch
        webhook_base = settings.webhook_base_url.rstrip("/")
        voice_url = f"{webhook_base}/api/telephony/twilio/voice?negotiation_id={negotiation_id}"
        status_url = f"{webhook_base}/api/telephony/twilio/status"

        for supp in suppliers:
            call_rec = CallRecord(
                session_id=session.id,
                negotiation_id=negotiation_id,
                supplier_id=supp.id,
                provider="twilio",
                call_state="CALLING",
                is_simulated=False,
                last_event="Initiating outbound call via Twilio",
            )
            db.add(call_rec)
            db.flush()

            try:
                is_valid, formatted_phone, _ = telephony_service.validate_phone_number(
                    supp.country_code, supp.phone_number
                )
                to_phone = formatted_phone if is_valid else f"{supp.country_code}{supp.phone_number.replace(' ', '')}"
                twilio_res = await telephony_service.initiate_outbound_call(
                    to_phone=to_phone,
                    webhook_url=voice_url,
                    status_callback_url=status_url,
                )
                call_rec.provider_call_sid = twilio_res.get("sid", "")
                call_rec.last_event = f"Call queued with Twilio SID: {call_rec.provider_call_sid}"
            except Exception as e:
                call_rec.call_state = "FAILED"
                call_rec.failure_reason = str(e)
                session.failed_calls += 1

        db.commit()
        db.refresh(session)
        return session

@router.get("/negotiations/{negotiation_id}/calls", response_model=List[CallRecordOut])
def list_calls(negotiation_id: str, db: Session = Depends(get_db)):
    calls = db.query(CallRecord).filter(CallRecord.negotiation_id == negotiation_id).order_by(CallRecord.created_at.desc()).all()
    results = []
    for c in calls:
        rec_out = CallRecordOut(
            id=c.id,
            session_id=c.session_id,
            negotiation_id=c.negotiation_id,
            supplier_id=c.supplier_id,
            business_name=c.supplier.business_name if c.supplier else "Supplier",
            phone_number=f"{c.supplier.country_code} {c.supplier.phone_number}" if c.supplier else "",
            provider=c.provider,
            provider_call_sid=c.provider_call_sid,
            call_state=c.call_state,
            duration_seconds=c.duration_seconds,
            rounds_completed=c.rounds_completed,
            detected_language=c.detected_language,
            latest_offer_amount=c.latest_offer_amount,
            negotiation_status=c.negotiation_status,
            last_event=c.last_event,
            call_outcome=c.call_outcome,
            failure_reason=c.failure_reason,
            is_simulated=c.is_simulated,
            created_at=c.created_at,
            updated_at=c.updated_at,
            transcript=CallTranscriptOut(
                id=c.transcript.id,
                call_id=c.id,
                turns=c.transcript.turns or [],
                original_language=c.transcript.original_language,
                english_summary=c.transcript.english_summary,
                created_at=c.transcript.created_at,
            ) if c.transcript else None,
        )
        results.append(rec_out)
    return results

@router.get("/negotiations/{negotiation_id}/calls/{call_id}", response_model=CallRecordOut)
def get_call(negotiation_id: str, call_id: str, db: Session = Depends(get_db)):
    c = db.query(CallRecord).filter(
        CallRecord.id == call_id,
        CallRecord.negotiation_id == negotiation_id,
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="Call record not found")

    return CallRecordOut(
        id=c.id,
        session_id=c.session_id,
        negotiation_id=c.negotiation_id,
        supplier_id=c.supplier_id,
        business_name=c.supplier.business_name if c.supplier else "Supplier",
        phone_number=f"{c.supplier.country_code} {c.supplier.phone_number}" if c.supplier else "",
        provider=c.provider,
        provider_call_sid=c.provider_call_sid,
        call_state=c.call_state,
        duration_seconds=c.duration_seconds,
        rounds_completed=c.rounds_completed,
        detected_language=c.detected_language,
        latest_offer_amount=c.latest_offer_amount,
        negotiation_status=c.negotiation_status,
        last_event=c.last_event,
        call_outcome=c.call_outcome,
        failure_reason=c.failure_reason,
        is_simulated=c.is_simulated,
        created_at=c.created_at,
        updated_at=c.updated_at,
        transcript=CallTranscriptOut(
            id=c.transcript.id,
            call_id=c.id,
            turns=c.transcript.turns or [],
            original_language=c.transcript.original_language,
            english_summary=c.transcript.english_summary,
            created_at=c.transcript.created_at,
        ) if c.transcript else None,
    )

@router.post("/negotiations/{negotiation_id}/calls/{call_id}/cancel")
async def cancel_call(negotiation_id: str, call_id: str, db: Session = Depends(get_db)):
    c = db.query(CallRecord).filter(
        CallRecord.id == call_id,
        CallRecord.negotiation_id == negotiation_id,
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="Call record not found")

    if c.provider == "twilio" and c.provider_call_sid:
        await telephony_service.end_call(c.provider_call_sid)

    c.call_state = "CANCELLED"
    c.last_event = "Cancelled by user"
    db.commit()
    return {"message": "Call marked as cancelled"}

@router.post("/negotiations/{negotiation_id}/calls/{call_id}/retry")
def retry_call(negotiation_id: str, call_id: str, db: Session = Depends(get_db)):
    c = db.query(CallRecord).filter(
        CallRecord.id == call_id,
        CallRecord.negotiation_id == negotiation_id,
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="Call record not found")

    c.call_state = "QUEUED"
    c.failure_reason = ""
    c.last_event = "Queued for retry"
    db.commit()
    return {"message": "Call queued for retry"}

@router.get("/negotiations/{negotiation_id}/transcripts", response_model=List[CallTranscriptOut])
def list_transcripts(negotiation_id: str, db: Session = Depends(get_db)):
    transcripts = (
        db.query(CallTranscript)
        .join(CallRecord, CallTranscript.call_id == CallRecord.id)
        .filter(CallRecord.negotiation_id == negotiation_id)
        .all()
    )
    return [
        CallTranscriptOut(
            id=t.id,
            call_id=t.call_id,
            turns=t.turns or [],
            original_language=t.original_language,
            english_summary=t.english_summary,
            created_at=t.created_at,
        )
        for t in transcripts
    ]

@router.get("/negotiations/{negotiation_id}/evidence", response_model=List[EvidenceOut])
def list_evidence(negotiation_id: str, db: Session = Depends(get_db)):
    evidence_items = db.query(EvidenceRecord).filter(EvidenceRecord.negotiation_id == negotiation_id).all()
    return [
        EvidenceOut(
            id=e.id,
            negotiation_id=e.negotiation_id,
            offer_id=e.offer_id,
            call_id=e.call_id,
            field_name=e.field_name,
            stated_value=e.stated_value,
            verification_status=e.verification_status,
            verification_method=e.verification_method,
            verification_notes=e.verification_notes or "",
            created_at=e.created_at,
        )
        for e in evidence_items
    ]
