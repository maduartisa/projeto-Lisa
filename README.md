# projeto-Lisa
# Lisa Comercial

Documentação do projeto:

- [Fase 1 — Especificação de requisitos](docs/sdd/01-especificacao-requisitos.md)
- [Fase 2 — Arquitetura e instalação](docs/sdd/02-arquitetura-e-instalacao.md)
- [Fase 3 — Especificação técnica e plano](docs/sdd/03-especificacao-tecnica-e-plano.md)
- [Fase 4 — Manual de instalação, operação e validação](docs/sdd/04-manual-instalacao-operacao-validacao.md)
- [Fase 5 — Guia de infraestrutura AWS CDK](docs/sdd/05-guia-infraestrutura-cdk-implantacao.md)
- [Fase 6 — Implementação local da infraestrutura CDK](docs/sdd/06-implementacao-infraestrutura-cdk.md)

O projeto CDK inicial está em [`infrastructure/`](infrastructure/README.md). Ele contém somente a infraestrutura-base; não inclui a aplicação e não foi implantado na AWS.

A aplicação em [`application/`](application/README.md) inclui a fundação multiempresa e os fluxos iniciais de catálogo, clientes, estoque e pedidos. Interfaces web, WhatsApp/IA e deploy continuam fora desta entrega.
