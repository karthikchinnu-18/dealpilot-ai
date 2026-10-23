import pytest
from app.services.strategy_engine import NegotiationStrategyEngine
from app.services.scoring_engine import ScoringEngine

def test_strategy_engine_budget_enforcement():
    # Supplier quote exceeds budget
    budget = 10000.0
    supplier_quote = 15000.0
    
    # Round 1 counteroffer
    decision1 = NegotiationStrategyEngine.evaluate_round(
        budget=budget,
        target_price=8000.0,
        max_authorized_price=budget,
        quantity=100,
        current_supplier_quote=supplier_quote,
        current_round=1,
        max_rounds=3,
        delivery_days_quoted=3,
        max_delivery_days_allowed=5,
    )
    assert decision1.action == "counteroffer"
    assert decision1.suggested_amount <= budget
    assert decision1.suggested_amount == 8000.0

    # Final round where supplier is still over budget
    decision_final = NegotiationStrategyEngine.evaluate_round(
        budget=budget,
        target_price=8000.0,
        max_authorized_price=budget,
        quantity=100,
        current_supplier_quote=13000.0,
        current_round=3,
        max_rounds=3,
        delivery_days_quoted=3,
        max_delivery_days_allowed=5,
    )
    assert decision_final.action == "reject"
    assert decision_final.meets_mandatory_requirements is False
    assert "budget" in decision_final.rationale.lower()

def test_strategy_engine_multilingual_formatting():
    kannada_dec = NegotiationStrategyEngine.evaluate_round(
        budget=12000.0,
        target_price=10000.0,
        max_authorized_price=12000.0,
        quantity=50,
        current_supplier_quote=14000.0,
        current_round=1,
        max_rounds=3,
        delivery_days_quoted=4,
        max_delivery_days_allowed=7,
        language="Kannada",
    )
    assert "ಬಜೆಟ್" in kannada_dec.counteroffer_text or "₹10,000" in kannada_dec.counteroffer_text

    hindi_dec = NegotiationStrategyEngine.evaluate_round(
        budget=12000.0,
        target_price=10000.0,
        max_authorized_price=12000.0,
        quantity=50,
        current_supplier_quote=14000.0,
        current_round=1,
        max_rounds=3,
        delivery_days_quoted=4,
        max_delivery_days_allowed=7,
        language="Hindi",
    )
    assert "बजट" in hindi_dec.counteroffer_text or "₹10,000" in hindi_dec.counteroffer_text

def test_scoring_engine_mandatory_constraint_failure():
    # If all offers exceed budget or delivery, return No Suitable Offer
    budget = 10000.0
    offers = [
        {
            "id": "1",
            "business_name": "Overpriced Vendor",
            "total_price": 14000.0,
            "delivery_days": 3,
            "evidence_status": "verified",
        },
        {
            "id": "2",
            "business_name": "Too Slow Vendor",
            "total_price": 9000.0,
            "delivery_days": 15,  # Exceeds max 5 days
            "evidence_status": "verified",
        },
    ]

    res = ScoringEngine.evaluate_offers(
        offers=offers,
        budget=budget,
        deadline="Within 5 days",
        priorities=["best_value"],
        max_delivery_days=5,
    )
    assert res.recommendation is None
    assert "No suitable offer found" in res.message

def test_scoring_engine_valid_selection():
    budget = 12000.0
    offers = [
        {
            "id": "1",
            "business_name": "Vendor A",
            "total_price": 10500.0,
            "initial_offer": 13000.0,
            "delivery_days": 3,
            "evidence_status": "Supplier Stated",
            "warranty": "1-year warranty",
        },
        {
            "id": "2",
            "business_name": "Vendor B",
            "total_price": 11800.0,
            "initial_offer": 12500.0,
            "delivery_days": 5,
            "evidence_status": "unverified",
        },
    ]

    res = ScoringEngine.evaluate_offers(
        offers=offers,
        budget=budget,
        deadline="Within 7 days",
        priorities=["best_value"],
        max_delivery_days=7,
    )
    assert res.recommendation is not None
    assert res.recommended_supplier == "Vendor A"
    assert res.discount_achieved == 2500.0
    assert res.score > 0
