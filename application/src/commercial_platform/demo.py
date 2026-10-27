import secrets
from pathlib import Path

import uvicorn
from sqlalchemy import select

from commercial_platform.api import create_app
from commercial_platform.config import Settings
from commercial_platform.database import create_session_factory
from commercial_platform.models import (
    Base,
    Customer,
    MembershipRole,
    Product,
    Supplier,
    Tenant,
    TenantMembership,
    User,
)
from commercial_platform.security import hash_password


DEMO_EMAIL = "admin@demo.example"


def main() -> None:
    data_directory = Path(__file__).resolve().parents[2] / ".local"
    data_directory.mkdir(parents=True, exist_ok=True)
    database_path = (data_directory / "demo.sqlite3").as_posix()
    password_path = data_directory / "demo-password.txt"
    if password_path.exists():
        demo_password = password_path.read_text(encoding="utf-8").strip()
        if not demo_password:
            raise RuntimeError(f"The local demo password file is empty: {password_path}")
    else:
        demo_password = secrets.token_urlsafe(24)
        password_path.write_text(demo_password, encoding="utf-8")
    settings = Settings(
        database_url=f"sqlite:///{database_path}",
        jwt_secret_key=secrets.token_urlsafe(48),
    )
    sessions = create_session_factory(settings)
    Base.metadata.create_all(sessions.kw["bind"])

    with sessions.begin() as session:
        tenant = session.scalar(select(Tenant).where(Tenant.slug == "demo"))
        if tenant is None:
            tenant = Tenant(
                slug="demo",
                display_name="Lisa Comercial — Demonstração",
                status="active",
            )
            user = User(
                email=DEMO_EMAIL,
                password_hash=hash_password(demo_password),
                is_active=True,
            )
            session.add_all((tenant, user))
            session.flush()
            session.add(
                TenantMembership(
                    tenant_id=tenant.id,
                    user_id=user.id,
                    display_name="Administradora Demo",
                    role=MembershipRole.COMPANY_ADMIN,
                    is_active=True,
                )
            )
            session.add_all(
                [
                    Product(
                        tenant_id=tenant.id,
                        sku="LIM-001",
                        name="Detergente concentrado",
                        category="Limpeza",
                        size="5 L",
                        color=None,
                        description="Produto de demonstração para a rotina de limpeza.",
                        price="28.90",
                        stock_quantity="24",
                        is_active=True,
                    ),
                    Product(
                        tenant_id=tenant.id,
                        sku="PISC-001",
                        name="Cloro granulado",
                        category="Piscina",
                        size="10 kg",
                        color=None,
                        description="Produto de demonstração para tratamento de piscinas.",
                        price="189.90",
                        stock_quantity="12",
                        is_active=True,
                    ),
                    Product(
                        tenant_id=tenant.id,
                        sku="CAM-AZ-M",
                        name="Camiseta Lisa",
                        category="Vestuário",
                        size="M",
                        color="Azul",
                        description="Variação de demonstração com SKU e saldo próprios.",
                        price="49.90",
                        stock_quantity="8",
                        is_active=True,
                    ),
                    Customer(
                        tenant_id=tenant.id,
                        name="Cliente Demonstração",
                        phone="5561999990000",
                        email="cliente@demo.example",
                    ),
                    Supplier(
                        tenant_id=tenant.id,
                        name="Fornecedor Demonstração",
                        contact_name="Equipe Comercial",
                        phone="5561999990001",
                        email="fornecedor@demo.example",
                    ),
                ]
            )
        else:
            user = session.scalar(select(User).where(User.email == DEMO_EMAIL))
            if user is None:
                raise RuntimeError("The local demo tenant exists without its demo administrator.")
            user.password_hash = hash_password(demo_password)

    print("Ambiente local de demonstração — não use estes dados em produção.", flush=True)
    print(f"E-mail: {DEMO_EMAIL}", flush=True)
    print(f"Senha local: {demo_password}", flush=True)
    print("Empresa: demo", flush=True)
    print("API: http://127.0.0.1:8000", flush=True)
    print(f"Banco local: {database_path}", flush=True)
    uvicorn.run(
        create_app(settings, sessions),
        host="127.0.0.1",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()
