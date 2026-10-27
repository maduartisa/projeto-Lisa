import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from commercial_platform.api import create_app
from commercial_platform.config import Settings
from commercial_platform.models import (
    Base,
    MembershipRole,
    Tenant,
    TenantMembership,
    User,
)
from commercial_platform.security import hash_password


@pytest.fixture
def client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    settings = Settings(
        database_url=str(engine.url),
        jwt_secret_key="test-key-that-is-at-least-thirty-two-characters",
    )
    app = create_app(settings, sessions)
    with sessions.begin() as session:
        for slug in ("empresa-a", "empresa-b"):
            tenant = Tenant(slug=slug, display_name=slug, status="active")
            user = User(
                email=f"admin@{slug}.example",
                password_hash=hash_password("strong-test-password"),
                is_active=True,
            )
            session.add_all((tenant, user))
            session.flush()
            session.add(
                TenantMembership(
                    tenant_id=tenant.id,
                    user_id=user.id,
                    role=MembershipRole.COMPANY_ADMIN,
                    is_active=True,
                )
            )
    with TestClient(app) as test_client:
        yield test_client
    engine.dispose()


def login(client: TestClient, slug: str) -> str:
    response = client.post(
        "/api/v1/auth/token",
        json={
            "email": f"admin@{slug}.example",
            "password": "strong-test-password",
            "tenant_slug": slug,
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]
