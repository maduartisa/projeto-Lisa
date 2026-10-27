from datetime import date, datetime
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
    size: str | None = Field(default=None, max_length=64)
    color: str | None = Field(default=None, max_length=64)
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

    @field_validator("size", "color")
    @classmethod
    def normalize_variant_attribute(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class ProductUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    name: str | None = Field(default=None, min_length=1, max_length=160)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    size: str | None = Field(default=None, max_length=64)
    color: str | None = Field(default=None, max_length=64)
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

    @field_validator("size", "color")
    @classmethod
    def normalize_variant_attribute(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

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
    size: str | None
    color: str | None
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
    size: str | None
    color: str | None
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


class PublicOrderCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=160)
    phone: str | None = Field(default=None, min_length=1, max_length=32)
    email: EmailStr | None = None
    fulfillment_method: FulfillmentMethod
    items: list[OrderItemCreate] = Field(min_length=1, max_length=100)

    @field_validator("customer_name", "phone")
    @classmethod
    def public_contact_fields_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("O campo não pode ficar vazio.")
        return value

    @model_validator(mode="after")
    def require_contact_and_unique_products(self):
        if not self.phone and not self.email:
            raise ValueError("Informe telefone ou e-mail para contato.")
        if self.fulfillment_method == FulfillmentMethod.COUNTER:
            raise ValueError("Escolha retirada ou entrega para o pedido online.")
        product_ids = [item.product_id for item in self.items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Cada produto deve aparecer uma única vez no pedido.")
        return self


class PublicOrderReceipt(BaseModel):
    order_id: UUID
    status: OrderStatus
    total: Decimal


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


class EmployeeCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=160)
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    role: MembershipRole

    @field_validator("display_name")
    @classmethod
    def employee_name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O nome não pode ficar vazio.")
        return value


class EmployeeUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    role: MembershipRole | None = None
    is_active: bool | None = None

    @field_validator("display_name")
    @classmethod
    def employee_name_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("O nome não pode ficar vazio.")
        return value

    @model_validator(mode="after")
    def reject_null_access_fields(self):
        for field in ("role", "is_active"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} não pode ser nulo.")
        return self


class EmployeeResponse(BaseModel):
    id: UUID
    user_id: UUID
    email: EmailStr
    display_name: str | None
    role: MembershipRole
    is_active: bool
    created_at: datetime


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    document: str | None = Field(default=None, max_length=32)
    contact_name: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None

    @field_validator("name")
    @classmethod
    def supplier_name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O nome do fornecedor não pode ficar vazio.")
        return value


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    document: str | None
    contact_name: str | None
    phone: str | None
    email: EmailStr | None
    created_at: datetime


class PurchaseItemCreate(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=3, allow_inf_nan=False)
    unit_cost: Decimal = Field(ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False)


class PurchaseCreate(BaseModel):
    supplier_id: UUID
    items: list[PurchaseItemCreate] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def reject_duplicate_products(self):
        product_ids = [item.product_id for item in self.items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Cada produto deve aparecer uma única vez na compra.")
        return self


class PurchaseStatusUpdate(BaseModel):
    status: str = Field(pattern=r"^(received|cancelled)$")


class PurchaseItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    quantity: Decimal
    unit_cost: Decimal
    line_total: Decimal


class PurchaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    supplier_id: UUID
    status: str
    total: Decimal
    created_at: datetime
    items: list[PurchaseItemResponse]


class FinancialEntryCreate(BaseModel):
    entry_type: str = Field(pattern=r"^(payable|receivable)$")
    description: str = Field(min_length=1, max_length=240)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2, allow_inf_nan=False)
    due_date: date

    @field_validator("description")
    @classmethod
    def description_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A descrição não pode ficar vazia.")
        return value


class FinancialEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entry_type: str
    description: str
    amount: Decimal
    due_date: date
    status: str
    settled_at: datetime | None
    created_at: datetime


class AccessLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    action: str
    created_at: datetime
