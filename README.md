# Checkpoint 1 — Pipeline de Análise de Notícias Multi-Agente

> Grupo 5 — Sistemas Multi-Agente | JSON-RPC 2.0 + Registro das etapas + MCP

## Objetivo

Prova de conceito de um pipeline de análise de notícias baseado em sistemas multi-agente.
Agentes especializados cooperam por meio do protocolo **JSON-RPC 2.0** (inspirado no A2A) para processar URLs de notícias e retornar resumo, sentimento e categoria de forma estruturada. A versão atual também inclui um **registro das etapas** e um servidor **MCP** para expor recursos, ferramentas e prompts a clientes de LLM.

## Arquitetura

```
┌─────────────────────────────────────────────────────┐
│                  Interface (Streamlit)               │
│                    localhost:8501                    │
└───────────────────────┬─────────────────────────────┘
                        │ HTTP POST /analyze
                        ▼
┌─────────────────────────────────────────────────────┐
│              Orquestrador (FastAPI)                  │
│                 localhost:8000                       │
│                                                      │
│  1. Extrai conteúdo de cada URL                      │
│  2. Distribui texto para os 3 agentes via JSON-RPC   │
│  3. Consolida resultados + mede latência por agente  │
│  4. Persiste relatório JSON em /reports/             │
│  5. Persiste registro JSON por execução              │
└────────┬────────────────┬───────────────┬────────────┘
         │ JSON-RPC 2.0   │ JSON-RPC 2.0  │ JSON-RPC 2.0
         ▼                ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
│  Resumidor   │ │  Sentimento  │ │  Categorizador   │
│  :8001 /rpc  │ │  :8002 /rpc  │ │   :8003 /rpc     │
│              │ │              │ │                  │
│ method:      │ │ method:      │ │ method:          │
│ "summarize"  │ │ "analyze_    │ │ "categorize"     │
│              │ │  sentiment"  │ │                  │
│ → resumo em  │ │ → positivo / │ │ → política /     │
│   3 frases   │ │   neutro /   │ │   economia /     │
│              │ │   negativo   │ │   tecnologia /   │
│              │ │              │ │   saúde / ...    │
└──────────────┘ └──────────────┘ └──────────────────┘
         │                │               │
         └────────────────┴───────────────┘
                          │ LLM (Groq — llama-3.1-8b-instant)
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│              Servidor MCP (:8004 /mcp)              │
│  Resources: arquitetura, relatórios                  │
│  Tools: analyze_urls, latest_report                  │
│  Prompt: roteiro de demo                             │
└─────────────────────────────────────────────────────┘
```

### Formato das mensagens (JSON-RPC 2.0)

**Requisição:**
```json
{
  "jsonrpc": "2.0",
  "method": "summarize",
  "params": { "text": "conteúdo da notícia..." },
  "id": "uuid-gerado-pelo-orquestrador"
}
```

**Resposta:**
```json
{
  "jsonrpc": "2.0",
  "result": { "summary": "resumo em 3 frases..." },
  "id": "uuid-gerado-pelo-orquestrador"
}
```

## Integrantes

| Nome | RA | Responsabilidade |
|------|----|-----------------|
| Gabriel Henrique da Silva | 22020864 | Orquestrador, contrato JSON-RPC, integração A2A |
| Lucas de Lima Benvenuti | 20030714 | Agente resumidor, extração de URLs |
| Gustavo Santos Steluti | 23016017 | Agente resumidor, validação dos resumos |
| Renan Oliveira da Silva | 22020962 | Agente de sentimento, categorizador, testes |
| Samantha Dell Vecchio Esteves | 22871941 | Diagrama de arquitetura, documentação, demo |

## Stack Técnica

| Componente | Tecnologia |
|-----------|-----------|
| Framework HTTP | FastAPI + Uvicorn |
| LLM | Groq API (llama-3.1-8b-instant) — gratuito |
| Comunicação inter-agentes | HTTP + JSON-RPC 2.0 |
| Integração com clientes LLM | MCP (`mcp[cli]` + FastMCP) |
| Validação de dados | Pydantic v2 |
| Extração de conteúdo | Extrator de texto de páginas |
| Interface | Streamlit |
| Persistência | Relatórios e registros das etapas em `/reports/` |
| Variáveis de ambiente | python-dotenv |

## Pré-requisitos

- Python 3.10+
- Chave gratuita da [Groq](https://console.groq.com/keys)

## Instalação

```bash
# 1. Clone o repositório
git clone <url-do-repo>
cd checkpoint2

# 2. Crie e ative um ambiente virtual
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Windows PowerShell: Copy-Item .env.example .env
# Por padrão AGENT_MODE=llm usa a API da Groq.
# Para testar sem API, altere para AGENT_MODE=local.
# Substitua GROQ_API_KEY pela sua chave real antes da demo principal.
```

## Como rodar

```bash
bash start.sh
```

No Windows PowerShell:

```powershell
.\start.ps1
```

Os scripts iniciam os 4 serviços principais (portas 8000–8003), o servidor MCP HTTP em `http://localhost:8004/mcp` e abrem o Streamlit em `http://localhost:8501`.

### Rodar manualmente (alternativa)

```bash
# Terminal 1 — Agente Resumidor
uvicorn agents.summarizer_agent:app --port 8001

# Terminal 2 — Agente de Sentimento
uvicorn agents.sentiment_agent:app --port 8002

# Terminal 3 — Agente Categorizador
uvicorn agents.categorizer_agent:app --port 8003

# Terminal 4 — Orquestrador
uvicorn orchestrator.main:app --port 8000

# Terminal 5 — Servidor MCP (HTTP streamable)
MCP_TRANSPORT=streamable-http MCP_PORT=8004 python mcp_server.py

# Terminal 6 — Interface
streamlit run app.py
```

### Testar via curl

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"urls": ["sample://tecnologia", "sample://economia", "sample://saude"]}'
```

As URLs `sample://tecnologia`, `sample://economia` e `sample://saude` são notícias locais de demonstração. Elas evitam depender de sites externos para extrair texto. Se `AGENT_MODE=llm`, os agentes ainda usam a API da Groq para resumo, sentimento e categoria. Para ensaiar sem gastar API, altere temporariamente para `AGENT_MODE=local`.

### Usar MCP

O servidor MCP expõe:

- Resource `news://architecture`: resumo da arquitetura e protocolos.
- Resource `news://reports`: índice dos relatórios gerados.
- Tool `analyze_urls`: executa o pipeline para uma lista de URLs.
- Tool `latest_report`: retorna o relatório JSON mais recente.
- Prompt `demo_script`: gera um roteiro curto para apresentação.

Exemplo de chamada da tool `analyze_urls` no Inspector:

```json
{"urls": ["sample://tecnologia", "sample://economia", "sample://saude"]}
```

Com `AGENT_MODE=llm`, essa chamada também usa a API da Groq. Use `AGENT_MODE=local` apenas se quiser testar o fluxo sem API.

Para testar com o MCP Inspector:

```bash
MCP_TRANSPORT=streamable-http MCP_PORT=8004 python mcp_server.py
npx -y @modelcontextprotocol/inspector
```

No Inspector, conecte em `http://localhost:8004/mcp`.

## Testes

Para rodar os testes sem consumir a API:

```powershell
$env:AGENT_MODE='local'
python -m unittest discover -s tests -v
python -m compileall agents orchestrator shared app.py extractor.py mcp_server.py tests
```

Linux/Mac:

```bash
AGENT_MODE=local python -m unittest discover -s tests -v
python -m compileall agents orchestrator shared app.py extractor.py mcp_server.py tests
```

## Modo seguro para demo

Por padrão, a demo usa a API da Groq (`AGENT_MODE=llm`). Para evitar gastar limite durante ensaios:

1. Altere `AGENT_MODE=local` no `.env`.
2. Use as URLs `sample://tecnologia`, `sample://economia` e `sample://saude`.
3. Rode testes automatizados apenas quando houver mudança de código relevante.

Com `AGENT_MODE=local`, cada agente responde usando regras simples. Esse modo serve apenas para ensaio e contingência. Para a entrega principal, deixe `AGENT_MODE=llm` e configure `GROQ_API_KEY`.

## Estrutura do Projeto

```
checkpoint2/
├── agents/
│   ├── summarizer_agent.py   # FastAPI — porta 8001
│   ├── sentiment_agent.py    # FastAPI — porta 8002
│   └── categorizer_agent.py  # FastAPI — porta 8003
├── orchestrator/
│   └── main.py               # FastAPI — porta 8000
├── shared/
│   ├── blackboard.py         # Registro das etapas em JSON
│   └── jsonrpc.py            # Modelos Pydantic JSON-RPC 2.0
├── extractor.py              # Extração de texto das notícias
├── app.py                    # Interface Streamlit
├── mcp_server.py             # Servidor MCP com resources, tools e prompt
├── tests/                    # Testes com mocks para fluxo principal
├── reports/                  # Relatórios JSON gerados automaticamente
├── requirements.txt
├── .env.example
├── start.ps1
├── start.sh
└── README.md
```

## Exemplo de Saída (JSON)

```json
{
  "id": "a1b2c3d4-...",
  "total_urls": 1,
  "resultados": [
    {
      "url": "https://...",
      "titulo": "Título da notícia",
      "resumo": "A notícia trata de... O impacto foi... No geral...",
      "sentimento": {
        "sentimento": "neutro",
        "confianca": 0.85,
        "justificativa": "O tom é informativo, sem carga emocional clara."
      },
      "categoria": {
        "categoria": "tecnologia",
        "confianca": 0.92
      },
      "latencia": {
        "extrator_s": 0.812,
        "resumidor_s": 1.204,
        "sentimento_s": 0.987,
        "categorizador_s": 0.756,
        "total_s": 3.759
      }
    }
  ],
  "arquivo": "reports/report_a1b2c3d4.json",
  "blackboard": "reports/blackboard_a1b2c3d4.json"
}
```
