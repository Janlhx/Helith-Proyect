from domains.bot.router import intent_router


def test_needs_web_search_explicit_triggers():
    """Prueba que los disparadores explícitos fuercen la búsqueda."""
    assert (
        intent_router.needs_web_search(
            "busca a qué hora juega el Real Madrid"
        )
        is True
    )
    assert (
        intent_router.needs_web_search("buscar precio del bitcoin hoy")
        is True
    )
    assert (
        intent_router.needs_web_search("google qué es el proyecto Helith")
        is True
    )
    assert intent_router.needs_web_search("search latest news") is True


def test_needs_web_search_news_keywords():
    """Prueba que las palabras de noticias disparen la búsqueda."""
    assert (
        intent_router.needs_web_search("cuéntame sobre la actualidad en Colombia")
        is True
    )
    assert (
        intent_router.needs_web_search(
            "¿Qué pasó recientemente con Totó la Momposina?"
        )
        is True
    )
    assert (
        intent_router.needs_web_search("¿Quién falleció esta semana?") is True
    )
    assert (
        intent_router.needs_web_search("¿Qué se sabe del paro campesino?")
        is True
    )


def test_needs_web_search_sports_and_music():
    """Prueba que deportes y música disparen la búsqueda."""
    assert (
        intent_router.needs_web_search("¿Cuál es la canción del mundial 2026?")
        is True
    )
    assert (
        intent_router.needs_web_search("¿Quién ganó el oscar a mejor película?")
        is True
    )
    assert (
        intent_router.needs_web_search("¿Cómo va el partido de fútbol hoy?")
        is True
    )


def test_needs_web_search_finance_and_weather():
    """Prueba que el clima y divisas disparen la búsqueda."""
    assert (
        intent_router.needs_web_search("¿A cuánto está el dólar en pesos hoy?")
        is True
    )
    assert (
        intent_router.needs_web_search(
            "¿Qué alerta dio el Ideam sobre las lluvias?"
        )
        is True
    )
    assert (
        intent_router.needs_web_search(
            "¿Cuál es el clima para esta tarde en Bogotá?"
        )
        is True
    )


def test_needs_web_search_no_trigger():
    """Prueba que la conversación cotidiana no dispare la búsqueda."""
    assert intent_router.needs_web_search("hola, cómo estás?") is False
    assert intent_router.needs_web_search("me gusta comer pizza") is False
    assert intent_router.needs_web_search("cuéntame un chiste") is False
