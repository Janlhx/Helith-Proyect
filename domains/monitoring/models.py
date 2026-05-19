from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TokenUsageLog:
    """Registro de una llamada a un LLM con metadata de consumo."""

    model_name: str
    server_id: str
    user_id: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convierte el registro a un diccionario para insertar en Supabase."""
        return {
            "model_name": self.model_name,
            "server_id": self.server_id,
            "user_id": self.user_id,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "timestamp": self.timestamp.isoformat(),
        }
