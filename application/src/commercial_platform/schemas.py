from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    StringConstraints,
    field_validator,
    model_validator,
)

from commercial_platform.models import (
    FulfillmentMethod,
    InventoryMovementType,
    MembershipRole,
    OrderSource,
    OrderStatus,
    TenantStatus,
)

TenantSlug = Annotated[
    str,
    StringConstraints(
        min_length=3,
        max_length=63,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        strip_whitespace=True,
    ),
]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    tenant_slug: TenantSlug


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthenticatedUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr


class CurrentTenant(BaseModel):
    id: UUID
    slug: str
    display_name: str
    status: TenantStatus
    role: MembershipRole
    created_at: datetime


class CurrentUserResponse(BaseModel):
    user: AuthenticatedUser
    tenant: CurrentTenant


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal = Field(
        ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False
    )
    stock_quantity: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        max_digits=14,
        decimal_places=3,
        allow_inf_nan=False,
    )
    image_url: HttpUrl | None = Field(default=None, max_length=2048)
    is_active: bool = True

    @field_validator("name", "category")
    @classmethod
    def product_text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O campo não pode ficar vazio.")
        return value


class ProductUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    name: str | None = Field(default=None, min_length=1, max_length=160)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
        allow_inf_nan=False,
    )
    image_url: HttpUrl | None = Field(default=None, max_length=2048)
    is_active: bool | None = None

    @field_validator("name", "category")
    @classmethod
    def product_text_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("O campo não pode ficar vazio.")
        return value

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        for field in ("sku", "name", "category", "price", "is_active"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} não pode ser nulo.")
        return self


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sku: str
    name: str
    category: str
    description: str | None
    price: Decimal
    stock_quantity: Decimal
    image_url: str | None
    is_active: bool
    created_at: datetime


class PublicProductResponse(BaseModel):
    id: UUID
    sku: str
    name: str
    category: str
    description: str | None
    price: Decimal
    in_stock: bool
    image_url: str | None


class PublicTenantResponse(BaseModel):
    slug: TenantSlug
    display_name: str


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    phone: str | None = Field(default=None, min_length=1, max_length=32)
    email: EmailStr | None = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O nome não pode ficar vazio.")
        return value


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    phone: str | None
    email: EmailStr | None
    created_at: datetime


class InventoryAdjustment(BaseModel):
    quantity_delta: Decimal = Field(
        allow_inf_nan=False,
        max_digits=14,
        decimal_places=3,
    )
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_nonzero_delta(self):
        if self.quantity_delta == 0:
            raise ValueError("A movimentação deve alterar o saldo.")
        return self


class InventoryMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    quantity_delta: Decimal
    movement_type: InventoryMovementType
    reference_id: UUID | None
    note: str | None
    created_at: datetime


class OrderItemCreate(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(
        gt=0,
        max_digits=14,
        decimal_places=3,
        allow_inf_nan=False,
    )


class OrderCreate(BaseModel):
    customer_id: UUID
    source: OrderSource
    fulfillment_method: FulfillmentMethod
    items: list[OrderItemCreate] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def reject_duplicate_products(self):
        product_ids = [item.product_id for item in self.items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Cada produto deve aparecer uma única vez no pedido.")
        return self


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    status: OrderStatus
    source: OrderSource
    fulfillment_method: FulfillmentMethod
    total: Decimal
    created_at: datetime
    items: list[OrderItemResponse]
