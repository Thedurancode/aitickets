from pydantic_settings import BaseSettings
from functools import lru_cache
import os


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

    # Telnyx (Voice Calling)
    telnyx_api_key: str = ""
    telnyx_connection_id: str = ""
    telnyx_phone_number: str = ""

    # Postiz (Social Media)
    postiz_api_key: str = ""
    postiz_url: str = "https://api.postiz.com"  # or self-hosted URL

    # Meta Ads (Facebook/Instagram)
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_access_token: str = ""  # Long-lived access token with ads_management permission
    meta_ad_account_id: str = ""  # Format: act_xxxxx
    meta_business_id: str = ""
    facebook_page_id: str = ""  # Required for publishing ads
    instagram_account_id: str = ""  # Instagram Business Account ID (optional)

    # Apple Wallet
    apple_wallet_team_id: str = ""
    apple_wallet_pass_type_id: str = "pass.com.example.event"
    apple_wallet_cert_path: str = ""
    apple_wallet_key_path: str = ""
    apple_wallet_wwdr_cert_path: str = ""

    # Application
    base_url: str = "http://localhost:8000"
    uploads_dir: str = "uploads"
    environment: str = "development"  # development, test, production

    # Branding
    org_name: str = "Toronto Raptors"
    org_color: str = "#CE1141"
    org_logo_url: str = "https://upload.wikimedia.org/wikipedia/en/3/36/Toronto_Raptors_logo.svg"
    show_header_links: bool = True  # Show/hide navigation links in header

    # Notifications
    reminder_hours_before: int = 24

    # Authentication
    mcp_api_key: str = ""  # API key for MCP/voice endpoints (empty = auth disabled)
    admin_api_key: str = ""  # Separate API key for REST /api/* endpoints (empty = falls back to mcp_api_key)

    # CORS
    cors_origins: str = ""  # Comma-separated allowed origins (empty = allow all)

    # Owner phone (default SMS recipient for style picker etc.)
    owner_phone: str = ""

    # Gemini (Image Generation)
    gemini_api_key: str = ""

    # Image Generation via OpenRouter (Flux 2 Pro)
    # Uses same OpenRouter key as LLM routing
    image_generation_provider: str = "openrouter"  # Options: openrouter, nanobanana
    flux_model: str = "black-forest-labs/flux.2-pro"  # OpenRouter model ID

    # Alternative: NanoBanana (if not using OpenRouter)
    nanobanana_api_key: str = ""
    nanobanana_api_url: str = "https://api.nanobanana.com/v1/generate"

    # LLM Routing (supports OpenRouter, Zhipu, OpenAI)
    openrouter_api_key: str = ""
    openai_api_key: str = ""
    zhipu_api_key: str = ""
    zhipu_base_url: str = "https://open.bigmodel.cn/api/paas/v4/"
    llm_router_model: str = "openai/gpt-4o-mini"

    # Logging
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_format: str = "structured"  # structured or human

    # Content Moderation (NSFW detection)
    content_moderation_enabled: bool = True  # Enable/disable content moderation
    nsfw_threshold: float = 0.5  # Threshold for blocking content (0-1)
    auto_approve_safe: bool = True  # Auto-approve content below threshold

    # Alert Delivery
    slack_webhook_url: str = ""  # Slack incoming webhook URL for alerts
    admin_email: str = ""  # Email address for critical alerts
    admin_phone: str = ""  # Phone number for critical SMS alerts (Twilio)
    app_url: str = "http://localhost:3000"  # Frontend URL for alert links

    # External Research APIs
    google_places_api_key: str = ""  # Google Places API for venue research

    # Google Ads API
    google_ads_developer_token: str = ""  # Developer token from Google Ads API
    google_ads_client_id: str = ""  # OAuth2 client ID
    google_ads_client_secret: str = ""  # OAuth2 client secret
    google_ads_refresh_token: str = ""  # OAuth2 refresh token
    google_ads_customer_id: str = ""  # Google Ads account ID (e.g., "1234567890")
    google_ads_login_customer_id: str = ""  # MCC account ID (optional)
    openweather_api_key: str = ""  # OpenWeather API for weather forecasts
    census_api_key: str = ""  # US Census API for demographics
    youtube_api_key: str = ""  # YouTube Data API v3 for artist video research

    # Spotify API (for artist research)
    spotify_client_id: str = ""  # Spotify Client ID
    spotify_client_secret: str = ""  # Spotify Client Secret

    class Config:
        # Support environment-specific .env files
        # Usage: ENV=production python app.py
        # Falls back to .env if ENV not set
        env_file = f".env.{os.getenv('ENV', 'development')}" if os.getenv('ENV') else ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
