# Deploy na AWS Lightsail por IP com Docker (HTTP)

Este procedimento publica a interface web, a API FastAPI e PostgreSQL na mesma instância Lightsail, usando Docker Compose e Caddy. Não exige domínio: o acesso é feito pelo IPv4 público ou estático da instância na porta 8080:

```text
http://IP_PUBLICO:8080
```

O Compose usa a porta 8080 do host para evitar conflito com serviços que já possam ocupar a porta 80. Ele usa `compose.lightsail.yaml` e não altera o Compose de desenvolvimento local.

## Limites e pré-requisitos

- Esta configuração usa HTTP sem TLS. Não use senhas ou dados reais até configurar um domínio e HTTPS.
- Para reduzir custos, é possível tentar um plano menor, mas 1 GB de RAM pode ficar limitado ao compilar e executar PostgreSQL, API e Next.js. Monitore memória e disco; se houver falta de memória ou containers instáveis, considere um plano com pelo menos 2 GB.
- Associe um IPv4 estático à instância para manter o endereço após parar e iniciar a máquina. Confira os custos e as condições do Lightsail.
- No firewall do Lightsail, permita TCP 22 somente a partir do IP do operador e TCP 8080 para os clientes que acessarão o site. Não abra 3000, 5432 ou 8000.
- O banco de dados deste piloto fica na mesma instância. Faça backups fora dela e teste restauração; o volume Docker não substitui backup.
- Este Compose não implementa chatbot ou webhook WhatsApp. Não configure um callback Meta até que essas funções estejam implementadas e testadas.
- Este guia prepara a implantação; não cria nem atualiza recursos na conta AWS.

## Preparar a instância

Crie uma instância Ubuntu no Lightsail, associe o IPv4 estático e configure as regras de firewall descritas acima. Conecte-se por SSH usando a chave privada no seu próprio computador. Não copie nem envie a chave, senhas ou tokens pelo chat.

Na instância, instale Docker Compose e Git:

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2 git
sudo systemctl enable --now docker
docker --version
docker compose version
```

Em uma instalação nova, clone o repositório em um diretório de implantação vazio:

```bash
sudo install -d -o "$USER" -g "$USER" /opt/lisa
git clone https://github.com/maduartisa/projeto-Lisa.git /opt/lisa/app-lightsail
cd /opt/lisa/app-lightsail
```

Para um repositório privado, use um método de acesso Git autorizado sem gravar tokens na URL.
Se já houver um checkout em `/opt/lisa/app-lightsail`, não clone por cima; entre no diretório existente com `cd /opt/lisa/app-lightsail`.

## Configurar os segredos

Gere os segredos uma única vez na instância. A senha do PostgreSQL usa somente caracteres hexadecimais para ser segura na URL de conexão:

```bash
POSTGRES_PASSWORD="$(openssl rand -hex 32)"
JWT_SECRET_KEY="$(openssl rand -hex 48)"
umask 077
printf 'POSTGRES_PASSWORD=%s\nJWT_SECRET_KEY=%s\n' \
  "$POSTGRES_PASSWORD" "$JWT_SECRET_KEY" > .env.lightsail
unset POSTGRES_PASSWORD JWT_SECRET_KEY
chmod 600 .env.lightsail
```

O arquivo `.env.lightsail` é ignorado pelo Git e contém segredos. Não o publique, não o envie em logs e não gere novos segredos em uma instalação já em uso.

## Validar e iniciar

Na raiz `/opt/lisa/app-lightsail`, valide a configuração e inicie os serviços:

```bash
sudo docker compose --env-file .env.lightsail -f compose.lightsail.yaml config --quiet
sudo docker compose --env-file .env.lightsail -f compose.lightsail.yaml up --build -d
sudo docker compose --env-file .env.lightsail -f compose.lightsail.yaml ps
```

A API executa `alembic upgrade head` antes de iniciar. PostgreSQL e API não publicam portas no host. Caddy recebe tráfego na porta 8080 do host, encaminha à interface web na rede Docker e serve HTTP sem certificado TLS.

Verifique a interface e a API na própria instância:

```bash
curl --fail --show-error http://127.0.0.1:8080/
curl --fail --show-error http://127.0.0.1:8080/health/ready
```

No navegador, acesse `http://IP_PUBLICO:8080`, substituindo `IP_PUBLICO` pelo IPv4 estático da instância. Use dados fictícios até que HTTPS, backups, restauração e controles operacionais tenham sido configurados e verificados.

## Operação

Ver estado e logs:

```bash
sudo docker compose --env-file .env.lightsail -f compose.lightsail.yaml ps
sudo docker compose --env-file .env.lightsail -f compose.lightsail.yaml logs --tail=100 api web caddy db
```

Antes de atualizar, faça backup do banco. Se os arquivos Compose ou Caddyfile tiverem alterações locais, não force o `git pull`; preserve essas alterações e alinhe-as aos arquivos versionados sem substituir `.env.lightsail`.

```bash
cd /opt/lisa/app-lightsail
git pull --ff-only
sudo docker compose --env-file .env.lightsail -f compose.lightsail.yaml up --build -d
```

Faça um backup PostgreSQL e copie-o para armazenamento fora da instância:

```bash
umask 077
sudo docker compose --env-file .env.lightsail -f compose.lightsail.yaml exec -T db \
  pg_dump -U lisa_app -d platform -Fc > "$HOME/lisa-$(date +%F-%H%M%S).dump"
```

Monitore espaço em disco, memória, logs, custos e a validade dos backups. Teste periodicamente a restauração em uma instância separada antes de confiar em dados reais.

## WhatsApp

O chatbot e o webhook Meta não estão incluídos nesta implantação. Não configure um callback até que o webhook HTTPS, as respostas aprovadas e o encaminhamento humano estejam implementados e testados. Não coloque tokens no repositório nem neste chat.
