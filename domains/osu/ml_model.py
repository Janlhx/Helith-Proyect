import logging
import math
from typing import List, Tuple, TypedDict

logger = logging.getLogger("helith.osu.ml_model")


class PredictionResult(TypedDict):
    current_rank: int
    target_rank: int
    improvement_indicator: float
    slope: float
    is_improving: bool
    days_to_target: float | None
    confidence_interval: Tuple[float, float] | None
    message: str


def calculate_expected_playtime(pp: float) -> float:
    """Calculate expected playtime (in hours) based on Performance Points (pp).

    Uses the empirical formula from the Chrome extension:
    Expected = -12 + 0.0781 * pp + 6.01e-6 * pp^2
    """
    if pp <= 0:
        return 0.0
    expected = -12.0 + (0.0781 * pp) + (6.01e-6 * (pp**2))
    return max(0.0, expected)


def calculate_improvement_indicator(pp: float, play_time_seconds: int) -> float:
    """Calculate Improvement Indicator (ii) comparing expected vs actual playtime.

    ii = Expected Playtime / Actual Playtime

    Interpretation:
    - ii = 1.0: Average progress compared to 10,000 players.
    - ii > 1.0: Faster progress than average (efficient).
    - ii < 1.0: Slower progress than average.
    """
    actual_hours = play_time_seconds / 3600.0
    if actual_hours <= 1.0:
        return 1.0  # Avoid division by zero or extremely new data

    expected_hours = calculate_expected_playtime(pp)
    if expected_hours <= 0:
        return 1.0

    return round(expected_hours / actual_hours, 3)


def fit_log_linear_regression(
    history: List[Tuple[int, int]], ii: float = 1.0
) -> Tuple[float, float]:
    """Fit log-linear regression over ranks using OLS in pure Python.

    ln(rank) = m * day + c

    Adjusts the slope 'm' according to the user's Improvement Indicator (ii).
    Returns the tuple (m_adjusted, c).
    """
    n = len(history)
    if n < 2:
        return 0.0, 0.0

    # Extract x (days) and y (log of rank)
    x = [float(item[0]) for item in history]
    y = [math.log(float(item[1])) for item in history]

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    # Calculate covariance and variance for OLS
    numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    denominator = sum((x[i] - mean_x) ** 2 for i in range(n))

    if denominator == 0:
        return 0.0, mean_y

    m = numerator / denominator
    c = mean_y - (m * mean_x)

    # --- Adaptive Adjustment by ii (Improvement Indicator) ---
    # ii > 1.0 means the player progresses very efficiently.
    # If their trend is improving (m < 0, since a lower rank number is better),
    # we accelerate the slope using a damped factor.
    # If their trend is bad (m > 0), a high ii helps dampen the decline.
    factor = 0.7 + (0.3 * ii)  # Stable damping factor

    if m < 0:
        m_adjusted = m * factor  # Becomes more negative (faster improvement)
    else:
        m_adjusted = m / factor  # Reduces the speed of regression

    logger.debug(
        f"Slope adjustment: m_original={m:.6f}, "
        f"m_adjusted={m_adjusted:.6f} with ii={ii}"
    )
    return m_adjusted, c


def predict_days_to_rank(
    history: List[Tuple[int, int]], target_rank: int, ii: float = 1.0
) -> PredictionResult:
    """Trains the model and predicts the number of days needed to reach
    the target rank.

    - 'history' must be a list of tuples (relative_day, rank). The last
      element represents today.
    """
    current_rank = history[-1][1]
    last_day = history[-1][0]

    # 1. Fit the model
    m, c = fit_log_linear_regression(history, ii)

    # If the rank is the same or the target has already been surpassed
    if target_rank >= current_rank:
        return {
            "current_rank": current_rank,
            "target_rank": target_rank,
            "improvement_indicator": ii,
            "slope": m,
            "is_improving": m < 0,
            "days_to_target": 0.0,
            "confidence_interval": None,
            "message": (
                f"You have already reached or surpassed your target rank of "
                f"#{target_rank}."
            ),
        }

    # 2. Verify slope direction
    # m < 0 means log(rank) is decreasing, i.e., the numeric rank
    # is improving.
    is_improving = m < 0

    if not is_improving:
        # Flat or positive slope (regressing)
        return {
            "current_rank": current_rank,
            "target_rank": target_rank,
            "improvement_indicator": ii,
            "slope": m,
            "is_improving": False,
            "days_to_target": None,
            "confidence_interval": None,
            "message": (
                f"Your trend over the last {len(history)} days indicates "
                "stagnation or regression. At this pace, you will not "
                f"mathematically reach rank #{target_rank}."
            ),
        }

    # 3. Calculate the prediction
    # ln(target_rank) = m * x_target + c  =>  x_target = (ln(target_rank) - c) / m
    target_y = math.log(float(target_rank))
    target_x = (target_y - c) / m

    days_to_target = target_x - last_day

    if days_to_target < 0:
        # Theoretically should not happen if target_rank < current_rank and
        # is_improving, but we guard against numerical anomalies.
        days_to_target = 0.0

    # 4. Calculate basic confidence interval (±15% based on stability)
    # The more dispersed the log-linear points, the wider the interval.
    residuals = []
    for day, r in history:
        pred_ln = m * day + c
        actual_ln = math.log(float(r))
        residuals.append((actual_ln - pred_ln) ** 2)

    mse = sum(residuals) / len(history) if history else 0
    uncertainty_multiplier = 1.0 + (math.sqrt(mse) * 2.0)

    min_days = max(1.0, days_to_target / uncertainty_multiplier)
    max_days = days_to_target * uncertainty_multiplier

    # 5. Formatear mensaje según la personalidad de Helith
    ii_desc = ""
    if ii > 1.2:
        ii_desc = (
            f"Your improvement index is excellent ({ii:.2f}), "
            "you progress faster than average. "
        )
    elif ii < 0.8:
        ii_desc = (
            f"Your current improvement index is low ({ii:.2f}), "
            "you need to improve your play efficiency. "
        )
    else:
        ii_desc = f"Your improvement index is average ({ii:.2f}), right in the middle. "

    message = (
        f"{ii_desc}Based on your current trend, I estimate you'll reach rank "
        f"#{target_rank} in approximately **{round(days_to_target)} days** "
        f"(likely range: {round(min_days)} to {round(max_days)} days)."
    )

    return {
        "current_rank": current_rank,
        "target_rank": target_rank,
        "improvement_indicator": ii,
        "slope": m,
        "is_improving": True,
        "days_to_target": round(days_to_target, 1),
        "confidence_interval": (round(min_days, 1), round(max_days, 1)),
        "message": message,
    }
