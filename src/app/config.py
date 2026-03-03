from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_number: str = ""  # e.g. +14155238886 (sandbox)

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_success_url: str = "https://formcheck.fr/success"
    stripe_cancel_url: str = "https://formcheck.fr/cancel"

    # LLM APIs
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///./formcheck.db"
    rules_db_path: str = "database/rules_db.sqlite"

    # App
    debug: bool = False
    base_url: str = "https://formcheck-bot.onrender.com"  # For media/report URLs
    test_mode: bool = False  # Bypass credit checks for testing
    verify_twilio_signature: bool = True  # Reject unsigned/invalid webhook calls
    upload_max_mb: int = 1024  # Web upload fallback for heavy videos
    upload_chunk_size_mb: int = 2

    # Phase de test — toutes les analyses gratuites
    # Remettre a False pour reactiver le paywall Stripe
    test_mode_free: bool = False

    # Render API key (aussi utilise pour auth du /debug/errors endpoint)
    render_api_key: str = ""

    # Watchdog Twilio: auto-fallback message when inbound media fails (ex: >16MB)
    failed_media_fallback_enabled: bool = True
    failed_media_error_code: str = "11751"
    failed_media_poll_interval_s: int = 90
    failed_media_max_age_minutes: int = 30

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()  # type: ignore[call-arg]
