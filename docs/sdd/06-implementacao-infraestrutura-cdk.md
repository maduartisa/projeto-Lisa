# Fase 6 — Implementação local da infraestrutura CDK

## 1. Objetivo e controle da fase

Registrar a implementação local, sem implantação AWS, do projeto inicial de infraestrutura aprovado para a plataforma multiempresa.

| Campo | Valor |
|---|---|
| Fase | 6 — Implementação local da infraestrutura CDK |
| Estado | Aprovada pelo solicitante em 26/10/2026; testes e síntese locais passaram |
| Aprovação de escopo | Criar código CDK Python no repositório; sem deploy |
| Decisões anteriores | Região `sa-east-1`, AWS CDK Python, ECS Fargate, PostgreSQL compartilhado com `tenant_id` |

## 2. Arquivos criados

- `infrastructure/app.py`: entry point do CDK, contexto de ambiente e região.
- `infrastructure/stacks/stage_config.py`: configuração tipada dos ambientes `dev`, `staging` e `prod`.
- `infrastructure/stacks/platform_stack.py`: base de rede, PostgreSQL, bucket S3, repositórios ECR, cluster ECS e grupos de log.
- `infrastructure/cdk.json`: configuração local do CDK, com ambiente de síntese padrão `dev` e região `sa-east-1`.
- `infrastructure/requirements.txt`: dependências Python do CDK fixadas.
- `infrastructure/package.json` e `infrastructure/package-lock.json`: CLI local do CDK fixada e scripts.
- `infrastructure/tests/`: testes de configuração e propriedades sintetizadas.
- `infrastructure/README.md`: preparação, síntese, testes e limitações da base.

## 3. Recursos cobertos pela base

- VPC com sub-redes públicas, privadas com egress e privadas isoladas.
- Grupo de segurança de banco com ingresso PostgreSQL apenas do grupo de segurança reservado às tasks da aplicação.
- Instância PostgreSQL 17.6 no RDS, privada e criptografada, com senha gerada e armazenada pelo Secrets Manager, backups e proteção contra exclusão.
- Bucket S3 com bloqueio de acesso público, HTTPS obrigatório, criptografia e versionamento.
- Repositórios ECR separados para API, web e worker, com tags imutáveis e análise de imagens ao envio.
- Cluster ECS e grupos de logs destinados a serviços que serão adicionados quando as imagens da aplicação existirem.
- Configuração de referência por ambiente; produção usa Multi-AZ e retenção de backup maior, valores que ainda dependem de revisão de custo/capacidade.
- Egress reservado ao tráfego HTTPS e PostgreSQL da aplicação; as integrações e endpoints externos ainda precisam de revisão antes da implantação.

## 4. O que não foi implementado

- Nenhum comando de AWS foi executado; não houve `cdk bootstrap`, `cdk diff` contra conta ou `cdk deploy`.
- Não foram criados serviços ECS Fargate, ALB, domínio, certificado, pipeline, escalabilidade, alarmes, scheduler ou políticas de custo.
- A aplicação e as migrações agora existem em `application/`, mas ainda não há Dockerfiles/imagens, serviços ECS Fargate, ALB nem configuração de runtime para publicá-las.
- O CDK não cria tenants. A aplicação implementa autenticação e isolamento por `tenant_id`; esse isolamento ainda precisa ser exercitado contra a infraestrutura implantada.
- Segredos específicos de WhatsApp/IA por tenant não são criados ou preenchidos nesta base.

## 5. Validação requerida

- Instalar dependências fixadas em ambiente virtual local.
- Executar os testes `unittest` da infraestrutura.
- Sintetizar os templates CDK e revisar propriedades de segurança e recursos gerados.
- Confirmar que nenhuma chamada a conta AWS, bootstrap ou deploy foi executada.

Validação local executada:

- Testes `unittest`: 8 testes passaram.
- `npm run synth`: síntese de `CommercialPlatform-dev` concluída localmente.
- Nenhuma chamada AWS, bootstrap, diff contra conta ou deploy foi executado.
- O ambiente local usa Node 26, que a versão da CLI avisou não estar entre as versões testadas oficialmente (indicou Node 22 ou 24); síntese e testes concluíram mesmo com o aviso.

## 6. Critérios de aceite

- [x] Testes locais passam.
- [x] A síntese CDK gera template para `dev` em `sa-east-1`.
- [x] Banco e bucket atendem às propriedades de segurança cobertas pelos testes.
- [x] Não há aplicação ou serviço placeholder publicado como funcional.
- [x] Não foram executados comandos que provisionem ou alterem recursos AWS.
- [x] Limitações e próximos itens estão compreendidos.

## 7. Gate

**Fase aprovada pelo solicitante em 26/10/2026. A aprovação cobre a infraestrutura CDK local; deploy AWS continua dependendo de autorização operacional separada.**

## 8. Preparação operacional local (27/10/2026)

- O entry point agora resolve a conta e a região do perfil selecionado a partir de `CDK_DEFAULT_ACCOUNT` e `CDK_DEFAULT_REGION`, preservando os contextos CDK explícitos e o padrão `sa-east-1`.
- `infrastructure/README.md` documenta autenticação AWS CLI por perfil/SSO, confirmação de identidade, revisão com `synth`/`diff`, bootstrap condicional e deploy explícito somente da stack de fundação `CommercialPlatform-dev`.
- A aplicação ainda não pode receber tráfego via esta stack: faltam empacotamento Docker, serviços ECS, balanceador, endpoint TLS e configuração do usuário de aplicação no banco.
- Nenhum perfil AWS foi configurado, nenhuma identidade foi consultada e nenhum bootstrap, diff contra conta ou deploy foi executado.
