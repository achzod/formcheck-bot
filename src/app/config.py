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
    gemini_api_key: str = ""

    # MiniMax Motion Coach
    minimax_enabled: bool = True
    minimax_base_url: str = "https://agent.minimax.io"
    minimax_token: str = ""
    minimax_user_id: str = ""
    minimax_device_id: str = ""
    minimax_uuid: str = ""
    minimax_chat_id: str = ""
    minimax_chat_type: int = 2
    minimax_lang: str = "en"
    minimax_browser_language: str = "fr-FR"
    minimax_os_name: str = "Mac"
    minimax_browser_name: str = "chrome"
    minimax_browser_platform: str = "MacIntel"
    minimax_device_memory: int = 8
    minimax_cpu_core_num: int = 8
    minimax_screen_width: int = 1920
    minimax_screen_height: int = 1080
    minimax_app_id: int = 3001
    minimax_version_code: int = 22201
    minimax_biz_id: int = 3
    minimax_client: str = "web"
    minimax_timezone_offset: int = 0
    minimax_timeout_s: int = 180
    minimax_poll_interval_s: float = 2.0
    minimax_model_option: int = 0
    minimax_prompt_template: str = ""
    minimax_prefer_motion_coach_chat: bool = True
    minimax_require_motion_coach_chat: bool = True
    minimax_motion_coach_keywords: str = "ai motion coach|motion coach|video motion analysis"
    minimax_fallback_to_local: bool = False
    minimax_strict_source: bool = True
    minimax_use_cloudscraper: bool = True
    minimax_request_max_attempts: int = 3
    minimax_retry_backoff_s: float = 1.0
    minimax_browser_refresh_enabled: bool = False
    minimax_browser_only: bool = True
    minimax_browser_email: str = ""
    minimax_browser_password: str = ""
    minimax_browser_headless: bool = True
    minimax_browser_timeout_s: int = 120
    minimax_browser_profile_dir: str = "media/minimax_browser_profile"
    minimax_browser_local_storage_json: str = ""
    minimax_browser_session_storage_json: str = ""
    minimax_motion_coach_expert_url: str = "https://agent.minimax.io/expert/chat/362683345551702"
    minimax_remote_worker_enabled: bool = False
    minimax_remote_worker_token: str = ""
    minimax_remote_worker_poll_interval_s: int = 5
    minimax_enable_cache: bool = True
    minimax_cache_ttl_hours: int = 168
    minimax_cache_path: str = "media/minimax_cache.sqlite"
    minimax_optimize_video: bool = True
    minimax_max_clip_s: int = 45
    minimax_target_height: int = 720
    minimax_target_fps: int = 24
    minimax_target_video_bitrate_kbps: int = 1400
    minimax_keep_audio: bool = False
    minimax_local_augmentation: bool = False
    minimax_user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0.0.0 Safari/537.36"
    )
    minimax_cookie: str = ""

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
    report_include_annotated_frames: bool = False

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
