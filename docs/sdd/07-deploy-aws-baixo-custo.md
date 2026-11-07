# Deploy AWS de baixo custo — sem Docker

## Recomendação

Para um piloto, use uma única instância Linux no Amazon Lightsail. Instale PostgreSQL 17, a API FastAPI e o frontend Next.js diretamente no Ubuntu; execute API e frontend como serviços `systemd` e use Caddy como proxy HTTPS. Assim, não há Docker, NAT Gateway, RDS, ECR, ECS Fargate nem Application Load Balancer.

| Componente | Configuração inicial sugerida |
|---|---|
| Região | `sa-east-1` para reduzir latência no Brasil; confira o preço antes de criar |
| VM | Ubuntu 24.04, plano com pelo menos 2 GB RAM e IPv4 público |
| Serviços | PostgreSQL 17, API e Next.js na mesma VM; Caddy termina HTTPS |
| Rede | SSH apenas do IP do operador; HTTP/HTTPS públicos; portas 3000, 5432 e 8000 somente locais |
| Orçamento | AWS Budget de alerta em valor baixo, por exemplo US$ 20/mês |

Como referência, um plano de 2 GB costuma custar na ordem de dezenas baixas de dólares mensais, mas o preço muda por região, plano, impostos e alterações comerciais. Confira o valor final em `sa-east-1` no console do Lightsail antes de confirmar. US$ 100 em créditos cobrem alguns meses, não um prazo garantido. Domínio, snapshots, tráfego excedente e recursos esquecidos também podem consumir créditos. Confirme em **Billing and Cost Management → Credits** se o crédito está ativo e quais serviços cobre.

Este arranjo é somente para demonstração e dados não críticos. Banco e aplicação compartilham uma VM, sem failover; perda da instância pode significar perda dos dados. Para produção, planeje banco gerenciado privado, backup testado, monitoramento e alta disponibilidade, aceitando o custo maior. A infraestrutura CDK atual não publica a aplicação e cria recursos adicionais com custo recorrente; não a use como atalho para este piloto.

## 1. Conta, orçamento e DNS

1. Ative MFA na conta AWS. Não compartilhe credenciais nem grave chaves AWS no repositório.
2. Crie um AWS Budget mensal e alertas de custo real e previsto, por exemplo em 50%, 80% e 100% do orçamento. Budgets pode atrasar e apenas alerta; não garante teto nem desliga recursos.
3. Tenha um domínio próprio e acesso ao DNS. O domínio não está incluído no preço da VM.

## 2. Criar e proteger a VM

No console AWS, crie uma instância Linux/Ubuntu 24.04 no Lightsail, na região escolhida. Selecione o menor bundle com pelo menos 2 GB e confira o preço total antes de criar. Use uma chave SSH própria.

Associe um IP estático e aponte o registro DNS `A` do domínio para ele. No firewall do Lightsail, permita TCP 22 somente do seu IP; permita TCP 80 e 443 publicamente. Não abra as portas 3000, 5432 ou 8000.

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

Não use Node.js 18 do repositório padrão do Ubuntu: Next.js 16 exige versão mais nova.

## 3. Preparar usuário, código e banco

Crie um usuário de sistema dedicado e coloque o código revisado em `/opt/lisa/app` por clone autorizado ou cópia segura. Não copie `.env`, chaves, bancos locais nem dados reais.

```bash
sudo useradd --system --create-home --home-dir /opt/lisa --shell /usr/sbin/nologin lisa
sudo install -d -o lisa -g lisa -m 750 /opt/lisa/app
sudo -u lisa git clone <URL_DO_REPOSITORIO> /opt/lisa/app
```

Se copiar os arquivos em vez de clonar, confirme que `/opt/lisa/app` pertence ao usuário `lisa` e contém `application/`.

Crie o banco e o usuário da aplicação com privilégio apenas sobre esse banco:

```bash
sudo -u postgres psql
```

No prompt do PostgreSQL, execute `CREATE ROLE lisa_app LOGIN;`, depois `\password lisa_app` e informe uma senha forte quando solicitada (a senha não deve ser digitada como parte de um comando). Em seguida, execute `CREATE DATABASE platform OWNER lisa_app;` e `\q`.

Crie `/etc/lisa/app.env` interativamente, sem colocar segredos nos argumentos do shell ou no histórico:

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

Não imprima esse arquivo em logs ou terminal.

Crie o ambiente Python e instale a API:

```bash
sudo -u lisa python3.12 -m venv /opt/lisa/app/application/.venv
sudo -u lisa /opt/lisa/app/application/.venv/bin/pip install --upgrade pip
sudo -u lisa /opt/lisa/app/application/.venv/bin/pip install /opt/lisa/app/application
```

Instale e compile o frontend. O endereço da API é definido na compilação porque o Next.js usa esse valor nos rewrites:

```bash
sudo -u lisa sh -c 'cd /opt/lisa/app/application/web && npm ci && API_SERVER_URL=http://127.0.0.1:8000 npm run build'
```

## 4. Iniciar API e frontend com systemd

Crie `/etc/systemd/system/lisa-api.service` com este conteúdo:

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

Ative os serviços e confira os logs:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now lisa-api lisa-web
sudo systemctl status lisa-api lisa-web --no-pager
sudo journalctl -u lisa-api -u lisa-web -n 100 --no-pager
```

## 5. Publicar HTTPS com Caddy

Configure `/etc/caddy/Caddyfile`, trocando pelo domínio real:

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

Com o DNS propagado e portas 80/443 abertas, o Caddy solicita e renova o certificado TLS automaticamente. Valide `https://app.seudominio.com` e `https://app.seudominio.com/health/ready`. API e banco continuam acessíveis apenas localmente.

## 6. Operação e encerramento

- Consulte estado com `sudo systemctl status lisa-api lisa-web caddy` e logs com `sudo journalctl -u lisa-api -u lisa-web -u caddy -n 100`.
- Para atualizar, aplique uma versão revisada do código, reinstale dependências, recompile o frontend e reinicie os serviços. Faça backup antes das migrações.
- Gere backups PostgreSQL e copie-os para fora da VM; teste a restauração. O disco da própria VM não é backup. Armazenamento remoto pode gerar custo adicional.
- Para parar gastos recorrentes, faça backup e exclua a instância quando não precisar mais dela. Apenas parar a instância pode continuar cobrando o plano. Antes de excluir, confira snapshots e libere o IP estático se ficar desassociado.
- Confira Billing e Cost Explorer após o primeiro dia e semanalmente enquanto usar o crédito.

Para desenvolvimento sem URL pública, continue usando o ambiente local e não crie recursos AWS. Para produção, desenhe uma arquitetura gerenciada e estime seu custo antes de provisionar. Este guia não executa operações na AWS.