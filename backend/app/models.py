import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from .database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class PurchaseRequest(Base):
    __tablename__ = "purchase_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    product = Column(String(150), nullable=False)
    specifications = Column(Text, default="")
    quantity = Column(Integer, nullable=False, default=1)
    unit = Column(String(50), default="units")
    budget = Column(Float, nullable=False, default=0.0)
    currency = Column(String(10), default="INR")
    target_price = Column(Float, default=0.0)
    max_authorized_price = Column(Float, default=0.0)
    deadline = Column(String(100), nullable=False, default="Within 7 days")
    quality_requirements = Column(Text, default="Standard certified quality")
    warranty_requirements = Column(Text, default="Standard manufacturer warranty")
    return_requirements = Column(Text, default="30-day return on defect")
    payment_terms = Column(Text, default="Net 30 / Advance after delivery")
    delivery_location = Column(String(200), default="Bengaluru, Karnataka, India")
    mandatory_conditions = Column(JSON, default=list)
    priorities = Column(JSON, default=lambda: ["best_value"])
    max_negotiation_rounds = Column(Integer, default=3)
    allow_contact = Column(Boolean, default=True)
    notes = Column(Text, default="")
    status = Column(String(50), default="READY")
    human_approval_required = Column(Boolean, default=True)
    created_at = Column(String(50), default=utc_now_iso)
    updated_at = Column(String(50), default=utc_now_iso, onupdate=utc_now_iso)

    # Relationships
    suppliers = relationship("Supplier", back_populates="negotiation", cascade="all, delete-orphan")
    sessions = relationship("NegotiationSession", back_populates="negotiation", cascade="all, delete-orphan")
    offers = relationship("Offer", back_populates="negotiation", cascade="all, delete-orphan")
    calls = relationship("CallRecord", back_populates="negotiation", cascade="all, delete-orphan")
    evidence_items = relationship("EvidenceRecord", back_populates="negotiation", cascade="all, delete-orphan")
    recommendation = relationship("Recommendation", back_populates="negotiation", uselist=False, cascade="all, delete-orphan")


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    negotiation_id = Column(String(36), ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False)
    business_name = Column(String(150), nullable=False)
    country_code = Column(String(10), default="+91")
    phone_number = Column(String(30), nullable=False)
    contact_person = Column(String(100), default="")
    email = Column(String(120), default="")
    website = Column(String(200), default="")
    notes = Column(Text, default="")
    permission_status = Column(String(50), default="authorized")  # authorized, opt_out, pending
    is_valid_phone = Column(Boolean, default=True)
    preferred_language = Column(String(50), default="auto")
    created_at = Column(String(50), default=utc_now_iso)

    negotiation = relationship("PurchaseRequest", back_populates="suppliers")
    calls = relationship("CallRecord", back_populates="supplier", cascade="all, delete-orphan")
    offers = relationship("Offer", back_populates="supplier")


class NegotiationSession(Base):
    __tablename__ = "negotiation_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    negotiation_id = Column(String(36), ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False)
    mode = Column(String(20), default="simulated")  # "simulated" | "real"
    status = Column(String(50), default="QUEUED")  # QUEUED, IN_PROGRESS, COMPLETED, FAILED, CANCELLED
    total_suppliers = Column(Integer, default=0)
    completed_calls = Column(Integer, default=0)
    failed_calls = Column(Integer, default=0)
    offers_collected = Column(Integer, default=0)
    created_at = Column(String(50), default=utc_now_iso)
    updated_at = Column(String(50), default=utc_now_iso, onupdate=utc_now_iso)

    negotiation = relationship("PurchaseRequest", back_populates="sessions")
    calls = relationship("CallRecord", back_populates="session", cascade="all, delete-orphan")


class CallRecord(Base):
    __tablename__ = "call_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("negotiation_sessions.id", ondelete="CASCADE"), nullable=False)
    negotiation_id = Column(String(36), ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False)
    supplier_id = Column(String(36), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50), default="simulation")  # simulation, twilio
    provider_call_sid = Column(String(100), default="")
    call_state = Column(String(50), default="QUEUED")
    # States: QUEUED, CALLING, CONNECTED, NEGOTIATING, COMPLETED, NO_ANSWER, BUSY, REJECTED, FAILED, CANCELLED, NEEDS_REVIEW
    duration_seconds = Column(Integer, default=0)
    rounds_completed = Column(Integer, default=0)
    detected_language = Column(String(50), default="English")
    latest_offer_amount = Column(Float, default=0.0)
    negotiation_status = Column(String(100), default="Pending")
    last_event = Column(String(255), default="Initialized")
    call_outcome = Column(String(255), default="")
    failure_reason = Column(String(255), default="")
    is_simulated = Column(Boolean, default=True)
    created_at = Column(String(50), default=utc_now_iso)
    updated_at = Column(String(50), default=utc_now_iso, onupdate=utc_now_iso)

    session = relationship("NegotiationSession", back_populates="calls")
    negotiation = relationship("PurchaseRequest", back_populates="calls")
    supplier = relationship("Supplier", back_populates="calls")
    transcript = relationship("CallTranscript", back_populates="call", uselist=False, cascade="all, delete-orphan")
    offer = relationship("Offer", back_populates="call", uselist=False)


class CallTranscript(Base):
    __tablename__ = "call_transcripts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    call_id = Column(String(36), ForeignKey("call_records.id", ondelete="CASCADE"), nullable=False)
    turns = Column(JSON, default=list)
    # turns format: [{"round": 1, "speaker": "ai"|"supplier", "text_original": str, "text_translated": str, "language": str, "timestamp": str}]
    original_language = Column(String(50), default="English")
    english_summary = Column(Text, default="")
    created_at = Column(String(50), default=utc_now_iso)

    call = relationship("CallRecord", back_populates="transcript")


class Offer(Base):
    __tablename__ = "offers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    negotiation_id = Column(String(36), ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False)
    supplier_id = Column(String(36), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    call_id = Column(String(36), ForeignKey("call_records.id", ondelete="SET NULL"), nullable=True)
    
    business_name = Column(String(150), nullable=False)
    unit_price = Column(Float, default=0.0)
    total_price = Column(Float, nullable=False, default=0.0)
    currency = Column(String(10), default="INR")
    delivery_days = Column(Integer, nullable=False, default=3)
    
    initial_offer = Column(Float, default=0.0)
    counteroffers = Column(JSON, default=list)
    final_explicit_offer = Column(Float, default=0.0)
    bulk_discount = Column(Float, default=0.0)
    taxes = Column(Float, default=0.0)
    shipping_charges = Column(Float, default=0.0)
    other_charges = Column(Float, default=0.0)
    
    availability = Column(String(100), default="In stock")
    quality_conditions = Column(String(255), default="Verified")
    warranty = Column(String(255), default="Standard")
    payment_terms = Column(String(255), default="Net 30")
    returns_cancellation = Column(String(255), default="Applicable")
    quote_validity = Column(String(100), default="7 days")
    
    missing_information = Column(JSON, default=list)
    uncertainty_flag = Column(Boolean, default=False)
    extraction_confidence = Column(Float, default=1.0)
    
    terms = Column(Text, default="")
    evidence_note = Column(Text, nullable=False, default="")
    evidence_status = Column(String(50), default="unverified")
    # evidence_status: "verified", "unverified", "demo", "supplier_stated", "disputed", "expired"
    source_type = Column(String(50), default="phone")
    # source_type: "phone", "email", "website", "demo", "other"
    is_simulated = Column(Boolean, default=False)
    created_at = Column(String(50), default=utc_now_iso)

    negotiation = relationship("PurchaseRequest", back_populates="offers")
    supplier = relationship("Supplier", back_populates="offers")
    call = relationship("CallRecord", back_populates="offer")
    evidence_records = relationship("EvidenceRecord", back_populates="offer", cascade="all, delete-orphan")


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    negotiation_id = Column(String(36), ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False)
    offer_id = Column(String(36), ForeignKey("offers.id", ondelete="SET NULL"), nullable=True)
    call_id = Column(String(36), ForeignKey("call_records.id", ondelete="SET NULL"), nullable=True)
    
    field_name = Column(String(100), nullable=False)  # e.g., "total_price", "delivery_days", "warranty"
    stated_value = Column(String(255), nullable=False)
    verification_status = Column(String(50), default="Supplier Stated")
    # Statuses: "Unverified", "Supplier Stated", "User Entered", "Awaiting Confirmation", "Verified by Documented Check", "Disputed", "Expired", "Simulated"
    verification_method = Column(String(100), default="Transcript Audio Match")
    verification_notes = Column(Text, default="")
    created_at = Column(String(50), default=utc_now_iso)

    negotiation = relationship("PurchaseRequest", back_populates="evidence_items")
    offer = relationship("Offer", back_populates="evidence_records")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    negotiation_id = Column(String(36), ForeignKey("purchase_requests.id", ondelete="CASCADE"), unique=True, nullable=False)
    recommended_offer_id = Column(String(36), nullable=True)
    
    recommended_supplier = Column(String(150), default="")
    final_price = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    currency = Column(String(10), default="INR")
    discount_achieved = Column(Float, default=0.0)
    baseline_savings = Column(Float, default=0.0)
    baseline_reference = Column(String(200), default="")
    delivery_days = Column(Integer, default=0)
    warranty_terms = Column(String(255), default="")
    payment_terms = Column(String(255), default="")
    
    score = Column(Float, default=0.0)
    score_breakdown = Column(JSON, default=dict)
    reasons = Column(JSON, default=list)
    pros_cons = Column(JSON, default=dict)
    next_best_offer = Column(JSON, default=dict)
    missing_uncertain_info = Column(JSON, default=list)
    ranked_offers = Column(JSON, default=list)
    
    human_approval_status = Column(String(50), default="PENDING")  # PENDING, APPROVED, REJECTED
    approval_notes = Column(Text, default="")
    approval_timestamp = Column(String(50), default="")
    note = Column(Text, default="")
    created_at = Column(String(50), default=utc_now_iso)

    negotiation = relationship("PurchaseRequest", back_populates="recommendation")
