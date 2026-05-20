import math
from domains.osu.ml_model import (
    calculate_expected_playtime,
    calculate_improvement_indicator,
    fit_log_linear_regression,
    predict_days_to_rank
)
from domains.osu.client import osu_api_client
from domains.osu.models import OsuSnapshot
from domains.osu.repository import osu_repo

def test_expected_playtime():
    # 0 PP debería dar 0 de tiempo esperado
    assert calculate_expected_playtime(0) == 0.0
    
    # 5000 PP -> esperado debería ser aprox:
    # -12 + 0.0781 * 5000 + 6.01e-6 * 5000^2 = -12 + 390.5 + 150.25 = 528.75 horas
    expected = calculate_expected_playtime(5000)
    assert abs(expected - 528.75) < 0.1

def test_improvement_indicator():
    # 5000 PP con 528.75 horas jugadas debería dar ii = 1.0
    play_time_seconds = int(528.75 * 3600)
    ii = calculate_improvement_indicator(5000, play_time_seconds)
    assert abs(ii - 1.0) < 0.05
    
    # Si juega solo 264.375 horas (la mitad), el ii debería ser aprox 2.0 (doble de eficiente)
    ii_fast = calculate_improvement_indicator(5000, int(264.375 * 3600))
    assert abs(ii_fast - 2.0) < 0.05

def test_fit_log_linear_regression():
    # Serie de mejora de rango: del #100,000 al #50,000 en 10 días
    # (El rango disminuye = mejora, por lo que la pendiente 'm' de ln(rango) debe ser negativa)
    history = [
        (0, 100000),
        (5, 70710),  # Aprox media geométrica
        (10, 50000)
    ]
    
    m, c = fit_log_linear_regression(history, ii=1.0)
    assert m < 0
    # Al día 0, predice c
    assert abs(math.exp(c) - 100000) < 1.0

def test_predict_days_to_rank():
    # Jugador que mejora del 20k al 10k en 10 días
    history = [
        (0, 20000),
        (10, 10000)
    ]
    
    # Predecir cuánto tarda en llegar al rango 5,000
    # ln(20k) = 9.90, ln(10k) = 9.21  => m = (9.21 - 9.90) / 10 = -0.0693 por día
    # Para llegar a 5,000 (ln(5000) = 8.51):
    # 8.51 = -0.0693 * x + 9.90 => x = (8.51 - 9.90) / -0.0693 = 20 días desde el día 0,
    # es decir, 10 días adicionales desde hoy (día 10).
    result = predict_days_to_rank(history, target_rank=5000, ii=1.0)
    assert result["is_improving"] is True
    assert abs(result["days_to_target"] - 10.0) < 1.0

def test_osu_client_mock_determinism():
    # Verificar que el modo mock de client sea determinista según el seed del usuario
    data1 = osu_api_client._generate_mock_user_data("Litxe")
    data2 = osu_api_client._generate_mock_user_data("Litxe")
    data3 = osu_api_client._generate_mock_user_data("Juan")
    
    assert data1["osu_id"] == data2["osu_id"]
    assert data1["global_rank"] == data2["global_rank"]
    assert len(data1["rank_history"]) == 90
    
    # Diferentes usuarios deben tener diferentes estadísticas simuladas
    assert data1["osu_id"] != data3["osu_id"]

def test_osu_repository_sqlite_fallback():
    # Testear la persistencia de snapshots en la base local SQLite
    snapshot = OsuSnapshot(
        osu_id=12345,
        username="test_user",
        global_rank=1500,
        pp=9000.0,
        play_time=1800000,
        improvement_indicator=1.25,
        recorded_at="2026-05-19"
    )
    
    # Guardamos forzando SQLite (o Supabase si está disponible, pero garantizamos que se registre)
    osu_repo.save_snapshot(snapshot)
    
    # Recuperamos el historial
    history = osu_repo.get_history("test_user")
    assert len(history) >= 1
    last_snapshot = history[-1]
    
    assert last_snapshot["osu_id"] == 12345
    assert last_snapshot["username"].lower() == "test_user"
    assert last_snapshot["global_rank"] == 1500
    assert abs(last_snapshot["pp"] - 9000.0) < 0.1
    assert abs(last_snapshot["improvement_indicator"] - 1.25) < 0.01
