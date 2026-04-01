from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field, SecretStr
from urllib.parse import quote_plus
from typing import Optional


class Settings(BaseSettings):
    database_hostname: str
    database_port: str
    database_username: str
    database_password: SecretStr  # Hidden in logs
    database_name: str

    secret_key: SecretStr         # Hidden in logs
    algorithm: str
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    cookie_domain: Optional[str] = None     # None = browser auto-sets to current domain
    cookie_secure: bool = False             # True in production (requires HTTPS)
    cookie_samesite: str = "lax"            # "lax" prevents CSRF on cross-site requests
    cors_origins: str
    redis_url: str
    trusted_hosts: str = "localhost,127.0.0.1,testserver"
    is_production: bool = False
    default_timezone: str = "UTC"
    google_client_id: str
    google_client_secret: SecretStr
    google_redirect_uri: str
    frontend_url: str
    smtp_host: str = "smtp.resend.com"
    smtp_port: int = 465
    smtp_username: str = "resend"
    smtp_password: Optional[SecretStr] = None
    smtp_use_tls: bool = False
    email_from: str = "Sarflog <no-reply@staging-mail.sarflog.uz>"
    resend_api_key: Optional[SecretStr] = None

    # Telegram (manual payment verification)
    telegram_bot_token: Optional[SecretStr] = None
    telegram_webhook_secret_token: Optional[SecretStr] = None
    telegram_admin_chat_ids: str = ""

    # Debug / dev-only toggles
    debug_allow_premium_toggle: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @computed_field
    def database_url(self) -> str:
        # Safely encode the password to handle special characters (@, #, !, etc.)
        pw = quote_plus(self.database_password.get_secret_value())
        return f"postgresql://{self.database_username}:{pw}@{self.database_hostname}:{self.database_port}/{self.database_name}"

    @computed_field
    def cors_origins_list(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]

    @computed_field
    def trusted_hosts_list(self) -> list[str]:
        return [host.strip().lower() for host in self.trusted_hosts.split(",") if host.strip()]

    @computed_field
    def telegram_admin_chat_id_list(self) -> list[int]:
        ids: list[int] = []
        for raw in self.telegram_admin_chat_ids.split(","):
            value = raw.strip()
            if not value:
                continue
            try:
                ids.append(int(value))
            except ValueError:
                continue
        return ids


settings = Settings()
