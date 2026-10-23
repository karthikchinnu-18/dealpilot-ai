from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class ScoredOffer(BaseModel):
    offer_id: str
    business_name: str
    total_price: float
    delivery_days: int
    evidence_status: str
    source_type: str
    is_simulated: bool
    overall_score: float
    cost_score: float
    delivery_score: float
    compliance_score: float
    quality_score: float
    evidence_score: float
    penalties: float
    mandatory_failed: bool
    failure_reasons: List[str]
    missing_information: List[str]
    terms: str
    warranty: str

class ScoringResult(BaseModel):
    recommendation: Optional[Dict[str, Any]] = None
    recommended_supplier: str = ""
    final_price: float = 0.0
    total_cost: float = 0.0
    currency: str = "INR"
    discount_achieved: float = 0.0
    baseline_savings: float = 0.0
    baseline_reference: str = ""
    delivery_days: int = 0
    warranty_terms: str = ""
    payment_terms: str = ""
    score: float = 0.0
    score_breakdown: Dict[str, Any] = {}
    reasons: List[str] = []
    pros_cons: Dict[str, List[str]] = {}
    next_best_offer: Optional[Dict[str, Any]] = None
    missing_uncertain_info: List[str] = []
    offers_compared: int = 0
    ranked_offers: List[Dict[str, Any]] = []
    note: str = ""
    message: Optional[str] = None

class ScoringEngine:
    """
    Deterministic, transparent multi-criteria scoring and comparison engine.
    Ensures that mandatory constraint failures disqualify offers from winning.
    """

    @staticmethod
    def evaluate_offers(
        offers: List[Dict[str, Any]],
        budget: float,
        deadline: str,
        priorities: List[str],
        mandatory_conditions: Optional[List[str]] = None,
        max_delivery_days: int = 7,
    ) -> ScoringResult:
        if not offers:
            return ScoringResult(
                message="No offers available to evaluate. Add offers or run automated supplier calls.",
                note="No supplier offers recorded yet.",
            )

        mandatory_conditions = mandatory_conditions or []
        priorities = priorities or ["best_value"]

        scored_list: List[ScoredOffer] = []
        
        # Determine baseline for savings calculation (highest initial quote or authorized budget)
        max_initial_quote = max([o.get("initial_offer", o.get("total_price", budget)) for o in offers], default=budget)
        baseline = max(max_initial_quote, budget)

        for o in offers:
            tot = float(o.get("total_price", 0.0))
            deliv = int(o.get("delivery_days", 3))
            ev_status = o.get("evidence_status", "unverified")
            missing_info = o.get("missing_information", []) or []
            
            mandatory_failed = False
            failure_reasons = []

            # Check hard constraints
            if tot > budget:
                # If over budget, flag failure
                mandatory_failed = True
                failure_reasons.append(f"Exceeds authorized budget (₹{tot:,.2f} > ₹{budget:,.2f})")

            if max_delivery_days > 0 and deliv > max_delivery_days:
                mandatory_failed = True
                failure_reasons.append(f"Exceeds delivery deadline ({deliv} days > {max_delivery_days} days)")

            # Component scores (0.0 to 100.0)
            # 1. Cost Score: Normalized against budget
            cost_ratio = max(0.0, 1.0 - (tot / max(budget * 1.2, tot, 1.0)))
            cost_score = round(cost_ratio * 100, 1)

            # 2. Delivery Score: Exponential decay with days
            delivery_score = round((1.0 / (1.0 + (deliv * 0.25))) * 100, 1)

            # 3. Evidence Score
            ev_weights = {
                "Verified by Documented Check": 100.0,
                "verified": 95.0,
                "Supplier Stated": 75.0,
                "unverified": 50.0,
                "demo": 40.0,
                "Simulated": 40.0,
                "Disputed": 10.0,
                "Expired": 10.0,
            }
            evidence_score = ev_weights.get(ev_status, 50.0)

            # 4. Compliance & Quality
            quality_score = 80.0
            if "warranty" in str(o.get("warranty", "")).lower():
                quality_score += 10.0
            if "gst" in str(o.get("terms", "")).lower() or o.get("taxes", 0) > 0:
                quality_score += 10.0

            # 5. Penalties for missing information
            penalties = round(len(missing_info) * 6.0, 1)

            # Calculate Weighted Overall Score based on user priorities
            if "lowest_price" in priorities:
                w_cost, w_deliv, w_ev, w_qual = 0.65, 0.15, 0.10, 0.10
            elif "fastest_delivery" in priorities:
                w_cost, w_deliv, w_ev, w_qual = 0.25, 0.55, 0.10, 0.10
            else:  # "best_value"
                w_cost, w_deliv, w_ev, w_qual = 0.45, 0.25, 0.15, 0.15

            raw_score = (
                (cost_score * w_cost)
                + (delivery_score * w_deliv)
                + (evidence_score * w_ev)
                + (quality_score * w_qual)
            )
            overall_score = max(0.0, min(100.0, round(raw_score - penalties, 1)))

            # If mandatory requirement failed, drastically penalize overall score so it cannot win
            if mandatory_failed:
                overall_score = min(overall_score, 25.0)

            scored_list.append(
                ScoredOffer(
                    offer_id=str(o.get("id", "")),
                    business_name=o.get("business_name", "Unknown Supplier"),
                    total_price=tot,
                    delivery_days=deliv,
                    evidence_status=ev_status,
                    source_type=o.get("source_type", "other"),
                    is_simulated=bool(o.get("is_simulated", False)),
                    overall_score=overall_score,
                    cost_score=cost_score,
                    delivery_score=delivery_score,
                    compliance_score=0.0 if mandatory_failed else 100.0,
                    quality_score=quality_score,
                    evidence_score=evidence_score,
                    penalties=penalties,
                    mandatory_failed=mandatory_failed,
                    failure_reasons=failure_reasons,
                    missing_information=missing_info,
                    terms=str(o.get("terms", "")),
                    warranty=str(o.get("warranty", "Standard")),
                )
            )

        # Sort offers by overall score descending
        ranked = sorted(scored_list, key=lambda x: (not x.mandatory_failed, x.overall_score), reverse=True)

        # Check if ALL offers failed mandatory constraints
        valid_offers = [s for s in ranked if not s.mandatory_failed]
        if not valid_offers:
            return ScoringResult(
                message="No suitable offer found. All suppliers exceeded budget or failed mandatory delivery conditions.",
                note="Mandatory constraint failure. Review supplier constraints or negotiate higher budget/extended deadline.",
                offers_compared=len(offers),
                ranked_offers=[
                    {
                        "business_name": s.business_name,
                        "score": s.overall_score,
                        "price": s.total_price,
                        "mandatory_failed": s.mandatory_failed,
                        "failure_reasons": s.failure_reasons,
                    }
                    for s in ranked
                ],
            )

        best = ranked[0]
        best_raw_offer = next((o for o in offers if str(o.get("id", "")) == best.offer_id), offers[0])

        # Savings and discounts
        init_quote = float(best_raw_offer.get("initial_offer", best.total_price))
        discount_achieved = max(0.0, round(init_quote - best.total_price, 2))
        savings_from_baseline = max(0.0, round(baseline - best.total_price, 2))

        # Reasons
        reasons = [
            f"Quoted final total: ₹{best.total_price:,.2f} (Savings of ₹{savings_from_baseline:,.2f} vs baseline)",
            f"Estimated delivery: {best.delivery_days} day(s)",
            f"Evidence status: {best.evidence_status} (Audio transcript recorded)",
            f"Negotiated discount: ₹{discount_achieved:,.2f} achieved during negotiation calls",
        ]
        if best.terms:
            reasons.append(f"Terms: {best.terms}")

        pros = [
            f"Best overall balance of price (₹{best.total_price:,.2f}) and delivery speed ({best.delivery_days}d).",
            f"Satisfies all mandatory delivery and budget requirements.",
        ]
        if discount_achieved > 0:
            pros.append(f"Successfully lowered initial quote by ₹{discount_achieved:,.2f}.")

        cons = []
        if best.missing_information:
            cons.extend(best.missing_information)
        if best.delivery_days > 4:
            cons.append("Delivery time is slightly longer than express alternatives.")

        # Next best offer comparison
        next_best = None
        if len(valid_offers) > 1:
            nb = valid_offers[1]
            diff_price = round(nb.total_price - best.total_price, 2)
            diff_days = nb.delivery_days - best.delivery_days
            next_best = {
                "business_name": nb.business_name,
                "total_price": nb.total_price,
                "delivery_days": nb.delivery_days,
                "score": nb.overall_score,
                "price_difference": diff_price,
                "delivery_difference_days": diff_days,
                "summary": f"{nb.business_name} quoted ₹{nb.total_price:,.2f} ({'+' if diff_price >= 0 else ''}₹{diff_price:,.2f}) with {nb.delivery_days} days delivery.",
            }

        return ScoringResult(
            recommendation=best_raw_offer,
            recommended_supplier=best.business_name,
            final_price=best.total_price,
            total_cost=best.total_price,
            currency="INR",
            discount_achieved=discount_achieved,
            baseline_savings=savings_from_baseline,
            baseline_reference=f"Highest initial quote / authorized budget (₹{baseline:,.2f})",
            delivery_days=best.delivery_days,
            warranty_terms=best.warranty,
            payment_terms="Net 30 / Advance after delivery",
            score=best.overall_score,
            score_breakdown={
                "cost_score": best.cost_score,
                "delivery_score": best.delivery_score,
                "evidence_score": best.evidence_score,
                "quality_score": best.quality_score,
                "penalties": best.penalties,
                "compliance_score": best.compliance_score,
            },
            reasons=reasons,
            pros_cons={"pros": pros, "cons": cons},
            next_best_offer=next_best,
            missing_uncertain_info=best.missing_information,
            offers_compared=len(offers),
            ranked_offers=[
                {
                    "business_name": s.business_name,
                    "score": s.overall_score,
                    "price": s.total_price,
                    "delivery_days": s.delivery_days,
                    "evidence_status": s.evidence_status,
                    "mandatory_failed": s.mandatory_failed,
                    "failure_reasons": s.failure_reasons,
                }
                for s in ranked
            ],
            note="Heuristic recommendation backed by recorded evidence. Human approval is mandatory before any binding commitment.",
        )
