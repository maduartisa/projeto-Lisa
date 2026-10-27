from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from commercial_platform.config import Settings
from commercial_platform.models import TenantMembership, TenantStatus, User

password_hasher = PasswordHasher()
DUMMY_PASSWORD_HASH = password_hasher.hash("not-a-real-account-password")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def issue_access_token(
    user: User,
    membership: TenantMembership,
    settings: Settings,
) -> tuple[str, int]:
    lifetime = settings.access_token_minutes * 60
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user.id),
        "tid": str(membership.tenant_id),
        "mid": str(membership.id),
        "role": membership.role,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": now + timedelta(seconds=lifetime),
    }
    return jwt.encode(claims, settings.jwt_secret_key, algorithm="HS256"), lifetime


def decode_access_token(token: str, settings: Settings) -> dict:
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=["HS256"],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        options={"require": ["sub", "tid", "mid", "role", "iat", "exp"]},
    )


def token_ids(claims: dict) -> tuple[UUID, UUID, UUID]:
    return UUID(claims["sub"]), UUID(claims["tid"]), UUID(claims["mid"])


def membership_is_active(membership: TenantMembership) -> bool:
    return (
        membership.is_active
        and membership.user.is_active
        and membership.tenant.status == TenantStatus.ACTIVE
    )
