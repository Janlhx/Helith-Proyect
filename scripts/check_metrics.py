"""
Helith — Token usage metrics script
Usage: python scripts/check_metrics.py
"""

import os
import sys

try:
    import requests
except ImportError:
    print("❌ You need 'requests' installed.")
    print("   Run: pip install requests")
    sys.exit(1)


# ── Configuration ──────────────────────────────────────────────────────────────
# Loads the token from .env if it exists, otherwise prompts the user
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
        token = input("Enter your DISCORD_TOKEN: ").strip()
    return token


RENDER_URL = os.environ.get(
    "HELITH_URL",
    "https://helith-proyect-staging-phase.onrender.com",  # Change to your real URL
)


def separator(char="─", width=55):
    print(char * width)


def main():
    token = load_token()
    if not token:
        print("❌ DISCORD_TOKEN not found.")
        sys.exit(1)

    token_prefix = token[:20]
    url = f"{RENDER_URL}/dashboard"

    print()
    separator("═")
    print("  📊  HELITH — Token Usage Dashboard")
    separator("═")
    print(f"  🌐 Querying: {url}")

    try:
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token_prefix}"},
            timeout=15,
        )
    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect. Is the bot running on Render?")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(
            "\n⏱️  Timeout. Render may be waking up the bot "
            "(wait 30s and try again)."
        )
        sys.exit(1)

    if resp.status_code == 401:
        print("\n🔒 Unauthorized. Check your DISCORD_TOKEN.")
        sys.exit(1)

    if resp.status_code != 200:
        print(f"\n❌ HTTP Error {resp.status_code}: {resp.text}")
        sys.exit(1)

    data = resp.json()
    stats = data.get("stats_7d", {})
    predictions = data.get("predictions", {})

    # ── General summary ────────────────────────────────────────────────────────
    print()
    separator()
    print("  📅  SUMMARY — Last 7 days")
    separator()
    print(f"  🔢 Total tokens consumed  : {stats.get('total_tokens', 0):>10,}")
    print(
        f"  📈 Daily average          : {stats.get('avg_tokens_per_day', 0):>10,}"
    )

    alerts = data.get("active_alerts", 0)
    alert_label = (
        f"⚠️  {alerts} model(s) on alert" if alerts > 0 else "✅ No active alerts"
    )
    print(f"\n  {alert_label}")

    # ── Usage by model ─────────────────────────────────────────────────────────
    by_model = stats.get("by_model", {})
    if by_model:
        print()
        separator()
        print("  🤖  USAGE BY MODEL (7 days)")
        separator()
        for model, tokens in sorted(by_model.items(), key=lambda x: -x[1]):
            bar_pct = tokens / max(by_model.values()) * 20
            bar = "█" * int(bar_pct) + "░" * (20 - int(bar_pct))
            print(f"  {model[:35]:<35} {tokens:>8,}t  [{bar}]")

    # ── Exhaustion predictions ─────────────────────────────────────────────────
    print()
    separator()
    print("  🔮  EXHAUSTION FORECAST (by model)")
    separator()
    for model, pred in predictions.items():
        if pred.get("avg_daily_tokens", 0) == 0:
            continue  # Skip models with no data

        pct = pred.get("pct_used", 0)
        days = pred.get("days_until_exhaustion")
        alert = pred.get("alert", False)
        icon = "⚠️ " if alert else "✅"

        days_str = f"{days}d" if days else "∞"
        print(f"\n  {icon} {model}")
        print(f"     Daily usage: {pred['avg_daily_tokens']:,} tokens")
        print(f"     Limit used:  {pct}%  |  Days until exhaustion: {days_str}")
        print(f"     {pred.get('message', '')}")

    # ── Footer ─────────────────────────────────────────────────────────────────
    print()
    separator("═")
    print(f"  ⏱️  Generated: {data.get('generated_at', 'N/A')}")
    separator("═")
    print()


if __name__ == "__main__":
    main()
