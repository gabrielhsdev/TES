import json

try:
    import trafilatura
except ImportError:
    trafilatura = None


SAMPLE_ARTICLES = {
    "sample://tecnologia": {
        "title": "Startup brasileira anuncia avanço em inteligência artificial",
        "text": (
            "Uma startup brasileira apresentou um novo aplicativo de inteligência artificial para resumir dados "
            "de atendimento ao cliente. A empresa afirma que a tecnologia melhora a produtividade das equipes "
            "e reduz falhas operacionais. Especialistas avaliam que o avanço pode beneficiar pequenas empresas."
        ),
    },
    "sample://economia": {
        "title": "Mercado reduz previsão de inflação após queda do dólar",
        "text": (
            "Analistas do mercado financeiro reduziram a previsão de inflação após nova queda do dólar. "
            "O banco central informou que continuará acompanhando juros e atividade econômica. "
            "Investidores veem o movimento como positivo para a economia."
        ),
    },
    "sample://saude": {
        "title": "Hospital testa sistema para agilizar atendimento de pacientes",
        "text": (
            "Um hospital iniciou testes com um sistema digital para organizar filas de pacientes. "
            "Médicos afirmam que a ferramenta melhora a triagem e reduz o tempo de espera. "
            "A pesquisa clínica será acompanhada durante os próximos meses."
        ),
    },
}


def extract_article(url: str) -> dict:
    if url.startswith("sample://"):
        article = SAMPLE_ARTICLES.get(url)
        if not article:
            return {"url": url, "title": None, "text": None, "error": "Amostra local não encontrada"}
        return {"url": url, "title": article["title"], "text": article["text"], "error": None}

    if trafilatura is None:
        return {
            "url": url,
            "title": None,
            "text": None,
            "error": "Dependência trafilatura não instalada; use sample:// para demo offline",
        }

    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return {"url": url, "title": None, "text": None, "error": "Falha ao buscar a URL"}

    text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    metadata_json = trafilatura.extract(downloaded, output_format="json", include_comments=False)

    title = None
    if metadata_json:
        try:
            meta = json.loads(metadata_json)
            title = meta.get("title")
        except Exception:
            pass

    if not text:
        return {"url": url, "title": title, "text": None, "error": "Não foi possível extrair texto da URL"}

    return {"url": url, "title": title, "text": text[:5000], "error": None}
