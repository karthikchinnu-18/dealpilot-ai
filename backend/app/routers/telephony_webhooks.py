from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from sqlalchemy.orm import Session
from ..config import settings
from ..database import get_db
from ..models import CallRecord, CallTranscript, EvidenceRecord, Offer, PurchaseRequest
from ..services.extraction_engine import OfferExtractionEngine
from ..services.strategy_engine import NegotiationStrategyEngine
from ..services.telephony_service import TwilioTelephonyProvider
from .calls import update_negotiation_recommendation

router = APIRouter(prefix="/api/telephony/twilio", tags=["telephony_webhooks"])

@router.get("/test-twiml")
@router.post("/test-twiml")
async def twilio_test_twiml():
    """
    Called by Twilio when verifying outbound calls to customer's phone.
    """
    twiml = TwilioTelephonyProvider.generate_twiml_test_greeting(to_phone="")
    return Response(content=twiml, media_type="application/xml")

@router.post("/voice")
async def twilio_voice_webhook(
    request: Request,
    negotiation_id: str = "",
    CallSid: str = Form(default=""),
    db: Session = Depends(get_db),
):
    """
    Called by Twilio when outbound call connects to supplier.
    Generates TwiML greeting with transparent AI identity disclosure.
    """
    req = db.query(PurchaseRequest).filter(PurchaseRequest.id == negotiation_id).first() if negotiation_id else None
    product = req.product if req else "the requested items"
    quantity = req.quantity if req else 100
    unit = req.unit if req else "units"

    webhook_base = settings.webhook_base_url.rstrip("/")
    gather_url = f"{webhook_base}/api/telephony/twilio/gather?negotiation_id={negotiation_id}" if webhook_base else f"/api/telephony/twilio/gather?negotiation_id={negotiation_id}"

    twiml = TwilioTelephonyProvider.generate_twiml_greeting(
        product=product,
        quantity=quantity,
        unit=unit,
        language="en-IN",
        action_url=gather_url,
    )

    if CallSid:
        call_rec = db.query(CallRecord).filter(CallRecord.provider_call_sid == CallSid).first()
        if call_rec:
            call_rec.call_state = "CONNECTED"
            call_rec.last_event = "Supplier answered. Greeting played."
            db.commit()

    return Response(content=twiml, media_type="application/xml")

@router.post("/status")
async def twilio_status_webhook(
    CallSid: str = Form(default=""),
    CallStatus: str = Form(default=""),
    CallDuration: str = Form(default="0"),
    db: Session = Depends(get_db),
):
    """
    Called by Twilio when call status updates (initiated, ringing, answered, completed).
    """
    if not CallSid:
        return {"status": "ignored"}

    call_rec = db.query(CallRecord).filter(CallRecord.provider_call_sid == CallSid).first()
    if call_rec:
        status_map = {
            "queued": "QUEUED",
            "initiated": "CALLING",
            "ringing": "CALLING",
            "in-progress": "CONNECTED",
            "completed": "COMPLETED",
            "busy": "BUSY",
            "no-answer": "NO_ANSWER",
            "canceled": "CANCELLED",
            "failed": "FAILED",
        }
        call_rec.call_state = status_map.get(CallStatus.lower(), call_rec.call_state)
        call_rec.last_event = f"Twilio status: {CallStatus}"
        try:
            call_rec.duration_seconds = int(CallDuration)
        except ValueError:
            pass
        db.commit()

    return {"status": "ok"}

@router.post("/gather")
async def twilio_gather_webhook(
    SpeechResult: str = Form(default=""),
    Confidence: str = Form(default="1.0"),
    CallSid: str = Form(default=""),
    negotiation_id: str = "",
    db: Session = Depends(get_db),
):
    """
    Receives transcribed speech from Twilio Gather, formulates counteroffer,
    extracts structured quote into Offer table, updates Evidence, and triggers
    deterministic deal ranking to find the best business deal.
    """
    speech_text = SpeechResult.strip()
    webhook_base = settings.webhook_base_url.rstrip("/")
    gather_url = f"{webhook_base}/api/telephony/twilio/gather?negotiation_id={negotiation_id}" if webhook_base else f"/api/telephony/twilio/gather?negotiation_id={negotiation_id}"

    if not speech_text:
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="en-IN">We did not catch that. Please state your quotation again clearly after the tone.</Say>
    <Gather input="speech" timeout="6" speechTimeout="auto" action="{gather_url}" method="POST"/>
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    # Locate call record
    call_rec = None
    if CallSid:
        call_rec = db.query(CallRecord).filter(CallRecord.provider_call_sid == CallSid).first()
    if not call_rec and negotiation_id:
        call_rec = (
            db.query(CallRecord)
            .filter(CallRecord.negotiation_id == negotiation_id, CallRecord.provider == "twilio")
            .order_by(CallRecord.created_at.desc())
            .first()
        )

    if not call_rec:
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="en-IN">Thank you. We have received your response. Goodbye.</Say>
    <Hangup/>
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    # Update transcript
    transcript = call_rec.transcript
    if not transcript:
        transcript = CallTranscript(call_id=call_rec.id, original_language="English")
        db.add(transcript)

    turns = transcript.turns or []
    current_round = call_rec.rounds_completed + 1
    turns.append({
        "round": current_round,
        "speaker": "supplier",
        "text_original": speech_text,
        "text_translated": speech_text,
        "language": "English",
        "timestamp": "now",
    })
    transcript.turns = turns
    call_rec.rounds_completed = current_round
    db.commit()

    # Extract quotation
    req = db.query(PurchaseRequest).filter(PurchaseRequest.id == call_rec.negotiation_id).first()
    supplier_name = call_rec.supplier.business_name if call_rec.supplier else "Supplier"
    qty = req.quantity if req else 100

    extracted = OfferExtractionEngine.extract_from_transcript(
        turns=turns,
        business_name=supplier_name,
        requested_quantity=qty,
        is_simulated=False,
    )

    # Check if we should negotiate a counteroffer
    max_rounds = req.max_negotiation_rounds if req else 3
    target_price = req.target_price if req else 0.0

    needs_counteroffer = (
        extracted.total_price > 0
        and target_price > 0
        and extracted.total_price > target_price
        and current_round < max_rounds
    )

    if needs_counteroffer:
        # Evaluate counteroffer decision
        decision = NegotiationStrategyEngine.evaluate_round(
            budget=req.budget,
            target_price=req.target_price,
            max_authorized_price=req.max_authorized_price,
            quantity=req.quantity,
            current_supplier_quote=extracted.total_price,
            current_round=current_round,
            max_rounds=max_rounds,
            delivery_days_quoted=extracted.delivery_days,
            max_delivery_days_allowed=10,
        )

        counter_speech = (
            f"Thank you. Our buyer's target budget is ₹{int(target_price):,}. "
            f"We are ready to issue a purchase order today if you can meet us closer to ₹{int(decision.suggested_amount):,}. "
            f"Can you offer any discount or meet our budget?"
        )

        turns.append({
            "round": current_round,
            "speaker": "ai",
            "text_original": counter_speech,
            "text_translated": counter_speech,
            "language": "English",
            "timestamp": "now",
        })
        transcript.turns = turns
        db.commit()

        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="en-IN">{counter_speech}</Say>
    <Gather input="speech" timeout="6" speechTimeout="auto" action="{gather_url}" method="POST">
        <Say language="en-IN">We are listening to your counter response.</Say>
    </Gather>
    <Say language="en-IN">We did not hear a response. Thank you and goodbye.</Say>
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    # Finalize offer and update recommendation
    offer = db.query(Offer).filter(Offer.call_id == call_rec.id).first()
    if not offer:
        offer = Offer(
            negotiation_id=call_rec.negotiation_id,
            call_id=call_rec.id,
            business_name=supplier_name,
            source_type="voice_call",
            is_simulated=False,
        )
        db.add(offer)
        db.flush()

    offer.total_price = extracted.total_price
    offer.unit_price = extracted.unit_price
    offer.initial_offer = extracted.initial_offer or extracted.total_price
    offer.bulk_discount = extracted.bulk_discount
    offer.delivery_days = extracted.delivery_days
    offer.warranty = extracted.warranty
    offer.terms = extracted.terms_summary
    offer.evidence_status = "Verified by Documented Check" if not extracted.uncertainty_flag else "Supplier Stated"
    offer.missing_information = extracted.missing_information

    # Add Evidence Records
    price_ev = EvidenceRecord(
        negotiation_id=call_rec.negotiation_id,
        offer_id=offer.id,
        call_id=call_rec.id,
        field_name="Total Quoted Price",
        stated_value=f"₹{extracted.total_price:,.2f}",
        verification_status="Verified by Documented Check",
        verification_method="Twilio Audio Speech Recognition Transcription",
        verification_notes=f"Confirmed by supplier representative over phone: '{speech_text}'",
    )
    db.add(price_ev)

    deliv_ev = EvidenceRecord(
        negotiation_id=call_rec.negotiation_id,
        offer_id=offer.id,
        call_id=call_rec.id,
        field_name="Delivery Timeline",
        stated_value=f"{extracted.delivery_days} days",
        verification_status="Verified by Documented Check",
        verification_method="Twilio Audio Speech Recognition Transcription",
        verification_notes=f"Delivery timeline stated during voice dialogue: {extracted.delivery_days} business days",
    )
    db.add(deliv_ev)

    call_rec.call_state = "COMPLETED"
    call_rec.call_outcome = f"Quotation of ₹{extracted.total_price:,.2f} captured via live phone call"
    call_rec.latest_offer_amount = extracted.total_price
    call_rec.last_event = "Quotation extracted and saved to evidence ledger"
    db.commit()

    # Re-score all offers and update Recommendation
    update_negotiation_recommendation(db, call_rec.negotiation_id)

    closing_speech = (
        f"Thank you. We have recorded your quotation of ₹{int(extracted.total_price):,} "
        f"with delivery in {extracted.delivery_days} days. "
        f"Our procurement manager will review the proposal for final approval. "
        f"Have a great day. Goodbye!"
    )

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="en-IN">{closing_speech}</Say>
    <Hangup/>
</Response>"""
    return Response(content=twiml, media_type="application/xml")
