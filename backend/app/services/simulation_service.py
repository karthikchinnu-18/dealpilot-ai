import asyncio
from datetime import datetime, timezone
import random
from typing import Any, Dict, List, Optional
from ..models import CallRecord, CallTranscript, EvidenceRecord, NegotiationSession, Offer, PurchaseRequest, Supplier
from .strategy_engine import NegotiationStrategyEngine
from .extraction_engine import OfferExtractionEngine

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

# Fictional Personas for Simulation
SIMULATED_PERSONAS = [
    {
        "name": "Bharat Textiles & Print Works",
        "phone": "+91 98450 12345",
        "language": "Hindi",
        "initial_quote_factor": 1.15,
        "floor_quote_factor": 0.88,
        "delivery_days": 4,
        "personality": "Friendly merchant, open to bulk discount in Hindi",
        "behavior": "success",
    },
    {
        "name": "Bengaluru Merchandising Hub",
        "phone": "+91 98860 67890",
        "language": "Kannada",
        "initial_quote_factor": 1.18,
        "floor_quote_factor": 0.91,
        "delivery_days": 3,
        "personality": "Local supplier in Bengaluru, speaks polite Kannada",
        "behavior": "success",
    },
    {
        "name": "Apex Industrial Supplies",
        "phone": "+91 99000 54321",
        "language": "English",
        "initial_quote_factor": 1.20,
        "floor_quote_factor": 0.94,
        "delivery_days": 3,
        "personality": "Corporate vendor, clear terms, negotiable in English",
        "behavior": "success",
    },
    {
        "name": "Chennai Cotton Krafts",
        "phone": "+91 94440 98765",
        "language": "Tamil",
        "initial_quote_factor": 1.10,
        "floor_quote_factor": 0.98,
        "delivery_days": 2,
        "personality": "Express fast delivery, firm on price in Tamil",
        "behavior": "success",
    },
    {
        "name": "Metro Print Labs",
        "phone": "+91 98200 11223",
        "language": "English",
        "initial_quote_factor": 1.25,
        "floor_quote_factor": 1.05,
        "delivery_days": 5,
        "personality": "Busy line / no answer scenario",
        "behavior": "no_answer",
    },
    {
        "name": "Prestige Apparel Ltd",
        "phone": "+91 98110 99887",
        "language": "English",
        "initial_quote_factor": 1.35,
        "floor_quote_factor": 1.25,
        "delivery_days": 6,
        "personality": "High-end supplier, refuses to discount below budget",
        "behavior": "price_refused",
    },
]

class SimulationService:
    """
    Simulates multi-supplier autonomous AI phone calls, multilingual dialogues,
    objections, counteroffers, and quote extractions.
    Works 100% offline without any paid external services.
    """

    @staticmethod
    def get_persona_for_supplier(supplier_name: str, preferred_language: str = "auto", index: int = 0) -> Dict[str, Any]:
        lower_name = supplier_name.lower()
        if "busy" in lower_name or "no answer" in lower_name:
            return SIMULATED_PERSONAS[4]

        # Match by name if it matches our demo personas
        for p in SIMULATED_PERSONAS:
            if p["name"].lower() in lower_name:
                return p

        # For user-created custom suppliers: default to an active, responsive negotiation
        # Alternate delivery days and price factors so multiple custom suppliers create a real comparison
        lang = preferred_language if preferred_language and preferred_language != "auto" else "English"
        
        # Variations across custom suppliers so multiple teammates yield realistic, competitive comparisons
        initial_factors = [1.14, 1.19, 1.12, 1.16]
        floor_factors = [0.89, 0.92, 0.88, 0.94]
        delivery_days_list = [3, 2, 4, 3]

        var_idx = index % 4
        return {
            "name": supplier_name,
            "phone": "",
            "language": lang,
            "initial_quote_factor": initial_factors[var_idx],
            "floor_quote_factor": floor_factors[var_idx],
            "delivery_days": delivery_days_list[var_idx],
            "personality": f"Verified supplier negotiating in {lang}",
            "behavior": "success",
        }

    @staticmethod
    def run_simulated_call(
        session: NegotiationSession,
        request: PurchaseRequest,
        supplier: Supplier,
        index: int,
    ) -> Dict[str, Any]:
        persona = SimulationService.get_persona_for_supplier(
            supplier.business_name,
            supplier.preferred_language or "auto",
            index,
        )
        behavior = persona["behavior"]
        language = persona["language"]
        budget = request.budget
        quantity = request.quantity
        product = request.product

        # Base calculations
        base_budget = budget if budget > 0 else 10000.0
        initial_price = round(base_budget * persona["initial_quote_factor"], 2)
        floor_price = round(base_budget * persona["floor_quote_factor"], 2)

        call_record = CallRecord(
            session_id=session.id,
            negotiation_id=request.id,
            supplier_id=supplier.id,
            provider="simulation",
            provider_call_sid=f"sim_{supplier.id[:8]}_{random.randint(1000, 9999)}",
            is_simulated=True,
            detected_language=language,
        )

        # Scenario 1: No Answer / Busy
        if behavior == "no_answer":
            call_record.call_state = "NO_ANSWER"
            call_record.duration_seconds = 18
            call_record.rounds_completed = 0
            call_record.latest_offer_amount = 0.0
            call_record.negotiation_status = "Failed: No Answer"
            call_record.last_event = "Line rang for 18s with no representative response"
            call_record.call_outcome = "No answer. Call queued for retry or manual follow-up."
            call_record.failure_reason = "Supplier line busy or unanswered after 18 seconds."
            
            transcript = CallTranscript(
                call_id=call_record.id,
                original_language=language,
                english_summary="Call was initiated. Phone rang repeatedly without answer from representative.",
                turns=[
                    {
                        "round": 0,
                        "speaker": "system",
                        "text_original": f"Dialing {supplier.country_code} {supplier.phone_number}...",
                        "text_translated": f"Dialing {supplier.country_code} {supplier.phone_number}...",
                        "language": language,
                        "timestamp": utc_now(),
                    },
                    {
                        "round": 0,
                        "speaker": "system",
                        "text_original": "Ringing... Ringing... Call timeout. No answer.",
                        "text_translated": "Ringing... Ringing... Call timeout. No answer.",
                        "language": language,
                        "timestamp": utc_now(),
                    },
                ],
            )
            return {"call": call_record, "transcript": transcript, "offer": None, "evidence": []}

        # Scenario 2: Successful Dialogue with dynamic rounds
        turns: List[Dict[str, Any]] = []
        
        # Turn 1: AI Introduction
        ai_intro_en = f"Hello, I am DealPilot AI, an autonomous purchasing assistant calling on behalf of a verified buyer. We are inquiring about purchasing {quantity} {request.unit} of {product}. Could you provide your best quotation including taxes and delivery?"
        
        if language == "Kannada":
            ai_intro_orig = f"ನಮಸ್ಕಾರ, ನಾನು ಡೀಲ್‌ಪೈಲಟ್ ಎಐ (DealPilot AI) ಖರೀದಿ ಸಹಾಯಕ. ನಾವು {quantity} {request.unit} {product} ಖರೀದಿಸಲು ಆಸಕ್ತಿ ಹೊಂದಿದ್ದೇವೆ. ತೆರಿಗೆ ಮತ್ತು ಡೆಲಿವರಿ ಸೇರಿದಂತೆ ನಿಮ್ಮ ಅತ್ಯುತ್ತಮ ಬೆಲೆ ತಿಳಿಸುತ್ತೀರಾ?"
            supp_rep_1_orig = f"ನಮಸ್ಕಾರ ಸ್ವಾಮಿ. ನಮ್ಮಲ್ಲಿ ಉತ್ತಮ ಗುಣಮಟ್ಟದ ಸ್ಟಾಕ್ ಇದೆ. {quantity} {request.unit}ಗೆ ಒಟ್ಟು ₹{initial_price:,.0f} ಆಗುತ್ತದೆ. ಜಿಎಸ್‌ಟಿ ಪ್ರತ್ಯೇಕ."
            supp_rep_1_en = f"Hello sir. We have top quality stock available. For {quantity} units the total price is ₹{initial_price:,.0f}. GST is extra."
        elif language == "Hindi":
            ai_intro_orig = f"नमस्ते, मैं डीलपायलट एआई (DealPilot AI) परचेजिंग असिस्टेंट बोल रहा हूँ। हमें {quantity} {request.unit} {product} की आवश्यकता है। क्या आप टैक्स और डिलीवरी सहित अपना सर्वश्रेष्ठ कोटेशन दे सकते हैं?"
            supp_rep_1_orig = f"नमस्ते जी! माल बिल्कुल तैयार है। {quantity} पीस का कुल रेट ₹{initial_price:,.0f} पड़ेगा, 5 दिनों में डिलीवरी मिल जाएगी।"
            supp_rep_1_en = f"Hello! The stock is ready. For {quantity} pieces, total rate is ₹{initial_price:,.0f}, delivery within 5 days."
        elif language == "Tamil":
            ai_intro_orig = f"வணக்கம், நான் டீல்பைலட் ஏஐ (DealPilot AI) கொள்முதல் உதவியாளர் பேசுகிறேன். எங்களுக்கு {quantity} {request.unit} {product} தேவைப்படுகிறது. சிறந்த விலையை கூற முடியுமா?"
            supp_rep_1_orig = f"வணக்கம்! நாங்கள் பிரீமியம் தரம் தருகிறோம். {quantity} யூனிட்களுக்கு ₹{initial_price:,.0f} ஆகும். 2 நாட்களில் எக்ஸ்பிரஸ் டெலிவரி செய்வோம்."
            supp_rep_1_en = f"Hello! We provide premium quality. For {quantity} units it will be ₹{initial_price:,.0f}. Express delivery in 2 days."
        else:
            ai_intro_orig = ai_intro_en
            supp_rep_1_orig = f"Hello! Yes, we have ready stock for {product}. For an order of {quantity} units, our standard quotation is ₹{initial_price:,.2f} with delivery in 3 days."
            supp_rep_1_en = supp_rep_1_orig

        turns.append({
            "round": 1,
            "speaker": "ai",
            "text_original": ai_intro_orig,
            "text_translated": ai_intro_en,
            "language": language,
            "timestamp": utc_now(),
        })
        turns.append({
            "round": 1,
            "speaker": "supplier",
            "text_original": supp_rep_1_orig,
            "text_translated": supp_rep_1_en,
            "language": language,
            "timestamp": utc_now(),
        })

        # Turn 2: Strategy Engine evaluates round 1
        decision1 = NegotiationStrategyEngine.evaluate_round(
            budget=budget,
            target_price=request.target_price,
            max_authorized_price=request.max_authorized_price,
            quantity=quantity,
            current_supplier_quote=initial_price,
            current_round=1,
            max_rounds=request.max_negotiation_rounds,
            delivery_days_quoted=persona["delivery_days"],
            max_delivery_days_allowed=7,
            language=language,
        )

        turns.append({
            "round": 2,
            "speaker": "ai",
            "text_original": decision1.counteroffer_text,
            "text_translated": f"Thank you. Our approved budget for {quantity} units is ₹{decision1.suggested_amount:,.2f}. Can you meet us at this price with all taxes and delivery included?",
            "language": language,
            "timestamp": utc_now(),
        })

        # Supplier counter / response
        mid_price = round((initial_price + floor_price) / 2.0, 2)
        if behavior == "price_refused":
            # Refusal
            if language == "Hindi":
                supp_rep_2_orig = f"नहीं जी, ₹{decision1.suggested_amount:,.0f} पर संभव नहीं है। हमारा न्यूनतम ₹{initial_price:,.0f} ही रहेगा।"
                supp_rep_2_en = f"No, ₹{decision1.suggested_amount:,.0f} is not possible. Our minimum remains ₹{initial_price:,.0f}."
            else:
                supp_rep_2_orig = f"We appreciate the offer, but our raw material costs are fixed. We cannot go below ₹{initial_price:,.2f}."
                supp_rep_2_en = supp_rep_2_orig
                
            turns.append({
                "round": 2,
                "speaker": "supplier",
                "text_original": supp_rep_2_orig,
                "text_translated": supp_rep_2_en,
                "language": language,
                "timestamp": utc_now(),
            })

            # AI rejects respectfully
            decision_final = NegotiationStrategyEngine.evaluate_round(
                budget=budget,
                target_price=request.target_price,
                max_authorized_price=request.max_authorized_price,
                quantity=quantity,
                current_supplier_quote=initial_price,
                current_round=2,
                max_rounds=2,
                delivery_days_quoted=persona["delivery_days"],
                max_delivery_days_allowed=7,
                language=language,
            )
            turns.append({
                "round": 2,
                "speaker": "ai",
                "text_original": decision_final.counteroffer_text,
                "text_translated": f"Understood. Our maximum authorized budget is ₹{budget:,.2f}, so we cannot proceed at this price. Thank you for your time.",
                "language": language,
                "timestamp": utc_now(),
            })

            call_record.call_state = "COMPLETED"
            call_record.duration_seconds = 72
            call_record.rounds_completed = 2
            call_record.latest_offer_amount = initial_price
            call_record.negotiation_status = "Finished: Price Refused (Above Budget)"
            call_record.last_event = f"Supplier firm at ₹{initial_price:,.2f}; exceeds budget"
            call_record.call_outcome = "Supplier refused counteroffer; price exceeds authorized limit."

            transcript = CallTranscript(
                call_id=call_record.id,
                original_language=language,
                english_summary=f"Supplier quoted ₹{initial_price:,.2f} and refused negotiation below budget limit.",
                turns=turns,
            )

            # Record non-compliant offer for transparency
            offer = Offer(
                negotiation_id=request.id,
                supplier_id=supplier.id,
                call_id=call_record.id,
                business_name=supplier.business_name,
                unit_price=round(initial_price / max(1, quantity), 2),
                total_price=initial_price,
                currency="INR",
                delivery_days=persona["delivery_days"],
                initial_offer=initial_price,
                final_explicit_offer=initial_price,
                terms=f"Firm quote; exceeds budget of ₹{budget:,.2f}",
                evidence_note="Simulated call dialogue recorded; price non-compliant with budget.",
                evidence_status="Simulated",
                source_type="phone",
                is_simulated=True,
                uncertainty_flag=True,
            )
            return {"call": call_record, "transcript": transcript, "offer": offer, "evidence": []}

        # Scenario 3: Successful multi-round negotiation
        final_negotiated_price = floor_price
        if language == "Kannada":
            supp_rep_2_orig = f"ನೋಡಿ ಸ್ವಾಮಿ, ₹{decision1.suggested_amount:,.0f} ಸ್ವಲ್ಪ ಕಡಿಮೆ ಆಯಿತು. ಆದರೂ ನಿಯಮಿತ ಗ್ರಾಹಕರಾಗಲು ನಾವು ₹{final_negotiated_price:,.0f} ಗೆ ಒಪ್ಪಿಕೊಳ್ಳುತ್ತೇವೆ, ಜಿಎಸ್‌ಟಿ ಮತ್ತು ಫ್ರೀ ಡೆಲಿವರಿ ಸಹ ನೀಡುತ್ತೇವೆ."
            supp_rep_2_en = f"Look sir, ₹{decision1.suggested_amount:,.0f} is slightly low. However, to build a regular relationship we can do ₹{final_negotiated_price:,.0f}, including GST and free delivery."
            ai_confirm_orig = f"ಧನ್ಯವಾದಗಳು! ₹{final_negotiated_price:,.0f} ಬೆಲೆಗೆ ಒಪ್ಪಂದವನ್ನು ನಾನು ದಾಖಲಿಸಿಕೊಂಡಿದ್ದೇನೆ. ನಮ್ಮ ಕ್ಲೈಂಟ್ ಅಂತಿಮ ಅನುಮೋದನೆ ನೀಡಲಿದ್ದಾರೆ."
            ai_confirm_en = f"Thank you! I have confirmed the deal at ₹{final_negotiated_price:,.0f}. Our client will provide final approval."
        elif language == "Hindi":
            supp_rep_2_orig = f"साहब, आपके बल्क ऑर्डर को देखते हुए हम बीच का रास्ता निकाल लेते हैं। फाइनल डील ₹{final_negotiated_price:,.0f} में पक्की करते हैं, जीएसटी और डिलीवरी फ्री रहेगी।"
            supp_rep_2_en = f"Sir, seeing your bulk order we will find a middle ground. We finalize the deal at ₹{final_negotiated_price:,.0f}, GST and delivery included free."
            ai_confirm_orig = f"बहुत-बहुत धन्यवाद। मैंने ₹{final_negotiated_price:,.0f} का यह फाइनल कोटेशन नोट कर लिया है। ग्राहक की मंज़ूरी के बाद आगे की प्रक्रिया होगी।"
            ai_confirm_en = f"Thank you very much. I have recorded this final quotation of ₹{final_negotiated_price:,.0f}. Next steps after customer approval."
        elif language == "Tamil":
            supp_rep_2_orig = f"சரிங்க, எங்கள் தரத்திற்கு இந்த விலை மிகக் குறைவு. இருந்தாலும் ₹{final_negotiated_price:,.0f}க்கு 2 நாள் எக்ஸ்பிரஸ் டெலிவரியுடன் செய்து தருகிறோம்."
            supp_rep_2_en = f"Alright, for our quality this is quite low. However we will do ₹{final_negotiated_price:,.0f} with 2-day express delivery."
            ai_confirm_orig = f"மிக்க நன்றி! ₹{final_negotiated_price:,.0f} ஒப்பந்தத்தை பதிவு செய்துவிட்டேன். வாடிக்கையாளர் ஒப்புதலுக்கு சமர்ப்பிக்கிறேன்."
            ai_confirm_en = f"Thank you! Recorded the quotation of ₹{final_negotiated_price:,.0f} for customer approval."
        else:
            supp_rep_2_orig = f"Considering this is a bulk order of {quantity} units, we can offer our special vendor pricing of ₹{final_negotiated_price:,.2f} inclusive of GST and standard 3-day delivery."
            supp_rep_2_en = supp_rep_2_orig
            ai_confirm_orig = f"Thank you for that adjustment. I have recorded the final quotation of ₹{final_negotiated_price:,.2f} with 3-day delivery and GST included for customer authorization."
            ai_confirm_en = ai_confirm_orig

        turns.append({
            "round": 2,
            "speaker": "supplier",
            "text_original": supp_rep_2_orig,
            "text_translated": supp_rep_2_en,
            "language": language,
            "timestamp": utc_now(),
        })
        turns.append({
            "round": 3,
            "speaker": "ai",
            "text_original": ai_confirm_orig,
            "text_translated": ai_confirm_en,
            "language": language,
            "timestamp": utc_now(),
        })

        call_record.call_state = "COMPLETED"
        call_record.duration_seconds = random.randint(85, 135)
        call_record.rounds_completed = 3
        call_record.latest_offer_amount = final_negotiated_price
        call_record.negotiation_status = f"Completed: Settled at ₹{final_negotiated_price:,.2f}"
        call_record.last_event = f"Agreed on ₹{final_negotiated_price:,.2f} after 3 rounds"
        call_record.call_outcome = f"Negotiation successful. Initial: ₹{initial_price:,.2f} -> Final: ₹{final_negotiated_price:,.2f}."

        transcript = CallTranscript(
            call_id=call_record.id,
            original_language=language,
            english_summary=f"Supplier in {language} initially quoted ₹{initial_price:,.2f}. After AI counteroffer, agreed to ₹{final_negotiated_price:,.2f} including taxes and delivery in {persona['delivery_days']} days.",
            turns=turns,
        )

        # Structured offer extraction
        extracted = OfferExtractionEngine.extract_from_transcript(
            turns=turns,
            business_name=supplier.business_name,
            requested_quantity=quantity,
            is_simulated=True,
        )

        offer = Offer(
            negotiation_id=request.id,
            supplier_id=supplier.id,
            call_id=call_record.id,
            business_name=supplier.business_name,
            unit_price=extracted.unit_price,
            total_price=extracted.total_price,
            currency="INR",
            delivery_days=persona["delivery_days"],
            initial_offer=initial_price,
            final_explicit_offer=extracted.final_explicit_offer,
            bulk_discount=max(0.0, initial_price - final_negotiated_price),
            taxes=round(final_negotiated_price * 0.18, 2),
            shipping_charges=0.0,
            availability=extracted.availability,
            warranty=extracted.warranty,
            payment_terms=extracted.payment_terms,
            terms=extracted.terms_summary,
            evidence_note=f"Simulated {language} phone conversation. Audio turns transcribed and price verified.",
            evidence_status="Simulated",
            source_type="phone",
            is_simulated=True,
            missing_information=extracted.missing_information,
            uncertainty_flag=extracted.uncertainty_flag,
            extraction_confidence=extracted.extraction_confidence,
        )

        # Create Evidence Records
        evidence_items = [
            EvidenceRecord(
                negotiation_id=request.id,
                call_id=call_record.id,
                field_name="total_price",
                stated_value=f"₹{final_negotiated_price:,.2f}",
                verification_status="Simulated",
                verification_method=f"Simulated Voice AI Call ({language})",
                verification_notes=f"Confirmed explicitly by representative in Round 2 dialogue.",
            ),
            EvidenceRecord(
                negotiation_id=request.id,
                call_id=call_record.id,
                field_name="delivery_days",
                stated_value=f"{persona['delivery_days']} days",
                verification_status="Simulated",
                verification_method=f"Simulated Voice AI Call ({language})",
                verification_notes=f"Delivery commitment stated by supplier.",
            ),
        ]

        return {
            "call": call_record,
            "transcript": transcript,
            "offer": offer,
            "evidence": evidence_items,
        }
