import trafilatura
import json


def extract_article(url: str) -> dict:
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
