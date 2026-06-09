from unittest.mock import patch

import pytest

from core.llm.embeddings import generate_embedding


@pytest.mark.asyncio
@patch("core.llm.embeddings.settings")
async def test_generate_embedding_missing_key(mock_settings):
    """Test that a zero-vector dummy is returned if the API key is not configured."""
    mock_settings.GEMINI_API_KEY = ""

    embedding = await generate_embedding("hola")
    assert len(embedding) == 768
    assert all(val == 0.0 for val in embedding)


@pytest.mark.asyncio
@patch("core.llm.embeddings.settings")
@patch("google.generativeai.embed_content_async")
async def test_generate_embedding_success(mock_embed, mock_settings):
    """Test that the real Gemini embedding vector is returned on success."""
    mock_settings.GEMINI_API_KEY = "test_key"
    mock_embed.return_value = {"embedding": [0.1, 0.2] + [0.0] * 766}

    embedding = await generate_embedding("hola")
    assert len(embedding) == 768
    assert embedding[0] == 0.1
    assert embedding[1] == 0.2
    mock_embed.assert_called_once_with(
        model="models/gemini-embedding-2",
        content="hola",
        task_type="retrieval_query",
        output_dimensionality=768,
    )


@pytest.mark.asyncio
@patch("core.llm.embeddings.settings")
@patch("google.generativeai.embed_content_async")
async def test_generate_embedding_error_fallback(mock_embed, mock_settings):
    """Test that a zero-vector dummy is returned if the API call fails."""
    mock_settings.GEMINI_API_KEY = "test_key"
    mock_embed.side_effect = Exception("API Error")

    embedding = await generate_embedding("hola")
    assert len(embedding) == 768
    assert all(val == 0.0 for val in embedding)
