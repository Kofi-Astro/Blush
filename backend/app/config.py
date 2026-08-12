from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str

    supabase_url: str
    supabase_service_role_key: str
    supabase_media_bucket: str = "media"

    admin_username: str
    admin_password_hash: str
    jwt_secret_key: str
    jwt_expire_minutes: int = 720  # 12 hours

    # Comma-separated list, e.g. "https://blushcloset.xyz,http://localhost:5500"
    allowed_origins: str = "*"

    @property
    def allowed_origins_list(self) -> list[str]:
        if self.allowed_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
