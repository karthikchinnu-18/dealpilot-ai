import os
from pathlib import Path
from typing import Literal
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_FILE = (BASE_DIR / "dealpilot.db").as_posix()
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DB_FILE}"

class Settings(BaseModel):
    app_name: str = "DealPilot AI — The Negotiator"
    app_version: str = "1.0.0"
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    # Database - absolute path so it never depends on terminal cwd
    database_url: str = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    
    # Telephony Provider (Twilio)
    telephony_provider: str = os.getenv("TELEPHONY_PROVIDER", "twilio")
    twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_phone_number: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    webhook_base_url: str = os.getenv("WEBHOOK_BASE_URL", "")
    
    # AI Keys
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    
    # Default mode
    default_calling_mode: Literal["simulated", "real"] = "simulated"
    
    @property
    def is_twilio_configured(self) -> bool:
        return bool(
            self.twilio_account_sid.strip()
            and self.twilio_auth_token.strip()
            and self.twilio_phone_number.strip()
            and not self.twilio_account_sid.startswith("your_")
        )

    @property
    def is_ai_configured(self) -> bool:
        return bool(
            (self.openai_api_key.strip() and not self.openai_api_key.startswith("your_"))
            or (self.gemini_api_key.strip() and not self.gemini_api_key.startswith("your_"))
        )

    def save_telephony(
        self,
        account_sid: str,
        auth_token: str,
        phone_number: str,
        webhook_base_url: str,
    ):
        self.twilio_account_sid = account_sid.strip()
        self.twilio_auth_token = auth_token.strip()
        self.twilio_phone_number = phone_number.strip()
        self.webhook_base_url = webhook_base_url.strip()

        env_file = BASE_DIR / ".env"
        existing_lines = []
        if env_file.exists():
            existing_lines = env_file.read_text(encoding="utf-8").splitlines()

        keys_to_update = {
            "TWILIO_ACCOUNT_SID": self.twilio_account_sid,
            "TWILIO_AUTH_TOKEN": self.twilio_auth_token,
            "TWILIO_PHONE_NUMBER": self.twilio_phone_number,
            "WEBHOOK_BASE_URL": self.webhook_base_url,
        }

        updated_lines = []
        handled_keys = set()
        for line in existing_lines:
            stripped = line.strip()
            if "=" in stripped and not stripped.startswith("#"):
                key = stripped.split("=", 1)[0].strip()
                if key in keys_to_update:
                    updated_lines.append(f"{key}={keys_to_update[key]}")
                    handled_keys.add(key)
                    continue
            updated_lines.append(line)

        for key, val in keys_to_update.items():
            if key not in handled_keys:
                updated_lines.append(f"{key}={val}")

        env_file.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")


settings = Settings()
