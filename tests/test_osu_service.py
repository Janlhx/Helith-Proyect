from unittest.mock import AsyncMock, patch

import pytest

from domains.osu.service import osu_service


@pytest.mark.asyncio
@patch("domains.osu.service.osu_api_client")
async def test_process_slash_predict_user_not_found(mock_osu_api_client):
    """If user does not exist, returns controlled error message."""
    mock_osu_api_client.get_user_data = AsyncMock(return_value=None)

    response = await osu_service.process_slash_predict(
        "unknown_user", 5000, "sv1", "usr1"
    )
    assert "I could not find user" in response


@pytest.mark.asyncio
@patch("domains.osu.service.osu_api_client")
@patch("domains.osu.service.osu_repo")
@patch("domains.osu.service.llm_pool")
async def test_process_slash_predict_success(
    mock_llm_pool, mock_repo, mock_osu_api_client
):
    """Tests the full flow and mathematical prediction logic with historic saving."""
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
        return_value="Structured final LLM prediction."
    )

    response = await osu_service.process_slash_predict("TestUser", 5000, "sv1", "usr1")

    # Snapshot should be saved
    mock_repo.save_snapshot.assert_called_once()
    assert response == "Structured final LLM prediction."


@pytest.mark.asyncio
@patch("domains.osu.service.osu_api_client")
@patch("domains.osu.service.osu_repo")
@patch("domains.osu.service.llm_pool")
async def test_process_slash_predict_invalid_target(
    mock_llm_pool, mock_repo, mock_osu_api_client
):
    """If target rank is <= 0, it falls back to 5000 for safety."""
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

    # Verify that target_rank in prompt was corrected to 5000
    kwargs = mock_llm_pool.generate_response.call_args.kwargs
    assert "Target rank: #5,000" in kwargs["prompt"]
