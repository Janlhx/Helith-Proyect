"""Detección generalizada de cuándo una consulta requiere búsqueda web.

En lugar de listas enormes caso por caso, se combinan señales:
- intención explícita de buscar (busca, google, etc. en cualquier parte del mensaje)
- frescura temporal (reciente, hoy, año actual, etc.)
- hechos dinámicos (precios, resultados, noticias, etc.)
- exclusiones para conocimiento estático o charla casual
"""

from __future__ import annotations

import re

# Intención explícita: el usuario pide buscar, no solo pregunta algo
EXPLICIT_SEARCH = re.compile(
    r"\b("
    r"busca|buscar|búscame|búsca|search|google|googlear|"
    r"mira en internet|busca en internet|"
    r"puedes buscar|podrías buscar|podrias buscar|"
    r"puedes mirar|podrías mirar"
    r")\b",
    re.IGNORECASE,
)

# Información que caduca: no confiar solo en el LLM
FRESHNESS = re.compile(
    r"\b("
    r"reciente|recientes|recientemente|"
    r"últim[oa]s?|ultim[oa]s?|"
    r"actual(?:es|mente)?|ahora|hoy|"
    r"este año|esta semana|este mes|"
    r"en qué año|en que año|en que ano|"
    r"qué año es|que año es|qué año estamos|que año estamos|"
    r"año actual|ano actual|fecha actual|"
    r"right now|latest|current(?:ly)?|today|this year"
    r")\b",
    re.IGNORECASE,
)

# Dominios que casi siempre cambian con el tiempo
DYNAMIC_FACTS = re.compile(
    r"\b("
    r"noticias|news|actualidad|"
    r"precio|precios|cotización|cotizacion|valor|"
    r"dólar|dolar|euro|peso|pesos|trm|bitcoin|crypto|cripto|"
    r"resultado|resultados|ganó|gano|ganador|campeón|campeon|"
    r"partido|mundial|copa|"
    r"presidente|alcalde|"
    r"clima|weather|pronóstico|pronostico|temperatura|lluvia|lluvias|"
    r"alerta|alertas|ideam|"
    r"estreno|lanzamiento|lanzó|lanzo|"
    r"murió|murio|falleció|fallecio|muerte|"
    r"paro|huelga|protesta|manifestación|manifestacion"
    r")\b",
    re.IGNORECASE,
)

DYNAMIC_PHRASES: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"quién ganó",
        r"quien gano",
        r"qué pasó con",
        r"que paso con",
        r"quién es el actual",
        r"quien es el actual",
        r"cuánto está",
        r"cuanto esta",
        r"a cuánto está",
        r"a cuanto esta",
        r"más reciente",
        r"mas reciente",
        r"lo más nuevo",
        r"lo mas nuevo",
        r"álbum más reciente",
        r"album mas reciente",
        r"canción más reciente",
        r"cancion mas reciente",
    )
)

# Charla o conocimiento enciclopédico estático — no gastar Tavily
EXCLUDE = re.compile(
    r"\b("
    r"chiste|broma|cuéntame un chiste|cuentame un chiste|"
    r"cómo te llamas|como te llamas|qué eres|que eres|"
    r"fotosíntesis|fotosintesis"
    r")\b",
    re.IGNORECASE,
)

STATIC_DEFINITION = re.compile(
    r"^(?:qué es|que es|qué son|que son|define|explica qué es|explica que es)\s+",
    re.IGNORECASE,
)

MENTION_PATTERN = re.compile(r"<@!?\d+>")
BOT_PREFIX = re.compile(r"^(?:helith|@helith)\s*,?\s*", re.IGNORECASE)
POLITE_PREFIX = re.compile(
    r"^(?:oal|hola|hey|por favor|please)\s*,?\s*",
    re.IGNORECASE,
)
EXPLICIT_QUERY = re.compile(
    r"\b(?:busca|buscar|búscame|search|google)\s+"
    r"(?:en\s+)?(?:internet\s+)?(?:sobre\s+)?(.+)",
    re.IGNORECASE,
)
YEAR_QUESTION = re.compile(
    r"(?:en qué año|en que año|en que ano|qué año|que año|que ano)"
    r".*(?:estamos|es|va)",
    re.IGNORECASE,
)


def _normalize(content: str) -> str:
    text = content.lower().strip()
    text = MENTION_PATTERN.sub("", text).strip()
    return text


def needs_web_search(content: str) -> bool:
    """True si la consulta probablemente requiere datos actuales de internet."""
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
    """Prepara una query más limpia para Tavily a partir del mensaje del usuario."""
    text = content.strip()
    text = MENTION_PATTERN.sub("", text).strip()
    text = BOT_PREFIX.sub("", text).strip()
    text = POLITE_PREFIX.sub("", text).strip()

    match = EXPLICIT_QUERY.search(text)
    if match:
        text = match.group(1).strip()

    if YEAR_QUESTION.search(text):
        return "año actual fecha de hoy"

    return text or content.strip()
