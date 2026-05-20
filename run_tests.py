import logging
import sys


def main():
    # Configurar logs
    logging.basicConfig(level=logging.INFO)

    # Añadir directorio actual al path
    sys.path.insert(0, ".")

    from tests.unit.test_osu_ml import (
        test_expected_playtime,
        test_fit_log_linear_regression,
        test_improvement_indicator,
        test_osu_client_mock_determinism,
        test_osu_repository_sqlite_fallback,
        test_predict_days_to_rank,
    )

    print("==================================================")
    print("         INICIANDO TEST RUNNER DE HELITH          ")
    print("==================================================")

    tests = [
        ("Cálculo de Tiempo Esperado de Juego", test_expected_playtime),
        ("Cálculo de Indicador de Mejora (ii)", test_improvement_indicator),
        ("Ajuste de Regresión Log-Lineal (OLS)", test_fit_log_linear_regression),
        ("Predicción de Días al Rango Objetivo", test_predict_days_to_rank),
        (
            "Determinismo del Cliente en Modo Mock",
            test_osu_client_mock_determinism,
        ),
        (
            "Persistencia y Fallback de SQLite",
            test_osu_repository_sqlite_fallback,
        ),
    ]

    failed = 0
    passed = 0

    for name, test_func in tests:
        try:
            print(f"-> Ejecutando: {name}...", end="", flush=True)
            test_func()
            print("  [OK]")
            passed += 1
        except Exception as e:
            print("  [FALLO]")
            print(f"   -> Error: {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("==================================================")
    print(f"RESULTADO: {passed} PASADOS | {failed} FALLADOS")
    print("==================================================")

    if failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
