# Fase 3 — Especificação técnica e plano de implementação

## 1. Objetivo e controle da fase

Transformar os requisitos e a arquitetura aprovados em especificação técnica para orientar implementação e instalação da plataforma multiempresa. Este documento não provisiona recursos nem altera código de aplicação.

| Campo | Valor |
|---|---|
| Fase | 3 — Especificação técnica e plano de implementação |
| Estado | Aprovada pelo solicitante em 26/10/2026 |
| Fases anteriores | Fases 1 e 2 aprovadas em 26/10/2026 |
| Runtime de containers aprovado | Amazon ECS com Fargate |
| Banco de dados | PostgreSQL compartilhado com `tenant_id` e isolamento rigoroso |

## 2. Pilha técnica de referência

| Camada | Tecnologia de referência | Responsabilidade |
|---|---|---|
| Interfaces web | Next.js / React | Catálogo web responsivo e interface administrativa/PDV |
| API | Python / FastAPI | APIs, autenticação, autorização, regras comerciais e integrações |
| Dados | PostgreSQL gerenciado (AWS RDS) | Dados transacionais compartilhados e segregados por tenant |
| Imagens e arquivos | AWS S3 privado | Armazenamento de objetos vinculados à empresa |
| Containers | Docker em Amazon ECS/Fargate | Execução independente da API, aplicações web e workers |
| Entrada web | Application Load Balancer com HTTPS | Encaminhamento seguro para serviços publicados |
| Segredos | AWS Secrets Manager ou serviço equivalente aprovado | Segredos de banco e integrações |
| Imagens de container | Amazon ECR | Armazenamento de imagens versionadas |
| Logs e alertas | Amazon CloudWatch | Logs, métricas, alarmes e diagnóstico operacional |
| Agendamento | Amazon EventBridge Scheduler ou mecanismo aprovado | Acionamento do worker de recompra |

A região AWS, linguagem de IaC, versões suportadas, planos de serviços, dimensionamento, alta disponibilidade e orçamento continuam parâmetros a aprovar antes da produção. As versões de dependências deverão ser fixadas e atualizadas por processo controlado; não se devem copiar versões ou credenciais de exemplos sem validação.

## 3. Especificação de identidade e multiempresa

### 3.1. Modelo de identidade

- `tenants`: cadastro e estado operacional de cada empresa.
- `users`: identidade da pessoa, sem assumir acesso automático a dados de qualquer empresa.
- `tenant_memberships`: vínculo usuário-empresa, estado do vínculo e papel aplicado naquele tenant.
- `tenant_integrations`: referência à configuração e ao segredo do provedor, sempre associada a um tenant.
- Papéis iniciais: administrador da empresa, operador de balcão, responsável pelo estoque e atendimento humano. Permissões específicas devem ser expressas por ações, não apenas por ocultação de telas.
- Acesso de suporte/plataforma, se requerido, deve ser separado dos papéis de empresa, restrito e auditado. Não deve existir acesso global implícito para usuários comuns.

### 3.2. Identificação segura do tenant

- Em rotas autenticadas, o backend determina a empresa a partir da sessão/token validado e da associação ativa do usuário.
- Um identificador de tenant enviado pelo cliente serve, no máximo, para seleção; nunca substitui a validação de membership e papel.
- Webhooks são associados ao tenant por configuração de integração validada, além da verificação de assinatura/autenticidade do provedor.
- Rotinas agendadas carregam o tenant explicitamente para cada unidade de trabalho.
- Ausência de tenant válido, tenant suspenso ou vínculo inativo resulta em rejeição explícita; não há fallback para a Lisa nem para um tenant padrão.

### 3.3. Isolamento no PostgreSQL

- Todas as tabelas com dados pertencentes a empresas têm `tenant_id NOT NULL`; exceções globais devem ser justificadas e documentadas.
- Índices únicos de valores que só precisam ser únicos dentro da empresa incluem `tenant_id` (por exemplo, SKU e telefone do cliente).
- Relacionamentos entre entidades tenant-owned usam chaves/validações que impedem referências cruzadas entre tenants.
- Cada transação define seu contexto de tenant de maneira local à transação. Se RLS for adotado, políticas devem negar acesso sem contexto válido e aplicar operações de leitura e escrita.
- O usuário de banco da aplicação não deve ser proprietário das tabelas nem possuir `BYPASSRLS` quando depender de RLS como controle de segurança.
- Consultas também aplicam escopo explícito na camada de dados; RLS é defesa adicional, não justificativa para omitir autorização de aplicação.
- Testes devem validar comportamento de pool de conexões e garantir limpeza do contexto entre transações.

### 3.4. Dados e objetos

Entidades tenant-owned mínimas: configurações, memberships, clientes, produtos, imagens vinculadas, posição/movimentações de estoque, pedidos, itens, histórico de status, ciclos de recompra, mensagens/tentativas de integração e auditoria operacional.

Objetos S3 devem ser associados a um tenant validado no backend. O acesso a objetos privados usa autorização ou URLs temporárias de curta duração; nomes de prefixo contendo tenant não são, por si só, controle de autorização.

## 4. Módulos e fronteiras de implementação

Organizar a aplicação em módulos com fronteiras claras:

1. `identity`: login, sessões/tokens, memberships e papéis.
2. `tenants`: cadastro, ativação, suspensão e configuração da empresa.
3. `catalog`: categorias, produtos, preços e imagens.
4. `inventory`: saldo, limites e movimentações de estoque.
5. `customers`: dados de contato e preferências aplicáveis.
6. `orders`: orçamento, pedido, itens, transições de status e consistência transacional.
7. `channels`: catálogo web e origem dos atendimentos.
8. `whatsapp`: webhook, validação do provedor, envio e encaminhamento para pessoa.
9. `assistant`: orquestração de IA e ferramentas comerciais limitadas.
10. `replenishment`: elegibilidade, agenda, tentativas de envio e descadastro.
11. `audit`: trilha de ações administrativas e mudanças de estado.

Rotas HTTP devem validar payloads com modelos estritos, autenticar/autorizá-las conforme o caso, invocar regras de domínio e retornar erros estruturados sem detalhes internos. Operações de banco devem usar transações e não concatenar valores de usuário em SQL.

## 5. Contratos funcionais mínimos de API

Os caminhos abaixo são nomes lógicos para orientar o contrato OpenAPI; os nomes definitivos poderão ser ajustados sem alterar as regras de autorização.

| Operação | Acesso esperado | Regra principal |
|---|---|---|
| `GET /api/v1/catalog/products` | Público conforme publicação do tenant | Retornar somente produtos ativos e campos publicáveis daquele tenant |
| `GET /api/v1/admin/products` | Usuário autenticado com permissão de catálogo | Aplicar tenant da sessão |
| `POST /api/v1/admin/products` | Administrador/estoque autorizado | Validar SKU e unicidade no tenant |
| `GET /api/v1/admin/orders` | Operador autorizado | Listar apenas pedidos do tenant |
| `POST /api/v1/admin/orders` | Operador autorizado | Criar pedido e validar itens/preços/estoque na transação |
| `PATCH /api/v1/admin/orders/{id}/status` | Operador com permissão | Validar estado de origem/destino e tenant do pedido |
| `POST /api/v1/integrations/whatsapp/{integration_key}/webhook` | Provedor validado | Validar origem/assinatura e resolver tenant sem aceitar tenant arbitrário do corpo |
| `GET /health/live` | Verificação operacional | Indicar processo ativo, sem dados confidenciais |
| `GET /health/ready` | Verificação operacional | Verificar dependências essenciais com resposta sanitizada |

Toda rota administrativa deve verificar identidade, vínculo ativo, papel e tenant. Rotas públicas do catálogo devem resolver o tenant por identificador de publicação configurado e expor apenas os dados explicitamente publicáveis.

## 6. Regras transacionais e de negócio

- Criação ou confirmação de pedido, reserva/baixa de estoque e gravação de itens devem manter consistência em uma transação.
- Quantidade, preço, estado, modalidade e tenant devem ser validados no servidor; valores enviados pela interface não são fonte autoritativa para preço ou disponibilidade.
- Definir estados permitidos e transições em configuração controlada; rejeitar mudança de estado inválida sem alterar dados.
- Usar idempotência ou identificador de evento para webhooks e operações que possam ser reenviadas, evitando duplicação de orçamento, pedido ou mensagem.
- Respostas de IA são informativas; o backend confirma produto, estoque, preço e totais antes de registrar qualquer orçamento.
- Ferramentas da IA recebem apenas argumentos necessários e chamam serviços internos com contexto de tenant explícito; não recebem acesso SQL arbitrário.
- CRM/recompra valida preferências e limites do tenant antes do envio e registra tentativa, resultado e erro sem considerar falha de provedor como envio bem-sucedido.

## 7. Especificação de implantação AWS

### 7.1. Recursos de produção

- VPC com sub-redes públicas para entrada e sub-redes privadas para ECS e banco, distribuídas conforme o nível de disponibilidade aprovado.
- Application Load Balancer público com certificado TLS e regras direcionadas aos serviços ECS necessários.
- ECS Cluster com serviços Fargate separados por responsabilidade de execução: API, interface(s) web e worker, conforme perfil de escala.
- ECR com repositórios privados para imagens versionadas.
- RDS PostgreSQL em sub-redes privadas, criptografia habilitada, acesso apenas por security group dos serviços autorizados e backups configurados.
- S3 com bloqueio de acesso público e políticas de menor privilégio.
- Secrets Manager para credenciais e chaves; task roles ECS distintas por serviço.
- CloudWatch para logs, métricas e alarmes. Mascarar segredos e limitar retenção conforme política aprovada.
- EventBridge Scheduler para disparar trabalho recorrente de recompra; execução deve ser monitorada e idempotente.
- DNS e certificado de domínio; a decisão de domínio/subdomínio por tenant permanece parametrizável.

### 7.2. Ambientes

- **Desenvolvimento:** uso de dados sintéticos; integrações externas em sandbox ou simuladas; sem dados pessoais de produção.
- **Homologação:** infraestrutura e configuração representativas sem copiar segredos de produção; tenants de teste isolados.
- **Produção:** conta/ambiente restrito, segredos independentes, backup, monitoramento e processo de mudança aprovado.

Não reutilizar banco, credenciais ou buckets entre desenvolvimento/homologação e produção. Nenhum ambiente deve receber dados reais da Lisa ou de outra empresa sem autorização e procedimento de proteção apropriados.

### 7.3. Sequência de implantação

1. Validar conta AWS, região, domínio, orçamento, quotas e permissões de implantação.
2. Provisionar recursos de rede, políticas IAM, segredos e infraestrutura por IaC versionada, após seleção e aprovação da ferramenta.
3. Criar ECR e publicar imagens construídas a partir de commit/release identificado.
4. Criar RDS e S3 privados com criptografia, políticas e backup definidos.
5. Configurar serviços ECS, task definitions, task roles, security groups, health checks e variáveis não secretas.
6. Inserir segredos no Secrets Manager e conceder acesso somente às task roles necessárias.
7. Aplicar migrações de banco por job controlado antes de encaminhar tráfego à nova versão.
8. Criar tenant por fluxo administrativo protegido e configurar domínio/publicação, identidade, usuário inicial, papéis, catálogo e integrações.
9. Validar webhook, TLS, readiness, acesso ao banco e armazenamento com um tenant de teste.
10. Executar testes cross-tenant negativos e fluxos de pedido/estoque, envio e falha de integração.
11. Ativar alarmes, backup, logs, rotina de restauração e procedimento de rollback.
12. Aprovar a liberação para produção e registrar versão, migração aplicada, testes e responsável.

### 7.4. Atualização e rollback

- Construir e publicar imagens imutáveis identificadas por versão, sem credenciais embutidas.
- Aplicar migrações compatíveis com a versão anterior sempre que possível; mudanças incompatíveis exigem plano de migração e janela aprovados.
- Validar health checks antes de direcionar tráfego à nova revisão ECS.
- Em falha, retornar a revisão anterior da aplicação quando compatível com o esquema atual; rollback de banco requer procedimento próprio e backup, não deve ser automático ou destrutivo.

## 8. Plano de implementação por entregas

### Entrega 1 — Fundação multiempresa

- Migrações e entidades de tenant, usuário e membership.
- Autenticação, autorização por papel e contexto de tenant.
- Testes unitários e de integração para acesso cruzado negado.
- Critério de saída: tenant ausente ou indevido não lê nem altera registros de outra empresa.

### Entrega 2 — Catálogo, estoque e pedidos

- Cadastro de produtos e clientes com escopo de tenant.
- Movimentações e saldos de estoque.
- Criação e atualização de orçamento/pedido com consistência transacional.
- Critério de saída: fluxo de pedido completo em tenant de teste, incluindo validação de saldo e status.

### Entrega 3 — Interfaces web

- Catálogo responsivo resolvido para empresa configurada.
- Área administrativa/PDV com permissões por papel.
- Critério de saída: duas empresas de teste visualizam suas próprias configurações e dados, sem vazamento cruzado.

### Entrega 4 — WhatsApp e assistência de IA

- Configuração isolada de integração por tenant, validação de webhook e envio.
- Ferramentas limitadas para consulta e orçamento; transferência para atendimento humano.
- Critério de saída: webhook de cada tenant não acessa catálogo, clientes ou pedidos de outro tenant.

### Entrega 5 — Recompra, auditoria e operação

- Rotina agendada com controle de tenant, consentimento, frequência e resultado.
- Registros de auditoria e observabilidade operacional.
- Critério de saída: falhas são observáveis, não marcadas como sucesso e não repetem notificações sem regra de idempotência.

### Entrega 6 — Infraestrutura e implantação

- IaC aprovada, pipelines/imagens versionadas, ambientes, backup, monitoramento e runbooks.
- Testes de implantação, atualização, recuperação e isolamento.
- Critério de saída: ambiente de homologação instalado e aprovado antes da produção.

## 9. Testes técnicos mínimos para aceite

- Testes unitários de regras de pedido, estoque, estado e permissões.
- Testes de integração com PostgreSQL para constraints e transações.
- Testes negativos de isolamento entre pelo menos dois tenants, em leitura, escrita, busca, exportação, webhook, arquivos e background jobs.
- Testes de tenant suspenso, membership revogado, tenant ausente e eventos duplicados.
- Testes de webhook inválido e indisponibilidade de provedor, com falha registrada sem sucesso falso.
- Testes de health check, migração, backup e procedimento de restauração.
- Testes de regressão de catálogo, consulta de estoque, orçamento e operação de balcão.

## 10. Decisões pendentes para preparação da produção

- Região AWS, domínio e estratégia de subdomínios.
- Ferramenta e linguagem de IaC.
- Orçamento, escala inicial, quotas, dimensionamento, disponibilidade, RPO/RTO e retenção de backups/logs.
- Provedor e plano de WhatsApp e IA, limites de uso e política de falhas.
- Política de consentimento, retenção, acesso de suporte e processo de solicitação de dados.
- Formato e responsável pela carga inicial de catálogo e provisionamento de novas empresas.
- Política de pagamento registrada, validade de orçamento e transições finais de pedido.

Essas decisões não impedem a especificação lógica, mas são necessárias antes de comprometer custos ou liberar a plataforma em produção.

## 11. Critérios de aceite da Fase 3

- [ ] A pilha e os componentes estão alinhados à decisão de ECS Fargate e ao PostgreSQL multiempresa.
- [ ] O desenho de autenticação, `tenant_id`, consultas, objetos e workers define controles contra acesso cruzado.
- [ ] Os módulos, contratos mínimos de API e regras transacionais permitem iniciar implementação sem ambiguidades críticas.
- [ ] A sequência de implantação cobre ambientes, migrações, segredos, validação, atualização e recuperação.
- [ ] O plano de entregas e os testes mínimos verificam os requisitos de isolamento e operação.
- [ ] As decisões pendentes de produção estão identificadas e não foram inventadas como aprovadas.

## 12. Gate de aprovação

**Fase aprovada pelo solicitante em 26/10/2026. A Fase 4 documental está autorizada; não implica autorização para provisionar recursos ou alterar o código da aplicação.**

Decisão registrada: seguir com manual de instalação, operação e validação em arquivo separado.
