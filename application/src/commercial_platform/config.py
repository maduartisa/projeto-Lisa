import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret_key: str
    jwt_issuer: str = "commercial-platform"
    jwt_audience: str = "commercial-platform-api"
    access_token_minutes: int = 30

    @classmethod
    def from_environment(cls) -> "Settings":
        database_url = os.environ.get("DATABASE_URL")
        jwt_secret_key = os.environ.get("JWT_SECRET_KEY")
        if not database_url:
            raise RuntimeError("DATABASE_URL must be configured.")
        if not jwt_secret_key or len(jwt_secret_key) < 32:
            raise RuntimeError("JWT_SECRET_KEY must contain at least 32 characters.")
        return cls(database_url=database_url, jwt_secret_key=jwt_secret_key)
