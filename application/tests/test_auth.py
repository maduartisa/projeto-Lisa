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
