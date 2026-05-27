"""Generalized detection of when a query requires web search.

Instead of huge case-by-case lists, signals are combined:
- Explicit search intent (search, google, etc. anywhere in the message)
- Temporal freshness (recent, today, current year, etc.)
- Dynamic facts (prices, results, news, etc.)
- Exclusions for static knowledge or casual chat
"""

from __future__ import annotations

import re

# Explicit search intent: user asks to search, not just asks a question
EXPLICIT_SEARCH = re.compile(
    r"\b("
    r"busca|buscar|búscame|búsca|search|google|googlear|look|look it up|"
    r"mira en internet|busca en internet|check online|"
    r"puedes buscar|podrías buscar|podrias buscar|can you search|could you search|"
    r"puedes mirar|podrías mirar|can you look"
    r")\b",
    re.IGNORECASE,
)

# Information that expires: don't rely only on LLM knowledge
FRESHNESS = re.compile(
    r"\b("
    r"reciente|recientes|recientemente|recent|recently|"
    r"últim[oa]s?|ultim[oa]s?|latest|last|"
    r"actual(?:es|mente)?|ahora|hoy|current(?:ly)?|today|now|"
    r"este año|esta semana|este mes|this year|this week|this month|"
    r"en qué año|en que año|en que ano|what year|which year|"
    r"qué año es|que año es|qué año estamos|que año estamos|what year is it|"
    r"año actual|ano actual|fecha actual|current date|"
    r"right now|current date"
    r")\b",
    re.IGNORECASE,
)

# Domains that almost always change over time
DYNAMIC_FACTS = re.compile(
    r"\b("
    r"noticias|news|actualidad|breaking news|"
    r"precio|precios|price|prices|cotización|cotizacion|valuation|value|"
    r"dólar|dolar|dollar|euro|peso|pesos|trm|bitcoin|crypto|cripto|cryptocurrency|"
    r"resultado|resultados|result|results|ganó|gano|won|ganador|winner|campeón|campeon|champion|"
    r"partido|match|mundial|world cup|copa|tournament|"
    r"presidente|president|alcalde|mayor|"
    r"clima|weather|pronóstico|pronostico|forecast|temperatura|temperature|lluvia|lluvias|rain|"
    r"alerta|alertas|alert|alerts|ideam|"
    r"estreno|premiere|lanzamiento|launch|lanzó|lanzo|launched|"
    r"murió|murio|died|falleció|fallecio|death|muerte|"
    r"paro|strike|huelga|protesta|protest|manifestación|manifestacion|demonstration"
    r")\b",
    re.IGNORECASE,
)

DYNAMIC_PHRASES: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"who won|quién ganó|quien gano|",
        r"what happened with|qué pasó con|que paso con|",
        r"who is the current|quién es el actual|quien es el actual|",
        r"how much is|cuánto está|cuanto esta|",
        r"at how much|a cuánto está|a cuanto esta|",
        r"most recent|más reciente|mas reciente|",
        r"the newest|lo más nuevo|lo mas nuevo|",
        r"most recent album|álbum más reciente|album mas reciente|",
        r"most recent song|canción más reciente|cancion mas reciente|",
    )
)

# Static knowledge or encyclopedia - don't waste Tavily
EXCLUDE = re.compile(
    r"\b("
    r"chiste|broma|joke|tell me a joke|cuéntame un chiste|cuentame un chiste|"
    r"cómo te llamas|como te llamas|what are you called|qué eres|que eres|what are you|"
    r"fotosíntesis|fotosintesis|photosynthesis"
    r")\b",
    re.IGNORECASE,
)

STATIC_DEFINITION = re.compile(
    r"^(?:qué es|que es|qué son|que son|define|explica qué es|"
    r"explica que es|what is|what are|explain what is)\s+",
    re.IGNORECASE,
)

MENTION_PATTERN = re.compile(r"<@!?\d+>")
BOT_PREFIX = re.compile(r"^(?:helith|@helith)\s*,?\s*", re.IGNORECASE)
POLITE_PREFIX = re.compile(
    r"^(?:oal|hola|hey|por favor|please|hi|hello|kindly)\s*,?\s*",
    re.IGNORECASE,
)
EXPLICIT_QUERY = re.compile(
    r"\b(?:busca|buscar|búscame|search|google|look|check)\s+"
    r"(?:en\s+)?(?:internet\s+)?(?:sobre\s+)?(?:about\s+)?(.+)",
    re.IGNORECASE,
)
YEAR_QUESTION = re.compile(
    r"(?:en qu\u00e9 año|en que año|en que ano|qu\u00e9 año|que año|que ano|what year)"
    r".*(?:estamos|es|va|is|are)",
    re.IGNORECASE,
)


def _normalize(content: str) -> str:
    text = content.lower().strip()
    text = MENTION_PATTERN.sub("", text).strip()
    return text


def needs_web_search(content: str) -> bool:
    """Return True if the query likely requires current data from the internet."""
    text = _normalize(content)
    if not text:
        return False

    if EXCLUDE.search(text):
        return False

    if (
        STATIC_DEFINITION.match(text)
        and not FRESHNESS.search(text)
        and not EXPLICIT_SEARCH.search(text)
    ):
        return False

    if EXPLICIT_SEARCH.search(text):
        return True

    if FRESHNESS.search(text):
        return True

    if DYNAMIC_FACTS.search(text):
        return True

    return any(pattern.search(text) for pattern in DYNAMIC_PHRASES)


def build_search_query(content: str) -> str:
    """Prepare a cleaner query for Tavily from the user's message."""
    text = content.strip()
    text = MENTION_PATTERN.sub("", text).strip()
    text = BOT_PREFIX.sub("", text).strip()
    text = POLITE_PREFIX.sub("", text).strip()

    match = EXPLICIT_QUERY.search(text)
    if match:
        text = match.group(1).strip()

    if YEAR_QUESTION.search(text):
        return "current year today's date"

    return text or content.strip()
