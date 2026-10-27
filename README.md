# projeto-Lisa
# Lisa Comercial

Documentação do projeto:

- [Fase 1 — Especificação de requisitos](docs/sdd/01-especificacao-requisitos.md)
- [Fase 2 — Arquitetura e instalação](docs/sdd/02-arquitetura-e-instalacao.md)
- [Fase 3 — Especificação técnica e plano](docs/sdd/03-especificacao-tecnica-e-plano.md)
- [Fase 4 — Manual de instalação, operação e validação](docs/sdd/04-manual-instalacao-operacao-validacao.md)
- [Fase 5 — Guia de infraestrutura AWS CDK](docs/sdd/05-guia-infraestrutura-cdk-implantacao.md)
- [Fase 6 — Implementação local da infraestrutura CDK](docs/sdd/06-implementacao-infraestrutura-cdk.md)

O projeto CDK em [`infrastructure/`](infrastructure/README.md) contém a infraestrutura-base para AWS; não foi implantado.

A aplicação em [`application/`](application/README.md) inclui uma interface web responsiva para catálogo e operação comercial, com autenticação multiempresa, clientes, equipe e perfis, produtos com variações de tamanho/cor e SKU próprio, compras, estoque, pedidos online sem cobrança, PDV operacional, financeiro básico e auditoria de acessos. Gateways de pagamento, emissão fiscal, WhatsApp/IA e deploy AWS continuam como fases futuras.
