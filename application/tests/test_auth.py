from fastapi.testclient import TestClient

from conftest import login


def test_login_returns_access_token_for_active_membership(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/token",
        json={
            "email": "admin@empresa-a.example",
            "password": "strong-test-password",
            "tenant_slug": "empresa-a",
        },
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["expires_in"] == 1800


def test_company_registration_creates_admin_and_starts_session(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Nova Loja",
            "tenant_slug": "nova-loja",
            "admin_name": "Ana Silva",
            "email": "ana@novaloja.example",
            "password": "strong-registration-password",
        },
    )

    assert response.status_code == 201
    token = response.json()["access_token"]
    context = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert context.status_code == 200
    assert context.json()["tenant"]["slug"] == "nova-loja"
    assert context.json()["tenant"]["display_name"] == "Nova Loja"
    assert context.json()["tenant"]["role"] == "company_admin"
    assert context.json()["user"]["email"] == "ana@novaloja.example"


def test_company_registration_rejects_existing_company_slug(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Outra Loja",
            "tenant_slug": "empresa-a",
            "admin_name": "Ana Silva",
            "email": "ana@outraloja.example",
            "password": "strong-registration-password",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "O identificador da empresa já está em uso."


def test_company_registration_rejects_existing_email(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Outra Loja",
            "tenant_slug": "outra-loja",
            "admin_name": "Ana Silva",
            "email": "admin@empresa-a.example",
            "password": "strong-registration-password",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Este e-mail já possui acesso ao sistema."


def test_company_registration_requires_strong_password(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Nova Loja",
            "tenant_slug": "nova-loja",
            "admin_name": "Ana Silva",
            "email": "ana@novaloja.example",
            "password": "short",
        },
    )

    assert response.status_code == 422


def test_login_rejects_membership_in_another_tenant(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/token",
        json={
            "email": "admin@empresa-a.example",
            "password": "strong-test-password",
            "tenant_slug": "empresa-b",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciais inválidas."


def test_authenticated_context_contains_only_selected_tenant(client: TestClient) -> None:
    token = login(client, "empresa-a")

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["tenant"]["slug"] == "empresa-a"
    assert response.json()["user"]["email"] == "admin@empresa-a.example"


def test_authentication_is_required_for_tenant_context(client: TestClient) -> None:
    response = client.get("/api/v1/admin/tenants/me")

    assert response.status_code == 401
