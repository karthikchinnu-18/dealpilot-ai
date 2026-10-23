from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..config import settings
from ..database import get_db
from ..models import PurchaseRequest, Supplier
from ..schemas import SettingsStatusOut, TelephonyConfigUpdate, TestCallRequest
from ..services.telephony_service import telephony_service

router = APIRouter(prefix="/api/settings", tags=["settings"])

@router.get("/status", response_model=SettingsStatusOut)
def get_settings_status():
    db_type = "PostgreSQL" if "postgres" in settings.database_url else "SQLite (Local File Persistence)"
    ai_provider = "Configured" if settings.is_ai_configured else "Rule-based Built-in NLP (Active)"

    return SettingsStatusOut(
        app_name=settings.app_name,
        app_version=settings.app_version,
        environment=settings.environment,
        database_url=settings.database_url.split("@")[-1],  # redact credentials
        database_type=db_type,
        telephony_provider=settings.telephony_provider,
        twilio_configured=settings.is_twilio_configured,
        twilio_phone_number=settings.twilio_phone_number if settings.is_twilio_configured else "Not Configured",
        webhook_base_url=settings.webhook_base_url or "Not set",
        ai_configured=settings.is_ai_configured,
        ai_provider=ai_provider,
        supported_languages=[
            "English",
            "Kannada (ಕನ್ನಡ)",
            "Hindi (हिन्दी)",
            "Tamil (தமிழ்)",
            "Telugu (తెలుగు)",
            "Malayalam (മലയാളം)",
        ],
        default_mode=settings.default_calling_mode,
        notice="Human approval is mandatory before any purchasing or binding financial commitment.",
    )

@router.get("/telephony")
def get_telephony_settings():
    is_ready, reason = telephony_service.is_configured()
    masked_sid = ""
    if settings.twilio_account_sid:
        sid = settings.twilio_account_sid
        masked_sid = sid[:6] + "..." + sid[-4:] if len(sid) > 10 else "***"
    return {
        "configured": is_ready,
        "reason": reason,
        "twilio_account_sid": masked_sid,
        "twilio_phone_number": settings.twilio_phone_number,
        "webhook_base_url": settings.webhook_base_url,
    }

@router.post("/telephony")
async def update_telephony_settings(payload: TelephonyConfigUpdate):
    sid = payload.twilio_account_sid.strip()
    token = payload.twilio_auth_token.strip()
    phone = payload.twilio_phone_number.strip()
    webhook = payload.webhook_base_url.strip()

    # If SID and token provided, verify them against Twilio API
    if sid and token and not sid.startswith("your_"):
        is_valid, msg = await telephony_service.verify_credentials(sid, token)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Twilio validation failed: {msg}",
            )
    else:
        msg = "Saved offline configuration."

    settings.save_telephony(
        account_sid=sid,
        auth_token=token if token else settings.twilio_auth_token,
        phone_number=phone,
        webhook_base_url=webhook,
    )
    telephony_service.reload_credentials()

    return {
        "success": True,
        "message": f"Telephony credentials updated. {msg}",
        "twilio_configured": settings.is_twilio_configured,
        "twilio_phone_number": settings.twilio_phone_number,
        "webhook_base_url": settings.webhook_base_url,
    }

@router.post("/test-call")
async def make_test_call(payload: TestCallRequest):
    is_ready, reason = telephony_service.is_configured()
    if not is_ready:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Real calling is disabled: {reason} Please configure your Twilio Account SID, Auth Token, and Twilio Phone Number in Settings first.",
        )

    is_valid, formatted_phone, err = telephony_service.validate_phone_number(
        payload.country_code, payload.phone_number
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid phone number: {err}",
        )

    webhook_base = settings.webhook_base_url.rstrip("/")
    if not webhook_base or "localhost" in webhook_base or "127.0.0.1" in webhook_base:
        # Note: Twilio needs a public HTTPS URL (ngrok or domain) for callbacks
        pass

    test_voice_url = f"{webhook_base}/api/telephony/twilio/test-twiml"
    status_url = f"{webhook_base}/api/telephony/twilio/status"

    try:
        res = await telephony_service.initiate_outbound_call(
            to_phone=formatted_phone,
            webhook_url=test_voice_url,
            status_callback_url=status_url,
        )
        return {
            "success": True,
            "call_sid": res.get("sid", ""),
            "to_phone": formatted_phone,
            "message": f"Test outbound call placed to {formatted_phone}! Your phone should ring shortly.",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to place Twilio test call: {str(e)}",
        )

@router.post("/reset-demo")
def reset_demo(db: Session = Depends(get_db)):
    """
    Seeds a clean, realistic demonstration negotiation with sample fictional suppliers.
    """
    # Create sample request
    req = PurchaseRequest(
        product="Premium Screen-Printed Cotton T-Shirts",
        specifications="180 GSM, 100% bio-washed cotton, front 3-color screen print, assorted sizes (M: 40, L: 40, XL: 20)",
        quantity=100,
        unit="units",
        budget=12500.0,
        currency="INR",
        target_price=10500.0,
        max_authorized_price=12500.0,
        deadline="Within 5 days",
        quality_requirements="180 GSM bio-washed combed cotton, non-fading discharge screen print",
        warranty_requirements="Replacement for print peeling or stitching defects",
        payment_terms="Net 15 days or 50% advance / 50% on verified delivery",
        delivery_location="Koramangala, Bengaluru, Karnataka 560034",
        priorities=["best_value", "fastest_delivery"],
        max_negotiation_rounds=3,
        notes="Fictional sample dataset prepared for live hackathon demonstration.",
        status="READY",
    )
    db.add(req)
    db.flush()

    # Add 4 diverse fictional suppliers
    suppliers_data = [
        {
            "business_name": "Bharat Textiles & Print Works",
            "country_code": "+91",
            "phone_number": "9845012345",
            "contact_person": "Ramesh Gupta",
            "preferred_language": "Hindi",
            "notes": "Large volume screen-printing facility in Surat/Bengaluru.",
        },
        {
            "business_name": "Bengaluru Merchandising Hub",
            "country_code": "+91",
            "phone_number": "9886067890",
            "contact_person": "Suresh Gowda",
            "preferred_language": "Kannada",
            "notes": "Local textile vendor in Chickpet, Bengaluru.",
        },
        {
            "business_name": "Apex Industrial Supplies",
            "country_code": "+91",
            "phone_number": "9900054321",
            "contact_person": "Anita Sharma",
            "preferred_language": "English",
            "notes": "Corporate apparel manufacturer with ISO certification.",
        },
        {
            "business_name": "Metro Print Labs",
            "country_code": "+91",
            "phone_number": "9820011223",
            "contact_person": "Vikram Patel",
            "preferred_language": "English",
            "notes": "Commercial printer (Simulates busy/no-answer scenario).",
        },
    ]

    for s_data in suppliers_data:
        supp = Supplier(
            negotiation_id=req.id,
            business_name=s_data["business_name"],
            country_code=s_data["country_code"],
            phone_number=s_data["phone_number"],
            contact_person=s_data["contact_person"],
            preferred_language=s_data["preferred_language"],
            notes=s_data["notes"],
            is_valid_phone=True,
            permission_status="authorized",
        )
        db.add(supp)

    db.commit()
    db.refresh(req)
    return {
        "message": "Demo data successfully loaded.",
        "negotiation_id": req.id,
        "product": req.product,
        "suppliers_count": len(suppliers_data),
    }
