import re


CATEGORIES = ["política", "economia", "tecnologia", "saúde", "esportes", "entretenimento", "mundo", "outro"]

KEYWORDS = {
    "política": ["governo", "congresso", "eleição", "presidente", "ministro", "senado", "câmara"],
    "economia": ["economia", "mercado", "inflação", "juros", "banco", "dólar", "investimento"],
    "tecnologia": ["tecnologia", "inteligência artificial", "software", "aplicativo", "dados", "startup"],
    "saúde": ["saúde", "hospital", "vacina", "médico", "paciente", "doença", "pesquisa clínica"],
    "esportes": ["esporte", "futebol", "campeonato", "time", "atleta", "partida", "gol"],
    "entretenimento": ["filme", "série", "show", "música", "festival", "artista", "cinema"],
    "mundo": ["internacional", "país", "guerra", "onu", "europa", "américa", "ásia"],
}

POSITIVE_WORDS = ["alta", "cresce", "melhora", "avanço", "positivo", "recorde", "benefício", "sucesso"]
NEGATIVE_WORDS = ["queda", "crise", "piora", "risco", "negativo", "prejuízo", "falha", "problema"]


def summarize_locally(text: str, max_sentences: int = 3) -> str:
    sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text.strip()) if sentence.strip()]
    if not sentences:
        return "Resumo indisponível: o texto não possui conteúdo suficiente."
    return " ".join(sentences[:max_sentences])


def analyze_sentiment_locally(text: str) -> dict:
    lowered = text.lower()
    positive = sum(1 for word in POSITIVE_WORDS if word in lowered)
    negative = sum(1 for word in NEGATIVE_WORDS if word in lowered)

    if positive > negative:
        sentiment = "positivo"
        confidence = 0.65 + min((positive - negative) * 0.05, 0.25)
    elif negative > positive:
        sentiment = "negativo"
        confidence = 0.65 + min((negative - positive) * 0.05, 0.25)
    else:
        sentiment = "neutro"
        confidence = 0.6

    return {
        "sentimento": sentiment,
        "confianca": round(confidence, 2),
        "justificativa": "Classificação local baseada em palavras-chave para demo sem consumo de API.",
    }


def categorize_locally(text: str) -> dict:
    lowered = text.lower()
    scores = {
        category: sum(1 for keyword in keywords if keyword in lowered)
        for category, keywords in KEYWORDS.items()
    }
    category, score = max(scores.items(), key=lambda item: item[1])
    if score == 0:
        category = "outro"
        confidence = 0.5
    else:
        confidence = min(0.6 + score * 0.1, 0.95)
    return {"categoria": category, "confianca": round(confidence, 2)}
