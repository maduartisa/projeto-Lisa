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


def nfe_xml(access_key: str = "1" * 44) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
  <NFe><infNFe Id="NFe{access_key}">
    <ide><nNF>12345</nNF></ide>
    <emit><CNPJ>12345678000199</CNPJ><xNome>Fornecedor da Nota</xNome></emit>
    <det nItem="1"><prod>
      <cProd>AUTO-001</cProd><cEAN>7891234567890</cEAN>
      <xProd>Produto importado</xProd><NCM>61091000</NCM>
      <qCom>3.0000</qCom><vUnCom>9.60</vUnCom><vProd>28.80</vProd>
    </prod><imposto><ICMS><ICMS00><CST>00</CST></ICMS00></ICMS></imposto></det>
    <total><ICMSTot><vNF>28.80</vNF></ICMSTot></total>
  </infNFe></NFe></nfeProc>"""


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


def test_nfe_import_creates_missing_products_and_receives_stock_once(client):
    admin = headers(login(client, "empresa-a"))

    imported = client.post(
        "/api/v1/admin/purchases/import-nfe",
        headers=admin,
        json={"xml": nfe_xml()},
    )
    assert imported.status_code == 201, imported.text
    result = imported.json()
    assert result["created_products"] == 1
    assert result["purchase"]["invoice_number"] == "12345"
    assert result["purchase"]["status"] == "received"
    assert result["purchase"]["total"] == "28.80"

    products = client.get("/api/v1/admin/products", headers=admin).json()
    product = next(item for item in products if item["sku"] == "AUTO-001")
    assert product["name"] == "Produto importado"
    assert product["barcode"] == "7891234567890"
    assert product["ncm"] == "61091000"
    assert product["cst"] == "00"
    assert product["stock_quantity"] == "3.000"
    assert product["price"] == "9.60"

    movements = client.get(
        f"/api/v1/admin/products/{product['id']}/inventory",
        headers=admin,
    )
    assert any(
        movement["movement_type"] == "purchase"
        and movement["quantity_delta"] == "3.000"
        for movement in movements.json()
    )
    entries = client.get("/api/v1/admin/finance", headers=admin).json()
    assert any(
        entry["description"].startswith("NF-e 12345")
        and entry["amount"] == "28.80"
        for entry in entries
    )

    duplicate = client.post(
        "/api/v1/admin/purchases/import-nfe",
        headers=admin,
        json={"xml": nfe_xml()},
    )
    assert duplicate.status_code == 409
    products_after_duplicate = client.get(
        "/api/v1/admin/products", headers=admin
    ).json()
    assert next(
        item for item in products_after_duplicate if item["id"] == product["id"]
    )["stock_quantity"] == "3.000"


def test_nfe_import_matches_existing_barcode_and_is_tenant_scoped(client):
    admin_a = headers(login(client, "empresa-a"))
    product = create_product(client, admin_a)
    updated = client.patch(
        f"/api/v1/admin/products/{product['id']}",
        headers=admin_a,
        json={"barcode": "7891234567890"},
    )
    assert updated.status_code == 200

    imported = client.post(
        "/api/v1/admin/purchases/import-nfe",
        headers=admin_a,
        json={"xml": nfe_xml("2" * 44)},
    )
    assert imported.status_code == 201, imported.text
    assert imported.json()["created_products"] == 0
    assert imported.json()["purchase"]["items"][0]["product_id"] == product["id"]

    admin_b = headers(login(client, "empresa-b"))
    isolated_import = client.post(
        "/api/v1/admin/purchases/import-nfe",
        headers=admin_b,
        json={"xml": nfe_xml("2" * 44)},
    )
    assert isolated_import.status_code == 201
    assert isolated_import.json()["created_products"] == 1
    assert client.get("/api/v1/admin/products", headers=admin_b).json()[0]["sku"] == (
        "AUTO-001"
    )


def test_nfe_import_rejects_malformed_and_unsafe_xml(client):
    admin = headers(login(client, "empresa-a"))
    malformed = client.post(
        "/api/v1/admin/purchases/import-nfe",
        headers=admin,
        json={"xml": "<NF-e>incompleta"},
    )
    assert malformed.status_code == 422

    unsafe = client.post(
        "/api/v1/admin/purchases/import-nfe",
        headers=admin,
        json={"xml": '<!DOCTYPE nfe [<!ENTITY x "x">]><nfe>&x;</nfe>'},
    )
    assert unsafe.status_code == 422

    unsupported_quantity = client.post(
        "/api/v1/admin/purchases/import-nfe",
        headers=admin,
        json={"xml": nfe_xml().replace("<qCom>3.0000</qCom>", "<qCom>3.0001</qCom>")},
    )
    assert unsupported_quantity.status_code == 422
    assert client.get("/api/v1/admin/purchases", headers=admin).json() == []


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


def test_counter_operator_does_not_receive_product_cost_or_tax_rates(client):
    admin = headers(login(client, "empresa-a"))
    product = client.post(
        "/api/v1/admin/products",
        headers=admin,
        json={
            "sku": "PRIVATE-COST",
            "name": "Produto com custo interno",
            "category": "Geral",
            "price": "30.00",
            "cost_price": "10.00",
            "icms_rate": "18.00",
        },
    )
    assert product.status_code == 201
    created = client.post(
        "/api/v1/admin/employees",
        headers=admin,
        json={
            "display_name": "Operador",
            "email": "operador-custo@empresa-a.example",
            "password": "a-secure-test-password",
            "role": MembershipRole.COUNTER_OPERATOR.value,
        },
    )
    assert created.status_code == 201
    operator_token = client.post(
        "/api/v1/auth/token",
        json={
            "email": "operador-custo@empresa-a.example",
            "password": "a-secure-test-password",
            "tenant_slug": "empresa-a",
        },
    )
    assert operator_token.status_code == 200
    products = client.get(
        "/api/v1/admin/products",
        headers=headers(operator_token.json()["access_token"]),
    )
    assert products.status_code == 200
    hidden = next(
        item for item in products.json() if item["id"] == product.json()["id"]
    )
    assert hidden["cost_price"] is None
    assert hidden["icms_rate"] is None
    assert hidden["ipi_rate"] is None
    assert hidden["pis_rate"] is None
    assert hidden["cofins_rate"] is None


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
