# Interface web

Aplicação Next.js/React em português para o catálogo público e a operação autenticada da empresa. O painel oferece produtos com tamanho/cor por SKU, clientes, fornecedores, funcionários e perfis, compras e recebimentos, estoque, financeiro, vendas no PDV por pedidos e auditoria de acessos. O catálogo abre em `/catalog/{identificador-da-empresa}` e envia pedidos para confirmação da equipe.

## Teste rápido local

Siga o modo de demonstração SQLite do [guia da aplicação](../README.md#teste-rápido-com-dados-fictícios) para iniciar a API sem PostgreSQL. Em seguida, inicie a interface:

```powershell
Set-Location .\application\web
npm ci
npm run dev
```

Abra `http://localhost:3000` e entre com os dados de demonstração documentados no guia. O WhatsApp abre uma conversa via `wa.me` para revisão e envio manual; disparos automáticos pela WhatsApp Business API exigem uma conta Meta e credenciais.

## Requisitos de ambiente PostgreSQL

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

Os tokens de acesso ficam em `sessionStorage` do navegador e são removidos ao sair ou quando a API rejeita a sessão. A API valida o usuário, o vínculo, o tenant e as permissões em cada operação. O checkout público cria apenas uma solicitação de pedido, sem cobrança; a loja confirma disponibilidade, entrega e pagamento. A venda no PDV também não captura pagamentos por cartão/Pix e depende da confirmação operacional da equipe.
