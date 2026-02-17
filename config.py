from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field, SecretStr
from urllib.parse import quote_plus


class Settings(BaseSettings):
    database_hostname: str
    database_port: str
    database_username: str
    database_password: SecretStr  # Hidden in logs
    database_name: str

    secret_key: SecretStr         # Hidden in logs
    algorithm: str
    access_token_expire_minutes: int
    cors_origins: str
    redis_url: str
    trusted_hosts: str = "localhost,127.0.0.1,testserver"
    is_production: bool = False
    default_timezone: str = "UTC"

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


settings = Settings()
