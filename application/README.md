# Aplicação — automação comercial

A aplicação reúne API FastAPI e interface web responsiva para catálogo, operação de balcão e administração multiempresa. Inclui cadastro de clientes, fornecedores e funcionários; produtos com grade de tamanho/cor por SKU; compras, estoque, pedidos, contas a pagar/receber e auditoria de acessos. O checkout online apenas envia pedido para confirmação e não processa pagamentos.

## Teste rápido com dados fictícios

Para experimentar sem instalar PostgreSQL, abra um PowerShell na raiz do repositório e inicie a API local:

```powershell
Set-Location .\application
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
python -m commercial_platform.demo
```

O comando cria e popula um banco SQLite isolado em `application\.local\demo.sqlite3` e escuta apenas em `127.0.0.1:8000`. Ele imprime o e-mail `admin@demo.example`, uma senha aleatória local e o identificador da empresa `demo`; use esses dados no painel. A senha fica somente no diretório local ignorado pelo Git, e não deve ser publicada nem reutilizada em produção.

Em outro PowerShell, inicie o frontend:

```powershell
Set-Location .\application\web
npm ci
npm run dev
```

Abra `http://localhost:3000`. Os cadastros de demonstração são reinicializados apenas se o banco local for apagado; os dados criados durante o teste permanecem nesse arquivo.

## Requisitos para PostgreSQL

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
- `GET|POST /api/v1/admin/suppliers`: consulta e cadastro de fornecedores.
- `GET|POST /api/v1/admin/employees`, `PATCH /api/v1/admin/employees/{membership_id}`: gestão de funcionários e acessos (administradora).
- `GET|POST /api/v1/admin/purchases`, `PATCH /api/v1/admin/purchases/{purchase_id}/status`: compras; ao receber, registra entradas de estoque e conta a pagar.
- `GET|POST /api/v1/admin/finance`, `PATCH /api/v1/admin/finance/{entry_id}/settle`: lançamentos financeiros e baixa de contas.
- `GET /api/v1/admin/access-logs`: atividades autenticadas da empresa (administradora).
- `POST /api/v1/admin/products/{product_id}/inventory`: ajuste controlado de estoque.
- `GET /api/v1/admin/products/{product_id}/inventory`: histórico de movimentações.
- `GET|POST /api/v1/admin/orders` e `GET /api/v1/admin/orders/{order_id}`: criação e consulta de pedidos.
- `PATCH /api/v1/admin/orders/{order_id}/status`: transição validada de estado.
- `POST /api/v1/public/{tenant_slug}/orders`: solicita pedido pelo catálogo; requer nome, telefone ou e-mail e modalidade de retirada/entrega. Não há cobrança. A equipe confirma o pedido e o estoque só é baixado na conclusão.

O token não aceita seleção livre de tenant em headers ou parâmetros. Em cada requisição, a API verifica novamente usuário, membership, status do tenant e papel atual no banco. Quando o vínculo é revogado ou o tenant suspenso, o token deixa de autorizar acesso.

Todos os recursos operacionais são consultados no escopo do tenant autenticado, reforçado por chaves estrangeiras compostas no banco. Produtos em grade são cadastrados como uma linha por combinação de atributos, com SKU, preço e estoque independentes. O pedido guarda preço e total do momento da cotação. O estoque só é baixado ao concluir um pedido, com linhas de movimentação correspondentes na mesma transação; falta de saldo rejeita a conclusão sem alterações parciais. Receber uma compra adiciona o saldo e cria conta a pagar na mesma operação. A auditoria registra logins bem-sucedidos e chamadas autenticadas, sem registrar senhas ou tokens.

Esta versão não integra gateway de pagamento, emissão fiscal, conciliação bancária, fechamento de caixa, WhatsApp/IA nem emissão de nota fiscal; não use os lançamentos como substituto de contabilidade ou transação bancária.

## Testes locais

```powershell
python -m pytest
```

Os testes usam SQLite temporário para validar autenticação, isolamento, catálogo, estoque, preços congelados e transições de pedidos. A migração PostgreSQL é a fonte de chaves estrangeiras e constraints no banco. RLS ainda não está habilitada nesta entrega.
