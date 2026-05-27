import hashlib
import logging
import random
import time
from typing import Any, Dict, List, Optional

import aiohttp

from core.config import settings

logger = logging.getLogger("helith.osu.client")


class OsuApiClient:
    """Cliente asíncrono para interactuar con la API v2 de osu!.

    Implementa autenticación OAuth2 de tipo Client Credentials y almacenamiento en
    caché del token.
    Soporta un modo "Mock" robusto y determinista para testeo local si faltan
    credenciales.
    """

    def __init__(self):
        self.client_id = settings.OSU_CLIENT_ID
        self.client_secret = settings.OSU_CLIENT_SECRET
        self.token_url = "https://osu.ppy.sh/oauth/token"
        self.api_base_url = "https://osu.ppy.sh/api/v2"

        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    @property
    def is_mock_enabled(self) -> bool:
        """Determine if we should operate in mock mode."""
        return settings.OSU_MOCK_MODE or not self.client_id or not self.client_secret

    async def _get_access_token(self, session: aiohttp.ClientSession) -> str:
        """Get or refresh the OAuth2 access token."""
        now = time.time()
        # If the token is valid and has at least 60 seconds of life remaining, reuse it
        if self._access_token and self._token_expires_at > now + 60:
            return self._access_token

        logger.info("Obtaining new OAuth2 access token for osu! API...")
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "scope": "public",
        }

        async with session.post(self.token_url, json=payload) as response:
            if response.status != 200:
                text = await response.text()
                logger.error(
                    f"Error obtaining osu! token (HTTP {response.status}): {text}"
                )
                raise Exception("Could not authenticate with osu! API.")

            data = await response.json()
            self._access_token = data["access_token"]
            expires_in = data.get("expires_in", 86400)
            self._token_expires_at = now + expires_in
            logger.info("Token de acceso de osu! obtenido con éxito.")
            return self._access_token

    async def get_user_data(self, username: str) -> Optional[Dict[str, Any]]:
        """Retrieve player profile information and rank history.

        Returns a unified dictionary or None if an error occurs.
        """
        if self.is_mock_enabled:
            logger.warning(
                f"MOCK mode active. Simulating data for user: '{username}'"
            )
            return self._generate_mock_user_data(username)

        url = f"{self.api_base_url}/users/{username}/osu"
        params = {"key": "username"}

        try:
            async with aiohttp.ClientSession() as session:
                token = await self._get_access_token(session)
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }

                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 404:
                        logger.warning(f"osu! user not found: '{username}'")
                        return None
                    elif response.status != 200:
                        text = await response.text()
                        logger.error(
                            f"Error querying user (HTTP {response.status}): "
                            f"{text}"
                        )
                        return None

                    data = await response.json()

                    # Extract key fields ensuring clean structure
                    user_id = data.get("id")
                    actual_name = data.get("username", username)
                    stats = data.get("statistics", {})
                    global_rank = stats.get("global_rank")
                    pp = stats.get("pp", 0.0)
                    play_time = stats.get("play_time", 0)

                    # rank_history usually comes as:
                    # {"data": [rank_day_1, rank_day_2, ...]}
                    history_data = data.get("rank_history", {}).get("data", [])

                    if global_rank is None:
                        logger.warning(
                            f"User '{actual_name}' has no global rank assigned (inactive)."
                        )
                        return None

                    return {
                        "osu_id": user_id,
                        "username": actual_name,
                        "global_rank": int(global_rank),
                        "pp": float(pp),
                        "play_time": int(play_time),
                        "rank_history": history_data,
                    }

        except Exception as e:
            logger.exception(f"Exception querying osu! API for '{username}': {e}")
            return None

    def _generate_mock_user_data(self, username: str) -> Dict[str, Any]:
        """Generate a simulated osu! profile deterministically using the hash of the name.

        This ensures that querying 'Litxe' always gives the same mock result in tests.
        """
        # Crear un seed determinista basado en el nombre de usuario
        hash_val = int(hashlib.md5(username.lower().encode("utf-8")).hexdigest(), 16)
        rng = random.Random(hash_val)

        # Generar estadísticas deterministas basadas en el hash
        osu_id = rng.randint(100000, 30000000)

        # El rango base va de 2,000 a 250,000
        start_rank = rng.randint(2000, 250000)

        # PP estimado según el rango (aproximado a la curva de osu!)
        # Un rango de 5,000 suele tener aprox. 7,000 pp. 150,000 tiene aprox. 1,500 pp.
        if start_rank < 5000:
            pp = 8000.0 - (start_rank * 0.2)
        elif start_rank < 50000:
            pp = 6500.0 - (start_rank * 0.08)
        else:
            pp = 3000.0 - (start_rank * 0.01)
        pp = max(100.0, pp)

        # Tiempo de juego en segundos (promedio de 50 a 1500 horas)
        play_time = int(rng.randint(180000, 5400000))

        # Generar un historial de 90 días con tendencia a la mejora (rango disminuyendo)
        # Si el primer dígito del hash es par, el jugador está mejorando de verdad.
        # Si es impar, está un poco estancado o empeorando de rango.
        trend_direction = -1 if (hash_val % 2 == 0) else 0.1

        history: List[int] = []
        current_step_rank = start_rank + int(
            90 * rng.uniform(5, 50) * (-trend_direction)
        )

        for _ in range(90):
            # Añadir pequeña fluctuación diaria
            fluctuation = rng.randint(-15, 15)
            # Cambiar rango con la tendencia general
            current_step_rank += int(rng.uniform(2, 30) * trend_direction) + fluctuation
            current_step_rank = max(1, current_step_rank)
            history.append(current_step_rank)

        # El rango de hoy (el último día en la lista) es el que asignamos como actual
        final_rank = history[-1]

        return {
            "osu_id": osu_id,
            "username": username,
            "global_rank": final_rank,
            "pp": round(pp, 2),
            "play_time": play_time,
            "rank_history": history,
        }


osu_api_client = OsuApiClient()
