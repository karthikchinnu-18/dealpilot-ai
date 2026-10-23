from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

# -------------------------------------------------------------
# Backwards-compatible base schemas
# -------------------------------------------------------------

class NegotiationRequestIn(BaseModel):
    product: str = Field(min_length=2, max_length=150)
    quantity: int = Field(gt=0, le=100000)
    budget: float = Field(gt=0, le=100000000)
    deadline: str = Field(min_length=1, max_length=100)
    priorities: List[Literal["lowest_price", "fastest_delivery", "best_value"]] = Field(
        default_factory=lambda: ["best_value"], max_length=3
    )
    # Extended optional fields
    specifications: Optional[str] = Field(default="", max_length=2000)
    unit: Optional[str] = Field(default="units", max_length=50)
    currency: Optional[str] = Field(default="INR", max_length=10)
    target_price: Optional[float] = Field(default=0.0, ge=0.0)
    max_authorized_price: Optional[float] = Field(default=0.0, ge=0.0)
    quality_requirements: Optional[str] = Field(default="Standard certified quality", max_length=1000)
    warranty_requirements: Optional[str] = Field(default="Standard manufacturer warranty", max_length=1000)
    return_requirements: Optional[str] = Field(default="30-day return on defect", max_length=1000)
    payment_terms: Optional[str] = Field(default="Net 30 / Advance after delivery", max_length=1000)
    delivery_location: Optional[str] = Field(default="Bengaluru, Karnataka, India", max_length=200)
    mandatory_conditions: Optional[List[str]] = Field(default_factory=list)
    max_negotiation_rounds: Optional[int] = Field(default=3, ge=1, le=10)
    allow_contact: Optional[bool] = True
    notes: Optional[str] = Field(default="", max_length=2000)


class OfferIn(BaseModel):
    business_name: str = Field(min_length=2, max_length=150)
    total_price: float = Field(gt=0, le=100000000)
    delivery_days: int = Field(ge=0, le=3650)
    terms: str = Field(default="", max_length=1000)
    evidence_note: str = Field(min_length=3, max_length=1000)
    evidence_status: str = "unverified"
    source_type: str = "other"
    # Extended fields
    unit_price: Optional[float] = 0.0
    currency: Optional[str] = "INR"
    initial_offer: Optional[float] = 0.0
    final_explicit_offer: Optional[float] = 0.0
    bulk_discount: Optional[float] = 0.0
    taxes: Optional[float] = 0.0
    shipping_charges: Optional[float] = 0.0
    other_charges: Optional[float] = 0.0
    availability: Optional[str] = "In stock"
    quality_conditions: Optional[str] = "Standard"
    warranty: Optional[str] = "Standard warranty"
    payment_terms: Optional[str] = "Net 30"
    returns_cancellation: Optional[str] = "Applicable"
    quote_validity: Optional[str] = "7 days"
    supplier_id: Optional[str] = None
    call_id: Optional[str] = None
    is_simulated: Optional[bool] = False


class OfferOut(OfferIn):
    id: str
    negotiation_id: str
    created_at: str
    missing_information: List[str] = Field(default_factory=list)
    uncertainty_flag: bool = False
    extraction_confidence: float = 1.0


class SupplierCreate(BaseModel):
    business_name: str = Field(min_length=2, max_length=150)
    country_code: str = Field(default="+91", max_length=10)
    phone_number: str = Field(min_length=5, max_length=30)
    contact_person: Optional[str] = Field(default="", max_length=100)
    email: Optional[str] = Field(default="", max_length=120)
    website: Optional[str] = Field(default="", max_length=200)
    notes: Optional[str] = Field(default="", max_length=1000)
    preferred_language: Optional[str] = Field(default="auto", max_length=50)
    auto_call: bool = False
    calling_mode: Literal["simulated", "real"] = "simulated"


class SupplierUpdate(BaseModel):
    business_name: Optional[str] = None
    country_code: Optional[str] = None
    phone_number: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None
    permission_status: Optional[str] = None
    preferred_language: Optional[str] = None


class SupplierOut(BaseModel):
    id: str
    negotiation_id: str
    business_name: str
    country_code: str
    phone_number: str
    contact_person: Optional[str] = ""
    email: Optional[str] = ""
    website: Optional[str] = ""
    notes: Optional[str] = ""
    preferred_language: Optional[str] = "auto"
    permission_status: str
    is_valid_phone: bool
    created_at: str


class PhoneValidationRequest(BaseModel):
    country_code: str = "+91"
    phone_number: str


class PhoneValidationResponse(BaseModel):
    is_valid: bool
    formatted_e164: str
    country_code: str
    national_number: str
    reason: Optional[str] = None


class CallStartRequest(BaseModel):
    mode: Literal["simulated", "real"] = "simulated"
    supplier_ids: Optional[List[str]] = None
    user_confirmed: bool = Field(
        ...,
        description="Explicit user confirmation required before any outbound call batch starts"
    )


class SupplierCallRequest(BaseModel):
    mode: Literal["simulated", "real"] = "simulated"
    user_confirmed: bool = True


class TelephonyConfigUpdate(BaseModel):
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    webhook_base_url: str = ""


class TestCallRequest(BaseModel):
    country_code: str = "+91"
    phone_number: str


class TranscriptTurn(BaseModel):
    round: int
    speaker: Literal["ai", "supplier", "system"]
    text_original: str
    text_translated: Optional[str] = ""
    language: str = "English"
    timestamp: str


class CallTranscriptOut(BaseModel):
    id: str
    call_id: str
    turns: List[TranscriptTurn]
    original_language: str
    english_summary: str
    created_at: str


class CallRecordOut(BaseModel):
    id: str
    session_id: str
    negotiation_id: str
    supplier_id: str
    business_name: Optional[str] = ""
    phone_number: Optional[str] = ""
    provider: str
    provider_call_sid: str
    call_state: str
    duration_seconds: int
    rounds_completed: int
    detected_language: str
    latest_offer_amount: float
    negotiation_status: str
    last_event: str
    call_outcome: str
    failure_reason: str
    is_simulated: bool
    created_at: str
    updated_at: str
    transcript: Optional[CallTranscriptOut] = None


class NegotiationSessionOut(BaseModel):
    id: str
    negotiation_id: str
    mode: str
    status: str
    total_suppliers: int
    completed_calls: int
    failed_calls: int
    offers_collected: int
    created_at: str
    updated_at: str
    calls: List[CallRecordOut] = Field(default_factory=list)


class EvidenceOut(BaseModel):
    id: str
    negotiation_id: str
    offer_id: Optional[str] = None
    call_id: Optional[str] = None
    field_name: str
    stated_value: str
    verification_status: str
    verification_method: str
    verification_notes: str
    created_at: str


class RecommendationOut(BaseModel):
    id: Optional[str] = None
    negotiation_id: str
    recommendation: Optional[Dict[str, Any]] = None
    recommended_supplier: Optional[str] = ""
    final_price: Optional[float] = 0.0
    total_cost: Optional[float] = 0.0
    currency: Optional[str] = "INR"
    discount_achieved: Optional[float] = 0.0
    baseline_savings: Optional[float] = 0.0
    baseline_reference: Optional[str] = ""
    delivery_days: Optional[int] = 0
    warranty_terms: Optional[str] = ""
    payment_terms: Optional[str] = ""
    score: float = 0.0
    score_breakdown: Dict[str, Any] = Field(default_factory=dict)
    reasons: List[str] = Field(default_factory=list)
    pros_cons: Dict[str, List[str]] = Field(default_factory=dict)
    next_best_offer: Optional[Dict[str, Any]] = None
    missing_uncertain_info: List[str] = Field(default_factory=list)
    offers_compared: int = 0
    note: str = ""
    ranked_offers: List[Dict[str, Any]] = Field(default_factory=list)
    human_approval_status: str = "PENDING"
    approval_notes: Optional[str] = ""
    approval_timestamp: Optional[str] = ""
    message: Optional[str] = None


class ApprovalActionRequest(BaseModel):
    action: Literal["approve", "reject"]
    notes: Optional[str] = Field(default="", max_length=1000)


class NegotiationOut(NegotiationRequestIn):
    id: str
    created_at: str
    updated_at: Optional[str] = None
    status: str = "READY"
    human_approval_required: bool = True
    offers: List[OfferOut] = Field(default_factory=list)
    suppliers: List[SupplierOut] = Field(default_factory=list)
    sessions: List[NegotiationSessionOut] = Field(default_factory=list)
    recommendation: Optional[RecommendationOut] = None


class SettingsStatusOut(BaseModel):
    app_name: str
    app_version: str
    environment: str
    database_url: str
    database_type: str
    telephony_provider: str
    twilio_configured: bool
    twilio_phone_number: str
    webhook_base_url: str
    ai_configured: bool
    ai_provider: str
    supported_languages: List[str]
    default_mode: str
    notice: str
