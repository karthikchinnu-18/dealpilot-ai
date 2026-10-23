import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine
from app.services.extraction_engine import OfferExtractionEngine

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    return TestClient(app)

def test_real_calling_blocked_when_unconfigured(client):
    # Create request and supplier
    neg_res = client.post("/api/negotiations", json={
        "product": "Safety Helmets",
        "quantity": 20,
        "budget": 10000.0,
        "deadline": "Within 3 days",
    })
    neg_id = neg_res.json()["id"]

    client.post(f"/api/negotiations/{neg_id}/suppliers", json={
        "business_name": "Test Supplier",
        "country_code": "+91",
        "phone_number": "9876543210",
    })

    # Attempt real call without Twilio configured
    call_res = client.post(f"/api/negotiations/{neg_id}/calls/start", json={
        "mode": "real",
        "user_confirmed": True,
    })
    # Must fail with 400 and explicit reason
    assert call_res.status_code == 400
    assert "Real calling is disabled" in call_res.json()["detail"]

def test_simulated_calling_workflow(client):
    neg_res = client.post("/api/negotiations", json={
        "product": "Printed T-Shirts",
        "quantity": 100,
        "budget": 12000.0,
        "deadline": "Within 5 days",
        "priorities": ["best_value"],
    })
    neg_id = neg_res.json()["id"]

    # Add 2 suppliers
    client.post(f"/api/negotiations/{neg_id}/suppliers", json={
        "business_name": "Bharat Textiles & Print Works",
        "country_code": "+91",
        "phone_number": "9845012345",
        "preferred_language": "Hindi",
    })
    client.post(f"/api/negotiations/{neg_id}/suppliers", json={
        "business_name": "Bengaluru Merchandising Hub",
        "country_code": "+91",
        "phone_number": "9886067890",
        "preferred_language": "Kannada",
    })

    # Start simulated calls
    start_res = client.post(f"/api/negotiations/{neg_id}/calls/start", json={
        "mode": "simulated",
        "user_confirmed": True,
    })
    assert start_res.status_code == 200
    session_data = start_res.json()
    assert session_data["status"] == "COMPLETED"
    assert session_data["total_suppliers"] == 2
    assert session_data["offers_collected"] > 0

    # Verify calls list
    calls_res = client.get(f"/api/negotiations/{neg_id}/calls")
    assert calls_res.status_code == 200
    calls = calls_res.json()
    assert len(calls) == 2
    assert calls[0]["transcript"] is not None

    # Verify recommendation was computed
    rec_res = client.get(f"/api/negotiations/{neg_id}/recommendation")
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert rec_data["recommended_supplier"] != ""
    assert rec_data["score"] > 0
    assert rec_data["human_approval_status"] == "PENDING"

    # Test Human Approval
    appr_res = client.post(f"/api/negotiations/{neg_id}/approval", json={
        "action": "approve",
        "notes": "Terms and discount approved by operations lead.",
    })
    assert appr_res.status_code == 200
    assert appr_res.json()["human_approval_status"] == "APPROVED"

def test_offer_extraction_engine():
    turns = [
        {
            "round": 1,
            "speaker": "supplier",
            "text_original": "For 100 pieces the quote is ₹12,500, delivery in 4 days.",
            "text_translated": "For 100 pieces the quote is ₹12,500, delivery in 4 days.",
        },
        {
            "round": 2,
            "speaker": "supplier",
            "text_original": "Okay, we can do final deal at ₹10,800 with 1-year warranty.",
            "text_translated": "Okay, we can do final deal at ₹10,800 with 1-year warranty.",
        },
    ]

    extracted = OfferExtractionEngine.extract_from_transcript(
        turns=turns,
        business_name="Test Merchant",
        requested_quantity=100,
        is_simulated=True,
    )

    assert extracted.initial_offer == 12500.0
    assert extracted.final_explicit_offer == 10800.0
    assert extracted.total_price == 10800.0
    assert extracted.unit_price == 108.0
    assert extracted.delivery_days == 4
    assert extracted.bulk_discount == 1700.0
    assert extracted.evidence_status == "Simulated"


def test_supplier_auto_call_on_create(client):
    neg_res = client.post("/api/negotiations", json={
        "product": "Safety Boots",
        "quantity": 50,
        "budget": 25000.0,
        "deadline": "Within 4 days",
    })
    neg_id = neg_res.json()["id"]

    # Add supplier with auto_call = True
    supp_res = client.post(f"/api/negotiations/{neg_id}/suppliers", json={
        "business_name": "Rapid Safety Gear",
        "country_code": "+91",
        "phone_number": "9812345678",
        "auto_call": True,
        "calling_mode": "simulated",
    })
    assert supp_res.status_code == 201
    supp_data = supp_res.json()
    assert supp_data["business_name"] == "Rapid Safety Gear"

    # Verify that the call was placed immediately and recommendation updated
    rec_res = client.get(f"/api/negotiations/{neg_id}/recommendation")
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert rec_data["recommended_supplier"] == "Rapid Safety Gear"
    assert rec_data["final_price"] > 0


def test_call_single_supplier_endpoint(client):
    neg_res = client.post("/api/negotiations", json={
        "product": "Office Chairs",
        "quantity": 10,
        "budget": 30000.0,
        "deadline": "Within 7 days",
    })
    neg_id = neg_res.json()["id"]

    supp_res = client.post(f"/api/negotiations/{neg_id}/suppliers", json={
        "business_name": "ErgoWorks Direct",
        "country_code": "+91",
        "phone_number": "9876501234",
    })
    supp_id = supp_res.json()["id"]

    # Call this specific supplier
    call_res = client.post(f"/api/negotiations/{neg_id}/suppliers/{supp_id}/call", json={
        "mode": "simulated",
        "user_confirmed": True,
    })
    assert call_res.status_code == 200
    call_data = call_res.json()
    assert call_data["success"] is True
    assert call_data["recommended_supplier"] == "ErgoWorks Direct"


def test_telephony_settings_endpoints(client):
    # Test getting telephony settings
    get_res = client.get("/api/settings/telephony")
    assert get_res.status_code == 200
    data = get_res.json()
    assert "configured" in data

    # Test updating offline telephony settings
    update_res = client.post("/api/settings/telephony", json={
        "twilio_account_sid": "",
        "twilio_auth_token": "",
        "twilio_phone_number": "",
        "webhook_base_url": "https://test.ngrok.app",
    })
    assert update_res.status_code == 200
    assert update_res.json()["success"] is True


def test_twilio_webhooks_flow(client):
    neg_res = client.post("/api/negotiations", json={
        "product": "Packaging Boxes",
        "quantity": 500,
        "budget": 15000.0,
        "deadline": "Within 3 days",
    })
    neg_id = neg_res.json()["id"]

    # Test voice webhook
    voice_res = client.post(f"/api/telephony/twilio/voice?negotiation_id={neg_id}", data={
        "CallSid": "CA_test_voice_sid_123",
    })
    assert voice_res.status_code == 200
    assert "<Say" in voice_res.text

    # Test test-twiml endpoint
    test_twiml_res = client.get("/api/telephony/twilio/test-twiml")
    assert test_twiml_res.status_code == 200
    assert "DealPilot AI calling your phone" in test_twiml_res.text
