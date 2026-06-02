from domains.bot.search_intent import build_search_query, needs_web_search


def test_explicit_search_anywhere_in_message():
    """'can you search...' should trigger even if it doesn't start with search."""
    assert (
        needs_web_search(
            "puedes buscar cual fue la canción mas reciente que sacó shakira?"
        )
        is True
    )
    assert needs_web_search("puedes buscar en que año estamos?") is True
    assert needs_web_search("busca en que año estamos") is True


def test_freshness_without_explicit_search():
    assert needs_web_search("helith en qué año estamos?") is True
    assert needs_web_search("cuál es el álbum más reciente de calvin harris") is True


def test_build_search_query_year():
    assert build_search_query("busca en que año estamos") == "current year today's date"
    assert build_search_query("helith en qué año estamos?") == "current year today's date"


def test_build_search_query_strips_filler():
    q = build_search_query("busca cual es el album mas reciente de calvin harris")
    assert "calvin harris" in q.lower()
    assert not q.lower().startswith("busca")


def test_no_search_casual_chat():
    assert needs_web_search("hola, cómo estás?") is False
    assert needs_web_search("cuéntame un chiste") is False
    assert needs_web_search("me gusta comer pizza") is False


def test_no_search_static_knowledge():
    assert needs_web_search("qué es la fotosíntesis") is False


def test_search_news_and_finance():
    assert needs_web_search("cuéntame sobre la actualidad en Colombia") is True
    assert needs_web_search("¿A cuánto está el dólar en pesos hoy?") is True


def test_search_weather():
    assert needs_web_search("¿Cuál es el clima para esta tarde en Bogotá?") is True
