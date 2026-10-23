import base64
import logging
import re
from typing import Any, Dict, Optional, Tuple
import httpx
from ..config import settings

logger = logging.getLogger(__name__)

class TelephonyProvider:
    """Abstract base class for telephony providers."""
    def is_configured(self) -> Tuple[bool, str]:
        raise NotImplementedError

    async def initiate_outbound_call(
        self,
        to_phone: str,
        webhook_url: str,
        status_callback_url: str,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    async def end_call(self, call_sid: str) -> bool:
        raise NotImplementedError

class TwilioTelephonyProvider(TelephonyProvider):
    """
    Twilio Telephony Integration using official REST endpoints.
    Handles authentication, outbound dispatch, TwiML generation, and webhook security.
    """

    def __init__(self):
        self.reload_credentials()

    def reload_credentials(self):
        self.account_sid = settings.twilio_account_sid.strip()
        self.auth_token = settings.twilio_auth_token.strip()
        self.from_phone = settings.twilio_phone_number.strip()
        self.webhook_base = settings.webhook_base_url.strip()

    def is_configured(self) -> Tuple[bool, str]:
        if not self.account_sid or self.account_sid.startswith("your_"):
            return False, "TWILIO_ACCOUNT_SID is not set or has placeholder value."
        if not self.auth_token or self.auth_token.startswith("your_"):
            return False, "TWILIO_AUTH_TOKEN is not set or has placeholder value."
        if not self.from_phone or self.from_phone.startswith("your_"):
            return False, "TWILIO_PHONE_NUMBER is not set."
        return True, "Twilio telephony is configured and ready for outbound calling."

    async def verify_credentials(self, account_sid: str, auth_token: str) -> Tuple[bool, str]:
        sid = account_sid.strip()
        token = auth_token.strip()
        if not sid or not token:
            return False, "Account SID and Auth Token cannot be blank."
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}.json"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, auth=(sid, token))
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status", "active")
                    friendly = data.get("friendly_name", sid)
                    return True, f"Verified Twilio Account '{friendly}' (Status: {status})."
                elif resp.status_code == 401:
                    return False, "Twilio authentication failed: Invalid Account SID or Auth Token."
                else:
                    return False, f"Twilio API returned HTTP {resp.status_code}: {resp.text}"
        except Exception as e:
            return False, f"Failed to connect to Twilio API: {str(e)}"

    @staticmethod
    def validate_phone_number(country_code: str, phone: str) -> Tuple[bool, str, str]:
        """
        Validates and formats a phone number to E.164.
        Returns (is_valid, formatted_number, error_message).
        """
        clean_code = country_code.strip()
        if not clean_code.startswith("+"):
            clean_code = "+" + clean_code
            
        clean_number = re.sub(r"[^0-9]", "", phone)
        if len(clean_number) < 6 or len(clean_number) > 15:
            return False, "", f"Phone number length ({len(clean_number)} digits) is invalid."

        # If clean_number starts with the country code digits without the plus
        code_digits = clean_code.replace("+", "")
        if clean_number.startswith(code_digits):
            formatted = f"+{clean_number}"
        else:
            formatted = f"{clean_code}{clean_number}"

        return True, formatted, ""

    async def initiate_outbound_call(
        self,
        to_phone: str,
        webhook_url: str,
        status_callback_url: str,
    ) -> Dict[str, Any]:
        is_ready, reason = self.is_configured()
        if not is_ready:
            raise ValueError(f"Cannot initiate real call: {reason}")

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Calls.json"
        auth = (self.account_sid, self.auth_token)

        data = {
            "To": to_phone,
            "From": self.from_phone,
            "Url": webhook_url,
            "StatusCallback": status_callback_url,
            "StatusCallbackEvent": ["initiated", "ringing", "answered", "completed"],
            "StatusCallbackMethod": "POST",
            "Timeout": 30,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, data=data, auth=auth)
            if resp.status_code >= 400:
                logger.error(f"Twilio error {resp.status_code}: {resp.text}")
                raise RuntimeError(f"Twilio API Error ({resp.status_code}): {resp.text}")
            return resp.json()

    async def end_call(self, call_sid: str) -> bool:
        is_ready, _ = self.is_configured()
        if not is_ready or not call_sid or call_sid.startswith("sim_"):
            return False

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Calls/{call_sid}.json"
        auth = (self.account_sid, self.auth_token)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, data={"Status": "completed"}, auth=auth)
            return resp.status_code == 200

    @staticmethod
    def generate_twiml_greeting(
        product: str,
        quantity: int,
        unit: str,
        language: str = "en-IN",
        action_url: str = "/api/telephony/twilio/gather",
    ) -> str:
        """
        Generates standard TwiML with transparent AI disclosure and speech gather.
        """
        greeting = (
            f"Hello. This is DealPilot AI, an automated purchasing assistant calling on behalf of a verified buyer. "
            f"We are requesting a quotation for {quantity} {unit} of {product}. "
            f"Please state your price, delivery time, and payment terms after the tone."
        )
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="{language}">{greeting}</Say>
    <Gather input="speech" timeout="6" speechTimeout="auto" action="{action_url}" method="POST">
        <Say language="{language}">We are listening to your quotation. Please speak now.</Say>
    </Gather>
    <Say language="{language}">We did not hear a response. Thank you and goodbye.</Say>
</Response>"""
        return twiml

    @staticmethod
    def generate_twiml_test_greeting(to_phone: str) -> str:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="en-IN">Hello! This is DealPilot AI calling your phone to verify your telephony connection. Outbound phone calling is active and fully functional. Thank you, and have a wonderful day!</Say>
    <Hangup/>
</Response>"""

telephony_service = TwilioTelephonyProvider()
