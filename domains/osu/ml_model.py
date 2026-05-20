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
    """Calcula el tiempo de juego esperado (en horas) basado en Performance Points
    (pp).

    Usa la fórmula empírica de la extensión de Chrome:
    Expected = -12 + 0.0781 * pp + 6.01e-6 * pp^2
    """
    if pp <= 0:
        return 0.0
    expected = -12.0 + (0.0781 * pp) + (6.01e-6 * (pp**2))
    return max(0.0, expected)


def calculate_improvement_indicator(
    pp: float, play_time_seconds: int
) -> float:
    """Calcula el Improvement Indicator (ii) comparando el tiempo jugado esperado
    vs real.

    ii = Expected Playtime / Actual Playtime

    Interpretación:
    - ii = 1.0: Progreso promedio comparado con 10,000 jugadores.
    - ii > 1.0: Progreso más rápido que el promedio (eficiente).
    - ii < 1.0: Progreso más lento que el promedio.
    """
    actual_hours = play_time_seconds / 3600.0
    if actual_hours <= 1.0:
        return 1.0  # Evitar división por cero o datos extremadamente nuevos

    expected_hours = calculate_expected_playtime(pp)
    if expected_hours <= 0:
        return 1.0

    return round(expected_hours / actual_hours, 3)


def fit_log_linear_regression(
    history: List[Tuple[int, int]], ii: float = 1.0
) -> Tuple[float, float]:
    """Ajusta una regresión lineal sobre el logaritmo de los rangos usando OLS en
    Python puro.

    ln(rank) = m * dia + c

    Ajusta la pendiente 'm' según el Improvement Indicator (ii) del usuario.
    Retorna la tupla (m_adjusted, c).
    """
    n = len(history)
    if n < 2:
        return 0.0, 0.0

    # Extraer x (días) e y (logaritmo del rango)
    x = [float(item[0]) for item in history]
    y = [math.log(float(item[1])) for item in history]

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    # Calcular covarianza y varianza para OLS
    numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    denominator = sum((x[i] - mean_x) ** 2 for i in range(n))

    if denominator == 0:
        return 0.0, mean_y

    m = numerator / denominator
    c = mean_y - (m * mean_x)

    # --- Ajuste Adaptativo por ii (Improvement Indicator) ---
    # Un ii > 1.0 significa que el jugador es muy eficiente progresando.
    # Si su tendencia actual es de mejora (m < 0, ya que bajar de rango es mejorar),
    # aceleramos la pendiente de mejora usando un factor amortiguado.
    # Si su tendencia es mala (m > 0), el ii alto ayuda a amortiguar la caída.
    factor = 0.7 + (0.3 * ii)  # Damping factor estable

    if m < 0:
        m_adjusted = m * factor  # Se vuelve más negativo (mejora más rápida)
    else:
        m_adjusted = m / factor  # Se reduce la velocidad de empeoramiento

    logger.debug(
        f"Ajuste de pendiente: m_original={m:.6f}, "
        f"m_adjusted={m_adjusted:.6f} con ii={ii}"
    )
    return m_adjusted, c


def predict_days_to_rank(
    history: List[Tuple[int, int]], target_rank: int, ii: float = 1.0
) -> PredictionResult:
    """Entrena el modelo y predice los días necesarios para alcanzar el rango
    objetivo.

    - 'history' debe ser una lista de tuplas (dia_relativo, rango). El último
      elemento es hoy.
    """
    current_rank = history[-1][1]
    last_day = history[-1][0]

    # 1. Ajustar el modelo
    m, c = fit_log_linear_regression(history, ii)

    # Si el rango es el mismo o el objetivo ya se superó
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
                f"Ya has alcanzado o superado tu rango objetivo de #{target_rank}."
            ),
        }

    # 2. Verificar dirección de la pendiente
    # m < 0 significa que el log(rango) está disminuyendo, es decir, el rango
    # numérico está mejorando.
    is_improving = m < 0

    if not is_improving:
        # Pendiente plana o positiva (empeorando)
        return {
            "current_rank": current_rank,
            "target_rank": target_rank,
            "improvement_indicator": ii,
            "slope": m,
            "is_improving": False,
            "days_to_target": None,
            "confidence_interval": None,
            "message": (
                f"Tu tendencia actual de los últimos {len(history)} días indica "
                "estancamiento o retroceso. A este ritmo, matemáticamente no "
                f"alcanzarás el rango #{target_rank}."
            ),
        }

    # 3. Calcular la predicción
    # ln(target_rank) = m * x_target + c  =>  x_target = (ln(target_rank) - c) / m
    target_y = math.log(float(target_rank))
    target_x = (target_y - c) / m

    days_to_target = target_x - last_day

    if days_to_target < 0:
        # En teoría no debería pasar si target_rank < current_rank e is_improving,
        # pero protegemos de anomalías numéricas.
        days_to_target = 0.0

    # 4. Calcular intervalo de confianza básico (±15% según estabilidad)
    # Entre más dispersos los puntos del log lineal, mayor el intervalo.
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
            f"Tu índice de mejora es excelente ({ii:.2f}), "
            "progresas más rápido que el promedio. "
        )
    elif ii < 0.8:
        ii_desc = (
            f"Tu índice de mejora actual es bajo ({ii:.2f}), "
            "requieres mayor eficiencia de juego. "
        )
    else:
        ii_desc = f"Tu índice de mejora es estándar ({ii:.2f}), en la media general. "

    message = (
        f"{ii_desc}Con tu tendencia actual, estimo que alcanzarás el rango "
        f"#{target_rank} en aproximadamente **{round(days_to_target)} días** "
        f"(rango probable: {round(min_days)} a {round(max_days)} días)."
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
