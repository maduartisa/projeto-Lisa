# Fase 5 — Guia de infraestrutura e implantação com AWS CDK

## 1. Objetivo e controle da fase

Especificar uma sequência técnica para preparar e revisar a infraestrutura da plataforma multiempresa em AWS usando AWS CDK com Python e região `sa-east-1`.

Este documento é um guia para uma etapa futura de implementação e implantação. Não cria arquivos CDK, não instala dependências, não inicializa recursos AWS e não executa `cdk bootstrap`, `cdk deploy` ou qualquer operação cloud.

| Campo | Valor |
|---|---|
| Fase | 5 — Guia de infraestrutura e implantação |
| Estado | Aprovada pelo solicitante em 26/10/2026 |
| Fases anteriores | Fases 1 a 4 aprovadas em 26/10/2026 |
| IaC escolhida | AWS CDK com Python |
| Região padrão | `sa-east-1` (São Paulo) |
| Runtime | ECS com Fargate |
| Banco | PostgreSQL compartilhado com segregação por `tenant_id` |

## 2. Estado atual e pré-condição importante

No momento da elaboração desta Fase 5, o repositório continha apenas documentação, sem aplicação, `Dockerfile`, dependências Python da aplicação, definições ECS ou projeto CDK. A Fase 6 criou posteriormente uma base CDK local para a infraestrutura compartilhada. A aplicação e os serviços ECS executáveis continuam ausentes; portanto, os comandos que dependem de imagens ainda não estão prontos para implantação.

Não interpretar `cdk synth` ou `cdk deploy` como comandos que podem ser executados com sucesso no estado atual do repositório. Não criar infraestrutura a partir do documento-base da Lisa sem reespecificar e validar o modelo multiempresa.

## 3. Parâmetros de referência

### 3.1. Defaults definidos

- Região: `sa-east-1`.
- IaC: AWS CDK em Python.
- Runtime de containers: ECS Fargate.
- Banco relacional: PostgreSQL em sub-redes privadas.
- Dados de produção: compartilhados no banco, isolados por `tenant_id`, autorização e controles de banco aprovados.

### 3.2. Valores ainda necessários antes da implantação

- ID da conta AWS e perfis/roles de implantação.
- Nome dos ambientes e estratégia de contas separadas.
- Domínio, certificados e configuração DNS.
- Limites de CPU/memória e capacidade inicial dos serviços.
- Configuração de disponibilidade, NAT, RDS Multi-AZ, backup e recuperação.
- Imagem/release da aplicação e portas de health check.
- Nomes de segredos, provedor de WhatsApp/IA e política de conectividade de saída.
- Orçamento e limites de custo, inclusive NAT Gateway, RDS, ALB, Fargate, logs e tráfego.
- Estratégia de pipeline/revisão e aprovação de mudanças.

Nenhuma credencial, senha ou chave deve ser passada em linha de comando, incluída no código CDK, gravada em arquivo versionado ou impressa nos logs.

## 4. Estrutura esperada do projeto CDK

Quando autorizado criar a infraestrutura, a estrutura poderá seguir este padrão:

```text
infrastructure/
  app.py
  cdk.json
  requirements.txt
  stacks/
    network_stack.py
    data_stack.py
    application_stack.py
    monitoring_stack.py
  tests/
    test_network_stack.py
    test_data_stack.py
    test_application_stack.py
```

A divisão final de stacks deverá evitar dependências circulares. Segredos, IDs de conta, domínios, capacidades e outros valores variáveis devem ser lidos de configuração aprovada ou referências do AWS Systems Manager/Secrets Manager, sem segredos em `cdk.json`.

## 5. Recursos de infraestrutura a especificar no CDK

### Rede e entrada

- VPC em `sa-east-1`, com distribuição de sub-redes aprovada para entrada, workloads e dados.
- Security groups restritos: entrada HTTPS apenas no ALB; entrada aos targets somente a partir do ALB; PostgreSQL somente a partir dos serviços autorizados.
- NAT/egress definido com análise de disponibilidade e custo; workload e banco não devem receber IP público por conveniência.
- ALB com listener HTTPS, certificado emitido para domínio validado e health checks da aplicação.

### Aplicação

- ECS Cluster e serviços Fargate separados por função quando necessário: API, interface web e worker.
- Task definitions com imagens imutáveis do ECR, recursos dimensionados e health checks.
- Task roles distintas e de privilégio mínimo para cada serviço.
- Segredos injetados como referências autorizadas ao Secrets Manager; não como valores de build.
- Egress permitido somente para destinos necessários, sujeito ao desenho final dos provedores externos.

### Dados e objetos

- RDS PostgreSQL privado, criptografado, sem acesso público e com backup/retenção aprovados.
- Credencial gerada/gerenciada em mecanismo seguro; rotação e política de acesso definidas antes da produção.
- S3 privado com bloqueio de acesso público, criptografia e política de menor privilégio.
- Recursos e logs identificados por ambiente; não compartilhar dados ou credenciais entre homologação e produção.
- RLS poderá ser adotado como camada complementar, após desenho e testes do contexto de transação; isolamento de aplicação e consultas por tenant é obrigatório mesmo com RLS.

### Observabilidade

- Log groups com retenção definida, evitando conteúdo sensível e segredos.
- Métricas e alarmes para saúde dos serviços, falha ECS, capacidade de banco, execução do worker, falha de backup e limites de serviço.
- Alarmes encaminhados a responsáveis definidos antes da liberação de produção.

## 6. Preparação local (somente após autorização para implementação)

Os comandos desta seção são instruções futuras. Não devem ser executados como parte desta aprovação documental.

1. Instalar versões suportadas e aprovadas de Python, Node.js, AWS CLI e AWS CDK CLI.
2. Confirmar conta/perfil de implantação sem exibir credenciais:

```powershell
aws sts get-caller-identity --profile <perfil-aprovado>
```

3. Definir região no ambiente de sessão ou explicitamente nos comandos:

```powershell
$env:AWS_DEFAULT_REGION = "sa-east-1"
```

4. Após criar a pasta CDK autorizada, preparar ambiente Python e instalar dependências fixadas do projeto:

```powershell
Set-Location <caminho-do-projeto-cdk>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --requirement requirements.txt
```

5. Sintetizar a infraestrutura para revisão:

```powershell
cdk synth --profile <perfil-aprovado> --context environment=<ambiente>
```

6. Revisar diferenças contra a conta e ambiente pretendidos, sem aplicar:

```powershell
cdk diff --profile <perfil-aprovado> --context environment=<ambiente>
```

Os comandos devem ser adaptados ao nome real do ambiente e ao `cdk.json` aprovado. Não inserir token, senha ou secret em argumentos, contexto CDK ou histórico de terminal.

## 7. Bootstrap e implantação controlada

O bootstrap cria recursos de suporte do CDK na conta/região; deploy cria ou altera infraestrutura. Ambos são operações cloud com impacto e custo e exigem autorização explícita em uma etapa de implementação.

Somente após aprovação da fase que produzir o projeto CDK:

1. Confirmar a conta e a região com o responsável AWS.
2. Revisar versão da CLI e templates bootstrap definidos pela organização.
3. Apresentar o plano do bootstrap e obter autorização operacional.
4. Executar bootstrap uma única vez por combinação conta/região, com perfil aprovado e target explícito.
5. Revisar `cdk synth` e `cdk diff`, custos previstos, recursos de rede e controles de acesso.
6. Obter aprovação do plano de mudança para o ambiente específico.
7. Aplicar stacks por ordem de dependência usando o pipeline/perfil autorizado; não executar `cdk deploy --all` sem revisão do plano.
8. Registrar IDs da release, stacks, mudanças, responsável e resultado.
9. Validar health checks, conectividade privada, backup, logs e alarmes antes de onboarding de empresa.

Não usar `--require-approval never` em produção. O pipeline deve manter uma etapa explícita de aprovação das mudanças.

## 8. Migrações de banco e inicialização multiempresa

- A infraestrutura CDK não substitui migrações de esquema da aplicação.
- Migrações são versionadas, revisadas e aplicadas por processo controlado antes da versão que depende delas.
- O role de execução da aplicação não deve receber permissões administrativas desnecessárias no banco.
- Provisionamento do primeiro tenant deve ocorrer por fluxo seguro de aplicação/administrador autorizado, nunca por um tenant padrão fixo.
- Cada tenant deve receber contexto, usuário administrador e configuração próprias.
- Antes de abrir acesso, executar testes negativos cross-tenant sobre APIs, banco, arquivos, webhooks e workers.
- A criação de empresas adicionais ocorre pelo onboarding definido no manual da Fase 4, sem criar bancos ou contas AWS individuais por padrão.

## 9. Estratégia de ambientes, atualização e rollback

- Desenvolver primeiro em ambiente local/sintético, depois homologar em ambiente isolado e só então promover a produção.
- Usar releases imutáveis de imagem e rastrear versão de CDK, dependências, migrações e aplicação.
- Fazer deploy progressivo conforme capacidade de health check e plano de mudança aprovados.
- Mudanças de esquema devem preferir compatibilidade temporária entre versões.
- Reverter serviços ECS para imagem anterior somente quando compatível com o esquema atual.
- Não automatizar rollback destrutivo de banco. Recuperação de dados depende de backup e procedimento testado.
- Confirmar alarms e janela de observação após release; interromper rollout se houver falha de health, erro de integração ou suspeita de isolamento.

## 10. Testes de IaC antes de provisionar

- Síntese CDK produz template válido e determinístico.
- Testes CDK verificam ausência de exposição pública indevida de RDS e S3.
- Security groups e policies concedem somente os acessos necessários.
- Criptografia, backups, retenção de logs e health checks estão presentes conforme o ambiente.
- Task roles são distintas e não concedem acesso global a dados/segredos sem necessidade.
- Configuração impede segredos de aparecerem no template sintetizado ou outputs.
- Templates de desenvolvimento, homologação e produção usam parâmetros e recursos separados.
- `cdk diff` é revisado por responsável diferente do autor em mudanças de produção, quando aplicável.

## 11. Critérios de aceite da Fase 5

- [ ] Região `sa-east-1`, AWS CDK Python e ECS Fargate estão refletidos corretamente.
- [ ] Pré-requisitos e parâmetros pendentes são explícitos.
- [ ] Os comandos de referência distinguem preparação/síntese de bootstrap/deploy e alertam sobre impacto cloud.
- [ ] O desenho de rede, banco, containers, segredos e monitoramento preserva os requisitos multiempresa.
- [ ] Migrações, validações, atualização e rollback têm controles explícitos.
- [x] Está registrado que a Fase 5 não criou IaC nem executou comandos na AWS; a Fase 6 criou a base CDK local, sem executar comandos na AWS.

## 12. Gate de aprovação

**Fase 5 aprovada. A Fase 6 foi autorizada para criação local do projeto CDK, sem deploy. Bootstrap, diff contra conta e deploy continuam dependendo de autorização operacional AWS específica.**

Qualquer operação na AWS requer solicitação e autorização operacional específicas.
