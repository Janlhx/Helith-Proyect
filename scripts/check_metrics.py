"""
Helith — Script de métricas de consumo de tokens
Uso: python scripts/check_metrics.py
"""

import os
import sys

try:
    import requests
except ImportError:
    print("❌ Necesitas tener 'requests' instalado.")
    print("   Ejecuta: pip install requests")
    sys.exit(1)


# ── Configuración ─────────────────────────────────────────────────────────────
# Carga el token desde .env si existe, si no lo pide manualmente
def load_token() -> str:
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("DISCORD_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")

    token = os.environ.get("DISCORD_TOKEN", "")
    if not token:
        token = input("Introduce tu DISCORD_TOKEN: ").strip()
    return token


RENDER_URL = os.environ.get(
    "HELITH_URL",
    "https://helith-proyect-staging-phase.onrender.com",  # Cambia a tu URL real
)


def separador(char="─", ancho=55):
    print(char * ancho)


def main():
    token = load_token()
    if not token:
        print("❌ No se encontró el DISCORD_TOKEN.")
        sys.exit(1)

    token_prefix = token[:20]
    url = f"{RENDER_URL}/dashboard"

    print()
    separador("═")
    print("  📊  HELITH — Panel de Métricas de Consumo")
    separador("═")
    print(f"  🌐 Consultando: {url}")

    try:
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token_prefix}"},
            timeout=15,
        )
    except requests.exceptions.ConnectionError:
        print("\n❌ No se pudo conectar. ¿Está el bot corriendo en Render?")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(
            "\n⏱️  Timeout. Render puede estar despertando al bot "
            "(espera 30s e inténtalo de nuevo)."
        )
        sys.exit(1)

    if resp.status_code == 401:
        print("\n🔒 No autorizado. Verifica tu DISCORD_TOKEN.")
        sys.exit(1)

    if resp.status_code != 200:
        print(f"\n❌ Error HTTP {resp.status_code}: {resp.text}")
        sys.exit(1)

    data = resp.json()
    stats = data.get("stats_7d", {})
    predictions = data.get("predictions", {})

    # ── Resumen general ───────────────────────────────────────────────────────
    print()
    separador()
    print("  📅  RESUMEN — Últimos 7 días")
    separador()
    print(f"  🔢 Total de tokens consumidos : {stats.get('total_tokens', 0):>10,}")
    print(
        f"  📈 Promedio diario            : {stats.get('avg_tokens_per_day', 0):>10,}"
    )

    alerts = data.get("active_alerts", 0)
    alert_label = (
        f"⚠️  {alerts} modelo(s) en alerta" if alerts > 0 else "✅ Sin alertas activas"
    )
    print(f"\n  {alert_label}")

    # ── Consumo por modelo ────────────────────────────────────────────────────
    by_model = stats.get("by_model", {})
    if by_model:
        print()
        separador()
        print("  🤖  CONSUMO POR MODELO (7 días)")
        separador()
        for model, tokens in sorted(by_model.items(), key=lambda x: -x[1]):
            bar_pct = tokens / max(by_model.values()) * 20
            bar = "█" * int(bar_pct) + "░" * (20 - int(bar_pct))
            print(f"  {model[:35]:<35} {tokens:>8,}t  [{bar}]")

    # ── Predicciones de agotamiento ───────────────────────────────────────────
    print()
    separador()
    print("  🔮  PREDICCIÓN DE AGOTAMIENTO (por modelo)")
    separador()
    for model, pred in predictions.items():
        if pred.get("avg_daily_tokens", 0) == 0:
            continue  # Saltar modelos sin datos

        pct = pred.get("pct_used", 0)
        days = pred.get("days_until_exhaustion")
        alert = pred.get("alert", False)
        icon = "⚠️ " if alert else "✅"

        days_str = f"{days}d" if days else "∞"
        print(f"\n  {icon} {model}")
        print(f"     Consumo diario: {pred['avg_daily_tokens']:,} tokens")
        print(f"     Uso del límite: {pct}%  |  Días hasta agotar: {days_str}")
        print(f"     {pred.get('message', '')}")

    # ── Footer ────────────────────────────────────────────────────────────────
    print()
    separador("═")
    print(f"  ⏱️  Generado: {data.get('generated_at', 'N/A')}")
    separador("═")
    print()


if __name__ == "__main__":
    main()
