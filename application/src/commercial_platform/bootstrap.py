import getpass
import re
import sys

from sqlalchemy import select

from commercial_platform.config import Settings
from commercial_platform.database import create_session_factory
from commercial_platform.models import (
    MembershipRole,
    Tenant,
    TenantMembership,
    User,
)
from commercial_platform.security import hash_password


def main() -> int:
    settings = Settings.from_environment()
    sessions = create_session_factory(settings)
    slug = input("Identificador da empresa (slug): ").strip()
    display_name = input("Nome comercial: ").strip()
    email = input("E-mail do administrador: ").strip().lower()
    password = getpass.getpass("Senha inicial (mínimo 12 caracteres): ")
    confirmation = getpass.getpass("Confirme a senha: ")

    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) or not 3 <= len(slug) <= 63:
        print("Slug inválido; use letras minúsculas, números e hífens.", file=sys.stderr)
        return 2
    if not display_name or len(display_name) > 160:
        print("Nome comercial inválido.", file=sys.stderr)
        return 2
    if len(password) < 12 or password != confirmation:
        print("A senha deve ter ao menos 12 caracteres e as confirmações devem coincidir.", file=sys.stderr)
        return 2

    with sessions.begin() as session:
        if session.scalar(select(Tenant.id).where(Tenant.slug == slug)):
            print("Já existe uma empresa com esse slug.", file=sys.stderr)
            return 2
        if session.scalar(select(User.id).where(User.email == email)):
            print("Já existe um usuário com esse e-mail.", file=sys.stderr)
            return 2
        tenant = Tenant(slug=slug, display_name=display_name, status="active")
        user = User(email=email, password_hash=hash_password(password), is_active=True)
        session.add_all((tenant, user))
        session.flush()
        session.add(
            TenantMembership(
                tenant_id=tenant.id,
                user_id=user.id,
                role=MembershipRole.COMPANY_ADMIN,
                is_active=True,
            )
        )
    print(f"Empresa e administrador inicial criados para '{slug}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
