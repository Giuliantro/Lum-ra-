import base64
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class NotConfigured(Exception):
    """A required setting is missing (reported as HTTP 503)."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    image_model: str = "gpt-image-2"
    image_output_format: str = "webp"
    board_quality: str = "high"
    board_size: str = "1536x1024"
    preview_quality: str = "medium"
    final_quality: str = "high"

    # postgresql://user:pass@host:port/db (Railway format) or sqlite+aiosqlite:///file.db
    database_url: str = ""

    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""
    # Optional override; otherwise derived from the publishable key.
    clerk_jwks_url: str = ""
    # Allowed `azp` origins of session tokens; defaults to cors_origins.
    clerk_authorized_parties: list[str] = []

    cors_origins: list[str] = ["http://localhost:5173"]

    @property
    def async_database_url(self) -> str:
        url = self.database_url
        for prefix in ("postgresql://", "postgres://"):
            if url.startswith(prefix):
                return "postgresql+asyncpg://" + url[len(prefix):]
        return url

    @property
    def clerk_frontend_api(self) -> str:
        """pk_<env>_<base64("<frontend-api-host>$")> → frontend API host."""
        if not self.clerk_publishable_key:
            raise NotConfigured("Clerk non configurato: imposta CLERK_PUBLISHABLE_KEY nel backend")
        encoded = self.clerk_publishable_key.split("_", 2)[-1]
        decoded = base64.b64decode(encoded + "=" * (-len(encoded) % 4)).decode()
        return decoded.rstrip("$")

    @property
    def jwks_url(self) -> str:
        return self.clerk_jwks_url or f"https://{self.clerk_frontend_api}/.well-known/jwks.json"

    @property
    def authorized_parties(self) -> list[str]:
        return self.clerk_authorized_parties or self.cors_origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
