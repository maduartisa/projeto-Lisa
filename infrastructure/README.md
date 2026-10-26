# Infraestrutura AWS — CDK Python

Projeto inicial de infraestrutura para a plataforma comercial multiempresa. O escopo atual cria somente a base compartilhada: rede privada, PostgreSQL, armazenamento de objetos, repositórios ECR e cluster ECS. Como o repositório ainda não tem imagens da aplicação, serviços Fargate e load balancer serão adicionados após a implementação e validação dos containers.

## Requisitos locais

- Python 3.11 ou superior compatível com as dependências fixadas.
- Node.js 22 ou 24 e npm para executar a CLI do AWS CDK.
- AWS CDK CLI da versão fixada em `package.json`.
- AWS CLI e perfil autorizado apenas para consultar a conta quando necessário.

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

## Testes

```powershell
python -m unittest discover -s tests -t .
```

## O que ainda não faz

- Não cria serviços ECS Fargate, ALB, domínio, certificado, pipeline ou EventBridge Scheduler.
- Não inclui a aplicação, Dockerfiles ou migrações do banco.
- Não cria tenants nem aplica políticas de isolamento `tenant_id`; esses controles pertencem também à aplicação e ao esquema, ainda não implementados.
- Não executa `cdk bootstrap`, `cdk diff` ou `cdk deploy`.

Antes de provisionar recursos, revisar região, conta, topologia, custo, backup, disponibilidade e capacidades. A aprovação desta fase autoriza apenas os arquivos locais e a síntese/testes; implantação AWS requer autorização operacional separada.
