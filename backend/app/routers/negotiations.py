from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import EvidenceRecord, NegotiationSession, Offer, PurchaseRequest, Recommendation, Supplier
from ..schemas import (
    ApprovalActionRequest,
    NegotiationOut,
    NegotiationRequestIn,
    OfferIn,
    OfferOut,
    RecommendationOut,
)
from ..services.scoring_engine import ScoringEngine

router = APIRouter(prefix="/api", tags=["negotiations"])

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

@router.post("/negotiations", response_model=NegotiationOut, status_code=status.HTTP_201_CREATED)
def create_negotiation(payload: NegotiationRequestIn, db: Session = Depends(get_db)):
    data = payload.model_dump()
    priorities = data.get("priorities", ["best_value"])
    
    req = PurchaseRequest(
        product=data["product"],
        specifications=data.get("specifications", ""),
        quantity=data["quantity"],
        unit=data.get("unit", "units"),
        budget=data["budget"],
        currency=data.get("currency", "INR"),
        target_price=data.get("target_price", data["budget"] * 0.85),
        max_authorized_price=data.get("max_authorized_price", data["budget"]),
        deadline=data["deadline"],
        quality_requirements=data.get("quality_requirements", "Standard certified quality"),
        warranty_requirements=data.get("warranty_requirements", "Standard manufacturer warranty"),
        return_requirements=data.get("return_requirements", "30-day return on defect"),
        payment_terms=data.get("payment_terms", "Net 30 / Advance after delivery"),
        delivery_location=data.get("delivery_location", "Bengaluru, Karnataka, India"),
        mandatory_conditions=data.get("mandatory_conditions", []),
        priorities=priorities,
        max_negotiation_rounds=data.get("max_negotiation_rounds", 3),
        allow_contact=data.get("allow_contact", True),
        notes=data.get("notes", ""),
        status="READY",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req

@router.get("/negotiations", response_model=List[NegotiationOut])
def list_negotiations(db: Session = Depends(get_db)):
    return db.query(PurchaseRequest).order_by(PurchaseRequest.created_at.desc()).all()

@router.get("/negotiations/{negotiation_id}", response_model=NegotiationOut)
def get_negotiation(negotiation_id: str, db: Session = Depends(get_db)):
    req = db.query(PurchaseRequest).filter(PurchaseRequest.id == negotiation_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Negotiation request not found")
    return req

@router.post("/negotiations/{negotiation_id}/offers", response_model=OfferOut)
def add_offer(negotiation_id: str, payload: OfferIn, db: Session = Depends(get_db)):
    req = db.query(PurchaseRequest).filter(PurchaseRequest.id == negotiation_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Negotiation request not found")

    data = payload.model_dump()
    offer = Offer(
        negotiation_id=negotiation_id,
        supplier_id=data.get("supplier_id"),
        call_id=data.get("call_id"),
        business_name=data["business_name"],
        unit_price=data.get("unit_price") or round(data["total_price"] / max(1, req.quantity), 2),
        total_price=data["total_price"],
        currency=data.get("currency", "INR"),
        delivery_days=data["delivery_days"],
        initial_offer=data.get("initial_offer") or data["total_price"],
        final_explicit_offer=data.get("final_explicit_offer") or data["total_price"],
        bulk_discount=data.get("bulk_discount", 0.0),
        taxes=data.get("taxes", 0.0),
        shipping_charges=data.get("shipping_charges", 0.0),
        availability=data.get("availability", "In stock"),
        quality_conditions=data.get("quality_conditions", "Standard"),
        warranty=data.get("warranty", "Standard warranty"),
        payment_terms=data.get("payment_terms", "Net 30"),
        terms=data.get("terms", ""),
        evidence_note=data["evidence_note"],
        evidence_status=data["evidence_status"],
        source_type=data["source_type"],
        is_simulated=data.get("is_simulated", False),
    )
    db.add(offer)
    db.flush()

    # Create corresponding EvidenceRecord
    ev = EvidenceRecord(
        negotiation_id=negotiation_id,
        offer_id=offer.id,
        field_name="total_price",
        stated_value=f"₹{offer.total_price:,.2f}",
        verification_status=data["evidence_status"],
        verification_method="User Manual Entry" if data["source_type"] != "phone" else "Phone Record",
        verification_notes=data["evidence_note"],
    )
    db.add(ev)

    # Recalculate recommendation
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
        for o in req.offers + [offer]
    ]

    scoring_res = ScoringEngine.evaluate_offers(
        offers=all_offers,
        budget=req.budget,
        deadline=req.deadline,
        priorities=req.priorities or ["best_value"],
        mandatory_conditions=req.mandatory_conditions or [],
    )

    # Save or update recommendation record
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
    db.refresh(offer)
    return offer

@router.get("/negotiations/{negotiation_id}/recommendation", response_model=RecommendationOut)
def get_recommendation(negotiation_id: str, db: Session = Depends(get_db)):
    req = db.query(PurchaseRequest).filter(PurchaseRequest.id == negotiation_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Negotiation not found")

    offers = req.offers
    if not offers:
        return RecommendationOut(
            negotiation_id=negotiation_id,
            recommendation=None,
            message="No offers yet. Enter quotations or start automated supplier calls.",
            offers_compared=0,
            score=0.0,
            human_approval_status="PENDING",
        )

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
        for o in offers
    ]

    res = ScoringEngine.evaluate_offers(
        offers=all_offers,
        budget=req.budget,
        deadline=req.deadline,
        priorities=req.priorities or ["best_value"],
        mandatory_conditions=req.mandatory_conditions or [],
    )

    # Check if recommendation exists in DB to retrieve approval status
    rec_record = db.query(Recommendation).filter(Recommendation.negotiation_id == negotiation_id).first()
    approval_status = rec_record.human_approval_status if rec_record else "PENDING"
    approval_notes = rec_record.approval_notes if rec_record else ""
    approval_timestamp = rec_record.approval_timestamp if rec_record else ""

    return RecommendationOut(
        id=rec_record.id if rec_record else None,
        negotiation_id=negotiation_id,
        recommendation=res.recommendation,
        recommended_supplier=res.recommended_supplier,
        final_price=res.final_price,
        total_cost=res.total_cost,
        currency=res.currency,
        discount_achieved=res.discount_achieved,
        baseline_savings=res.baseline_savings,
        baseline_reference=res.baseline_reference,
        delivery_days=res.delivery_days,
        warranty_terms=res.warranty_terms,
        payment_terms=res.payment_terms,
        score=res.score,
        score_breakdown=res.score_breakdown,
        reasons=res.reasons,
        pros_cons=res.pros_cons,
        next_best_offer=res.next_best_offer,
        missing_uncertain_info=res.missing_uncertain_info,
        offers_compared=res.offers_compared,
        note=res.note,
        ranked_offers=res.ranked_offers,
        human_approval_status=approval_status,
        approval_notes=approval_notes,
        approval_timestamp=approval_timestamp,
        message=res.message,
    )

@router.post("/negotiations/{negotiation_id}/approval")
def set_approval(
    negotiation_id: str,
    payload: ApprovalActionRequest,
    db: Session = Depends(get_db),
):
    req = db.query(PurchaseRequest).filter(PurchaseRequest.id == negotiation_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Negotiation not found")

    rec = db.query(Recommendation).filter(Recommendation.negotiation_id == negotiation_id).first()
    if not rec:
        raise HTTPException(status_code=400, detail="Cannot approve without evaluated recommendation")

    status_val = "APPROVED" if payload.action == "approve" else "REJECTED"
    rec.human_approval_status = status_val
    rec.approval_notes = payload.notes or ""
    rec.approval_timestamp = utc_now()
    req.status = status_val

    db.commit()
    db.refresh(rec)
    return {
        "negotiation_id": negotiation_id,
        "human_approval_status": status_val,
        "approval_notes": rec.approval_notes,
        "approval_timestamp": rec.approval_timestamp,
        "message": f"Recommendation successfully {status_val.lower()} by authorized human supervisor.",
    }
