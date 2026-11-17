# Deploy do site na AWS Lightsail com Docker e HTTPS

Este procedimento publica a interface web, a API FastAPI e PostgreSQL na mesma instância Lightsail, com Caddy como proxy HTTPS. Ele usa `compose.lightsail.yaml`; não altera o Compose de desenvolvimento local.

## Limites e pré-requisitos

- A captura enviada mostra uma instância com 1 GB de RAM. Migre para um plano com pelo menos 2 GB antes de subir PostgreSQL, API e Next.js juntos. Faça backup/snapshot e confira preço e procedimento de migração no Lightsail.
- Associe um IPv4 estático à instância e configure um domínio próprio com registro DNS `A` para esse IP. O domínio informado ainda está pendente. Sem DNS apontado e propagado, o Caddy não consegue emitir certificado e o serviço não deve ser publicado.
- O firewall do Lightsail deve permitir TCP 22 somente a partir do IP do operador e TCP 80/443 publicamente. Não abra 3000, 5432 ou 8000.
- O banco de dados deste piloto fica na mesma instância. Faça backups fora dela e teste restauração; o volume Docker não substitui backup.
- Este Compose não implementa chatbot ou webhook WhatsApp. A interface atual não é uma integração WhatsApp. Não configure um callback Meta até que o bot, conteúdo de FAQ aprovado e credenciais da Meta estejam implementados e testados.
- Este guia prepara a implantação; não cria/atualiza recursos na conta AWS.

## Preparar a instância

Após migrar para uma instância Ubuntu com pelo menos 2 GB de RAM, associe o IP estático e configure o DNS. No provedor DNS, crie um registro `A` para o hostname que será usado, apontando para o IP estático. Aguarde a propagação antes de iniciar o Caddy.

Conecte-se por SSH usando a chave privada no seu próprio computador. Não envie a chave, senha ou tokens pelo chat. Na instância, instale Docker Compose e Git:

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2 git
sudo systemctl enable --now docker
docker compose version
```

Baixe uma versão revisada do repositório em um diretório de implantação. Para um repositório privado, use um método de acesso Git autorizado sem gravar tokens na URL:

```bash
sudo install -d -o "$USER" -g "$USER" /opt/lisa
git clone https://github.com/maduartisa/projeto-Lisa.git /opt/lisa/app
cd /opt/lisa/app
```

## Configurar segredos e hostname

Gere os segredos na própria instância. O segredo PostgreSQL usa somente caracteres hexadecimais para que possa ser incluído com segurança na URL de conexão:

```bash
read -r -p 'Hostname DNS (ex.: app.seudominio.com): ' APP_DOMAIN
POSTGRES_PASSWORD="$(openssl rand -hex 32)"
JWT_SECRET_KEY="$(openssl rand -hex 48)"
umask 077
printf 'POSTGRES_PASSWORD=%s\nJWT_SECRET_KEY=%s\nAPP_DOMAIN=%s\n' \
  "$POSTGRES_PASSWORD" "$JWT_SECRET_KEY" "$APP_DOMAIN" > .env.lightsail
unset POSTGRES_PASSWORD JWT_SECRET_KEY APP_DOMAIN
chmod 600 .env.lightsail
```

O arquivo `.env.lightsail` é ignorado pelo Git e contém segredos. Não o publique nem o envie em logs. Confira que o domínio resolve para o IP estático antes de continuar:

```bash
getent ahostsv4 app.seudominio.com
```

Substitua `app.seudominio.com` pelo hostname real. Se a resposta não incluir o IPv4 estático da instância, corrija o DNS e aguarde antes de iniciar o Caddy.

## Validar e iniciar

Na raiz `/opt/lisa/app`, valide a configuração e compile/suba os serviços:

```bash
sudo docker compose --env-file .env.lightsail -f compose.lightsail.yaml config --quiet
sudo docker compose --env-file .env.lightsail -f compose.lightsail.yaml up --build -d
sudo docker compose --env-file .env.lightsail -f compose.lightsail.yaml ps
```

O serviço da API executa `alembic upgrade head` antes de iniciar. PostgreSQL não publica portas no host; API e web só são acessíveis internamente pela rede Docker. Caddy recebe tráfego nas portas 80/443, encaminha à web e solicita/renova o certificado TLS para o domínio configurado.

Verifique a interface e a API pelo HTTPS:

```bash
curl --fail --show-error https://app.seudominio.com/
curl --fail --show-error https://app.seudominio.com/health/ready
```

Troque o hostname pelo domínio real. Em seguida, cadastre uma empresa e uma conta administradora na tela inicial. Use somente dados fictícios até que backups, restauração e controles operacionais tenham sido verificados.

## Operação

Ver logs e estado:

```bash
sudo docker compose --env-file .env.lightsail -f compose.lightsail.yaml ps
sudo docker compose --env-file .env.lightsail -f compose.lightsail.yaml logs --tail=100 api web caddy db
```

Atualizar o código exige revisão e backup prévio do banco:

```bash
cd /opt/lisa/app
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

O chatbot solicitado não está incluído na versão atual: não há webhook Meta, processamento de mensagens ou conteúdo de FAQ confiável. A implantação acima não ativa nem simula essas funções. Para uma fase posterior, será necessário implementar e testar o webhook HTTPS, definir as respostas aprovadas e o encaminhamento humano, criar/configurar o aplicativo Meta e inserir os segredos diretamente no ambiente protegido da instância. Não coloque tokens no repositório nem neste chat.
