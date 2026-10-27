from commercial_platform.models import MembershipRole

from conftest import login


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_product(client, auth_headers):
    response = client.post(
        "/api/v1/admin/products",
        headers=auth_headers,
        json={
            "sku": "OPS-001",
            "name": "Produto operacional",
            "category": "Geral",
            "price": "12.50",
            "stock_quantity": "2",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_purchase_receipt_updates_stock_and_finance(client):
    admin = headers(login(client, "empresa-a"))
    product = create_product(client, admin)
    supplier_response = client.post(
        "/api/v1/admin/suppliers",
        headers=admin,
        json={"name": "Fornecedor A", "email": "vendas@fornecedor.example"},
    )
    assert supplier_response.status_code == 201
    supplier = supplier_response.json()

    purchase_response = client.post(
        "/api/v1/admin/purchases",
        headers=admin,
        json={
            "supplier_id": supplier["id"],
            "items": [
                {"product_id": product["id"], "quantity": "3", "unit_cost": "8.00"}
            ],
        },
    )
    assert purchase_response.status_code == 201
    purchase = purchase_response.json()
    assert purchase["status"] == "draft"
    assert purchase["total"] == "24.00"

    received = client.patch(
        f"/api/v1/admin/purchases/{purchase['id']}/status",
        headers=admin,
        json={"status": "received"},
    )
    assert received.status_code == 200
    assert received.json()["status"] == "received"

    inventory = client.get(
        f"/api/v1/admin/products/{product['id']}/inventory",
        headers=admin,
    )
    assert inventory.status_code == 200
    assert any(
        movement["movement_type"] == "purchase"
        and movement["quantity_delta"] == "3.000"
        for movement in inventory.json()
    )

    entries = client.get("/api/v1/admin/finance", headers=admin)
    assert entries.status_code == 200
    payable = next(entry for entry in entries.json() if entry["entry_type"] == "payable")
    assert payable["amount"] == "24.00"
    settlement = client.patch(
        f"/api/v1/admin/finance/{payable['id']}/settle",
        headers=admin,
    )
    assert settlement.status_code == 200
    assert settlement.json()["status"] == "settled"


def test_employee_management_and_access_logs_are_tenant_scoped(client):
    admin_token = login(client, "empresa-a")
    admin = headers(admin_token)
    created = client.post(
        "/api/v1/admin/employees",
        headers=admin,
        json={
            "display_name": "Operadora",
            "email": "operadora@empresa-a.example",
            "password": "a-secure-test-password",
            "role": MembershipRole.COUNTER_OPERATOR.value,
        },
    )
    assert created.status_code == 201
    employee_token = client.post(
        "/api/v1/auth/token",
        json={
            "email": "operadora@empresa-a.example",
            "password": "a-secure-test-password",
            "tenant_slug": "empresa-a",
        },
    )
    assert employee_token.status_code == 200
    logs = client.get("/api/v1/admin/access-logs", headers=admin)
    assert logs.status_code == 200
    assert any(log["action"].startswith("POST /api/v1/auth/token") for log in logs.json())

    second_tenant = headers(login(client, "empresa-b"))
    assert client.get("/api/v1/admin/employees", headers=second_tenant).json()[0]["email"] == (
        "admin@empresa-b.example"
    )
    forbidden = client.get("/api/v1/admin/access-logs", headers=second_tenant)
    assert forbidden.status_code == 200
    own_user_id = client.get(
        "/api/v1/auth/me", headers=second_tenant
    ).json()["user"]["id"]
    assert all(
        log["user_id"] == own_user_id
        for log in forbidden.json()
    )


def test_employee_routes_are_admin_only(client):
    admin = headers(login(client, "empresa-a"))
    created = client.post(
        "/api/v1/admin/employees",
        headers=admin,
        json={
            "display_name": "Operador",
            "email": "operador@empresa-a.example",
            "password": "a-secure-test-password",
            "role": MembershipRole.COUNTER_OPERATOR.value,
        },
    )
    assert created.status_code == 201
    operator = headers(
        client.post(
            "/api/v1/auth/token",
            json={
                "email": "operador@empresa-a.example",
                "password": "a-secure-test-password",
                "tenant_slug": "empresa-a",
            },
        ).json()["access_token"]
    )
    assert client.get("/api/v1/admin/employees", headers=operator).status_code == 403


def test_public_checkout_creates_pending_catalog_order_without_charging(client):
    admin = headers(login(client, "empresa-a"))
    product = create_product(client, admin)
    response = client.post(
        "/api/v1/public/empresa-a/orders",
        json={
            "customer_name": "Cliente online",
            "phone": "+5511999999999",
            "fulfillment_method": "pickup",
            "items": [{"product_id": product["id"], "quantity": "1"}],
        },
    )
    assert response.status_code == 201
    receipt = response.json()
    assert receipt["status"] == "pending"
    assert receipt["total"] == "12.50"

    orders = client.get("/api/v1/admin/orders", headers=admin)
    assert orders.status_code == 200
    order = next(item for item in orders.json() if item["id"] == receipt["order_id"])
    assert order["source"] == "catalog"
    assert order["status"] == "pending"

    inventory = client.get(
        f"/api/v1/admin/products/{product['id']}/inventory",
        headers=admin,
    )
    assert inventory.status_code == 200
    assert all(movement["movement_type"] != "sale" for movement in inventory.json())


def test_public_checkout_requires_a_contact_method(client):
    admin = headers(login(client, "empresa-a"))
    product = create_product(client, admin)
    response = client.post(
        "/api/v1/public/empresa-a/orders",
        json={
            "customer_name": "Cliente sem contato",
            "fulfillment_method": "pickup",
            "items": [{"product_id": product["id"], "quantity": "1"}],
        },
    )
    assert response.status_code == 422


def test_catalog_exposes_product_grade_attributes(client):
    admin = headers(login(client, "empresa-a"))
    response = client.post(
        "/api/v1/admin/products",
        headers=admin,
        json={
            "sku": "CAM-AZ-M",
            "name": "Camiseta",
            "category": "Vestuário",
            "size": "M",
            "color": "Azul",
            "price": "39.90",
        },
    )
    assert response.status_code == 201
    product = response.json()
    assert product["size"] == "M"
    assert product["color"] == "Azul"

    catalog = client.get("/api/v1/public/empresa-a/catalog")
    assert catalog.status_code == 200
    public_product = next(item for item in catalog.json() if item["id"] == product["id"])
    assert public_product["size"] == "M"
    assert public_product["color"] == "Azul"
