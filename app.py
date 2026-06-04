import streamlit as st
import httpx
import os

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8000")

st.set_page_config(page_title="Analisador de Notícias", page_icon="📰", layout="wide")

st.title("Analisador de Notícias Multi-Agente")
st.markdown(
    "Pipeline baseado em sistemas multi-agente com comunicação via **JSON-RPC 2.0**. "
    "Agentes especializados cooperam para resumir, classificar sentimento e categorizar notícias. "
    "O projeto também expõe contexto e ferramentas via **MCP** para demonstrar integração vertical com LLMs."
)

st.divider()

with st.expander("Arquitetura e protocolos da demo"):
    st.markdown(
        """
        - **Orquestrador:** recebe URLs, extrai texto, chama agentes e consolida o relatório.
        - **JSON-RPC 2.0:** contrato horizontal entre orquestrador e agentes independentes.
        - **Registro das etapas:** arquivo JSON com eventos intermediários por URL e etapa.
        - **MCP:** servidor em `mcp_server.py` expondo recursos, ferramentas e prompts para clientes de LLM.
        """
    )

urls_input = st.text_area(
    "URLs das notícias (uma por linha)",
    height=150,
    placeholder="https://www.bbc.com/portuguese/articles/...\nhttps://g1.globo.com/...",
)

col_btn, col_info = st.columns([1, 4])
with col_btn:
    run = st.button("Analisar", type="primary", use_container_width=True)
with col_info:
    st.caption("Cada URL passa pelo orquestrador e pelos agentes de resumo, sentimento e categoria.")

if run:
    urls = [u.strip() for u in urls_input.strip().splitlines() if u.strip()]

    if not urls:
        st.error("Digite ao menos uma URL.")
        st.stop()

    with st.spinner(f"Analisando {len(urls)} URL(s) — isso pode levar alguns segundos..."):
        try:
            response = httpx.post(
                f"{ORCHESTRATOR_URL}/analyze",
                json={"urls": urls},
                timeout=180.0,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.ConnectError:
            st.error("Não foi possível conectar ao orquestrador. Certifique-se de que todos os serviços estão rodando (`bash start.sh`).")
            st.stop()
        except Exception as e:
            st.error(f"Erro: {e}")
            st.stop()

    st.success(f"Análise concluída! Relatório salvo em `{data.get('arquivo', 'N/A')}`")
    if data.get("blackboard"):
        st.caption(f"Registro das etapas salvo em `{data['blackboard']}`")
    st.divider()

    SENTIMENT_EMOJI = {"positivo": "😊", "neutro": "😐", "negativo": "😟"}

    for item in data.get("resultados", []):
        titulo = item.get("titulo") or item["url"]
        with st.expander(f"🔗 {titulo}", expanded=True):
            if item.get("erro"):
                st.error(f"Erro ao processar: {item['erro']}")
                continue

            sentimento = item.get("sentimento") or {}
            categoria = item.get("categoria") or {}
            latencia = item.get("latencia") or {}

            col1, col2, col3 = st.columns(3)

            with col1:
                tom = sentimento.get("sentimento", "N/A")
                emoji = SENTIMENT_EMOJI.get(tom, "❓")
                st.metric("Sentimento", f"{emoji} {tom.capitalize()}")
                confianca_s = sentimento.get("confianca")
                if confianca_s is not None:
                    st.progress(float(confianca_s), text=f"Confiança: {float(confianca_s):.0%}")

            with col2:
                cat = categoria.get("categoria", "N/A")
                st.metric("Categoria", cat.capitalize())
                confianca_c = categoria.get("confianca")
                if confianca_c is not None:
                    st.progress(float(confianca_c), text=f"Confiança: {float(confianca_c):.0%}")

            with col3:
                st.metric("Latência Total", f"{latencia.get('total_s', 0):.2f}s")
                st.caption(
                    f"Extrator: {latencia.get('extrator_s', '?')}s | "
                    f"Resumidor: {latencia.get('resumidor_s', '?')}s | "
                    f"Sentimento: {latencia.get('sentimento_s', '?')}s | "
                    f"Categorizador: {latencia.get('categorizador_s', '?')}s"
                )

            st.markdown("**Resumo:**")
            st.info(item.get("resumo") or "Não disponível")

            if sentimento.get("justificativa"):
                st.caption(f"Justificativa do sentimento: {sentimento['justificativa']}")

    with st.expander("Ver JSON completo do relatório"):
        st.json(data)
