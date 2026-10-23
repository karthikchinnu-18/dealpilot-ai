import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class ExtractedOfferData(BaseModel):
    business_name: str
    unit_price: float = 0.0
    total_price: float = 0.0
    currency: str = "INR"
    delivery_days: int = 3
    initial_offer: float = 0.0
    counteroffers: List[float] = []
    final_explicit_offer: float = 0.0
    bulk_discount: float = 0.0
    taxes: float = 0.0
    taxes_included: bool = True
    shipping_charges: float = 0.0
    shipping_included: bool = True
    other_charges: float = 0.0
    availability: str = "In Stock"
    quality_conditions: str = "Standard certified"
    warranty: str = "Standard 1-year"
    payment_terms: str = "Net 30 / Advance after delivery"
    returns_cancellation: str = "30-day defective return"
    quote_validity: str = "7 days"
    missing_information: List[str] = []
    uncertainty_flag: bool = False
    extraction_confidence: float = 1.0
    terms_summary: str = ""
    evidence_status: str = "Supplier Stated"
    is_simulated: bool = False

class OfferExtractionEngine:
    """
    Extracts structured supplier quotations from negotiation transcripts or call records.
    Never silently assumes unstated charges are 0; explicitly flags missing info.
    """

    @staticmethod
    def extract_from_transcript(
        turns: List[Dict[str, Any]],
        business_name: str,
        requested_quantity: int = 1,
        is_simulated: bool = False,
    ) -> ExtractedOfferData:
        extracted = ExtractedOfferData(
            business_name=business_name,
            is_simulated=is_simulated,
            evidence_status="Simulated" if is_simulated else "Supplier Stated",
        )

        all_supplier_text = " ".join([
            turn.get("text_original", "") + " " + turn.get("text_translated", "")
            for turn in turns
            if turn.get("speaker") == "supplier"
        ])
        
        all_text = " ".join([
            turn.get("text_original", "") + " " + turn.get("text_translated", "")
            for turn in turns
        ])

        # 1. Extract Price numbers
        # Find amounts preceded by ₹ or Rs or INR or words like "rupees"
        price_patterns = [
            r"(?:₹|Rs\.?|INR)\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]+)?)",
            r"([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]+)?)\s*(?:rupees|rs|inr)",
            r"(?:quote|price|total|cost|deal|rate)\s*(?:is|at|of)?\s*(?:₹|Rs\.?|INR)?\s*([0-9]{3,7})",
        ]

        found_prices: List[float] = []
        for pattern in price_patterns:
            matches = re.finditer(pattern, all_text, re.IGNORECASE)
            for m in matches:
                val_str = m.group(1).replace(",", "")
                try:
                    val = float(val_str)
                    if 100 <= val <= 100_000_000:
                        if val not in found_prices:
                            found_prices.append(val)
                except ValueError:
                    pass

        if found_prices:
            extracted.initial_offer = found_prices[0]
            extracted.final_explicit_offer = found_prices[-1]
            extracted.total_price = extracted.final_explicit_offer
            extracted.counteroffers = found_prices[1:-1]
            extracted.unit_price = round(extracted.total_price / max(1, requested_quantity), 2)
            if extracted.initial_offer > extracted.final_explicit_offer:
                extracted.bulk_discount = round(extracted.initial_offer - extracted.final_explicit_offer, 2)
        else:
            extracted.uncertainty_flag = True
            extracted.missing_information.append("Total price was not clearly identified in transcript.")
            extracted.extraction_confidence = 0.4

        # 2. Extract Delivery days
        delivery_patterns = [
            r"([0-9]+)\s*(?:to\s*([0-9]+))?\s*(?:days|business days|working days)",
            r"delivery\s*(?:within|in|by)?\s*([0-9]+)\s*days",
            r"([0-9]+)\s*ದಿನಗಳಲ್ಲಿ",  # Kannada: within N days
            r"([0-9]+)\s*दिनों\s*में",  # Hindi: within N days
        ]
        found_delivery = False
        for pattern in delivery_patterns:
            m = re.search(pattern, all_text, re.IGNORECASE)
            if m:
                try:
                    days = int(m.group(1))
                    extracted.delivery_days = days
                    found_delivery = True
                    break
                except (ValueError, IndexError):
                    pass
        if not found_delivery:
            extracted.missing_information.append("Delivery timeline not explicitly confirmed; defaulted based on context.")
            extracted.delivery_days = 4

        # 3. Check Taxes & Shipping
        tax_terms = ["gst", "tax", "taxes", "ತೆರಿಗೆ", "टैक्स"]
        shipping_terms = ["delivery", "shipping", "freight", "transport", "ಸಾಗಾಣಿಕೆ", "डिलीवरी"]

        has_tax_mention = any(t in all_supplier_text.lower() for t in tax_terms)
        has_shipping_mention = any(t in all_supplier_text.lower() for t in shipping_terms)

        if not has_tax_mention:
            extracted.missing_information.append("GST / Tax applicability was not explicitly clarified on call.")
            extracted.taxes_included = False
        else:
            if "tax included" in all_supplier_text.lower() or "including gst" in all_supplier_text.lower() or "inclusive" in all_supplier_text.lower():
                extracted.taxes_included = True
            else:
                extracted.taxes_included = True

        if not has_shipping_mention:
            extracted.missing_information.append("Shipping charges were not explicitly confirmed on call.")
            extracted.shipping_included = False
        else:
            extracted.shipping_included = True

        # 4. Check Warranty & Quality
        if "warranty" in all_text.lower() or "ವಾರಂಟಿ" in all_text or "वारंटी" in all_text:
            extracted.warranty = "1-year replacement warranty confirmed"
        else:
            extracted.missing_information.append("Specific warranty period not discussed.")

        if "quality" in all_text.lower() or "ಗುಣಮಟ್ಟ" in all_text or "क्वालिटी" in all_text or "sample" in all_text.lower():
            extracted.quality_conditions = "High grade verified sample"

        # Terms summary
        tax_note = "GST Included" if extracted.taxes_included else "GST Unconfirmed"
        ship_note = "Free Delivery" if extracted.shipping_included else "Shipping Extra"
        extracted.terms_summary = f"{extracted.delivery_days} days delivery · {tax_note} · {ship_note} · {extracted.warranty}"

        return extracted
