# Checkpoint 2 — Pipeline de Análise de Notícias Multi-Agente

> Grupo 5 — Sistemas Multi-Agente | Comunicação via JSON-RPC 2.0

## Objetivo

Prova de conceito de um pipeline de análise de notícias baseado em sistemas multi-agente.
Agentes especializados cooperam por meio do protocolo **JSON-RPC 2.0** (inspirado no A2A) para processar URLs de notícias e retornar resumo, sentimento e categoria de forma estruturada.

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
│  1. Extrai conteúdo de cada URL (trafilatura)        │
│  2. Distribui texto para os 3 agentes via JSON-RPC   │
│  3. Consolida resultados + mede latência por agente  │
│  4. Persiste relatório JSON em /reports/             │
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
| Validação de dados | Pydantic v2 |
| Extração de conteúdo | trafilatura |
| Interface | Streamlit |
| Persistência | Arquivos JSON em `/reports/` |
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
# Edite .env e adicione sua GROQ_API_KEY
```

## Como rodar

```bash
bash start.sh
```

O script inicia os 4 serviços (portas 8000–8003) e abre o Streamlit em `http://localhost:8501`.

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

# Terminal 5 — Interface
streamlit run app.py
```

### Testar via curl

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://www.bbc.com/portuguese/articles/c5y3r0r4r0go"]}'
```

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
│   └── jsonrpc.py            # Modelos Pydantic JSON-RPC 2.0
├── extractor.py              # Extração de conteúdo via trafilatura
├── app.py                    # Interface Streamlit
├── reports/                  # Relatórios JSON gerados automaticamente
├── requirements.txt
├── .env.example
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
  "arquivo": "reports/report_a1b2c3d4.json"
}
```
