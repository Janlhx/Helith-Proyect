from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class OsuSnapshot:
    """Registro del estado de progreso de rango y rendimiento de un jugador
    en un día específico.
    """

    osu_id: int
    username: str
    global_rank: int
    pp: float
    play_time: int  # En segundos
    improvement_indicator: float
    recorded_at: str = field(
        default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d")
    )
    id: int | None = None

    def to_dict(self) -> dict:
        """Convierte el snapshot a un diccionario para insertar en Supabase."""
        data = {
            "osu_id": self.osu_id,
            "username": self.username,
            "global_rank": self.global_rank,
            "pp": self.pp,
            "play_time": self.play_time,
            "improvement_indicator": self.improvement_indicator,
            "recorded_at": self.recorded_at,
        }
        if self.id is not None:
            data["id"] = self.id
        return data
