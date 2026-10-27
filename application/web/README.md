# Interface web

Aplicação Next.js/React em português para o catálogo público e a operação autenticada da empresa. O painel oferece visão geral, produtos, clientes, ajustes e histórico de estoque, criação de orçamentos e transições de pedidos. O catálogo público abre em `/catalog/{identificador-da-empresa}`.

## Requisitos

- Node.js 20.9 ou superior.
- API FastAPI e PostgreSQL preparados de acordo com o [guia da aplicação](../README.md).

## Instalação e execução local

Em uma janela do PowerShell:

```powershell
Set-Location .\application\web
npm ci
$env:API_SERVER_URL = "http://127.0.0.1:8000"
npm run dev
```

Em outra janela, inicie a API conforme o guia da aplicação. A interface usa rewrites Next.js para encaminhar `/api/*` e `/health/*` ao backend; assim, não é necessário habilitar CORS para desenvolvimento local. O URL do backend é uma configuração de execução, não uma chave secreta.

Abra `http://localhost:3000`. Para abrir o catálogo público, use `http://localhost:3000/catalog/{slug-da-empresa}`. Acesse o painel com e-mail, senha e slug de uma membership ativa.

## Validação

```powershell
npm run typecheck
npm run build
```

Os tokens de acesso ficam em `sessionStorage` do navegador e são removidos ao sair ou quando a API rejeita a sessão. A API valida o usuário, o vínculo, o tenant e as permissões em cada operação. Valores e disponibilidade exibidos no catálogo não substituem a confirmação da equipe; a seleção de produtos no catálogo é apenas informativa, pois não há checkout nem envio público de orçamento nesta entrega.
