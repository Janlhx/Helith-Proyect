import logging
import sys


def main():
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Add current directory to path
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
    print("           STARTING HELITH TEST RUNNER           ")
    print("==================================================")

    tests = [
        ("Expected Playtime Calculation", test_expected_playtime),
        ("Improvement Indicator (ii) Calculation", test_improvement_indicator),
        ("Log-Linear Regression Fit (OLS)", test_fit_log_linear_regression),
        ("Days to Target Rank Prediction", test_predict_days_to_rank),
        (
            "Mock Client Determinism",
            test_osu_client_mock_determinism,
        ),
        (
            "SQLite Persistence and Fallback",
            test_osu_repository_sqlite_fallback,
        ),
    ]

    failed = 0
    passed = 0

    for name, test_func in tests:
        try:
            print(f"-> Running: {name}...", end="", flush=True)
            test_func()
            print("  [OK]")
            passed += 1
        except Exception as e:
            print("  [FAIL]")
            print(f"   -> Error: {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("==================================================")
    print(f"RESULTS: {passed} PASSED | {failed} FAILED")
    print("==================================================")

    if failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
