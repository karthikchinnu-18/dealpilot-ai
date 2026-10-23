import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    return TestClient(app)

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_create_and_get_negotiation(client):
    payload = {
        "product": "Industrial Safety Helmets",
        "quantity": 50,
        "budget": 25000.0,
        "deadline": "Within 4 days",
        "priorities": ["best_value"],
        "specifications": "EN397 certified, ratchet adjustment, white color",
        "target_price": 20000.0,
        "max_authorized_price": 25000.0,
    }
    res = client.post("/api/negotiations", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["product"] == "Industrial Safety Helmets"
    assert data["budget"] == 25000.0
    neg_id = data["id"]

    # Retrieve
    get_res = client.get(f"/api/negotiations/{neg_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == neg_id

def test_add_and_list_suppliers(client):
    # Create request first
    neg_res = client.post("/api/negotiations", json={
        "product": "Safety Vests",
        "quantity": 100,
        "budget": 15000.0,
        "deadline": "Within 5 days",
    })
    neg_id = neg_res.json()["id"]

    # Add Supplier 1
    supp1 = {
        "business_name": "Kavach Safety Equipment",
        "country_code": "+91",
        "phone_number": "9876543210",
        "contact_person": "Vikas Rao",
        "preferred_language": "Kannada",
    }
    res1 = client.post(f"/api/negotiations/{neg_id}/suppliers", json=supp1)
    assert res1.status_code == 201
    assert res1.json()["business_name"] == "Kavach Safety Equipment"
    assert res1.json()["is_valid_phone"] is True

    # Add Supplier 2
    supp2 = {
        "business_name": "Metro Industrial Gear",
        "country_code": "+91",
        "phone_number": "9123456789",
        "contact_person": "Alok Kumar",
        "preferred_language": "Hindi",
    }
    res2 = client.post(f"/api/negotiations/{neg_id}/suppliers", json=supp2)
    assert res2.status_code == 201

    # List suppliers
    list_res = client.get(f"/api/negotiations/{neg_id}/suppliers")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 2

def test_phone_validation(client):
    valid_res = client.post("/api/suppliers/validate-phone", json={
        "country_code": "+91",
        "phone_number": "9876543210",
    })
    assert valid_res.status_code == 200
    assert valid_res.json()["is_valid"] is True
    assert valid_res.json()["formatted_e164"] == "+919876543210"

    invalid_res = client.post("/api/suppliers/validate-phone", json={
        "country_code": "+91",
        "phone_number": "12",  # Too short
    })
    assert invalid_res.status_code == 200
    assert invalid_res.json()["is_valid"] is False
