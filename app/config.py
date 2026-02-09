from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./tickets.db"

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_publishable_key: str = ""

    # Resend (Email)
    resend_api_key: str = ""
    from_email: str = "tickets@example.com"

    # Twilio (SMS)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # Postiz (Social Media)
    postiz_api_key: str = ""
    postiz_url: str = "https://api.postiz.com"  # or self-hosted URL

    # Application
    base_url: str = "http://localhost:8000"
    uploads_dir: str = "uploads"

    # Branding
    org_name: str = "Toronto Raptors"
    org_color: str = "#CE1141"
    org_logo_url: str = "https://upload.wikimedia.org/wikipedia/en/3/36/Toronto_Raptors_logo.svg"

    # Notifications
    reminder_hours_before: int = 24

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
