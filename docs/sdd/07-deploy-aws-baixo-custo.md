# Deploy AWS de baixo custo ? sem Docker

## Recomenda??o

Para um piloto, use uma ?nica inst?ncia Linux no Amazon Lightsail. Instale PostgreSQL 17, a API FastAPI e o frontend Next.js diretamente no Ubuntu; execute API e frontend como servi?os `systemd` e use Caddy como proxy HTTPS. Assim, n?o h? Docker, NAT Gateway, RDS, ECR, ECS Fargate nem Application Load Balancer.

| Componente | Configura??o inicial sugerida |
|---|---|
| Regi?o | `sa-east-1` para reduzir lat?ncia no Brasil; confira o pre?o antes de criar |
| VM | Ubuntu 24.04, plano com pelo menos 2 GB RAM e IPv4 p?blico |
| Servi?os | PostgreSQL 17, API e Next.js na mesma VM; Caddy termina HTTPS |
| Rede | SSH apenas do IP do operador; HTTP/HTTPS p?blicos; portas 3000, 5432 e 8000 somente locais |
| Or?amento | AWS Budget de alerta em valor baixo, por exemplo US$ 20/m?s |

Como refer?ncia, um plano de 2 GB costuma custar na ordem de dezenas baixas de d?lares mensais, mas o pre?o muda por regi?o, plano, impostos e altera??es comerciais. Confira o valor final em `sa-east-1` no console do Lightsail antes de confirmar. US$ 100 em cr?ditos cobrem alguns meses, n?o um prazo garantido. Dom?nio, snapshots, tr?fego excedente e recursos esquecidos tamb?m podem consumir cr?ditos. Confirme em **Billing and Cost Management ? Credits** se o cr?dito est? ativo e quais servi?os cobre.

Este arranjo ? somente para demonstra??o e dados n?o cr?ticos. Banco e aplica??o compartilham uma VM, sem failover; perda da inst?ncia pode significar perda dos dados. Para produ??o, planeje banco gerenciado privado, backup testado, monitoramento e alta disponibilidade, aceitando o custo maior. A infraestrutura CDK atual n?o publica a aplica??o e cria recursos adicionais com custo recorrente; n?o a use como atalho para este piloto.

## 1. Conta, or?amento e DNS

1. Ative MFA na conta AWS. N?o compartilhe credenciais nem grave chaves AWS no reposit?rio.
2. Crie um AWS Budget mensal e alertas de custo real e previsto, por exemplo em 50%, 80% e 100% do or?amento. Budgets pode atrasar e apenas alerta; n?o garante teto nem desliga recursos.
3. Tenha um dom?nio pr?prio e acesso ao DNS. O dom?nio n?o est? inclu?do no pre?o da VM.

## 2. Criar e proteger a VM

No console AWS, crie uma inst?ncia Linux/Ubuntu 24.04 no Lightsail, na regi?o escolhida. Selecione o menor bundle com pelo menos 2 GB e confira o pre?o total antes de criar. Use uma chave SSH pr?pria.

Associe um IP est?tico e aponte o registro DNS `A` do dom?nio para ele. No firewall do Lightsail, permita TCP 22 somente do seu IP; permita TCP 80 e 443 publicamente. N?o abra as portas 3000, 5432 ou 8000.

Conecte-se por SSH e instale PostgreSQL 17 e ferramentas de sistema:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg postgresql-common
sudo install -d /usr/share/postgresql-common/pgdg
sudo curl --fail --location --output /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc
echo 'deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt noble-pgdg main' | sudo tee /etc/apt/sources.list.d/pgdg.list
sudo apt-get update
sudo apt-get install -y postgresql-17 python3.12-venv python3.12-dev build-essential libpq-dev
```

Instale Node.js 22 e Caddy:

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs git
sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update
sudo apt-get install -y caddy
node --version
npm --version
psql --version
caddy version
```

N?o use Node.js 18 do reposit?rio padr?o do Ubuntu: Next.js 16 exige vers?o mais nova.

## 3. Preparar usu?rio, c?digo e banco

Crie um usu?rio de sistema dedicado e coloque o c?digo revisado em `/opt/lisa/app` por clone autorizado ou c?pia segura. N?o copie `.env`, chaves, bancos locais nem dados reais.

```bash
sudo useradd --system --create-home --home-dir /opt/lisa --shell /usr/sbin/nologin lisa
sudo install -d -o lisa -g lisa -m 750 /opt/lisa/app
sudo -u lisa git clone <URL_DO_REPOSITORIO> /opt/lisa/app
```

Se copiar os arquivos em vez de clonar, confirme que `/opt/lisa/app` pertence ao usu?rio `lisa` e cont?m `application/`.

Crie o banco e o usu?rio da aplica??o com privil?gio apenas sobre esse banco:

```bash
sudo -u postgres psql
```

No prompt do PostgreSQL, execute `CREATE ROLE lisa_app LOGIN;`, depois `\password lisa_app` e informe uma senha forte quando solicitada (a senha n?o deve ser digitada como parte de um comando). Em seguida, execute `CREATE DATABASE platform OWNER lisa_app;` e `\q`.

Crie `/etc/lisa/app.env` interativamente, sem colocar segredos nos argumentos do shell ou no hist?rico:

```bash
sudo install -d -o root -g lisa -m 750 /etc/lisa
sudo -i
read -rsp 'Digite novamente a senha definida para lisa_app: ' DB_PASSWORD; printf '\n'
JWT_SECRET_KEY="$(openssl rand -hex 48)"
printf 'DATABASE_URL=postgresql+psycopg://lisa_app:%s@127.0.0.1:5432/platform\nJWT_SECRET_KEY=%s\n' "$DB_PASSWORD" "$JWT_SECRET_KEY" > /etc/lisa/app.env
chown root:lisa /etc/lisa/app.env
chmod 640 /etc/lisa/app.env
unset DB_PASSWORD JWT_SECRET_KEY
exit
```

A vari?vel `DATABASE_URL` deve usar o driver `postgresql+psycopg`, incluir o usu?rio `lisa_app`, a senha informada no prompt e o endere?o local do PostgreSQL. N?o imprima esse arquivo em logs ou terminal.

Crie o ambiente Python e instale a API:

```bash
sudo -u lisa python3.12 -m venv /opt/lisa/app/application/.venv
sudo -u lisa /opt/lisa/app/application/.venv/bin/pip install --upgrade pip
sudo -u lisa /opt/lisa/app/application/.venv/bin/pip install /opt/lisa/app/application
```

Instale e compile o frontend. O endere?o da API ? definido na compila??o porque o Next.js usa esse valor nos rewrites:

```bash
sudo -u lisa sh -c 'cd /opt/lisa/app/application/web && npm ci && API_SERVER_URL=http://127.0.0.1:8000 npm run build'
```

## 4. Iniciar API e frontend com systemd

Crie `/etc/systemd/system/lisa-api.service` com este conte?do:

```ini
[Unit]
Description=Lisa Comercial API
After=postgresql.service
Requires=postgresql.service

[Service]
User=lisa
Group=lisa
WorkingDirectory=/opt/lisa/app/application
EnvironmentFile=/etc/lisa/app.env
ExecStartPre=/opt/lisa/app/application/.venv/bin/alembic upgrade head
ExecStart=/opt/lisa/app/application/.venv/bin/uvicorn commercial_platform.asgi:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Crie `/etc/systemd/system/lisa-web.service`:

```ini
[Unit]
Description=Lisa Comercial Web
After=lisa-api.service
Requires=lisa-api.service

[Service]
User=lisa
Group=lisa
WorkingDirectory=/opt/lisa/app/application/web
EnvironmentFile=/etc/lisa/app.env
Environment=API_SERVER_URL=http://127.0.0.1:8000
ExecStart=/usr/bin/npm run start -- --hostname 127.0.0.1 --port 3000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Ative os servi?os e confira os logs:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now lisa-api lisa-web
sudo systemctl status lisa-api lisa-web --no-pager
sudo journalctl -u lisa-api -u lisa-web -n 100 --no-pager
```

## 5. Publicar HTTPS com Caddy

Configure `/etc/caddy/Caddyfile`, trocando pelo dom?nio real:

```caddy
app.seudominio.com {
    encode zstd gzip
    reverse_proxy 127.0.0.1:3000
}
```

Valide e recarregue o Caddy:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl enable --now caddy
sudo systemctl reload caddy
```

Com o DNS propagado e portas 80/443 abertas, o Caddy solicita e renova o certificado TLS automaticamente. Valide `https://app.seudominio.com` e `https://app.seudominio.com/health/ready`. API e banco continuam acess?veis apenas localmente.

## 6. Opera??o e encerramento

- Consulte estado com `sudo systemctl status lisa-api lisa-web caddy` e logs com `sudo journalctl -u lisa-api -u lisa-web -u caddy -n 100`.
- Para atualizar, aplique uma vers?o revisada do c?digo, reinstale depend?ncias, recompile o frontend e reinicie os servi?os. Fa?a backup antes das migra??es.
- Gere backups PostgreSQL e copie-os para fora da VM; teste a restaura??o. O disco da pr?pria VM n?o ? backup. Armazenamento remoto pode gerar custo adicional.
- Para parar gastos recorrentes, fa?a backup e exclua a inst?ncia quando n?o precisar mais dela. Apenas parar a inst?ncia pode continuar cobrando o plano. Antes de excluir, confira snapshots e libere o IP est?tico se ficar desassociado.
- Confira Billing e Cost Explorer ap?s o primeiro dia e semanalmente enquanto usar o cr?dito.

Para desenvolvimento sem URL p?blica, continue usando o ambiente local e n?o crie recursos AWS. Para produ??o, desenhe uma arquitetura gerenciada e estime seu custo antes de provisionar. Este guia n?o executa opera??es na AWS.
