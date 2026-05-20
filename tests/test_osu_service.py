from unittest.mock import AsyncMock, patch

import pytest

from domains.osu.service import osu_service


@pytest.mark.asyncio
@patch("domains.osu.service.osu_api_client")
async def test_process_slash_predict_user_not_found(mock_osu_api_client):
    """Si el usuario no existe, devuelve el mensaje de error controlado."""
    mock_osu_api_client.get_user_data = AsyncMock(return_value=None)

    response = await osu_service.process_slash_predict(
        "unknown_user", 5000, "sv1", "usr1"
    )
    assert "No he podido encontrar al usuario" in response


@pytest.mark.asyncio
@patch("domains.osu.service.osu_api_client")
@patch("domains.osu.service.osu_repo")
@patch("domains.osu.service.llm_pool")
async def test_process_slash_predict_success(
    mock_llm_pool, mock_repo, mock_osu_api_client
):
    """Prueba flujo completo y matemático de predicción con guardado histórico."""
    mock_osu_api_client.get_user_data = AsyncMock(
        return_value={
            "osu_id": 123,
            "username": "TestUser",
            "global_rank": 10000,
            "pp": 6000.0,
            "play_time": 3000000,
            "rank_history": [11000, 10500, 10000],
        }
    )

    mock_llm_pool.generate_response = AsyncMock(
        return_value="Predicción final del LLM estructurada."
    )

    response = await osu_service.process_slash_predict("TestUser", 5000, "sv1", "usr1")

    # Se debe guardar el snapshot para que la BD relacional funcione en el futuro
    mock_repo.save_snapshot.assert_called_once()
    assert response == "Predicción final del LLM estructurada."


@pytest.mark.asyncio
@patch("domains.osu.service.osu_api_client")
@patch("domains.osu.service.osu_repo")
@patch("domains.osu.service.llm_pool")
async def test_process_slash_predict_invalid_target(
    mock_llm_pool, mock_repo, mock_osu_api_client
):
    """Si el rango objetivo es <= 0, se convierte a 5000 por seguridad."""
    mock_osu_api_client.get_user_data = AsyncMock(
        return_value={
            "osu_id": 123,
            "username": "TestUser",
            "global_rank": 10000,
            "pp": 6000.0,
            "play_time": 3000000,
            "rank_history": [11000, 10500, 10000],
        }
    )

    mock_llm_pool.generate_response = AsyncMock(return_value="Ok.")

    await osu_service.process_slash_predict("TestUser", -10, "sv1", "usr1")

    # Verificamos que el target_rank enviado al generador se corrigió a 5000
    kwargs = mock_llm_pool.generate_response.call_args.kwargs
    assert "Rango Objetivo: #5,000" in kwargs["prompt"]
