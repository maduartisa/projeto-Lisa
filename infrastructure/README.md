# Infraestrutura AWS — CDK Python

Projeto de infraestrutura-base para a plataforma comercial multiempresa. O CDK cria rede privada, PostgreSQL, armazenamento de objetos, repositórios ECR e cluster ECS. A aplicação possui API e frontend no repositório, mas ainda não há Dockerfiles/imagens, serviços Fargate, balanceador ou endpoint público: este stack não publica o site.

## Requisitos locais

- Python 3.11 ou superior compatível com as dependências fixadas.
- Node.js 22 ou 24 e npm para executar a CLI do AWS CDK.
- AWS CDK CLI da versão fixada em `package.json`.
- AWS CLI e perfil autorizado apenas para consultar a conta quando necessário.
- Conta AWS de destino e permissões IAM aprovadas para CDK/CloudFormation, EC2, RDS, Secrets Manager, S3, ECR, ECS e CloudWatch Logs.

## Preparação e síntese local

No PowerShell, a partir da raiz do repositório:

```powershell
Set-Location .\infrastructure
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --requirement requirements.txt
npm ci
npm run synth
```

O comando `synth` gera templates CloudFormation locais. Ele não provisiona recursos AWS.

Node.js 26 pode emitir um aviso de runtime não testado pela versão fixada da CLI; use Node.js 22 ou 24 para um ambiente suportado.

Para configurar o ambiente de síntese, passe o contexto CDK:

```powershell
npm run synth -- --context environment=dev
npm run synth -- --context environment=staging
npm run synth -- --context environment=prod
```

Os valores de `cdk.json` selecionam `dev` por padrão. Configurações de `staging` e `prod` são referências para revisão, não tamanhos aprovados para produção.

## Preparar uma conta e um perfil AWS

Não salve chaves AWS, senhas ou tokens no repositório, em `cdk.json`, nem em argumentos. Configure AWS CLI v2 por SSO ou pelo mecanismo aprovado pela organização e confirme a identidade do perfil antes de qualquer operação:

```powershell
aws configure sso --profile lisa-dev
aws sts get-caller-identity --profile lisa-dev
```

Confirme que `Account` corresponde à conta AWS aprovada para desenvolvimento. A região de destino padrão é `sa-east-1`; a aplicação CDK também reconhece a conta e a região resolvidas pelo perfil do CDK CLI (`CDK_DEFAULT_ACCOUNT` e `CDK_DEFAULT_REGION`). Contexto explícito pode substituir esses valores para síntese/revisão; não use um ID de conta de exemplo.

## Revisão e implantação da infraestrutura-base

Os passos abaixo provisionam recursos e podem gerar custos (especialmente NAT Gateway e RDS). O stack `CommercialPlatform-dev` é somente a fundação; não inicia containers nem disponibiliza o website.

Primeiro faça revisão local e teste o template:

```powershell
Set-Location .\infrastructure
$env:AWS_PROFILE = "lisa-dev"
$env:AWS_DEFAULT_REGION = "sa-east-1"
aws sts get-caller-identity --profile $env:AWS_PROFILE
npm run synth -- --context environment=dev
```

Após conferir a conta/region retornadas e obter aprovação do responsável AWS para provisionar:

```powershell
npm exec cdk -- bootstrap aws://<ID_DA_CONTA_APROVADA>/sa-east-1 --profile lisa-dev
npm exec cdk -- diff CommercialPlatform-dev --profile lisa-dev --context environment=dev
npm exec cdk -- deploy CommercialPlatform-dev --profile lisa-dev --context environment=dev
```

Substitua `<ID_DA_CONTA_APROVADA>` pelo ID confirmado por `sts get-caller-identity`. Revise cada mudança e estimativa de custos do `diff` antes de aprovar `deploy`. Não use `--require-approval never`. Para `staging` ou `prod`, repita a revisão com a conta e os limites de custo aprovados para o ambiente; não promova automaticamente os valores de referência de `prod`.

O bootstrap cria recursos de suporte CDK na conta/região; execute-o somente se ainda não existir um ambiente bootstrap compatível e após autorização. Nenhum desses comandos foi executado como parte desta preparação.

## Testes

```powershell
python -m unittest discover -s tests -t .
```

## O que ainda não faz

- Não cria serviços ECS Fargate, ALB, domínio, certificado, pipeline ou EventBridge Scheduler; portanto, não publica a aplicação nem gera uma URL pública.
- Não inclui Dockerfiles/imagens de API, web ou worker nem configuração de runtime, migrações automáticas ou acesso da aplicação ao Secrets Manager.
- O PostgreSQL é criado com senha mestra gerenciada no Secrets Manager; ainda é necessário configurar e provisionar um usuário de aplicação de privilégio mínimo antes de conectar serviços.
- Não cria tenants; os fluxos de autenticação e aplicação já possuem isolamento por `tenant_id`, que ainda deve ser exercitado na infraestrutura implantada.
- Não executa `cdk bootstrap`, `cdk diff` contra uma conta AWS ou `cdk deploy`.

Antes de provisionar recursos, revisar região, conta, topologia, custo, backup, disponibilidade e capacidades. A síntese é local; bootstrap e implantação exigem autorização operacional AWS para a conta e o ambiente escolhidos.
