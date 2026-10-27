from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from conftest import login
from commercial_platform.models import (
    InventoryMovement,
    MembershipRole,
    Order,
    Product,
    Tenant,
    TenantMembership,
)


def headers(client: TestClient, slug: str = "empresa-a") -> dict[str, str]:
    return {"Authorization": f"Bearer {login(client, slug)}"}


def create_customer(client: TestClient, auth: dict[str, str]) -> UUID:
    response = client.post(
        "/api/v1/admin/customers",
        headers=auth,
        json={"name": "Cliente de teste", "phone": "+5511999999999"},
    )
    assert response.status_code == 201
    return UUID(response.json()["id"])


def create_product(
    client: TestClient,
    auth: dict[str, str],
    *,
    sku: str = "SKU-1",
    quantity: str = "5",
    price: str = "10.00",
) -> dict:
    response = client.post(
        "/api/v1/admin/products",
        headers=auth,
        json={
            "sku": sku,
            "name": f"Produto {sku}",
            "category": "Limpeza",
            "price": price,
            "stock_quantity": quantity,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_product_inventory_and_public_catalog_are_tenant_scoped(
    client: TestClient,
) -> None:
    admin_a = headers(client, "empresa-a")
    admin_b = headers(client, "empresa-b")
    product = create_product(client, admin_a)
    other_product = create_product(client, admin_b, sku="SKU-1")

    hidden = client.post(
        "/api/v1/admin/products",
        headers=admin_a,
        json={
            "sku": "OFF",
            "name": "Inativo",
            "category": "Limpeza",
            "price": "1.00",
            "is_active": False,
        },
    )
    assert hidden.status_code == 201

    catalog = client.get("/api/v1/public/empresa-a/catalog?q=SKU-1")
    assert catalog.status_code == 200
    assert [item["id"] for item in catalog.json()] == [product["id"]]
    assert catalog.json()[0]["in_stock"] is True
    assert "stock_quantity" not in catalog.json()[0]
    profile = client.get("/api/v1/public/empresa-a")
    assert profile.status_code == 200
    assert profile.json()["display_name"] == "empresa-a"

    cross_tenant = client.patch(
        f"/api/v1/admin/products/{other_product['id']}",
        headers=admin_a,
        json={"price": "2.00"},
    )
    assert cross_tenant.status_code == 404

    adjustment = client.post(
        f"/api/v1/admin/products/{product['id']}/inventory",
        headers=admin_a,
        json={"quantity_delta": "-2", "note": "Ajuste de conferência"},
    )
    assert adjustment.status_code == 201
    assert Decimal(adjustment.json()["quantity_delta"]) == Decimal("-2")

    rejected = client.post(
        f"/api/v1/admin/products/{product['id']}/inventory",
        headers=admin_a,
        json={"quantity_delta": "-10"},
    )
    assert rejected.status_code == 409

    with client.app.state.session_factory() as session:
        updated = session.scalar(select(Product).where(Product.id == UUID(product["id"])))
        assert updated.stock_quantity == Decimal("3.000")
        movements = session.scalars(
            select(InventoryMovement).where(
                InventoryMovement.tenant_id == updated.tenant_id
            )
        ).all()
        assert len(movements) == 2
        assert all(movement.product_id == UUID(product["id"]) for movement in movements)


def test_order_snapshots_price_and_deducts_stock_once_on_completion(
    client: TestClient,
) -> None:
    admin = headers(client)
    customer_id = create_customer(client, admin)
    product = create_product(client, admin)
    order_response = client.post(
        "/api/v1/admin/orders",
        headers=admin,
        json={
            "customer_id": str(customer_id),
            "source": "counter",
            "fulfillment_method": "counter",
            "items": [{"product_id": product["id"], "quantity": "2"}],
        },
    )
    assert order_response.status_code == 201
    order = order_response.json()
    assert order["status"] == "quote"
    assert order["total"] == "20.00"
    assert order["items"][0]["unit_price"] == "10.00"

    price_update = client.patch(
        f"/api/v1/admin/products/{product['id']}",
        headers=admin,
        json={"price": "12.50"},
    )
    assert price_update.status_code == 200

    for next_status in ("pending", "separating", "completed"):
        transition = client.patch(
            f"/api/v1/admin/orders/{order['id']}/status",
            headers=admin,
            json={"status": next_status},
        )
        assert transition.status_code == 200
        assert transition.json()["status"] == next_status

    with client.app.state.session_factory() as session:
        stored_product = session.scalar(
            select(Product).where(Product.id == UUID(product["id"]))
        )
        stored_order = session.scalar(
            select(Order).where(Order.id == UUID(order["id"]))
        )
        assert stored_product.stock_quantity == Decimal("3.000")
        assert stored_order.total == Decimal("20.00")
        assert stored_order.items[0].unit_price == Decimal("10.00")
        sale_movements = session.scalars(
            select(InventoryMovement).where(
                InventoryMovement.reference_id == UUID(order["id"])
            )
        ).all()
        assert len(sale_movements) == 1
        assert sale_movements[0].quantity_delta == Decimal("-2.000")

    repeated = client.patch(
        f"/api/v1/admin/orders/{order['id']}/status",
        headers=admin,
        json={"status": "completed"},
    )
    assert repeated.status_code == 409


def test_insufficient_stock_prevents_order_completion_without_partial_changes(
    client: TestClient,
) -> None:
    admin = headers(client)
    customer_id = create_customer(client, admin)
    product = create_product(client, admin, quantity="1")
    order = client.post(
        "/api/v1/admin/orders",
        headers=admin,
        json={
            "customer_id": str(customer_id),
            "source": "counter",
            "fulfillment_method": "counter",
            "items": [{"product_id": product["id"], "quantity": "2"}],
        },
    ).json()
    for next_status in ("pending", "separating"):
        assert (
            client.patch(
                f"/api/v1/admin/orders/{order['id']}/status",
                headers=admin,
                json={"status": next_status},
            ).status_code
            == 200
        )

    response = client.patch(
        f"/api/v1/admin/orders/{order['id']}/status",
        headers=admin,
        json={"status": "completed"},
    )

    assert response.status_code == 409
    with client.app.state.session_factory() as session:
        stored_product = session.scalar(
            select(Product).where(Product.id == UUID(product["id"]))
        )
        stored_order = session.scalar(
            select(Order).where(Order.id == UUID(order["id"]))
        )
        assert stored_product.stock_quantity == Decimal("1.000")
        assert stored_order.status == "separating"
        assert session.scalar(select(InventoryMovement).where(
            InventoryMovement.reference_id == UUID(order["id"])
        )) is None


def test_cross_tenant_customer_and_product_cannot_create_order(
    client: TestClient,
) -> None:
    admin_a = headers(client, "empresa-a")
    admin_b = headers(client, "empresa-b")
    customer_id = create_customer(client, admin_b)
    product = create_product(client, admin_b)

    response = client.post(
        "/api/v1/admin/orders",
        headers=admin_a,
        json={
            "customer_id": str(customer_id),
            "source": "counter",
            "fulfillment_method": "counter",
            "items": [{"product_id": product["id"], "quantity": "1"}],
        },
    )

    assert response.status_code == 404
    own_customer = create_customer(client, admin_a)
    cross_product = client.post(
        "/api/v1/admin/orders",
        headers=admin_a,
        json={
            "customer_id": str(own_customer),
            "source": "counter",
            "fulfillment_method": "counter",
            "items": [{"product_id": product["id"], "quantity": "1"}],
        },
    )
    assert cross_product.status_code == 422
    assert client.get(
        "/api/v1/admin/orders", headers=admin_a
    ).json() == []


def test_order_lookup_and_fulfillment_transitions_are_tenant_scoped(
    client: TestClient,
) -> None:
    admin_a = headers(client, "empresa-a")
    admin_b = headers(client, "empresa-b")
    customer_id = create_customer(client, admin_b)
    product = create_product(client, admin_b)
    order = client.post(
        "/api/v1/admin/orders",
        headers=admin_b,
        json={
            "customer_id": str(customer_id),
            "source": "counter",
            "fulfillment_method": "delivery",
            "items": [{"product_id": product["id"], "quantity": "1"}],
        },
    ).json()

    hidden = client.get(f"/api/v1/admin/orders/{order['id']}", headers=admin_a)
    assert hidden.status_code == 404

    for next_status in ("pending", "separating"):
        assert client.patch(
            f"/api/v1/admin/orders/{order['id']}/status",
            headers=admin_b,
            json={"status": next_status},
        ).status_code == 200
    invalid_fulfillment = client.patch(
        f"/api/v1/admin/orders/{order['id']}/status",
        headers=admin_b,
        json={"status": "ready_for_pickup"},
    )
    assert invalid_fulfillment.status_code == 409
    assert client.get(
        f"/api/v1/admin/orders/{order['id']}", headers=admin_b
    ).json()["status"] == "separating"
    in_transit = client.patch(
        f"/api/v1/admin/orders/{order['id']}/status",
        headers=admin_b,
        json={"status": "in_transit"},
    )
    assert in_transit.status_code == 200
    completed = client.patch(
        f"/api/v1/admin/orders/{order['id']}/status",
        headers=admin_b,
        json={"status": "completed"},
    )
    assert completed.status_code == 200


def test_sku_is_unique_within_each_tenant(client: TestClient) -> None:
    product_a = create_product(client, headers(client, "empresa-a"))
    product_b = create_product(client, headers(client, "empresa-b"))
    assert product_a["sku"] == product_b["sku"]

    duplicate = client.post(
        "/api/v1/admin/products",
        headers=headers(client, "empresa-a"),
        json={
            "sku": product_a["sku"],
            "name": "SKU repetido",
            "category": "Limpeza",
            "price": "1.00",
        },
    )

    assert duplicate.status_code == 409


def test_product_rejects_non_http_image_urls_and_blank_names(
    client: TestClient,
) -> None:
    auth = headers(client)
    invalid_url = client.post(
        "/api/v1/admin/products",
        headers=auth,
        json={
            "sku": "BAD-URL",
            "name": "Produto inválido",
            "category": "Limpeza",
            "price": "1.00",
            "image_url": "javascript:alert(1)",
        },
    )
    blank_name = client.post(
        "/api/v1/admin/products",
        headers=auth,
        json={
            "sku": "BLANK",
            "name": "   ",
            "category": "Limpeza",
            "price": "1.00",
        },
    )

    assert invalid_url.status_code == 422
    assert blank_name.status_code == 422


def test_inventory_manager_can_manage_stock_but_cannot_manage_orders(
    client: TestClient,
) -> None:
    with client.app.state.session_factory.begin() as session:
        membership = session.scalar(
            select(TenantMembership)
            .join(Tenant)
            .where(Tenant.slug == "empresa-a")
        )
        membership.role = MembershipRole.INVENTORY_MANAGER

    inventory_headers = headers(client)
    product = create_product(client, inventory_headers, sku="STOCK-1")
    assert product["sku"] == "STOCK-1"
    assert client.get("/api/v1/admin/orders", headers=inventory_headers).status_code == 403
    assert client.post(
        "/api/v1/admin/customers",
        headers=inventory_headers,
        json={"name": "Operador inválido"},
    ).status_code == 403
