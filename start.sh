#!/bin/bash
set -e

echo "==> Verificando arquivo .env..."
if [ ! -f .env ]; then
    echo "ERRO: Arquivo .env não encontrado. Copie .env.example para .env e configure sua GROQ_API_KEY."
    exit 1
fi

echo "==> Encerrando processos anteriores nas portas 8000-8003..."
for port in 8000 8001 8002 8003; do
    lsof -ti:"$port" | xargs kill -9 2>/dev/null || true
done

sleep 1

echo "==> Iniciando Agente Resumidor   (porta 8001)..."
uvicorn agents.summarizer_agent:app --port 8001 --log-level warning &

echo "==> Iniciando Agente de Sentimento (porta 8002)..."
uvicorn agents.sentiment_agent:app --port 8002 --log-level warning &

echo "==> Iniciando Agente Categorizador (porta 8003)..."
uvicorn agents.categorizer_agent:app --port 8003 --log-level warning &

echo "==> Iniciando Orquestrador        (porta 8000)..."
uvicorn orchestrator.main:app --port 8000 --log-level warning &

echo ""
echo "Aguardando serviços subirem..."
sleep 3

echo "==> Iniciando interface Streamlit..."
streamlit run app.py
