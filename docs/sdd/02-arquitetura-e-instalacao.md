# Fase 2 — Arquitetura e especificação de instalação

## 1. Objetivo e controle da fase

Definir a arquitetura lógica e a abordagem de instalação da solução multiempresa aprovada na Fase 1, mantendo a fonte tecnológica como referência e evitando dados ou credenciais fixos da Lisa Comercial.

| Campo | Valor |
|---|---|
| Fase | 2 — Arquitetura e especificação de instalação |
| Estado | Aprovada pelo solicitante em 26/10/2026 |
| Fase anterior | Fase 1 — Aprovada em 26/10/2026 |
| Decisão de tenancy | PostgreSQL compartilhado com `tenant_id` e isolamento rigoroso |
| Nuvem de referência | AWS, conforme arquivo-fonte; dimensionamento final pendente |

## 2. Decisões e princípios de arquitetura

1. **Plataforma multiempresa compartilhada:** várias empresas usam a mesma aplicação e infraestrutura lógica.
2. **Banco PostgreSQL compartilhado:** dados pertencentes a uma empresa devem conter associação explícita ao tenant. Tabelas globais de referência, se houver, serão identificadas como tais e não conterão dados operacionais específicos de uma empresa.
3. **Isolamento obrigatório:** a aplicação identifica o tenant a partir de uma sessão autenticada ou de uma integração validada. Não deve confiar em um `tenant_id` fornecido livremente pelo navegador, pelo cliente de API ou pelo modelo de IA.
4. **Defesa em profundidade:** aplicar autorização na camada de serviço e escopo obrigatório nas consultas. Avaliar Row-Level Security (RLS) no PostgreSQL como controle adicional; a configuração e o contexto por transação deverão ser detalhados e testados na fase de implementação.
5. **Configuração por empresa:** identidade comercial, usuários, catálogo, preços, estoque, clientes, pedidos, políticas comerciais e integrações são específicos do tenant.
6. **Serviços externos por tenant:** credenciais e identificadores de WhatsApp e IA devem ser associados ao tenant, guardados em mecanismo de segredos e nunca distribuídos a outros tenants.
7. **Sem valores reais no repositório:** arquivos de configuração versionados contêm apenas nomes de variáveis e exemplos neutros; segredos serão fornecidos no ambiente de implantação.
8. **Instalação reproduzível:** imagens versionadas, configuração explícita por ambiente e procedimentos de verificação são necessários para desenvolvimento, homologação e produção.

## 3. Visão dos componentes

### 3.1. Aplicações

- **Catálogo web responsivo:** apresenta catálogo e caminhos de solicitação de orçamento ou pedido conforme as regras de cada empresa.
- **Administração e operação de balcão:** gerencia produtos, estoque, pedidos, usuários e configurações autorizadas do tenant.
- **API backend:** aplicação Python/FastAPI para autenticação, autorização, regras comerciais, APIs web, integrações e validação de tenant.
- **Processador de mensagens:** recebe webhooks validados e executa o fluxo de atendimento com IA e ferramentas autorizadas.
- **Worker de recompra:** executa tarefas agendadas para os tenants habilitados, respeitando consentimento, limites e resultado de envio.

### 3.2. Persistência e integrações

- **PostgreSQL gerenciado (AWS RDS):** persistência transacional compartilhada, inicialmente privada dentro da rede da aplicação.
- **Armazenamento de objetos (AWS S3):** imagens e arquivos permitidos; caminhos, políticas e acessos devem ser segregados por tenant.
- **Integração de WhatsApp:** provedor escolhido pela empresa/plataforma, com webhook verificado e configuração associada a um tenant.
- **Provedor de IA:** acessado pelo backend; o modelo não recebe credenciais de banco nem acesso direto à infraestrutura. Ferramentas disponíveis limitam-se às operações autorizadas.
- **Segredos e configuração:** armazenados fora do código-fonte e das imagens, em serviço apropriado de segredos/configuração no ambiente AWS.
- **Logs e métricas:** centralizados sem registrar tokens, senhas ou conteúdo pessoal desnecessário; acesso administrativo limitado.

## 4. Topologia AWS de referência

O arquivo-base cita VPC, EC2 com containers Docker, RDS PostgreSQL privado, S3 e IAM. A topologia abaixo preserva esses elementos e especifica as fronteiras de rede:

1. **DNS e HTTPS:** domínio da plataforma com TLS. Cada empresa poderá receber subdomínio ou outro identificador de tenant, a definir na fase de implementação; a identificação pelo domínio não substitui a autorização no backend.
2. **Camada pública:** ponto de entrada HTTPS/load balancer público. Banco de dados e containers de aplicação não devem ser expostos diretamente à internet.
3. **Rede privada de aplicação:** serviço/container da API, administração web, catálogo e workers, sem portas administrativas públicas.
4. **Rede privada de dados:** instância RDS PostgreSQL acessível apenas pelos componentes autorizados da aplicação.
5. **S3 privado:** bloqueio de acesso público, criptografia e política de acesso restrita. Entrega de arquivos públicos, se necessária para o catálogo, deverá usar mecanismo controlado e não expor objetos privados.
6. **IAM e segredos:** identidade de execução com privilégios mínimos e recuperação de segredos em tempo de execução.
7. **Operação:** health checks, logs, alertas, backups automáticos e procedimento de restauração.

EC2 com Docker é a referência do documento-fonte. Para produção, o solicitante escolheu Amazon ECS com Fargate na Fase 3; EC2 permanece apenas como alternativa não selecionada. Número de zonas, disponibilidade e dimensionamento dependem de orçamento, escala e requisitos de continuidade ainda não informados.

## 5. Regras de isolamento multiempresa

### 5.1. Identificação e autorização

- O tenant deve ser determinado por identidade autenticada ou por vínculo de integração previamente validado.
- Usuários internos pertencem a um ou mais tenants por meio de associação explícita; cada requisição é autorizada no contexto da empresa selecionada.
- Endpoints administrativos de plataforma, caso existam, são distintos das funções de administração de uma empresa.
- A aplicação rejeita requisições sem tenant válido e operações com associação divergente; não deve assumir tenant padrão.
- A troca de tenant por usuário com acesso a mais de uma empresa requer seleção explícita e nova validação de autorização.

### 5.2. Dados e consultas

- Tabelas de negócio, incluindo usuários vinculados à empresa, clientes, produtos, estoque, pedidos, itens, recompra, configurações e auditoria, carregam `tenant_id` conforme o modelo de dados.
- Consultas, atualizações, exclusões, contagens, exportações, pesquisas, tarefas em lote e ferramentas da IA sempre aplicam o escopo do tenant.
- Restrições únicas e relacionamentos devem considerar o tenant quando o identificador não for global; referências entre dados de tenants diferentes devem ser impedidas pelo desenho do esquema e pelas validações.
- Arquivos armazenados devem ter vínculo com tenant validado e políticas que impeçam leitura cruzada.
- Logs e métricas não devem permitir que operadores de uma empresa consultem dados operacionais de outra.

### 5.3. Testes de isolamento obrigatórios

- Acesso direto, alteração, exclusão e enumeração de registros de outro tenant devem falhar.
- IDs previsíveis, parâmetros manipulados, exportações, filtros de busca, rotinas agendadas e reprocessamento de webhook não devem contornar o isolamento.
- Testar tenant ausente, inativo, desconhecido e integração vinculada a tenant incorreto.
- Testes de autorização devem cobrir os caminhos de API e de tarefas de background antes da implantação.

## 6. Modelo lógico multiempresa

Entidades centrais previstas para o desenho detalhado:

- `tenants`: empresa, identificador, estado e configurações gerais.
- `usuarios` e `tenant_memberships`: identidade de acesso e papéis por empresa.
- `integracoes_tenant`: vínculo e referência segura a credenciais de provedores externos.
- `clientes`, `produtos`, `estoque`, `pedidos`, `itens_pedido`, `crm_recompra` e `auditoria`: dados operacionais vinculados ao tenant.

Os nomes acima são conceituais; o esquema físico, chaves, índices, migrações e regras de retenção serão definidos na fase técnica de implementação. O esquema SQL da fonte é individualizado para a Lisa e não deve ser implantado sem as adaptações multiempresa e revisão das regras de integridade.

## 7. Fluxos principais

### 7.1. Acesso web e operação de balcão

1. Usuário autentica-se e seleciona uma empresa à qual está associado.
2. A API valida usuário, papel, estado do tenant e escopo da operação.
3. Consultas e gravações são executadas no contexto do tenant autorizado.
4. A alteração de pedido e estoque ocorre em transação, com registro de auditoria aplicável.

### 7.2. Webhook do WhatsApp

1. O endpoint valida autenticidade e formato do webhook conforme o provedor.
2. A integração recebida é resolvida para um tenant habilitado; falha de resolução ou validação é rejeitada e registrada sem conteúdo sensível.
3. A mensagem é processada com contexto mínimo do tenant e ferramentas autorizadas.
4. Qualquer consulta ou orçamento usa o escopo daquele tenant.
5. A resposta é enviada pela integração correspondente, registrando resultado e falhas operacionais.

### 7.3. Recompra agendada

1. O worker seleciona registros vencidos e habilitados, agrupados/escopados por tenant.
2. Antes do envio, valida estado do tenant, configuração da integração, política de consentimento e regras de frequência.
3. Registra tentativa e resultado; falhas não devem ser marcadas como envio bem-sucedido.

## 8. Especificação de instalação — ambiente de produção

Esta seção define a sequência esperada, não comandos finais nem parâmetros de infraestrutura. A geração de IaC e os comandos exatos dependem da aprovação desta arquitetura e serão detalhados em fase posterior.

### Pré-requisitos

- Conta AWS administrada pela empresa responsável, região e domínio aprovados.
- Acesso operacional individual com MFA e permissões mínimas para provisionamento.
- Decisão de orçamento, escala prevista, disponibilidade e retenção de backup.
- Conta e credenciais de provedor de WhatsApp e provedor de IA configuradas conforme política de segurança.
- Catálogo e dados iniciais fornecidos pela empresa em formato acordado.

### Sequência de implantação

1. Criar ou selecionar ambientes separados de desenvolvimento, homologação e produção, com acessos e segredos independentes.
2. Provisionar VPC, sub-redes, regras de rede e entrada HTTPS; manter banco e workloads internos fora de acesso público direto.
3. Provisionar PostgreSQL gerenciado com criptografia, backups e regras de acesso limitadas à aplicação.
4. Criar bucket S3 privado, políticas por tenant e criptografia.
5. Configurar segredos de banco e integrações em serviço de segredos; não copiar valores de exemplo nem persistir credenciais em Git.
6. Publicar imagens de aplicação versionadas no registry de containers e implantar API, interfaces e worker com identidades IAM de privilégio mínimo.
7. Aplicar migrações de banco versionadas, incluindo criação de estruturas multiempresa, índices, restrições e controles de isolamento.
8. Criar tenant inicial por processo administrativo seguro; configurar identidade, usuários, papéis, catálogo, regras operacionais e integrações próprias.
9. Configurar DNS, certificado TLS e callback/webhook do provedor escolhido; validar assinatura e associação ao tenant.
10. Executar verificações de saúde, testes de isolamento entre pelo menos dois tenants de teste, teste de catálogo, orçamento, atualização de pedido, webhook e tarefa agendada.
11. Ativar alertas, políticas de backup, procedimento de restauração e runbook operacional.
12. Liberar o acesso de produção após aprovação do responsável da empresa e evidência dos testes.

### Critérios de prontidão da instalação

- Serviços acessíveis apenas pelos caminhos de rede necessários e TLS válido no ponto público.
- Banco e bucket sem exposição pública não intencional.
- Segredos ausentes do repositório, logs e imagens.
- Migrações concluídas e tenant de teste provisionado.
- Testes de isolamento cross-tenant aprovados.
- Monitoramento, backup e responsáveis operacionais definidos.
- Integrações externas validadas com credenciais da empresa responsável.

## 9. Operação, suporte e recuperação

- Monitorar saúde da API, erros de integração, latência, falhas do worker, conexões de banco e uso de armazenamento.
- Alertar sobre falhas de webhook, falhas de envio, erros em tarefas agendadas e falhas de backup.
- Restringir acesso aos logs; não registrar tokens, senhas, dados de pagamento ou mensagens completas sem necessidade aprovada.
- Definir em fase posterior responsáveis por atendimento, janela de suporte, política de atualização e procedimento de incidentes.
- Testar restauração de backup e documentar resultado antes da entrada em produção.
- Definir RPO, RTO, retenção, custo e plano de continuidade conforme criticidade acordada; esses valores ainda não foram especificados.

## 10. Fora das decisões fechadas nesta fase

Esta arquitetura não fixa:

- Região AWS, topologia multi-AZ, capacidade, metas de disponibilidade, RPO/RTO ou orçamento.
- Provedor, plano e limites de uso do WhatsApp e IA.
- Domínios/subdomínios e estratégia final de identificação pública de tenants.
- Política comercial de cada empresa, consentimento e retenção legal detalhados.
- Esquema SQL final, política de RLS, migrações, código, IaC ou comandos definitivos.

Esses detalhes devem ser especificados e aprovados antes da implantação de produção.

## 11. Critérios de aceite da Fase 2

- [ ] A arquitetura multiempresa atende à decisão de PostgreSQL compartilhado com `tenant_id`.
- [ ] Os controles propostos impedem acesso cruzado entre empresas em APIs, integrações, arquivos e tarefas agendadas.
- [ ] Os componentes e fluxos representam catálogo, operação, WhatsApp, IA e recompra.
- [ ] A abordagem AWS e as fronteiras de rede estão compreensíveis, com decisões ainda abertas identificadas.
- [ ] A sequência de instalação e os critérios de prontidão cobrem segurança, isolamento e validação.
- [ ] Os itens fora desta fase e as decisões dependentes de aprovação futura estão claros.

## 12. Gate de aprovação

**Fase aprovada pelo solicitante em 26/10/2026. A Fase 3 está autorizada; sua aprovação será necessária antes de qualquer implementação.**

Decisão registrada para a especificação técnica: execução de containers em produção com Amazon ECS e Fargate.
