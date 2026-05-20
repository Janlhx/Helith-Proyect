from unittest.mock import patch

from domains.monitoring.service import monitoring_service


@patch("domains.monitoring.service.monitoring_repo")
def test_monitoring_report_generation(mock_repo):
    """Verifica que el reporte calcule el uso diario y detecte alertas."""
    # Simular datos para que una predicción active alerta
    # (ej: 450k tokens diarios promedio)
    # Límite de llama-3.3-70b-versatile = 500k. 450k > 80% (400k)
    mock_repo.get_usage_last_days.return_value = [
        {
            "model_name": "llama-3.3-70b-versatile",
            "total_tokens": 3150000,
            "timestamp": "2026-05-19T12:00:00",
        }
    ]
    mock_repo.get_total_by_model.return_value = {"llama-3.3-70b-versatile": 3150000}
    mock_repo.get_server_usage_last_days.return_value = [
        {
            "server_id": "server1",
            "total_tokens": 5000,
            "timestamp": "2026-05-19T12:00:00",
        }
    ]
    mock_repo.get_rate_limit_hits_last_days.return_value = []

    report = monitoring_service.get_full_report()

    # Debe alertar porque superamos el 80% del límite de 500k
    assert report["active_alerts"] > 0
    assert report["server_usage_analysis"]["server1"]["status"] == "NORMAL"


def test_monitoring_rate_limit_hits():
    """Prueba que el status del servidor cambie a crítico en ataques de spam."""
    with patch("domains.monitoring.service.monitoring_repo") as mock_repo:
        mock_repo.get_usage_last_days.return_value = []
        mock_repo.get_total_by_model.return_value = {}
        mock_repo.get_server_usage_last_days.return_value = [
            {
                "server_id": "server_attack",
                "total_tokens": 50000,
                "timestamp": "2026-05-19T12:00:00",
            }
        ]
        # Simular 16 rate limits (Umbral para CRÍTICO es > 15 rate limits)
        mock_repo.get_rate_limit_hits_last_days.return_value = [
            {
                "server_id": "server_attack",
                "user_id": f"user{i}",
                "timestamp": "2026-05-19T12:00:00",
            }
            for i in range(16)
        ]

        report = monitoring_service.get_full_report()
        assert report["server_usage_analysis"]["server_attack"]["status"] == "CRÍTICO"
