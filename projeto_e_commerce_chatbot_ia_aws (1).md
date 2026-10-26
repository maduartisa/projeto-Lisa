# Projeto de Implementação: Lisa Comercial Ltda.
**Solução Completa de E-commerce, IA WhatsApp e CRM Preditivo**

---

## 1. Módulo de Banco de Dados (`schema.sql`)

```sql
-- =========================================================
-- ESQUEMA COMPLETO DE BANCO DE DADOS - POSTGRESQL (AWS RDS)
-- Projeto: Lisa Comercial Ltda.
-- =========================================================

-- TIPOS ENUMERADOS
CREATE TYPE status_pedido AS ENUM (
    'orcamento',
    'pendente',
    'em_separacao',
    'pronto_retirada',
    'em_transito',
    'concluido',
    'cancelado'
);

CREATE TYPE tipo_entrega AS ENUM (
    'clique_e_retire',
    'delivery_express'
);

CREATE TYPE canal_origem AS ENUM (
    'whatsapp_ia',
    'balcao_presencial',
    'catalogo_web'
);

-- 1. TABELA DE CLIENTES
CREATE TABLE clientes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    telefone VARCHAR(20) UNIQUE NOT NULL, -- Identificador único do WhatsApp
    cpf_cnpj VARCHAR(20),
    email VARCHAR(100),
    endereco_logradouro VARCHAR(150),
    endereco_numero VARCHAR(20),
    endereco_bairro VARCHAR(50) DEFAULT 'Taguatinga',
    endereco_cidade VARCHAR(50) DEFAULT 'Brasília',
    endereco_uf VARCHAR(2) DEFAULT 'DF',
    cep VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- INDEX PARA BUSCA RÁPIDA VIA TELEFONE DO WHATSAPP
CREATE INDEX idx_clientes_telefone ON clientes(telefone);

-- 2. TABELA DE PRODUTOS
CREATE TABLE produtos (
    id SERIAL PRIMARY KEY,
    codigo_sku VARCHAR(50) UNIQUE NOT NULL,
    nome VARCHAR(150) NOT NULL,
    categoria VARCHAR(50) NOT NULL, -- ex: 'Limpeza', 'Descartáveis', 'Piscina', 'Automotivo'
    descricao TEXT,
    preco NUMERIC(10,2) NOT NULL CHECK (preco >= 0),
    estoque_atual INT NOT NULL DEFAULT 0 CHECK (estoque_atual >= 0),
    imagem_url VARCHAR(255),
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- INDEX PARA BUSCA TEXTUAL EM NOME E CATEGORIA DE PRODUTOS
CREATE INDEX idx_produtos_busca ON produtos(LOWER(nome), categoria);

-- 3. TABELA DE PEDIDOS E ORÇAMENTOS
CREATE TABLE pedidos (
    id SERIAL PRIMARY KEY,
    cliente_id INT NOT NULL REFERENCES clientes(id) ON DELETE RESTRICT,
    tipo_entrega tipo_entrega NOT NULL DEFAULT 'clique_e_retire',
    status status_pedido NOT NULL DEFAULT 'orcamento',
    origem canal_origem NOT NULL DEFAULT 'whatsapp_ia',
    valor_produtos NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    taxa_entrega NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    valor_total NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    observacoes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- INDEX PARA ACOMPANHAMENTO DE STATUS DE PEDIDOS NO BALCÃO
CREATE INDEX idx_pedidos_status ON pedidos(status, created_at DESC);

-- 4. ITENS DO PEDIDO
CREATE TABLE itens_pedido (
    id SERIAL PRIMARY KEY,
    pedido_id INT NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    produto_id INT NOT NULL REFERENCES produtos(id) ON DELETE RESTRICT,
    quantidade INT NOT NULL CHECK (quantidade > 0),
    preco_unitario NUMERIC(10,2) NOT NULL
);

-- 5. TABELA DE HISTÓRICO E CRM PREDITIVO (RECOMPRA)
CREATE TABLE crm_recompra (
    id SERIAL PRIMARY KEY,
    cliente_id INT NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    produto_id INT NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    data_ultima_compra DATE NOT NULL,
    dias_ciclo_recompra INT NOT NULL DEFAULT 30, -- Dias estimados para consumo do produto
    proxima_notificacao DATE NOT NULL,
    notificado BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_crm_notificacao ON crm_recompra(proxima_notificacao, notificado);

-- 6. SEEDING INICIAL DE PRODUTOS DA LISA COMERCIAL
INSERT INTO produtos (codigo_sku, nome, categoria, descricao, preco, estoque_atual, imagem_url) VALUES
('LIM-001', 'Detergente Neutro Concentrado 5L', 'Limpeza', 'Detergente de alta rendimento para louças e superfícies.', 28.90, 45, 'https://lisa-comercial-media-assets.s3.sa-east-1.amazonaws.com/detergente-5l.jpg'),
('LIM-002', 'Desinfetante Pinho 5L', 'Limpeza', 'Desinfetante bactericida com aroma suave de pinho.', 32.50, 30, 'https://lisa-comercial-media-assets.s3.sa-east-1.amazonaws.com/desinfetante-5l.jpg'),
('LIM-003', 'Água Sanitária 5L', 'Limpeza', 'Alvejante e desinfetante com 2.5% de cloro ativo.', 18.00, 60, 'https://lisa-comercial-media-assets.s3.sa-east-1.amazonaws.com/agua-sanitaria-5l.jpg'),
('PISC-001', 'Cloro Granulado para Piscina 10kg', 'Piscina', 'Cloro dicloro concentrado para tratamento choque e manutenção.', 189.90, 15, 'https://lisa-comercial-media-assets.s3.sa-east-1.amazonaws.com/cloro-10kg.jpg'),
('PISC-002', 'Clarificante Líquido 1L', 'Piscina', 'Floculante para decantação e clarificação de água.', 24.00, 25, 'https://lisa-comercial-media-assets.s3.sa-east-1.amazonaws.com/clarificante-1l.jpg'),
('DESC-001', 'Copo Descartável 200ml (Caixa c/ 2500)', 'Descartáveis', 'Copos plásticos transparentes reforçados.', 85.00, 20, 'https://lisa-comercial-media-assets.s3.sa-east-1.amazonaws.com/copo-200ml.jpg'),
('DESC-002', 'Papel Toalha Interfolha 2 Dobras (Pct 1000 fls)', 'Descartáveis', 'Papel toalha 100% celulose branca de alta absorção.', 42.00, 50, 'https://lisa-comercial-media-assets.s3.sa-east-1.amazonaws.com/papel-toalha.jpg');

-- VIEW PARA RELATÓRIO DO BALCÃO (ACOMPANHAMENTO EM TEMPO REAL)
CREATE VIEW vw_pedidos_balcao AS
SELECT 
    p.id AS pedido_id,
    c.nome AS cliente_nome,
    c.telefone AS cliente_telefone,
    p.tipo_entrega,
    p.status,
    p.valor_total,
    p.created_at
FROM pedidos p
JOIN clientes c ON p.cliente_id = c.id
WHERE p.status IN ('pendente', 'em_separacao', 'pronto_retirada')
ORDER BY p.created_at ASC;
```

---

## 2. Configurações de Ambiente (`.env.example`)

```env
# SERVER CONFIG
PORT=8000
ENVIRONMENT=production

# DATABASE CONFIG (AWS RDS)
DB_HOST=lisa-db.c123456789.sa-east-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=lisacomercial
DB_USER=lisa_admin
DB_PASS=MudarSenhaSegura2026!

# AWS S3 & CREDENTIALS
AWS_REGION=sa-east-1
S3_BUCKET_NAME=lisa-comercial-media-assets

# WHATSAPP API (Evolution API / Z-API / Meta API)
WHATSAPP_API_URL=https://api.whatsapp.gateway.com/send
WHATSAPP_API_TOKEN=token_secreto_whatsapp_123

# OPENAI API KEY (AGENT DE IA)
OPENAI_API_KEY=sk-proj-xxxxxx_sua_chave_openai_aqui
```

---

## 3. Conexão com o Banco de Dados (`database.py`)

```python
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

def get_db_connection():
    """Cria e retorna uma conexão ativa com o banco de dados PostgreSQL no AWS RDS."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        print(f"[ERRO DE CONEXÃO COM BANCO]: {e}")
        raise e
```

---

## 4. Agente de IA Comercial e Processamento (`ai_agent.py`)

```python
import os
import json
from openai import OpenAI
from database import get_db_connection

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# DEFINE AS FERRAMENTAS (TOOLS) PARA O AGENTE DE IA
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "consultar_estoque_produtos",
            "description": "Consulta o estoque e preço de produtos de limpeza, piscina ou descartáveis na loja.",
            "parameters": {
                "type": "object",
                "properties": {
                    "termo_busca": {
                        "type": "string",
                        "description": "Nome ou tipo do produto (ex: cloro, detergente, copo, papel toalha)."
                    }
                },
                "required": ["termo_busca"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "criar_orcamento",
            "description": "Cria um orçamento/pré-pedido no sistema para Clique e Retire ou Delivery.",
            "parameters": {
                "type": "object",
                "properties": {
                    "telefone_cliente": {"type": "string"},
                    "nome_cliente": {"type": "string"},
                    "produtos_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Lista com os IDs dos produtos."
                    },
                    "quantidades": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Lista com as quantidades correspondentes."
                    },
                    "tipo_entrega": {
                        "type": "string",
                        "enum": ["clique_e_retire", "delivery_express"]
                    }
                },
                "required": ["telefone_cliente", "nome_cliente", "produtos_ids", "quantidades", "tipo_entrega"]
            }
        }
    }
]

def consultar_estoque_produtos(termo_busca: str):
    """Executa busca no banco RDS por produtos que contenham o termo procurado."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT id, codigo_sku, nome, categoria, preco, estoque_atual, imagem_url
        FROM produtos
        WHERE (LOWER(nome) LIKE LOWER(%s) OR LOWER(categoria) LIKE LOWER(%s)) AND ativo = TRUE;
    """
    param = f"%{termo_busca}%"
    cursor.execute(query, (param, param))
    produtos = cursor.fetchall()
    conn.close()
    
    if not produtos:
        return {"status": "sucesso", "mensagem": "Nenhum produto encontrado com esse termo."}
    
    return {"status": "sucesso", "produtos": produtos}

def criar_orcamento(telefone_cliente: str, nome_cliente: str, produtos_ids: list, quantidades: list, tipo_entrega: str):
    """Registra cliente (se novo) e cria orçamento no banco de dados."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Garante o cadastro do cliente
        cursor.execute("SELECT id FROM clientes WHERE telefone = %s;", (telefone_cliente,))
        cliente = cursor.fetchone()
        
        if not cliente:
            cursor.execute(
                "INSERT INTO clientes (nome, telefone) VALUES (%s, %s) RETURNING id;",
                (nome_cliente, telefone_cliente)
            )
            cliente_id = cursor.fetchone()['id']
        else:
            cliente_id = cliente['id']
            
        # 2. Calcula os totais
        valor_produtos = 0.00
        itens_para_inserir = []
        
        for p_id, qtd in zip(produtos_ids, quantidades):
            cursor.execute("SELECT preco, estoque_atual FROM produtos WHERE id = %s;", (p_id,))
            prod = cursor.fetchone()
            if prod:
                subtotal = float(prod['preco']) * qtd
                valor_produtos += subtotal
                itens_para_inserir.append((p_id, qtd, prod['preco']))
                
        taxa_entrega = 15.00 if tipo_entrega == "delivery_express" else 0.00
        valor_total = valor_produtos + taxa_entrega
        
        # 3. Insere o Pedido
        cursor.execute("""
            INSERT INTO pedidos (cliente_id, tipo_entrega, status, origem, valor_produtos, taxa_entrega, valor_total)
            VALUES (%s, %s, 'orcamento', 'whatsapp_ia', %s, %s, %s) RETURNING id;
        """, (cliente_id, tipo_entrega, valor_produtos, taxa_entrega, valor_total))
        
        pedido_id = cursor.fetchone()['id']
        
        # 4. Insere os Itens do Pedido
        for p_id, qtd, preco_unit in itens_para_inserir:
            cursor.execute("""
                INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario)
                VALUES (%s, %s, %s, %s);
            """, (pedido_id, p_id, qtd, preco_unit))
            
        conn.commit()
        conn.close()
        
        return {
            "status": "sucesso",
            "pedido_id": pedido_id,
            "valor_total": valor_total,
            "mensagem": f"Orçamento #{pedido_id} criado com sucesso! Total: R$ {valor_total:.2f}. Opção: {tipo_entrega}."
        }
    except Exception as e:
        conn.rollback()
        conn.close()
        return {"status": "erro", "detalhes": str(e)}

def orquestrar_resposta_ia(telefone_cliente: str, nome_cliente: str, mensagem_texto: str) -> str:
    """Orquestra o diálogo do cliente no WhatsApp usando a API Function Calling da OpenAI."""
    system_prompt = (
        "Você é o assistente virtual inteligente da empresa 'Lisa Comercial Ltda.', especialista em produtos "
        "de limpeza, piscina e descartáveis em Taguatinga/DF.\n"
        "Seu objetivo é ser atencioso, rápido e ajudar o cliente a consultar preços, checar estoque e montar orçamentos.\n"
        "Sempre informe que temos a opção de 'Clique e Retire' (sem filas no balcão) e 'Delivery Express' para o DF."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Cliente: {nome_cliente} ({telefone_cliente})\nMensagem: {mensagem_texto}"}
    ]
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=TOOLS_SCHEMA,
        tool_choice="auto"
    )
    
    response_message = response.choices[0].message
    
    # Executa Function Call se a IA requisitar
    if response_message.tool_calls:
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            
            if function_name == "consultar_estoque_produtos":
                tool_result = consultar_estoque_produtos(arguments.get("termo_busca"))
            elif function_name == "criar_orcamento":
                tool_result = criar_orcamento(
                    telefone_cliente=telefone_cliente,
                    nome_cliente=nome_cliente,
                    produtos_ids=arguments.get("produtos_ids"),
                    quantidades=arguments.get("quantidades"),
                    tipo_entrega=arguments.get("tipo_entrega")
                )
            
            messages.append(response_message)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(tool_result, ensure_ascii=False)
            })
            
        final_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        return final_response.choices[0].message.content

    return response_message.content
```

---

## 5. API Backend Principal (`main.py`)

```python
import os
import requests
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from database import get_db_connection
from ai_agent import orquestrar_resposta_ia

app = FastAPI(
    title="Lisa Comercial - API Backend",
    description="API do Sistema E-commerce, WhatsApp IA e CRM Preditivo",
    version="1.0.0"
)

WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL")
WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN")

class MensagemWhatsAppInbound(BaseModel):
    telefone: str
    nome: str
    mensagem: str

def enviar_resposta_whatsapp(telefone: str, texto_resposta: str):
    """Envia a mensagem de resposta via API Gateway do WhatsApp."""
    if not WHATSAPP_API_URL:
        print(f"[SIMULAÇÃO WHATSAPP PARA {telefone}]: {texto_resposta}")
        return
        
    payload = {
        "number": telefone,
        "options": {"delay": 1200},
        "textMessage": {"text": texto_resposta}
    }
    headers = {
        "Content-Type": "application/json",
        "apikey": WHATSAPP_API_TOKEN
    }
    try:
        requests.post(WHATSAPP_API_URL, json=payload, headers=headers, timeout=10)
    except Exception as e:
        print(f"[ERRO DISPARO WHATSAPP]: {e}")

@app.post("/webhook/whatsapp")
async def webhook_whatsapp(data: MensagemWhatsAppInbound, background_tasks: BackgroundTasks):
    """Webhook que recebe mensagens do WhatsApp e processa de forma assíncrona."""
    def processar_e_responder():
        resposta_ia = orquestrar_resposta_ia(
            telefone_cliente=data.telefone,
            nome_cliente=data.nome,
            mensagem_texto=data.mensagem
        )
        enviar_resposta_whatsapp(data.telefone, resposta_ia)

    background_tasks.add_task(processar_e_responder)
    return {"status": "recebido", "mensagem": "Processando mensagem no background."}

@app.get("/api/v1/produtos")
def listar_produtos():
    """Retorna lista de produtos cadastrados (utilizado pelo Catálogo Web)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM produtos WHERE ativo = TRUE ORDER BY categoria, nome;")
    produtos = cursor.fetchall()
    conn.close()
    return {"produtos": produtos}

@app.get("/api/v1/balcao/pedidos")
def listar_pedidos_balcao():
    """Retorna pedidos ativos para monitoramento nos 2 PCs de balcão da loja."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vw_pedidos_balcao;")
    pedidos = cursor.fetchall()
    conn.close()
    return {"pedidos_pendentes": pedidos}

@app.put("/api/v1/balcao/pedidos/{pedido_id}/status")
def atualizar_status_pedido(pedido_id: int, novo_status: str):
    """Atualiza o status do pedido (ex: de 'pendente' para 'pronto_retirada')."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE pedidos SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s RETURNING id;",
            (novo_status, pedido_id)
        )
        pedido = cursor.fetchone()
        conn.commit()
        conn.close()
        
        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido não encontrado.")
            
        return {"status": "sucesso", "mensagem": f"Pedido #{pedido_id} alterado para '{novo_status}'."}
    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))
```

---

## 6. Serviço de CRM Preditivo (`crm_service.py`)

```python
import os
import datetime
import requests
from database import get_db_connection

WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL")
WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN")

def processar_notificacoes_recompra():
    """
    Rotina periódica (cron job) que verifica no RDS quais clientes estão 
    no prazo estimado para reposição de produtos de limpeza/descartáveis.
    """
    hoje = datetime.date.today()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Busca clientes e itens a serem notificados hoje
    query = """
        SELECT 
            r.id AS crm_id,
            c.nome AS cliente_nome,
            c.telefone AS cliente_telefone,
            p.nome AS produto_nome,
            r.dias_ciclo_recompra
        FROM crm_recompra r
        JOIN clientes c ON r.cliente_id = c.id
        JOIN produtos p ON r.produto_id = p.id
        WHERE r.proxima_notificacao <= %s AND r.notificado = FALSE;
    """
    
    cursor.execute(query, (hoje,))
    pendentes = cursor.fetchall()
    
    print(f"[{hoje}] Encontrados {len(pendentes)} lembretes de recompra para disparar.")
    
    for item in pendentes:
        mensagem = (
            f"Olá, {item['cliente_nome']}! Tudo bem?\n\n"
            f"Notamos que já se passaram aproximadamente {item['dias_ciclo_recompra']} dias desde a sua última compra de "
            f"*{item['produto_nome']}* na Lisa Comercial.\n\n"
            f"Gostaria de renovar o seu estoque hoje com a gente? "
            f"Responda essa mensagem para montar o seu pedido no *Clique e Retire* ou *Entrega Express*!"
        )
        
        # Envia pelo WhatsApp
        if WHATSAPP_API_URL:
            payload = {
                "number": item['cliente_telefone'],
                "options": {"delay": 1000},
                "textMessage": {"text": mensagem}
            }
            headers = {"Content-Type": "application/json", "apikey": WHATSAPP_API_TOKEN}
            try:
                requests.post(WHATSAPP_API_URL, json=payload, headers=headers, timeout=10)
                
                # Marca como notificado no banco
                cursor.execute("UPDATE crm_recompra SET notificado = TRUE WHERE id = %s;", (item['crm_id'],))
                conn.commit()
                print(f"[CRM ENVIADO]: {item['cliente_telefone']} - {item['produto_nome']}")
            except Exception as e:
                print(f"[ERRO AO ENVIAR CRM]: {e}")
                conn.rollback()
        else:
            print(f"[SIMULAÇÃO CRM]:\nPara: {item['cliente_telefone']}\nMensagem: {mensagem}\n")

    conn.close()

if __name__ == "__main__":
    processar_notificacoes_recompra()
```

---

## 7. Containerização Docker (`Dockerfile` e `docker-compose.yml`)

### `Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia requisitos e instala bibliotecas Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código da aplicação
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `requirements.txt`
```text
fastapi==0.110.0
uvicorn==0.28.0
psycopg2-binary==2.9.9
requests==2.31.0
openai==1.14.1
python-dotenv==1.0.1
pydantic==2.6.4
```

### `docker-compose.yml`
```yaml
version: '3.8'

services:
  api:
    build: .
    container_name: lisa_api_server
    ports:
      - "8000:8000"
    env_file:
      - .env
    restart: always

  crm_cron:
    build: .
    container_name: lisa_crm_worker
    command: python crm_service.py
    env_file:
      - .env
    restart: "no"
```