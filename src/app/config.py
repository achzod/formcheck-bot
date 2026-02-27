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

    # App
    debug: bool = False
    base_url: str = "https://formcheck.fr"  # For media URLs
    test_mode: bool = False  # Bypass credit checks for testing

    # Phase de test — toutes les analyses gratuites
    # Remettre a False pour reactiver le paywall Stripe
    test_mode_free: bool = True

    # Render API key (aussi utilise pour auth du /debug/errors endpoint)
    render_api_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()  # type: ignore[call-arg]
