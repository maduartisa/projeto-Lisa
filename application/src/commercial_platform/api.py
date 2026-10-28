from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from commercial_platform.config import Settings
from commercial_platform.database import session_dependency
from commercial_platform.models import (
    AccessLog,
    Customer,
    FinancialEntry,
    FulfillmentMethod,
    InventoryMovement,
    InventoryMovementType,
    MembershipRole,
    Order,
    OrderItem,
    OrderSource,
    OrderStatus,
    Purchase,
    PurchaseItem,
    Product,
    Supplier,
    Tenant,
    TenantMembership,
    TenantStatus,
    User,
)
from commercial_platform.schemas import (
    AccessLogResponse,
    CurrentUserResponse,
    CustomerCreate,
    CustomerResponse,
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
    FinancialEntryCreate,
    FinancialEntryResponse,
    InventoryAdjustment,
    InventoryMovementResponse,
    LoginRequest,
    OrderCreate,
    OrderResponse,
    OrderStatusUpdate,
    PublicOrderCreate,
    PublicOrderReceipt,
    PurchaseCreate,
    PurchaseResponse,
    PurchaseStatusUpdate,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    PublicProductResponse,
    PublicTenantResponse,
    SupplierCreate,
    SupplierResponse,
    TenantSlug,
    TokenResponse,
)
from commercial_platform.security import (
    DUMMY_PASSWORD_HASH,
    decode_access_token,
    issue_access_token,
    membership_is_active,
    hash_password,
    token_ids,
    verify_password,
)

bearer_scheme = HTTPBearer(auto_error=False)
CENT = Decimal("0.01")
MAX_ORDER_TOTAL = Decimal("999999999999.99")
ORDER_TRANSITIONS = {
    OrderStatus.QUOTE: {OrderStatus.PENDING, OrderStatus.CANCELLED},
    OrderStatus.PENDING: {OrderStatus.SEPARATING, OrderStatus.CANCELLED},
    OrderStatus.SEPARATING: {
        OrderStatus.READY_FOR_PICKUP,
        OrderStatus.IN_TRANSIT,
        OrderStatus.COMPLETED,
        OrderStatus.CANCELLED,
    },
    OrderStatus.READY_FOR_PICKUP: {OrderStatus.COMPLETED, OrderStatus.CANCELLED},
    OrderStatus.IN_TRANSIT: {OrderStatus.COMPLETED, OrderStatus.CANCELLED},
    OrderStatus.COMPLETED: set(),
    OrderStatus.CANCELLED: set(),
}


@dataclass(frozen=True)
class AuthContext:
    user: User
    tenant: Tenant
    membership: TenantMembership


def create_app(settings: Settings, session_factory: sessionmaker[Session]) -> FastAPI:
    app = FastAPI(title="Commercial Platform API", version="0.1.0")
    app.state.session_factory = session_factory
    get_session = session_dependency(session_factory)
    router = APIRouter(prefix="/api/v1")

    def current_context(
        request: Request,
        credentials: Annotated[
            HTTPAuthorizationCredentials | None,
            Depends(bearer_scheme),
        ],
        session: Annotated[Session, Depends(get_session)],
    ) -> AuthContext:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Autenticação obrigatória.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            claims = decode_access_token(credentials.credentials, settings)
            user_id, tenant_id, membership_id = token_ids(claims)
        except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido ou expirado.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from None

        membership = session.scalar(
            select(TenantMembership)
            .where(
                TenantMembership.id == membership_id,
                TenantMembership.user_id == user_id,
                TenantMembership.tenant_id == tenant_id,
            )
        )
        if membership is None or not membership_is_active(membership):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vínculo inativo ou acesso à empresa indisponível.",
            )
        if claims.get("role") != membership.role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido ou expirado.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        session.add(
            AccessLog(
                tenant_id=membership.tenant_id,
                user_id=membership.user_id,
                action=f"{request.method} {request.url.path}",
            )
        )
        session.commit()
        return AuthContext(
            user=membership.user,
            tenant=membership.tenant,
            membership=membership,
        )

    def require_role(context: AuthContext, *roles: MembershipRole) -> None:
        if context.membership.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente para esta operação.",
            )

    def is_duplicate_sku_error(error: IntegrityError) -> bool:
        original_error = error.orig
        constraint_name = getattr(getattr(original_error, "diag", None), "constraint_name", None)
        if constraint_name == "uq_products_tenant_sku":
            return True
        return "products.tenant_id, products.sku" in str(original_error)

    def get_tenant_product(
        session: Session, tenant_id: UUID, product_id: UUID, *, lock: bool = False
    ) -> Product:
        query = select(Product).where(
            Product.id == product_id, Product.tenant_id == tenant_id
        )
        if lock:
            query = query.with_for_update()
        product = session.scalar(query)
        if product is None:
            raise HTTPException(status_code=404, detail="Produto não encontrado.")
        return product

    def get_tenant_order(
        session: Session, tenant_id: UUID, order_id: UUID, *, lock: bool = False
    ) -> Order:
        query = (
            select(Order)
            .where(Order.id == order_id, Order.tenant_id == tenant_id)
        )
        if lock:
            query = query.with_for_update()
        order = session.scalar(query)
        if order is None:
            raise HTTPException(status_code=404, detail="Pedido não encontrado.")
        return order

    @app.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    def ready(session: Annotated[Session, Depends(get_session)]) -> dict[str, str]:
        session.execute(select(1))
        return {"status": "ok"}

    @router.post("/auth/token", response_model=TokenResponse)
    def login(
        payload: LoginRequest,
        session: Annotated[Session, Depends(get_session)],
    ) -> TokenResponse:
        user = session.scalar(
            select(User).where(User.email == payload.email.lower())
        )
        membership = None
        if user is not None:
            membership = session.scalar(
                select(TenantMembership)
                .join(Tenant)
                .where(
                    TenantMembership.user_id == user.id,
                    Tenant.slug == payload.tenant_slug,
                )
            )
        password_hash = (
            user.password_hash if user is not None else DUMMY_PASSWORD_HASH
        )
        password_valid = verify_password(payload.password, password_hash)
        if (
            user is None
            or membership is None
            or not membership_is_active(membership)
            or not password_valid
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas.",
            )
        session.add(
            AccessLog(
                tenant_id=membership.tenant_id,
                user_id=user.id,
                action="POST /api/v1/auth/token (login)",
            )
        )
        session.commit()
        token, lifetime = issue_access_token(user, membership, settings)
        return TokenResponse(access_token=token, expires_in=lifetime)

    @router.get("/auth/me", response_model=CurrentUserResponse)
    def me(context: Annotated[AuthContext, Depends(current_context)]) -> dict:
        return {
            "user": context.user,
            "tenant": {
                "id": context.tenant.id,
                "slug": context.tenant.slug,
                "display_name": context.tenant.display_name,
                "status": context.tenant.status,
                "role": context.membership.role,
                "created_at": context.tenant.created_at,
            },
        }

    @router.get("/admin/tenants/me", response_model=CurrentUserResponse)
    def tenant_context(
        context: Annotated[AuthContext, Depends(current_context)],
    ) -> dict:
        return {
            "user": context.user,
            "tenant": {
                "id": context.tenant.id,
                "slug": context.tenant.slug,
                "display_name": context.tenant.display_name,
                "status": context.tenant.status,
                "role": context.membership.role,
                "created_at": context.tenant.created_at,
            },
        }

    @router.get(
        "/public/{tenant_slug}",
        response_model=PublicTenantResponse,
    )
    def public_tenant(
        tenant_slug: TenantSlug,
        session: Annotated[Session, Depends(get_session)],
    ) -> Tenant:
        tenant = session.scalar(
            select(Tenant).where(
                Tenant.slug == tenant_slug,
                Tenant.status == TenantStatus.ACTIVE,
            )
        )
        if tenant is None:
            raise HTTPException(status_code=404, detail="Catálogo não encontrado.")
        return tenant

    @router.get(
        "/public/{tenant_slug}/catalog",
        response_model=list[PublicProductResponse],
    )
    def public_catalog(
        tenant_slug: TenantSlug,
        session: Annotated[Session, Depends(get_session)],
        q: str | None = Query(default=None, max_length=160),
        category: str | None = Query(default=None, max_length=100),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> list[dict]:
        tenant = session.scalar(
            select(Tenant).where(
                Tenant.slug == tenant_slug,
                Tenant.status == TenantStatus.ACTIVE,
            )
        )
        if tenant is None:
            raise HTTPException(status_code=404, detail="Catálogo não encontrado.")
        query = select(Product).where(
            Product.tenant_id == tenant.id,
            Product.is_active.is_(True),
        )
        if q:
            query = query.where(
                Product.name.ilike(f"%{q}%") | Product.sku.ilike(f"%{q}%")
            )
        if category:
            query = query.where(Product.category == category)
        products = session.scalars(
            query.order_by(Product.name, Product.id).limit(limit).offset(offset)
        ).all()
        return [
            {
                "id": product.id,
                "sku": product.sku,
                "name": product.name,
                "category": product.category,
                "size": product.size,
                "color": product.color,
                "description": product.description,
                "price": product.price,
                "in_stock": product.stock_quantity > 0,
                "image_url": product.image_url,
            }
            for product in products
        ]

    @router.post(
        "/public/{tenant_slug}/orders",
        response_model=PublicOrderReceipt,
        status_code=status.HTTP_201_CREATED,
    )
    def create_public_order(
        tenant_slug: TenantSlug,
        payload: PublicOrderCreate,
        session: Annotated[Session, Depends(get_session)],
    ) -> dict:
        tenant = session.scalar(
            select(Tenant).where(
                Tenant.slug == tenant_slug,
                Tenant.status == TenantStatus.ACTIVE,
            )
        )
        if tenant is None:
            raise HTTPException(status_code=404, detail="Catálogo não encontrado.")
        requested = sorted(payload.items, key=lambda item: item.product_id)
        products = list(
            session.scalars(
                select(Product)
                .where(
                    Product.tenant_id == tenant.id,
                    Product.id.in_([item.product_id for item in requested]),
                    Product.is_active.is_(True),
                )
                .order_by(Product.id)
                .with_for_update()
            ).all()
        )
        if len(products) != len(requested):
            raise HTTPException(
                status_code=422,
                detail="Um ou mais produtos não existem ou estão indisponíveis.",
            )
        product_by_id = {product.id: product for product in products}
        total = Decimal("0.00")
        order_items = []
        for requested_item in requested:
            product = product_by_id[requested_item.product_id]
            if product.stock_quantity < requested_item.quantity:
                raise HTTPException(
                    status_code=409,
                    detail=f"Estoque insuficiente para o produto {product.sku}.",
                )
            line_total = (product.price * requested_item.quantity).quantize(
                CENT, rounding=ROUND_HALF_UP
            )
            total += line_total
            if total > MAX_ORDER_TOTAL:
                raise HTTPException(
                    status_code=422,
                    detail="O total do pedido excede o limite suportado.",
                )
            order_items.append(
                OrderItem(
                    tenant_id=tenant.id,
                    product_id=product.id,
                    quantity=requested_item.quantity,
                    unit_price=product.price,
                    line_total=line_total,
                )
            )
        customer = Customer(
            tenant_id=tenant.id,
            name=payload.customer_name,
            phone=payload.phone,
            email=str(payload.email).lower() if payload.email else None,
        )
        session.add(customer)
        session.flush()
        order = Order(
            tenant_id=tenant.id,
            customer_id=customer.id,
            status=OrderStatus.PENDING,
            source=OrderSource.CATALOG,
            fulfillment_method=payload.fulfillment_method,
            total=total,
            items=order_items,
        )
        session.add(order)
        session.commit()
        return {"order_id": order.id, "status": order.status, "total": order.total}

    @router.get("/admin/products", response_model=list[ProductResponse])
    def list_products(
        context: Annotated[AuthContext, Depends(current_context)],
        session: Annotated[Session, Depends(get_session)],
        q: str | None = Query(default=None, max_length=160),
        category: str | None = Query(default=None, max_length=100),
        limit: int = Query(default=100, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> list[dict]:
        require_role(
            context,
            MembershipRole.COMPANY_ADMIN,
            MembershipRole.INVENTORY_MANAGER,
            MembershipRole.COUNTER_OPERATOR,
        )
        query = select(Product).where(Product.tenant_id == context.tenant.id)
        if q:
            query = query.where(
                Product.name.ilike(f"%{q}%") | Product.sku.ilike(f"%{q}%")
            )
        if category:
            query = query.where(Product.category == category)
        products = list(
            session.scalars(
                query.order_by(Product.name, Product.id).limit(limit).offset(offset)
            ).all()
        )
        include_cost = context.membership.role in {
            MembershipRole.COMPANY_ADMIN,
            MembershipRole.INVENTORY_MANAGER,
        }
        return [
            {
                **ProductResponse.model_validate(product).model_dump(),
                **(
                    {}
                    if include_cost
                    else {
                        "cost_price": None,
                        "icms_rate": None,
                        "ipi_rate": None,
                        "pis_rate": None,
                        "cofins_rate": None,
                    }
                ),
            }
            for product in products
        ]

    @router.post(
        "/admin/products",
        response_model=ProductResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_product(
        payload: ProductCreate,
        context: Annotated[AuthContext, Depends(current_context)],
        session: Annotated[Session, Depends(get_session)],
    ) -> Product:
        require_role(
            context, MembershipRole.COMPANY_ADMIN, MembershipRole.INVENTORY_MANAGER
        )
        if session.scalar(
            select(Product.id).where(
                Product.tenant_id == context.tenant.id,
                Product.sku == payload.sku,
            )
        ):
            raise HTTPException(
                status_code=409, detail="Já existe um produto com esse SKU nesta empresa."
            )
        product = Product(
            tenant_id=context.tenant.id,
            sku=payload.sku,
            name=payload.name.strip(),
            category=payload.category.strip(),
            size=payload.size,
            color=payload.color,
            description=payload.description,
            price=payload.price,
            cost_price=payload.cost_price,
            icms_rate=payload.icms_rate,
            ipi_rate=payload.ipi_rate,
            pis_rate=payload.pis_rate,
            cofins_rate=payload.cofins_rate,
            stock_quantity=payload.stock_quantity,
            image_url=str(payload.image_url) if payload.image_url else None,
            is_active=payload.is_active,
        )
        try:
            session.add(product)
            session.flush()
            if payload.stock_quantity > 0:
                session.add(
                    InventoryMovement(
                        tenant_id=context.tenant.id,
                        product_id=product.id,
                        quantity_delta=payload.stock_quantity,
                        movement_type=InventoryMovementType.INITIAL,
                        note="Saldo inicial do cadastro do produto.",
                    )
                )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            if is_duplicate_sku_error(error):
                raise HTTPException(
                    status_code=409,
                    detail="Já existe um produto com esse SKU nesta empresa.",
                ) from None
            raise
        return product

    @router.patch("/admin/products/{product_id}", response_model=ProductResponse)
    def update_product(
        product_id: UUID,
        payload: ProductUpdate,
        context: Annotated[AuthContext, Depends(current_context)],
        session: Annotated[Session, Depends(get_session)],
    ) -> Product:
        require_role(
            context, MembershipRole.COMPANY_ADMIN, MembershipRole.INVENTORY_MANAGER
        )
        product = get_tenant_product(session, context.tenant.id, product_id, lock=True)
        updates = payload.model_dump(exclude_unset=True)
        if "sku" in updates and session.scalar(
            select(Product.id).where(
                Product.tenant_id == context.tenant.id,
                Product.sku == updates["sku"],
                Product.id != product.id,
            )
        ):
            raise HTTPException(
                status_code=409, detail="Já existe um produto com esse SKU nesta empresa."
            )
        for field, value in updates.items():
            if field in {"name", "category"} and value is not None:
                value = value.strip()
            if field == "image_url" and value is not None:
                value = str(value)
            setattr(product, field, value)
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            if is_duplicate_sku_error(error):
                raise HTTPException(
                    status_code=409,
                    detail="Já existe um produto com esse SKU nesta empresa.",
                ) from None
            raise
        return product

    @router.post(
        "/admin/products/{product_id}/inventory",
        response_model=InventoryMovementResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def adjust_inventory(
        product_id: UUID,
        payload: InventoryAdjustment,
        context: Annotated[AuthContext, Depends(current_context)],
        session: Annotated[Session, Depends(get_session)],
    ) -> InventoryMovement:
        require_role(
            context, MembershipRole.COMPANY_ADMIN, MembershipRole.INVENTORY_MANAGER
        )
        product = get_tenant_product(session, context.tenant.id, product_id, lock=True)
        new_quantity = product.stock_quantity + payload.quantity_delta
        if new_quantity < 0:
            raise HTTPException(
                status_code=409, detail="O saldo do estoque não pode ficar negativo."
            )
        product.stock_quantity = new_quantity
        movement = InventoryMovement(
            tenant_id=context.tenant.id,
            product_id=product.id,
            quantity_delta=payload.quantity_delta,
            movement_type=InventoryMovementType.ADJUSTMENT,
            note=payload.note,
        )
        session.add(movement)
        session.commit()
        return movement

    @router.get(
        "/admin/products/{product_id}/inventory",
        response_model=list[InventoryMovementResponse],
    )
    def list_inventory_movements(
        product_id: UUID,
        context: Annotated[AuthContext, Depends(current_context)],
        session: Annotated[Session, Depends(get_session)],
        limit: int = Query(default=100, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> list[InventoryMovement]:
        require_role(
            context,
            MembershipRole.COMPANY_ADMIN,
            MembershipRole.INVENTORY_MANAGER,
            MembershipRole.COUNTER_OPERATOR,
        )
        get_tenant_product(session, context.tenant.id, product_id)
        return list(
            session.scalars(
                select(InventoryMovement)
                .where(
                    InventoryMovement.tenant_id == context.tenant.id,
                    InventoryMovement.product_id == product_id,
                )
                .order_by(InventoryMovement.created_at.desc(), InventoryMovement.id)
                .limit(limit)
                .offset(offset)
            ).all()
        )

    @router.get("/admin/customers", response_model=list[CustomerResponse])
    def list_customers(
        context: Annotated[AuthContext, Depends(current_context)],
        session: Annotated[Session, Depends(get_session)],
        q: str | None = Query(default=None, max_length=160),
        limit: int = Query(default=100, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> list[Customer]:
        require_role(
            context,
            MembershipRole.COMPANY_ADMIN,
            MembershipRole.COUNTER_OPERATOR,
            MembershipRole.HUMAN_SUPPORT,
        )
        query = select(Customer).where(Customer.tenant_id == context.tenant.id)
        if q:
            query = query.where(
                Customer.name.ilike(f"%{q}%")
                | Customer.phone.ilike(f"%{q}%")
                | Customer.email.ilike(f"%{q}%")
                | Customer.document.ilike(f"%{q}%")
            )
        return list(
            session.scalars(
                query.order_by(Customer.name, Customer.id).limit(limit).offset(offset)
            ).all()
        )

    @router.post(
        "/admin/customers",
        response_model=CustomerResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_customer(
        payload: CustomerCreate,
        context: Annotated[AuthContext, Depends(current_context)],
        session: Annotated[Session, Depends(get_session)],
    ) -> Customer:
        require_role(
            context,
            MembershipRole.COMPANY_ADMIN,
            MembershipRole.COUNTER_OPERATOR,
            MembershipRole.HUMAN_SUPPORT,
        )
        customer = Customer(
            tenant_id=context.tenant.id,
            name=payload.name.strip(),
            phone=payload.phone,
            email=str(payload.email).lower() if payload.email else None,
            document=payload.document,
            address=payload.address,
            postal_code=payload.postal_code,
        )
        session.add(customer)
        session.commit()
        return customer

    @router.post(
        "/admin/orders",
        response_model=OrderResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_order(
        payload: OrderCreate,
        context: Annotated[AuthContext, Depends(current_context)],
        session: Annotated[Session, Depends(get_session)],
    ) -> Order:
        require_role(
            context, MembershipRole.COMPANY_ADMIN, MembershipRole.COUNTER_OPERATOR
        )
        customer = session.scalar(
            select(Customer).where(
                Customer.id == payload.customer_id,
                Customer.tenant_id == context.tenant.id,
            )
        )
        if customer is None:
            raise HTTPException(status_code=404, detail="Cliente não encontrado.")
        product_ids = sorted(item.product_id for item in payload.items)
        products = list(
            session.scalars(
                select(Product)
                .where(
                    Product.tenant_id == context.tenant.id,
                    Product.id.in_(product_ids),
                    Product.is_active.is_(True),
                )
                .order_by(Product.id)
                .with_for_update()
            ).all()
        )
        if len(products) != len(product_ids):
            raise HTTPException(
                status_code=422,
                detail="Um ou mais produtos não existem ou estão inativos nesta empresa.",
            )
        product_by_id = {product.id: product for product in products}
        order_items = []
        total = Decimal("0.00")
        for requested_item in payload.items:
            product = product_by_id[requested_item.product_id]
            line_total = (product.price * requested_item.quantity).quantize(
                CENT, rounding=ROUND_HALF_UP
            )
            if line_total > MAX_ORDER_TOTAL or total + line_total > MAX_ORDER_TOTAL:
                raise HTTPException(
                    status_code=422,
                    detail="O total do pedido excede o limite suportado.",
                )
            total += line_total
            order_items.append(
                OrderItem(
                    tenant_id=context.tenant.id,
                    product_id=product.id,
                    quantity=requested_item.quantity,
                    unit_price=product.price,
                    line_total=line_total,
                )
            )
        order = Order(
            tenant_id=context.tenant.id,
            customer_id=customer.id,
            status=OrderStatus.QUOTE,
            source=payload.source,
            fulfillment_method=payload.fulfillment_method,
            total=total,
            items=order_items,
        )
        session.add(order)
        session.commit()
        return order

    @router.get("/admin/orders", response_model=list[OrderResponse])
    def list_orders(
        context: Annotated[AuthContext, Depends(current_context)],
        session: Annotated[Session, Depends(get_session)],
        order_status: OrderStatus | None = Query(default=None, alias="status"),
        limit: int = Query(default=100, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> list[Order]:
        require_role(
            context, MembershipRole.COMPANY_ADMIN, MembershipRole.COUNTER_OPERATOR
        )
        query = select(Order).where(Order.tenant_id == context.tenant.id)
        if order_status is not None:
            query = query.where(Order.status == order_status)
        return list(
            session.scalars(
                query.order_by(Order.created_at.desc(), Order.id).limit(limit).offset(offset)
            ).all()
        )

    @router.get("/admin/orders/{order_id}", response_model=OrderResponse)
    def get_order(
        order_id: UUID,
        context: Annotated[AuthContext, Depends(current_context)],
        session: Annotated[Session, Depends(get_session)],
    ) -> Order:
        require_role(
            context, MembershipRole.COMPANY_ADMIN, MembershipRole.COUNTER_OPERATOR
        )
        return get_tenant_order(session, context.tenant.id, order_id)

    @router.patch("/admin/orders/{order_id}/status", response_model=OrderResponse)
    def update_order_status(
        order_id: UUID,
        payload: OrderStatusUpdate,
        context: Annotated[AuthContext, Depends(current_context)],
        session: Annotated[Session, Depends(get_session)],
    ) -> Order:
        require_role(
            context, MembershipRole.COMPANY_ADMIN, MembershipRole.COUNTER_OPERATOR
        )
        order = get_tenant_order(session, context.tenant.id, order_id, lock=True)
        current_status = OrderStatus(order.status)
        if payload.status not in ORDER_TRANSITIONS[current_status]:
            raise HTTPException(
                status_code=409,
                detail=f"Transição de {current_status.value} para {payload.status.value} não permitida.",
            )
        if payload.status == OrderStatus.READY_FOR_PICKUP and (
            order.fulfillment_method != FulfillmentMethod.PICKUP
        ):
            raise HTTPException(
                status_code=409,
                detail="Somente pedidos com retirada podem ficar prontos para retirada.",
            )
        if payload.status == OrderStatus.IN_TRANSIT and (
            order.fulfillment_method != FulfillmentMethod.DELIVERY
        ):
            raise HTTPException(
                status_code=409,
                detail="Somente pedidos com entrega podem ficar em trânsito.",
            )
        if payload.status == OrderStatus.COMPLETED:
            if (
                order.fulfillment_method == FulfillmentMethod.PICKUP
                and current_status != OrderStatus.READY_FOR_PICKUP
            ) or (
                order.fulfillment_method == FulfillmentMethod.DELIVERY
                and current_status != OrderStatus.IN_TRANSIT
            ):
                raise HTTPException(
                    status_code=409,
                    detail="A modalidade exige que o pedido passe pelo estado de atendimento anterior.",
                )
            order_items = sorted(order.items, key=lambda item: item.product_id)
            products = [
                get_tenant_product(
                    session, context.tenant.id, item.product_id, lock=True
                )
                for item in order_items
            ]
            for item, product in zip(order_items, products, strict=True):
                if product.stock_quantity < item.quantity:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Estoque insuficiente para o produto {product.sku}.",
                    )
            for item, product in zip(order_items, products, strict=True):
                product.stock_quantity -= item.quantity
                session.add(
                    InventoryMovement(
                        tenant_id=context.tenant.id,
                        product_id=product.id,
                        quantity_delta=-item.quantity,
                        movement_type=InventoryMovementType.SALE,
                        reference_id=order.id,
                        note="Baixa de estoque pela conclusão do pedido.",
                    )
                )
        order.status = payload.status
        session.commit()
        return order

    @router.get("/admin/employees", response_model=list[EmployeeResponse])
    def list_employees(
        context: Annotated[AuthContext, Depends(current_context)],
        session: Annotated[Session, Depends(get_session)],
    ) -> list[dict]:
        require_role(context, MembershipRole.COMPANY_ADMIN)
        memberships = session.scalars(
            select(TenantMembership)
            .where(TenantMembership.tenant_id == context.tenant.id)
            .order_by(TenantMembership.created_at, TenantMembership.id)
        ).all()
        return [
            {
                "id": membership.id,
                "user_id": membership.user_id,
                "email": membership.user.email,
                "display_name": membership.display_name,
                "role": membership.role,
                "is_active": membership.is_active and membership.user.is_active,
                "created_at": membership.created_at,
            }
            for membership in memberships
        ]

    @router.post(
        "/admin/employees",
        response_model=EmployeeResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_employee(
        payload: EmployeeCreate,
        context: Annotated[AuthContext, Depends(current_context)],
        session: Annotated[Session, Depends(get_session)],
    ) -> dict:
        require_role(context, MembershipRole.COMPANY_ADMIN)
        email = str(payload.email).lower()
        if session.scalar(select(User.id).where(User.email == email)):
            raise HTTPException(
                status_code=409,
                detail="Este e-mail já possui uma conta. Use outro endereço.",
            )
        user = User(email=email, password_hash=hash_password(payload.password))
        membership = TenantMembership(
            tenant_id=context.tenant.id,
            user=user,
            display_name=payload.display_name,
            role=payload.role,
            is_active=True,
        )
        session.add(membership)
        session.commit()
        return {
            "id": membership.id,
            "user_id": user.id,
            "email": user.email,
            "display_name": membership.display_name,
            "role": membership.role,
            "is_active": membership.is_active,
            "created_at": membership.created_at,
        }

    @router.patch("/admin/employees/{membership_id}", response_model=EmployeeResponse)
    def update_employee(
        membership_id: UUID,
        payload: EmployeeUpdate,
        context: Annotated[AuthContext, Depends(current_context)],
        session: Annotated[Session, Depends(get_session)],
    ) -> dict:
        require_role(context, MembershipRole.COMPANY_ADMIN)
        membership = session.scalar(
            select(TenantMembership)
            .where(
                TenantMembership.id == membership_id,
                TenantMembership.tenant_id == context.tenant.id,
            )
            .with_for_update()
        )
        if membership is None:
            raise HTTPException(status_code=404, detail="Funcionário não encontrado.")
        updates = payload.model_dump(exclude_unset=True)
        next_role = updates.get("role", membership.role)
        next_active = updates.get("is_active", membership.is_active)
        if membership.user_id == context.user.id and next_active is False:
            raise HTTPException(
                status_code=409,
                detail="Não é possível desativar o próprio acesso.",
            )
        if (
            membership.role == MembershipRole.COMPANY_ADMIN
            and membership.is_active
            and (
                next_role != MembershipRole.COMPANY_ADMIN
                or not next_active
            )
        ):
            other_admin = session.scalar(
                select(TenantMembership.id)
                .join(User)
                .where(
                    TenantMembership.tenant_id == context.tenant.id,
                    TenantMembership.id != membership.id,
                    TenantMembership.role == MembershipRole.COMPANY_ADMIN,
                    TenantMembership.is_active.is_(True),
                    User.is_active.is_(True),
                )
                .limit(1)
            )
            if other_admin is None:
                raise HTTPException(
                    status_code=409,
                    detail="A empresa precisa manter ao menos uma administradora ativa.",
                )
        for field, value in updates.items():
            setattr(membership, field, value)
        session.commit()
        return {
            "id": membership.id,
            "user_id": membership.user_id,
            "email": membership.user.email,
            "display_name": membership.display_name,
            "role": membership.role,
            "is_active": membership.is_active and membership.user.is_active,
            "created_at": membership.created_at,
        }

    @router.get("/admin/suppliers", response_model=list[SupplierResponse])
    def list_suppliers(
        context: Annotated[AuthContext, Depends(current_context)],
        session: Annotated[Session, Depends(get_session)],
        q: str | None = Query(default=None, max_length=160),
        limit: int = Query(default=100, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> list[Supplier]:
        require_role(context, MembershipRole.COMPANY_ADMIN, MembershipRole.INVENTORY_MANAGER)
        query = select(Supplier).where(Supplier.tenant_id == context.tenant.id)
        if q:
            query = query.where(Supplier.name.ilike(f"%{q}%"))
        return list(
            session.scalars(
                query.order_by(Supplier.name, Supplier.id).limit(limit).offset(offset)
            ).all()
        )

    @router.post(
        "/admin/suppliers",
        response_model=SupplierResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_supplier(
        payload: SupplierCreate,
        context: Annotated[AuthContext, Depends(current_context)],
        session: Annotated[Session, Depends(get_session)],
    ) -> Supplier:
        require_role(context, MembershipRole.COMPANY_ADMIN, MembershipRole.INVENTORY_MANAGER)
        supplier = Supplier(
            tenant_id=context.tenant.id,
            name=payload.name,
            document=payload.document,
            contact_name=payload.contact_name,
            phone=payload.phone,
            email=str(payload.email).lower() if payload.email else None,
        )
        session.add(supplier)
        session.commit()
        return supplier

    @router.get("/admin/purchases", response_model=list[PurchaseResponse])
    def list_purchases(
        context: Annotated[AuthContext, Depends(current_context)],
        session: Annotated[Session, Depends(get_session)],
        limit: int = Query(default=100, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> list[Purchase]:
        require_role(context, MembershipRole.COMPANY_ADMIN, MembershipRole.INVENTORY_MANAGER)
        return list(
            session.scalars(
                select(Purchase)
                .where(Purchase.tenant_id == context.tenant.id)
                .order_by(Purchase.created_at.desc(), Purchase.id)
                .limit(limit)
                .offset(offset)
            ).all()
        )

    @router.post(
        "/admin/purchases",
        response_model=PurchaseResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_purchase(
        payload: PurchaseCreate,
        context: Annotated[AuthContext, Depends(current_context)],
        session: Annotated[Session, Depends(get_session)],
    ) -> Purchase:
        require_role(context, MembershipRole.COMPANY_ADMIN, MembershipRole.INVENTORY_MANAGER)
        supplier = session.scalar(
            select(Supplier).where(
                Supplier.id == payload.supplier_id,
                Supplier.tenant_id == context.tenant.id,
            )
        )
        if supplier is None:
            raise HTTPException(status_code=404, detail="Fornecedor não encontrado.")
        requested = sorted(payload.items, key=lambda item: item.product_id)
        products = list(
            session.scalars(
                select(Product)
                .where(
                    Product.tenant_id == context.tenant.id,
                    Product.id.in_([item.product_id for item in requested]),
                )
                .order_by(Product.id)
                .with_for_update()
            ).all()
        )
        if len(products) != len(requested):
            raise HTTPException(
                status_code=422,
                detail="Um ou mais produtos não existem nesta empresa.",
            )
        total = Decimal("0.00")
        purchase_items = []
        for item in requested:
            line_total = (item.quantity * item.unit_cost).quantize(
                CENT, rounding=ROUND_HALF_UP
            )
            total += line_total
            if total > MAX_ORDER_TOTAL:
                raise HTTPException(
                    status_code=422,
                    detail="O valor da compra excede o limite suportado.",
                )
            purchase_items.append(
                PurchaseItem(
                    tenant_id=context.tenant.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_cost=item.unit_cost,
                    line_total=line_total,
                )
            )
        purchase = Purchase(
            tenant_id=context.tenant.id,
            supplier_id=supplier.id,
            status="draft",
            total=total,
            items=purchase_items,
        )
        session.add(purchase)
        session.commit()
        return purchase

    @router.patch(
        "/admin/purchases/{purchase_id}/status",
        response_model=PurchaseResponse,
    )
    def update_purchase_status(
        purchase_id: UUID,
        payload: PurchaseStatusUpdate,
        context: Annotated[AuthContext, Depends(current_context)],
        session: Annotated[Session, Depends(get_session)],
    ) -> Purchase:
        require_role(context, MembershipRole.COMPANY_ADMIN, MembershipRole.INVENTORY_MANAGER)
        purchase = session.scalar(
            select(Purchase)
            .where(
                Purchase.id == purchase_id,
                Purchase.tenant_id == context.tenant.id,
            )
            .with_for_update()
        )
        if purchase is None:
            raise HTTPException(status_code=404, detail="Compra não encontrada.")
        if purchase.status != "draft":
            raise HTTPException(
                status_code=409,
                detail="Somente compras em rascunho podem ser recebidas ou canceladas.",
            )
        if payload.status == "received":
            items = sorted(purchase.items, key=lambda item: item.product_id)
            products = [
                get_tenant_product(
                    session, context.tenant.id, item.product_id, lock=True
                )
                for item in items
            ]
            for item, product in zip(items, products, strict=True):
                product.stock_quantity += item.quantity
                session.add(
                    InventoryMovement(
                        tenant_id=context.tenant.id,
                        product_id=product.id,
                        quantity_delta=item.quantity,
                        movement_type=InventoryMovementType.PURCHASE,
                        reference_id=purchase.id,
                        note="Entrada de estoque pela recepção de compra.",
                    )
                )
            supplier = session.scalar(
                select(Supplier).where(
                    Supplier.id == purchase.supplier_id,
                    Supplier.tenant_id == context.tenant.id,
                )
            )
            if supplier is None:
                raise HTTPException(
                    status_code=409,
                    detail="O fornecedor associado à compra não está disponível.",
                )
            session.add(
                FinancialEntry(
                    tenant_id=context.tenant.id,
                    entry_type="payable",
                    description=f"Compra recebida - {supplier.name}",
                    amount=purchase.total,
                    due_date=date.today(),
                    status="pending",
                )
            )
        purchase.status = payload.status
        session.commit()
        return purchase

    @router.get("/admin/finance", response_model=list[FinancialEntryResponse])
    def list_financial_entries(
        context: Annotated[AuthContext, Depends(current_context)],
        session: Annotated[Session, Depends(get_session)],
        entry_status: str | None = Query(default=None, alias="status", pattern="^(pending|settled|cancelled)$"),
        limit: int = Query(default=100, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> list[FinancialEntry]:
        require_role(context, MembershipRole.COMPANY_ADMIN)
        query = select(FinancialEntry).where(
            FinancialEntry.tenant_id == context.tenant.id
        )
        if entry_status:
            query = query.where(FinancialEntry.status == entry_status)
        return list(
            session.scalars(
                query.order_by(FinancialEntry.due_date, FinancialEntry.id)
                .limit(limit)
                .offset(offset)
            ).all()
        )

    @router.post(
        "/admin/finance",
        response_model=FinancialEntryResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_financial_entry(
        payload: FinancialEntryCreate,
        context: Annotated[AuthContext, Depends(current_context)],
        session: Annotated[Session, Depends(get_session)],
    ) -> FinancialEntry:
        require_role(context, MembershipRole.COMPANY_ADMIN)
        entry = FinancialEntry(
            tenant_id=context.tenant.id,
            entry_type=payload.entry_type,
            description=payload.description,
            amount=payload.amount,
            due_date=payload.due_date,
            status="pending",
        )
        session.add(entry)
        session.commit()
        return entry

    @router.patch(
        "/admin/finance/{entry_id}/settle",
        response_model=FinancialEntryResponse,
    )
    def settle_financial_entry(
        entry_id: UUID,
        context: Annotated[AuthContext, Depends(current_context)],
        session: Annotated[Session, Depends(get_session)],
    ) -> FinancialEntry:
        require_role(context, MembershipRole.COMPANY_ADMIN)
        entry = session.scalar(
            select(FinancialEntry)
            .where(
                FinancialEntry.id == entry_id,
                FinancialEntry.tenant_id == context.tenant.id,
            )
            .with_for_update()
        )
        if entry is None:
            raise HTTPException(status_code=404, detail="Lançamento não encontrado.")
        if entry.status != "pending":
            raise HTTPException(
                status_code=409,
                detail="Somente lançamentos pendentes podem ser baixados.",
            )
        entry.status = "settled"
        entry.settled_at = datetime.now(timezone.utc)
        session.commit()
        return entry

    @router.get("/admin/access-logs", response_model=list[AccessLogResponse])
    def list_access_logs(
        context: Annotated[AuthContext, Depends(current_context)],
        session: Annotated[Session, Depends(get_session)],
        limit: int = Query(default=100, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> list[AccessLog]:
        require_role(context, MembershipRole.COMPANY_ADMIN)
        return list(
            session.scalars(
                select(AccessLog)
                .where(AccessLog.tenant_id == context.tenant.id)
                .order_by(AccessLog.created_at.desc(), AccessLog.id)
                .limit(limit)
                .offset(offset)
            ).all()
        )

    app.include_router(router)
    return app


def create_app_from_environment() -> FastAPI:
    from commercial_platform.config import Settings
    from commercial_platform.database import create_session_factory

    settings = Settings.from_environment()
    return create_app(settings, create_session_factory(settings))
