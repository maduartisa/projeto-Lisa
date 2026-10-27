from fastapi.testclient import TestClient

from conftest import login


def test_user_cannot_select_another_tenant_using_request_header(client: TestClient) -> None:
    token = login(client, "empresa-a")

    response = client.get(
        "/api/v1/admin/tenants/me",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-Id": "empresa-b",
        },
    )

    assert response.status_code == 200
    assert response.json()["tenant"]["slug"] == "empresa-a"


def test_suspended_tenant_invalidates_existing_access_token(client: TestClient) -> None:
    from sqlalchemy import update

    from commercial_platform.models import Tenant

    token = login(client, "empresa-a")
    with client.app.state.session_factory.begin() as session:
        session.execute(
            update(Tenant).where(Tenant.slug == "empresa-a").values(status="suspended")
        )

    response = client.get(
        "/api/v1/admin/tenants/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
