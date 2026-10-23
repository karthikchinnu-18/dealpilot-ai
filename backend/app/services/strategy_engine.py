from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class CounterofferDecision(BaseModel):
    action: str  # "counteroffer", "accept", "reject", "clarify"
    suggested_amount: float
    unit_price: float
    rationale: str
    counteroffer_text: str
    max_authorized_amount: float
    meets_mandatory_requirements: bool
    mandatory_violations: List[str]
    remaining_rounds: int
    requires_human_review: bool

class NegotiationStrategyEngine:
    """
    Transparent, deterministic negotiation strategy engine.
    Enforces user budget and constraint limits in code, independent of generative AI.
    """

    @staticmethod
    def evaluate_round(
        budget: float,
        target_price: float,
        max_authorized_price: float,
        quantity: int,
        current_supplier_quote: float,
        current_round: int,
        max_rounds: int,
        delivery_days_quoted: int,
        max_delivery_days_allowed: int,
        mandatory_conditions: Optional[List[str]] = None,
        supplier_terms: str = "",
        best_competing_quote: Optional[float] = None,
        language: str = "English",
    ) -> CounterofferDecision:
        # Defaults
        mandatory_conditions = mandatory_conditions or []
        effective_max = max_authorized_price if max_authorized_price > 0 else budget
        effective_target = target_price if target_price > 0 else (effective_max * 0.82)
        
        mandatory_violations: List[str] = []
        
        # Check delivery constraint
        if max_delivery_days_allowed > 0 and delivery_days_quoted > max_delivery_days_allowed:
            mandatory_violations.append(
                f"Quoted delivery time ({delivery_days_quoted} days) exceeds maximum deadline ({max_delivery_days_allowed} days)"
            )
            
        remaining_rounds = max(0, max_rounds - current_round)
        meets_mandatory = len(mandatory_violations) == 0

        # Safety Check: If supplier quote is already at or below target price
        if current_supplier_quote <= effective_target and meets_mandatory:
            return CounterofferDecision(
                action="accept",
                suggested_amount=round(current_supplier_quote, 2),
                unit_price=round(current_supplier_quote / max(1, quantity), 2),
                rationale="Quoted price is at or below the target price and satisfies all mandatory requirements.",
                counteroffer_text=NegotiationStrategyEngine._format_acceptance_text(
                    current_supplier_quote, quantity, language
                ),
                max_authorized_amount=round(effective_max, 2),
                meets_mandatory_requirements=True,
                mandatory_violations=[],
                remaining_rounds=remaining_rounds,
                requires_human_review=False,
            )

        # If supplier quote is over budget and no rounds remaining
        if remaining_rounds <= 0:
            if current_supplier_quote > effective_max:
                return CounterofferDecision(
                    action="reject",
                    suggested_amount=round(effective_max, 2),
                    unit_price=round(effective_max / max(1, quantity), 2),
                    rationale=f"Supplier's final quote (₹{current_supplier_quote:,.2f}) exceeds the authorized budget limit (₹{effective_max:,.2f}) after {current_round} rounds.",
                    counteroffer_text=NegotiationStrategyEngine._format_rejection_text(
                        effective_max, language
                    ),
                    max_authorized_amount=round(effective_max, 2),
                    meets_mandatory_requirements=False,
                    mandatory_violations=["Exceeds maximum authorized budget"],
                    remaining_rounds=0,
                    requires_human_review=True,
                )
            else:
                # Within budget on last round
                return CounterofferDecision(
                    action="accept",
                    suggested_amount=round(current_supplier_quote, 2),
                    unit_price=round(current_supplier_quote / max(1, quantity), 2),
                    rationale=f"Supplier quote is within authorized budget (₹{effective_max:,.2f}) on final round.",
                    counteroffer_text=NegotiationStrategyEngine._format_acceptance_text(
                        current_supplier_quote, quantity, language
                    ),
                    max_authorized_amount=round(effective_max, 2),
                    meets_mandatory_requirements=meets_mandatory,
                    mandatory_violations=mandatory_violations,
                    remaining_rounds=0,
                    requires_human_review=not meets_mandatory,
                )

        # Dynamic Counteroffer calculation across rounds:
        # In Round 1: Offer initial target price
        # In Round 2: If supplier dropped, move 40% towards their new price, capped strictly at effective_max
        # In Round 3+: Best and final counteroffer at min(supplier * 0.95, effective_max)
        if current_round == 1:
            counter_amount = effective_target
            reason = f"Initial counteroffer based on target budget for {quantity} units."
        elif current_round == 2:
            gap = current_supplier_quote - effective_target
            counter_amount = min(effective_target + (gap * 0.40), effective_max)
            reason = "Progressive counteroffer meeting supplier midway, within authorized budget."
        else:
            counter_amount = min(current_supplier_quote * 0.94, effective_max)
            reason = "Final counteroffer before concluding negotiations."

        # Hard guardrail: Never exceed authorized budget
        counter_amount = min(counter_amount, effective_max)
        counter_amount = round(counter_amount, 2)
        unit_price = round(counter_amount / max(1, quantity), 2)

        counter_text = NegotiationStrategyEngine._format_counteroffer_text(
            counter_amount, quantity, unit_price, best_competing_quote, language
        )

        return CounterofferDecision(
            action="counteroffer",
            suggested_amount=counter_amount,
            unit_price=unit_price,
            rationale=reason,
            counteroffer_text=counter_text,
            max_authorized_amount=round(effective_max, 2),
            meets_mandatory_requirements=meets_mandatory,
            mandatory_violations=mandatory_violations,
            remaining_rounds=remaining_rounds,
            requires_human_review=not meets_mandatory,
        )

    @staticmethod
    def _format_counteroffer_text(
        amount: float,
        quantity: int,
        unit_price: float,
        competing: Optional[float],
        language: str,
    ) -> str:
        lang = language.lower()
        if "kannada" in lang:
            return f"ಧನ್ಯವಾದಗಳು. ನಮ್ಮ ಬಜೆಟ್ ಮಿತಿ ₹{amount:,.0f} (ಪ್ರತಿ ಯೂನಿಟ್‌ಗೆ ₹{unit_price:,.0f}). ಈ ಬೆಲೆಗೆ {quantity} ಯೂನಿಟ್‌ಗಳನ್ನು ಪೂರೈಸಲು ಸಾಧ್ಯವೇ? ದಯವಿಟ್ಟು ಪರಿಶೀಲಿಸಿ."
        elif "hindi" in lang:
            return f"धन्यवाद। हमारा स्वीकृत बजट कुल ₹{amount:,.0f} (लगभग ₹{unit_price:,.0f} प्रति पीस) है। क्या आप {quantity} पीस के लिए इस मूल्य पर डील कर सकते हैं?"
        elif "tamil" in lang:
            return f"நன்றி. எங்கள் அங்கீகரிக்கப்பட்ட பட்ஜெட் மொத்தம் ₹{amount:,.0f} (ஒரு யூனிட்டுக்கு ₹{unit_price:,.0f}). {quantity} யூனிட்களுக்கு இந்த விலையில் வழங்க முடியுமா?"
        elif "telugu" in lang:
            return f"ధన్యవాదాలు. మా బడ్జెట్ మొత్తం ₹{amount:,.0f} (యూనిట్‌కు ₹{unit_price:,.0f}). {quantity} యూనిట్లకు ఈ ధరకు అందించగలరా?"
        else:
            competing_note = f" We have competing quotes near this range." if competing else ""
            return f"Thank you for that quotation. For an order of {quantity} units, our approved budget is ₹{amount:,.2f} (approx ₹{unit_price:,.2f} per unit).{competing_note} Can you do ₹{amount:,.2f} including taxes and delivery?"

    @staticmethod
    def _format_acceptance_text(amount: float, quantity: int, language: str) -> str:
        lang = language.lower()
        if "kannada" in lang:
            return f"ತುಂಬಾ ಸಂತೋಷ. ₹{amount:,.0f} ಬೆಲೆ ಮತ್ತು ಷರತ್ತುಗಳು ನಮಗೆ ಸ್ವೀಕಾರಾರ್ಹವಾಗಿವೆ. ನಾನು ನಮ್ಮ ಗ್ರಾಹಕರಿಗೆ ಅಂತಿಮ ಅನುಮೋದನೆಗಾಗಿ ವರದಿ ಮಾಡುತ್ತೇನೆ."
        elif "hindi" in lang:
            return f"बहुत बढ़िया। ₹{amount:,.0f} का यह ऑफर हमें स्वीकार्य है। मैं अंतिम ग्राहक अनुमोदन के लिए इसे नोट कर रहा हूँ।"
        else:
            return f"That sounds fair. ₹{amount:,.2f} for {quantity} units works within our parameters. I have recorded these exact terms for customer approval."

    @staticmethod
    def _format_rejection_text(max_amount: float, language: str) -> str:
        lang = language.lower()
        if "kannada" in lang:
            return f"ಕ್ಷಮಿಸಿ, ನಮ್ಮ ಗರಿಷ್ಠ ಬಜೆಟ್ ₹{max_amount:,.0f} ಆಗಿದೆ ಮತ್ತು ನಾವು ಇದನ್ನು ಮೀರಲು ಸಾಧ್ಯವಿಲ್ಲ. ನಿಮ್ಮ ಸಮಯಕ್ಕೆ ಧನ್ಯವಾದಗಳು."
        elif "hindi" in lang:
            return f"माफ़ कीजिए, हमारा अधिकतम अधिकृत बजट ₹{max_amount:,.0f} है और हम इससे ऊपर नहीं जा सकते। आपके समय के लिए धन्यवाद।"
        else:
            return f"Understood. Unfortunately our maximum authorized budget is ₹{max_amount:,.2f}, so we cannot proceed at this price. Thank you for your time."
