import math

from domains.osu.client import osu_api_client
from domains.osu.ml_model import (
    calculate_expected_playtime,
    calculate_improvement_indicator,
    fit_log_linear_regression,
    predict_days_to_rank,
)
from domains.osu.models import OsuSnapshot
from domains.osu.repository import osu_repo


def test_expected_playtime():
    # 0 PP should give 0 expected playtime
    assert calculate_expected_playtime(0) == 0.0

    # 5000 PP -> expected should be approx:
    # -12 + 0.0781 * 5000 + 6.01e-6 * 5000^2 = -12 + 390.5 + 150.25 = 528.75 hours
    expected = calculate_expected_playtime(5000)
    assert abs(expected - 528.75) < 0.1


def test_improvement_indicator():
    # 5000 PP with 528.75 hours played should give ii = 1.0
    play_time_seconds = int(528.75 * 3600)
    ii = calculate_improvement_indicator(5000, play_time_seconds)
    assert abs(ii - 1.0) < 0.05

    # If they play only 264.375 hours (half), the ii should be approx 2.0 (double)
    ii_fast = calculate_improvement_indicator(5000, int(264.375 * 3600))
    assert abs(ii_fast - 2.0) < 0.05


def test_fit_log_linear_regression():
    # Rank improvement series: from #100,000 to #50,000 in 10 days
    # (Rank decreases = improvement, so m of ln(rank) must be negative)
    history = [(0, 100000), (5, 70710), (10, 50000)]

    m, c = fit_log_linear_regression(history, ii=1.0)
    assert m < 0
    # At day 0, it predicts c
    assert abs(math.exp(c) - 100000) < 1.0


def test_predict_days_to_rank():
    # Player improving from 20k to 10k in 10 days
    history = [(0, 20000), (10, 10000)]

    # Predict how long it takes to reach rank 5,000
    # ln(20k) = 9.90, ln(10k) = 9.21  => m = (9.21 - 9.90) / 10 = -0.0693 per day
    # To reach 5,000 (ln(5000) = 8.51):
    # 8.51 = -0.0693 * x + 9.90 => x = (8.51 - 9.90) / -0.0693 = 20 days
    # i.e., 10 additional days from today (day 10).
    result = predict_days_to_rank(history, target_rank=5000, ii=1.0)
    assert result["is_improving"] is True
    assert abs(result["days_to_target"] - 10.0) < 1.0


def test_osu_client_mock_determinism():
    # Verify mock client mode is deterministic according to user seed
    data1 = osu_api_client._generate_mock_user_data("Litxe")
    data2 = osu_api_client._generate_mock_user_data("Litxe")
    data3 = osu_api_client._generate_mock_user_data("Juan")

    assert data1["osu_id"] == data2["osu_id"]
    assert data1["global_rank"] == data2["global_rank"]
    assert len(data1["rank_history"]) == 90

    # Different users should have different simulated stats
    assert data1["osu_id"] != data3["osu_id"]


def test_osu_repository_sqlite_fallback():
    # Test snapshot persistence in local SQLite db
    snapshot = OsuSnapshot(
        osu_id=12345,
        username="test_user",
        global_rank=1500,
        pp=9000.0,
        play_time=1800000,
        improvement_indicator=1.25,
        recorded_at="2026-05-19",
    )

    # Save to local storage (or Supabase if configured)
    osu_repo.save_snapshot(snapshot)

    # Retrieve history
    history = osu_repo.get_history("test_user")
    assert len(history) >= 1
    last_snapshot = history[-1]

    assert last_snapshot["osu_id"] == 12345
    assert last_snapshot["username"].lower() == "test_user"
    assert last_snapshot["global_rank"] == 1500
    assert abs(last_snapshot["pp"] - 9000.0) < 0.1
    assert abs(last_snapshot["improvement_indicator"] - 1.25) < 0.01
