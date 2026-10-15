from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="DealPilot AI",
    description="Hackathon starter for comparing offers. Real phone calling is not connected yet.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class NegotiationRequestIn(BaseModel):
    product: str = Field(min_length=2, max_length=150)
    quantity: int = Field(gt=0, le=100000)
    budget: float = Field(gt=0, le=100000000)
    deadline: str = Field(min_length=1, max_length=100)
    priorities: list[Literal["lowest_price", "fastest_delivery", "best_value"]] = Field(
        default_factory=lambda: ["best_value"], max_length=3
    )

class OfferIn(BaseModel):
    business_name: str = Field(min_length=2, max_length=120)
    total_price: float = Field(gt=0, le=100000000)
    delivery_days: int = Field(ge=0, le=3650)
    terms: str = Field(default="", max_length=1000)
    evidence_note: str = Field(min_length=3, max_length=1000)
    evidence_status: Literal["verified", "unverified", "demo"] = "unverified"
    source_type: Literal["phone", "email", "website", "demo", "other"] = "other"

class OfferOut(OfferIn):
    id: str
    created_at: str

class NegotiationOut(NegotiationRequestIn):
    id: str
    created_at: str
    offers: list[OfferOut] = Field(default_factory=list)

negotiations: dict[str, dict] = {}

@app.get("/")
def home():
    return {"app": "DealPilot AI", "status": "running", "version": "0.1.0",
            "note": "Starter prototype; real outbound calling is not connected."}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/api/negotiations", response_model=NegotiationOut)
def create_negotiation(payload: NegotiationRequestIn):
    record = payload.model_dump()
    record.update({"id": str(uuid4()), "created_at": datetime.now(timezone.utc).isoformat(), "offers": []})
    negotiations[record["id"]] = record
    return record

@app.get("/api/negotiations", response_model=list[NegotiationOut])
def list_negotiations():
    return list(negotiations.values())

@app.get("/api/negotiations/{negotiation_id}", response_model=NegotiationOut)
def get_negotiation(negotiation_id: str):
    record = negotiations.get(negotiation_id)
    if not record:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    return record

@app.post("/api/negotiations/{negotiation_id}/offers", response_model=OfferOut)
def add_offer(negotiation_id: str, payload: OfferIn):
    record = negotiations.get(negotiation_id)
    if not record:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    offer = payload.model_dump()
    offer.update({"id": str(uuid4()), "created_at": datetime.now(timezone.utc).isoformat()})
    record["offers"].append(offer)
    return offer

@app.get("/api/negotiations/{negotiation_id}/recommendation")
def recommendation(negotiation_id: str):
    record = negotiations.get(negotiation_id)
    if not record:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    offers = record["offers"]
    if not offers:
        return {"negotiation_id": negotiation_id, "recommendation": None,
                "message": "No offers yet. Add offers with their source and evidence notes.", "offers_compared": 0}

    priorities = record["priorities"]
    budget = record["budget"]

    def score(offer):
        price_score = max(0.0, 1.0 - offer["total_price"] / max(budget, offer["total_price"]))
        delivery_score = 1.0 / (1.0 + offer["delivery_days"])
        evidence_score = {"verified": 1.0, "unverified": 0.4, "demo": 0.2}[offer["evidence_status"]]
        if "lowest_price" in priorities:
            value = price_score
        elif "fastest_delivery" in priorities:
            value = delivery_score
        else:
            value = (price_score * 0.55) + (delivery_score * 0.45)
        return round((value * 0.8 + evidence_score * 0.2) * 100, 1)

    ranked = sorted(offers, key=score, reverse=True)
    best = ranked[0]
    reasons = [
        f"Quoted total: {best['total_price']:.2f}",
        f"Delivery estimate: {best['delivery_days']} day(s)",
        f"Evidence status: {best['evidence_status']}",
        f"Source type: {best['source_type']}",
    ]
    if best["total_price"] > budget:
        reasons.append("Warning: this offer exceeds the user's budget.")
    return {
        "negotiation_id": negotiation_id,
        "recommendation": best,
        "score": score(best),
        "reasons": reasons,
        "offers_compared": len(offers),
        "note": "Heuristic recommendation, not a guarantee. Verify final price, taxes, delivery, payment terms, and availability before committing.",
        "ranked_offers": [{"business_name": offer["business_name"], "score": score(offer)} for offer in ranked],
    }
