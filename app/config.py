from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Required
    tally_webhook_secret: str
    whatsapp_access_token: str
    whatsapp_phone_number_id: str
    whatsapp_api_version: str = "v22.0"
    wa_admin_number: str
    google_sheet_id: str
    google_sheet_tab: str = "Submissions"
    google_sheet_webhook_tab: str = "DeliveryLog"
    google_service_account_json_path: Optional[str] = None
    
    # Optional
    enable_whatsapp_send: bool = True
    enable_sheets_log: bool = True
    max_message_chars: int = 3500
    debug_tally_mapping: bool = False
    
    # Template Settings
    whatsapp_template_name: str = "job_post_notification"
    whatsapp_template_lang: str = "en"
    whatsapp_webhook_verify_token: str = "my_secure_token"

    # OpenAI Parsing feature
    enable_openai_parse: bool = True
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # WhatsApp Bot Settings
    enable_whatsapp_bot: bool = True
    whatsapp_admin_allowlist: str = ""  # Comma-separated normalized numbers
    bot_log_to_sheets: bool = True
    bot_log_sheet_tab: str = "BotLog"
    enable_bot_pending_notification: bool = True
    enable_bot_freeform_reply: bool = True

    # Frontend Config
    frontend_origin: str = "http://localhost:3000"
    validation_cache_ttl: int = 300

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
