from unittest.mock import MagicMock, patch

import pytest

from core.tools.search import TavilySearchClient


@pytest.mark.asyncio
@patch("core.tools.search.settings")
async def test_tavily_search_disabled(mock_settings):
    """Prueba que retorne vacío si la API key no está configurada."""
    mock_settings.TAVILY_API_KEY = ""
    client = TavilySearchClient()
    assert client.enabled is False

    res = await client.search("algo")
    assert res == ""


@pytest.mark.asyncio
@patch("core.tools.search.settings")
@patch("httpx.AsyncClient.post")
async def test_tavily_search_success(mock_post, mock_settings):
    """Prueba el éxito de la búsqueda retornando un resumen conciso."""
    mock_settings.TAVILY_API_KEY = "test_tavily_key"
    client = TavilySearchClient()
    assert client.enabled is True

    # Configurar respuesta HTTP exitosa con MagicMock sincrónico
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {"title": "Resultado 1", "content": "Contenido del primer resultado."},
            {"title": "Resultado 2", "content": "Detalles del segundo."},
        ]
    }
    mock_post.return_value = mock_response

    res = await client.search("noticias hoy")
    assert "- Resultado 1: Contenido del primer" in res
    assert "- Resultado 2: Detalles del segundo." in res
    mock_post.assert_called_once()


@pytest.mark.asyncio
@patch("core.tools.search.settings")
@patch("httpx.AsyncClient.post")
async def test_tavily_search_api_error(mock_post, mock_settings):
    """Prueba que si la API da error retorne una cadena vacía."""
    mock_settings.TAVILY_API_KEY = "test_tavily_key"
    client = TavilySearchClient()

    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Forbidden"
    mock_post.return_value = mock_response

    res = await client.search("noticias hoy")
    assert res == ""


@pytest.mark.asyncio
@patch("core.tools.search.settings")
@patch("httpx.AsyncClient.post")
async def test_tavily_search_exception(mock_post, mock_settings):
    """Prueba que si ocurre una excepción de red retorne cadena vacía."""
    mock_settings.TAVILY_API_KEY = "test_tavily_key"
    client = TavilySearchClient()
    mock_post.side_effect = Exception("Connection Refused")

    res = await client.search("noticias hoy")
    assert res == ""
