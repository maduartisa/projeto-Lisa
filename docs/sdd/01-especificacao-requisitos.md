# Fase 1 — Especificação de requisitos

## 1. Objetivo e controle da fase

Este documento registra a especificação inicial de um sistema digital para empresas do mesmo segmento comercial da Lisa Comercial: comércio de produtos como itens de limpeza, tratamento de piscinas, descartáveis e categorias correlatas. A solução deve ser parametrizável para cada empresa, sem depender de nome, catálogo, localização, preços, credenciais ou regras exclusivas da Lisa.

Esta é a primeira entrega do processo de desenvolvimento orientado por especificação (SDD). A fase seguinte só deve começar após aprovação explícita deste documento pelo solicitante.

| Campo | Valor |
|---|---|
| Fase | 1 — Especificação de requisitos |
| Estado | Aprovada pelo solicitante em 26/10/2026 |
| Fonte funcional | `projeto_e_commerce_chatbot_ia_aws (1).md` |
| Público-alvo | Empresas varejistas do mesmo ramo, com operação de balcão e atendimento digital |
| Estratégia multiempresa aprovada | PostgreSQL compartilhado com `tenant_id` e isolamento rigoroso entre empresas |

## 2. Visão do produto

Disponibilizar uma plataforma integrada e multiempresa para catálogo digital, consulta de produtos e estoque, criação e acompanhamento de orçamentos e pedidos, atendimento pelo WhatsApp com apoio de IA, operação de balcão e relacionamento para recompra. Cada empresa utilizará a mesma plataforma com dados e configurações segregados das demais.

## 3. Perfis de usuário identificados

1. **Administrador da empresa:** configura a operação e gerencia acessos e parâmetros do sistema.
2. **Operador de balcão:** consulta produtos, acompanha pedidos e atende ou conclui vendas.
3. **Responsável por estoque:** mantém o catálogo e acompanha entradas, saídas e níveis de estoque.
4. **Cliente:** consulta o catálogo, solicita orçamento e escolhe retirada ou entrega quando disponíveis.
5. **Atendimento humano:** assume conversas encaminhadas pelo atendimento automatizado, conforme configuração da empresa.

Os perfis e permissões finais deverão ser detalhados e aprovados na fase de arquitetura e desenho funcional.

## 4. Requisitos funcionais

### RF-01 — Cadastro e consulta de produtos

- Manter produtos com SKU, nome, categoria, descrição, preço, quantidade em estoque, imagem e situação ativa/inativa.
- Permitir consulta por nome, SKU ou categoria.
- Exibir ao cliente somente produtos ativos e informações comerciais autorizadas pela empresa.
- Permitir que a empresa configure suas categorias, produtos, imagens e preços; os dados de demonstração da Lisa não devem ser instalados como catálogo de produção.

### RF-02 — Clientes

- Registrar informações de contato necessárias para atendimento e pedidos.
- Reconhecer clientes por identificador de contato, sujeito à política de privacidade e às regras de normalização aprovadas.
- Permitir atualização dos dados e respeitar solicitações aplicáveis de acesso, correção e exclusão.

### RF-03 — Orçamentos e pedidos

- Criar orçamento ou pré-pedido com cliente, itens, quantidades, preços considerados, modalidade de atendimento e totais.
- Suportar, quando habilitadas pela empresa, venda presencial, retirada no estabelecimento e entrega local.
- Registrar origem do atendimento, incluindo balcão, catálogo digital e WhatsApp.
- Manter estados do pedido configuráveis ou definidos em fluxo aprovado, contemplando ao menos orçamento, pendente, separação, pronto para retirada, em trânsito, concluído e cancelado.
- Preservar a consistência de valores e itens durante a criação e atualização do pedido.

### RF-04 — Estoque

- Consultar disponibilidade de produtos para os canais autorizados.
- Registrar movimentações relevantes, incluindo entradas, saídas de venda e ajustes, conforme definido na configuração funcional.
- Evitar que a finalização de uma venda produza quantidade negativa ou divergência entre pedido e estoque.
- Permitir que cada empresa informe seus limites e regras de reserva ou baixa de estoque.

### RF-05 — Catálogo digital

- Disponibilizar catálogo responsivo, priorizando o uso em dispositivos móveis.
- Apresentar produtos, preços e disponibilidade conforme as regras da empresa.
- Permitir encaminhar uma seleção para solicitação de orçamento ou pedido, sem assumir integração de pagamento online nesta fase.

### RF-06 — Atendimento pelo WhatsApp com IA

- Receber mensagens por integração de WhatsApp suportada e configurada para a empresa.
- Permitir consulta de produtos e estoque e composição de orçamento por ferramentas limitadas às operações autorizadas.
- Informar ao cliente opções comerciais configuradas pela empresa, sem afirmar disponibilidade, preço ou condição que não tenha sido confirmada pelo sistema.
- Permitir encaminhamento para atendimento humano.
- Registrar falhas de integração e estado do processamento de forma operacionalmente observável.

### RF-07 — Operação de balcão

- Exibir pedidos que demandem ação da equipe.
- Permitir atualização de estado por usuário autorizado.
- Disponibilizar consulta rápida de produto e situação do pedido para os operadores.

### RF-08 — Recompra e relacionamento

- Permitir identificar produtos e clientes elegíveis para lembrete de recompra com base em ciclos configurados.
- Permitir ativar, pausar e parametrizar as notificações por empresa.
- Enviar mensagens somente após definição e validação da política de consentimento, frequência, descadastro e canal aplicável.
- Registrar tentativas e resultados de envio para evitar marcação incorreta de notificações não entregues.

### RF-09 — Configuração por empresa

- Permitir configurar identidade comercial, catálogo, localização, horários, modalidades de entrega/retirada, taxas, mensagens e integrações.
- Não fixar em código nome, endereço, região, preços, ciclo de recompra, credenciais ou dados de clientes da Lisa.
- A solução será multiempresa: empresas diferentes poderão utilizar a mesma plataforma, cada uma com seus próprios usuários, configurações, clientes, catálogo, estoque, pedidos e registros operacionais.
- Impedir que usuários de uma empresa consultem ou alterem dados de outra empresa; toda operação deverá ser vinculada à empresa correspondente e ter essa associação validada no servidor.
- Prever cadastro e configuração inicial de cada empresa (tenant), com identidade comercial e integrações próprias.
- Usar PostgreSQL compartilhado com `tenant_id` nos dados pertencentes a empresas; aplicar isolamento rigoroso no servidor em todas as operações.
- Detalhar na Fase 2 os controles técnicos complementares, o provisionamento e a administração dos tenants.

## 5. Requisitos não funcionais

### RNF-01 — Segurança e privacidade

- Proteger dados pessoais e credenciais de integração em trânsito e em armazenamento.
- Aplicar controle de acesso por função e princípio do menor privilégio.
- Aplicar segregação de dados entre empresas em todas as camadas pertinentes, inclusive API, consultas e tarefas em segundo plano; não confiar apenas em filtros ou identificadores enviados pelo cliente.
- Não incluir senhas, tokens ou chaves em código-fonte, documentação pública, imagens de container ou repositório.
- Registrar ações administrativas e alterações relevantes, com acesso restrito aos registros.
- Definir retenção e tratamento de dados conforme legislação aplicável, incluindo a LGPD, e validar políticas com a empresa responsável.

### RNF-02 — Integridade

- Executar alterações relacionadas a pedido e estoque em transações consistentes.
- Validar dados de entrada e retornar erros estruturados, sem expor segredos ou detalhes internos.
- Evitar duplicação de pedidos ou notificações em reenvios de eventos sempre que a integração permitir idempotência.

### RNF-03 — Disponibilidade e recuperação

- A solução deve ter monitoramento de saúde, registro de erros e procedimento documentado de cópia de segurança e restauração.
- Frequência, retenção, objetivos de recuperação e disponibilidade devem ser definidos conforme porte e criticidade da empresa na fase de desenho.

### RNF-04 — Manutenibilidade e integração

- Manter separação entre interface, API, regras de negócio, persistência e integrações externas.
- Expor documentação de API atualizada para as interfaces implementadas.
- Permitir substituir ou configurar provedores externos de WhatsApp e IA sem divulgar credenciais nem amarrar dados a uma empresa específica.

### RNF-05 — Implantação

- A fonte propõe Python/FastAPI, PostgreSQL, Docker e serviços AWS (incluindo banco gerenciado e armazenamento de objetos). Essa combinação é uma referência inicial, não uma decisão final de arquitetura.
- O procedimento de instalação deverá cobrir pré-requisitos, configuração segura de ambiente, provisionamento, implantação, inicialização, validação e operação.
- A topologia, tamanhos, custos, região, disponibilidade e serviços AWS deverão ser aprovados antes da especificação final de instalação.

## 6. Escopo desta solução

### Incluído na especificação inicial

- Catálogo digital e consulta de disponibilidade.
- Cadastro básico de clientes, produtos, orçamentos e pedidos.
- Operação de pedidos de balcão, retirada e entrega local configurável.
- Integração de atendimento via WhatsApp com assistência de IA e transferência humana.
- Rotina de recompra parametrizável.
- Instalação em ambiente de nuvem com banco relacional e execução containerizada como hipótese inicial.

### Fora do escopo da versão inicial

Os itens abaixo não fazem parte da entrega inicial especificada. Sua inclusão futura exige uma nova decisão de escopo e estimativa:

- Checkout e cobrança online, incluindo integração com PIX, cartões ou gateways de pagamento. O sistema poderá registrar informações de pagamento definidas no processo operacional, mas não processará transações nesta versão.
- Emissão de nota fiscal, obrigações contábeis e integração fiscal.
- Integração com ERP, marketplace ou sistemas externos de gestão empresarial.
- Integração automatizada com parceiros de logística para cálculo de rotas, rastreamento ou despacho. A modalidade de entrega local será configurável, sem presumir essa automação.
- Aplicativos nativos para Android ou iOS; a experiência digital será via web responsiva.
- Migração automatizada de dados históricos de outros sistemas. O cadastro/importação inicial de produtos e dados de cada empresa será tratado como procedimento de implantação a especificar, não como migração histórica incluída.
- Gestão de múltiplas filiais, depósitos ou estoques por empresa. Multiempresa significa que várias empresas serão atendidas pela plataforma com isolamento entre elas; não implica, por si só, controle de filiais/depósitos dentro de uma mesma empresa.
- Relatórios avançados de BI, previsão automatizada de demanda, precificação dinâmica ou modelos preditivos além dos lembretes de recompra definidos nos requisitos.
- Desenvolvimento de integrações ou regras sob medida para uma empresa sem aprovação formal de mudança de escopo.

### Decisões a detalhar nas próximas fases

Os pontos abaixo não são funcionalidades excluídas; são decisões de desenho e implantação ainda pendentes:

- Estratégia de isolamento multiempresa (por exemplo, segregação lógica ou recursos de dados separados) e processo de provisionamento de tenants.
- Provedor, plano, região, dimensionamento, disponibilidade e custos da nuvem, WhatsApp e IA.
- Regras comerciais por empresa para entrega, taxas, meios de pagamento registrados, validade de orçamento e horários.
- Política de consentimento, frequência, descadastro e retenção para mensagens de relacionamento, conforme legislação aplicável.
- Procedimento e formato para carga inicial de catálogo e configuração de cada empresa.

## 7. Critérios de aceite desta fase

- [x] O propósito e o público-alvo estão corretos.
- [x] Os perfis de usuário e os módulos funcionais representam a operação desejada.
- [x] A plataforma multiempresa e a segregação de dados entre empresas estão especificadas corretamente.
- [x] O escopo da versão inicial e os itens fora de escopo estão claros.
- [x] As decisões que serão detalhadas nas próximas fases estão corretamente identificadas.
- [x] As premissas de tecnologia e instalação estão corretamente identificadas como hipóteses, quando não forem decisões já aprovadas.

## 8. Gate de aprovação

**Fase aprovada pelo solicitante. A Fase 2 está autorizada e será submetida a aprovação própria antes da Fase 3.**

Decisão registrada: plataforma multiempresa com PostgreSQL compartilhado, `tenant_id` e isolamento rigoroso dos dados de cada empresa.
