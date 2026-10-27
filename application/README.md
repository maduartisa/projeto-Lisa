# Aplicação — fundação multiempresa

Esta entrega implementa identidade e tenancy, catálogo, clientes, estoque e o fluxo inicial de orçamento/pedido. Ainda não inclui interfaces web, integrações WhatsApp/IA nem serviços ECS.

A interface web responsiva está no diretório [`web/`](web/README.md).

## Requisitos

- Python 3.11+
- PostgreSQL 17 (o mesmo major da infraestrutura aprovada)

## Preparar ambiente

Na raiz do repositório, no PowerShell:

```powershell
Set-Location .\application
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:DATABASE_URL = "postgresql+psycopg://localhost/platform_dev"
$env:JWT_SECRET_KEY = (python -c "import secrets; print(secrets.token_urlsafe(48))")
```

Configure a autenticação local do PostgreSQL sem gravar credenciais no repositório. Não use dados reais da Lisa; injete segredos de produção pelo Secrets Manager. Gere uma chave nova por ambiente e mantenha-a estável entre réplicas do mesmo ambiente.

## Migrar e iniciar

```powershell
alembic upgrade head
python -m commercial_platform.bootstrap
uvicorn commercial_platform.asgi:app --host 127.0.0.1 --port 8000
```

O comando de bootstrap solicita slug, nome comercial, e-mail e senha inicial em prompts; a senha não é passada na linha de comando. Aplique a migração antes de criar a empresa.

## Rotas iniciais

- `GET /health/live`: processo ativo.
- `GET /health/ready`: verifica conexão com banco.
- `POST /api/v1/auth/token`: autentica usuário, senha e slug da empresa e emite token de curta duração.
- `GET /api/v1/auth/me`: retorna o usuário e o tenant fixado no token.
- `GET /api/v1/admin/tenants/me`: exemplo de rota administrativa autenticada.
- `GET /api/v1/public/{tenant_slug}/catalog`: consulta pública, somente de produtos ativos.
- `GET /api/v1/public/{tenant_slug}`: nome comercial público da empresa.
- `GET|POST /api/v1/admin/products`: consulta e cadastro de produtos por empresa.
- `PATCH /api/v1/admin/products/{product_id}`: atualização de produto.
- `GET|POST /api/v1/admin/customers`: consulta e cadastro de clientes por empresa.
- `POST /api/v1/admin/products/{product_id}/inventory`: ajuste controlado de estoque.
- `GET /api/v1/admin/products/{product_id}/inventory`: histórico de movimentações.
- `GET|POST /api/v1/admin/orders` e `GET /api/v1/admin/orders/{order_id}`: criação e consulta de pedidos.
- `PATCH /api/v1/admin/orders/{order_id}/status`: transição validada de estado.

O token não aceita seleção livre de tenant em headers ou parâmetros. Em cada requisição, a API verifica novamente usuário, membership, status do tenant e papel atual no banco. Quando o vínculo é revogado ou o tenant suspenso, o token deixa de autorizar acesso.

Todos os recursos operacionais são consultados no escopo do tenant autenticado, reforçado por chaves estrangeiras compostas no banco. O pedido guarda preço e total do momento da cotação. O estoque só é baixado ao concluir o pedido, com linhas de movimentação correspondentes na mesma transação; falta de saldo rejeita a conclusão sem alterações parciais. O catálogo público mostra apenas disponibilidade booleana.

## Testes locais

```powershell
python -m pytest
```

Os testes usam SQLite temporário para validar autenticação, isolamento, catálogo, estoque, preços congelados e transições de pedidos. A migração PostgreSQL é a fonte de chaves estrangeiras e constraints no banco. RLS ainda não está habilitada nesta entrega.
