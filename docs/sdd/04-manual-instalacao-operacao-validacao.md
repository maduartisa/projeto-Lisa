# Fase 4 — Manual de instalação, operação e validação

## 1. Objetivo e controle da fase

Definir um procedimento repetível para preparar, instalar, configurar e validar a plataforma multiempresa em nome de uma empresa contratante. O manual destina-se à equipe técnica responsável pelo ambiente AWS e à equipe autorizada da empresa.

Este documento é uma especificação de procedimento. Não provisiona recursos AWS, não cria credenciais e não substitui comandos específicos da ferramenta de IaC que ainda deverá ser selecionada.

| Campo | Valor |
|---|---|
| Fase | 4 — Manual de instalação, operação e validação |
| Estado | Aprovada pelo solicitante em 26/10/2026 |
| Fases anteriores | Fases 1, 2 e 3 aprovadas em 26/10/2026 |
| Modelo | Plataforma compartilhada; isolamento por empresa usando PostgreSQL e `tenant_id` |
| Runtime | Amazon ECS com Fargate |
| Ambiente cloud de referência | AWS |

## 2. Responsabilidades

| Papel | Responsabilidades |
|---|---|
| Responsável pela plataforma | Conta AWS, rede, serviços compartilhados, releases, backups, monitoramento e segurança da plataforma |
| Administrador da empresa | Dados comerciais, usuários, catálogo, políticas locais e aprovação de integrações da própria empresa |
| Operação/estoque da empresa | Atualização de produtos, estoque e pedidos conforme permissões atribuídas |
| Responsável por privacidade/negócio | Aprovação de consentimento, mensagens, retenção e atendimento às solicitações relacionadas a dados |

O responsável pela plataforma não deve usar credenciais compartilhadas com usuários da empresa. Todo acesso operacional deve ser individual, autenticado, limitado e auditável.

## 3. Dados e parâmetros necessários antes da instalação

Preencher e aprovar os valores no sistema autorizado de gestão de configuração/segredos. Não registrar valores secretos neste documento ou no repositório.

### 3.1. Parâmetros da plataforma

- Conta AWS e ambiente de destino (desenvolvimento, homologação ou produção).
- Região AWS aprovada.
- Domínio e subdomínios necessários, titularidade e acesso ao DNS.
- Escolha de ferramenta/linguagem de IaC e versão aprovada.
- Tamanho inicial, limites de escala, disponibilidade, orçamento e quotas.
- Política de backup, retenção, RPO/RTO e responsáveis por recuperação.
- Referências das imagens versionadas da aplicação no ECR.
- Segredos e parâmetros com nomes aprovados para banco, provedores e integrações.

### 3.2. Parâmetros de cada empresa

- Nome e identidade comercial, estado do tenant e identificador público.
- Endereço, horário, canais de contato, modalidades de retirada/entrega e regras autorizadas.
- Usuário administrador inicial e canal seguro de entrega do convite.
- Catálogo, categorias, SKU, preço e disponibilidade inicial.
- Limites e políticas de estoque.
- Provedor e configuração de WhatsApp, incluindo validação do webhook.
- Provedor de IA, limites de uso e mensagens institucionais aprovadas.
- Política de consentimento, frequência, descadastro e retenção para comunicações.

Dados de demonstração da Lisa não são dados iniciais padrão. Cada empresa fornece seus próprios dados e aprova a carga inicial.

## 4. Checklist de pré-instalação

- [ ] Fases 1, 2 e 3 aprovadas e versão desta especificação aprovada.
- [ ] Conta e região AWS aprovadas; acesso de implantação protegido por MFA e menor privilégio.
- [ ] Domínio/DNS sob controle do responsável.
- [ ] Orçamento, quotas, dimensionamento e níveis de disponibilidade definidos.
- [ ] Ferramenta de IaC e revisão das mudanças de infraestrutura aprovadas.
- [ ] Imagens de container identificadas por release e verificadas pela equipe responsável.
- [ ] Segredos cadastrados no gestor de segredos, sem arquivos `.env` com valores reais no repositório.
- [ ] Dados de catálogo e configurações de empresa revisados e autorizados.
- [ ] Plano de backup, recuperação, monitoramento e rollback aprovado.
- [ ] Integrações externas configuradas em sandbox ou com credenciais de produção autorizadas.

Se um item obrigatório estiver pendente, interromper a implantação de produção e registrar o bloqueio. Não usar valores fictícios como fallback em produção.

## 5. Instalação por ambiente

### 5.1. Desenvolvimento

1. Usar dados sintéticos e tenant(s) de teste.
2. Executar serviços por ambiente local/containerizado conforme instruções técnicas do repositório, sem expor serviços internos à internet.
3. Usar sandbox ou simulação para WhatsApp e IA.
4. Aplicar migrações por procedimento controlado e validar isolamento com pelo menos dois tenants de teste.
5. Nunca copiar banco, segredos, mensagens ou dados pessoais de produção para desenvolvimento.

### 5.2. Homologação

1. Usar conta/ambiente isolado de produção, com rede, serviços e controle de acesso representativos.
2. Provisionar a infraestrutura por IaC aprovada e revisar o plano antes da aplicação.
3. Configurar segredos independentes dos de produção.
4. Publicar release candidata imutável e executar migrações aprovadas.
5. Criar tenants sintéticos, validar integrações em sandbox e executar toda a lista de testes da seção 7.
6. Registrar resultados e aprovação do responsável técnico antes de promover a release.

### 5.3. Produção

1. Confirmar todos os itens do checklist pré-instalação e a janela de mudança autorizada.
2. Aplicar a infraestrutura aprovada: VPC/sub-redes, regras de rede, entrada HTTPS, ECS/Fargate, RDS PostgreSQL, S3, IAM, ECR, segredos, logs e alarmes.
3. Confirmar que RDS, ECS e S3 não têm exposição pública não autorizada; conferir security groups e IAM por serviço.
4. Publicar as imagens aprovadas, com tags imutáveis vinculadas à release. Não embutir segredo em imagem ou variável de build.
5. Configurar task definitions e roles separadas conforme a necessidade da API, interface e worker.
6. Aplicar migrações com job controlado e observar resultado. Não direcionar tráfego se a migração falhar.
7. Implantar serviços, validar health checks e readiness, TLS e conectividade autorizada ao banco e S3.
8. Configurar DNS e webhook(s) validados para as integrações selecionadas.
9. Criar o primeiro tenant por processo administrativo protegido; adicionar administrador inicial e encaminhar convite por canal seguro.
10. Carregar somente dados da empresa aprovados, validar catálogo e regras operacionais e executar testes de isolamento.
11. Confirmar backup recente, alertas ativos, logs acessíveis apenas a operadores autorizados e procedimento de rollback.
12. Registrar release, migrações, testes, aprovações, responsáveis e horário de liberação.

Os comandos exatos para provisionar e publicar dependem da ferramenta de IaC, pipeline e repositórios selecionados. Não executar comandos de provisionamento manual fora do procedimento aprovado para o ambiente.

## 6. Onboarding de uma nova empresa

1. Receber autorização e dados cadastrais mínimos da empresa.
2. Criar tenant com identificador único e estado inicial controlado.
3. Criar vínculo de administrador ao tenant e entregar convite individual com expiração.
4. Configurar identidade, localização, canais, horário, modalidades de atendimento e políticas comerciais.
5. Carregar catálogo da empresa e validar SKU, preços, status e saldo inicial.
6. Configurar integrações específicas da empresa em gestor seguro de segredos, associando referências ao tenant.
7. Validar domínio ou identificador público, catálogo e webhooks sem misturar configurações de outros tenants.
8. Executar testes de isolamento e teste de operação com usuários da própria empresa.
9. Registrar quem aprovou a ativação e habilitar o tenant somente após validação.

Suspensão ou encerramento de tenant deve desabilitar acesso, integrações e tarefas futuras conforme política aprovada, preservando ou eliminando dados conforme requisitos legais e de retenção aplicáveis. A ação deve ser auditada.

## 7. Validação pós-instalação

Executar em homologação e repetir verificações críticas em produção após cada release.

### 7.1. Saúde e rede

- [ ] DNS resolve para o ponto de entrada esperado e TLS está válido.
- [ ] Health checks de liveness/readiness estão saudáveis.
- [ ] Banco e buckets não estão acessíveis publicamente.
- [ ] Apenas serviços autorizados alcançam PostgreSQL e S3.
- [ ] Logs e métricas chegam ao ambiente de monitoramento sem segredos.

### 7.2. Funcionalidade e dados

- [ ] Usuário do tenant A autentica, consulta o próprio catálogo e executa operações permitidas.
- [ ] Usuário do tenant B vê somente catálogo, configurações e pedidos do tenant B.
- [ ] Busca, IDs manipulados, filtros, exportações e alterações não revelam nem alteram registros do outro tenant.
- [ ] SKU repetido em empresas distintas é processado conforme unicidade por tenant.
- [ ] Orçamento/pedido e alterações de estoque respeitam transações, permissões e quantidades válidas.
- [ ] Estado inválido de pedido é rejeitado sem gravação parcial.
- [ ] Tenant inativo, membership revogado ou contexto ausente não é tratado como tenant padrão.

### 7.3. Integrações e tarefas

- [ ] Webhook inválido ou não autenticado é rejeitado e não revela dados.
- [ ] Webhook válido é associado somente ao tenant da integração.
- [ ] Falha de provedor é registrada como falha, não como envio concluído.
- [ ] Reentrega do mesmo evento não cria pedidos ou notificações duplicados.
- [ ] Worker de recompra respeita tenant, consentimento, frequência e descadastro.
- [ ] Arquivos privados de uma empresa não podem ser obtidos por usuário de outra.

### 7.4. Recuperação e operação

- [ ] Backup automático está ativo com retenção aprovada.
- [ ] Restauração foi ensaiada em ambiente não produtivo e o resultado registrado.
- [ ] Alarmes de falha de serviço, banco, worker, webhook e backup têm responsável.
- [ ] Versão anterior e procedimento de rollback são conhecidos pela equipe de plantão.
- [ ] Aprovação de liberação foi registrada por responsável autorizado.

## 8. Operação recorrente

### Diariamente ou conforme criticidade

- Revisar alarmes, falhas da API, erros de webhook/envio e execução do worker.
- Verificar uso de banco, conexões, armazenamento e limites de serviço.
- Acompanhar tenants suspensos e integrações com falha.

### A cada release

- Revisar mudanças e migrações, validar em homologação, confirmar testes cross-tenant e registrar versão.
- Publicar imagens imutáveis; não substituir tag já liberada.
- Observar a nova revisão ECS e manter plano de retorno compatível com o estado do banco.

### Periodicamente

- Ensaiar restauração de backup e revisar retenção.
- Revisar acessos IAM, memberships administrativas, credenciais de integração e domínios.
- Rever custos, quotas, limites de IA/mensageria e capacidade do ambiente.
- Revisar políticas de consentimento, retenção, descadastro e acesso a dados com responsáveis da empresa.

## 9. Tratamento de falhas

- **Serviço ECS não saudável:** interromper promoção da release, consultar logs/health checks e reverter a revisão se a aplicação anterior for compatível com o esquema atual.
- **Falha de conexão PostgreSQL:** confirmar estado do RDS, rede, security groups, segredo e limite de conexões; não habilitar acesso público como mitigação.
- **Migração com falha:** interromper o rollout, preservar logs, avaliar o estado do esquema e executar plano aprovado; não apagar ou recriar banco para contornar erro.
- **Webhook sem tenant correspondente:** rejeitar e registrar metadados mínimos para diagnóstico; não escolher tenant por padrão.
- **Falha de mensagem/IA:** registrar o estado e oferecer fluxo de atendimento humano quando possível; não afirmar ao cliente que uma operação foi concluída se não foi confirmada.
- **Suspeita de acesso cruzado:** suspender a operação afetada conforme procedimento de incidente, preservar evidências e acionar responsáveis de segurança/privacidade.

## 10. Itens ainda necessários para um guia executável por comandos

Antes de publicar comandos copy/paste e parâmetros definitivos, aprovar:

- Região AWS, conta/ambientes, domínio e nomes dos recursos.
- Ferramenta e linguagem de IaC, processo de CI/CD e repositório de deploy.
- Tamanho/escala dos serviços, quotas, disponibilidade, RPO/RTO, backup e retenção.
- Provedor de WhatsApp e IA, configuração de webhook, limites e procedimento de suporte.
- Regras comerciais, carga do catálogo e processo de onboarding/encerramento de tenants.

Este manual fornece o fluxo comum para empresas do ramo. Parâmetros específicos devem ser fornecidos por cada empresa e tratados como configuração isolada, não como alteração no código da plataforma.

## 11. Critérios de aceite da Fase 4

- [ ] O procedimento diferencia desenvolvimento, homologação e produção.
- [ ] Os passos de instalação cobrem infraestrutura, aplicação, migrações, tenant inicial, integrações e validação.
- [ ] O onboarding pode ser repetido para empresas distintas sem reutilizar dados ou credenciais.
- [ ] Os testes verificam isolamento de dados, arquivos, webhooks e tarefas em segundo plano.
- [ ] As práticas de release, backup, recuperação e tratamento de falhas estão documentadas.
- [ ] Dependências e parâmetros pendentes para comandos definitivos estão explícitos.

## 12. Gate de aprovação

**Fase aprovada pelo solicitante em 26/10/2026. A Fase 5 documental está autorizada; essa aprovação não autoriza provisionar infraestrutura nem executar comandos de implantação.**

Decisões registradas para a Fase 5: região AWS `sa-east-1` e AWS CDK com Python.
