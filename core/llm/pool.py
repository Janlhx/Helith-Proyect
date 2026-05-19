import logging

from core.config import settings

logger = logging.getLogger("helith.llm")


class LLMPool:
    """Gestiona el pool de LLMs con lógica de fallback."""

    def __init__(self):
        # Verificamos qué llaves están disponibles
        self.gemini_enabled = (
            bool(settings.GEMINI_API_KEY)
            and settings.GEMINI_API_KEY != "your_gemini_key"
        )
        self.groq_enabled = (
            bool(settings.GROQ_API_KEY)
            and settings.GROQ_API_KEY != "your_groq_key"
        )

        logger.info(
            f"Pool inicializado: Gemini={self.gemini_enabled}, Groq={self.groq_enabled}"
        )

    async def generate_response(
        self,
        prompt: str,
        system_prompt: str = "",
        server_id: str = "unknown",
        user_id: str = "unknown",
    ) -> str:
        """Genera respuesta usando el pool de modelos con fallback."""

        # 1. Nivel Primario: Gemini
        if self.gemini_enabled:
            try:
                logger.info("Intentando generar respuesta con Gemini (Primario)...")
                text, prompt_t, completion_t = await self._call_gemini(
                    prompt, system_prompt
                )
                self._record("gemini-2.5-flash", server_id, user_id, prompt_t, completion_t)
                return text
            except Exception as e:
                logger.error(
                    f"Fallo en Gemini: {e}. Intentando con el siguiente disponible..."
                )

        # 2. Nivel Secundario: Pool de Groq
        if self.groq_enabled:
            # Lista de modelos a intentar en orden
            groq_models = [
                "llama-3.3-70b-versatile",
                "deepseek-r1-distill-llama-70b",
                "llama-3.1-8b-instant",
                "meta-llama/llama-4-scout-17b-16e-instruct",
            ]

            for model_name in groq_models:
                try:
                    logger.info(
                        f"Intentando generar respuesta con Groq ({model_name})..."
                    )
                    text, prompt_t, completion_t = await self._call_groq(
                        prompt, system_prompt, model_name
                    )
                    self._record(model_name, server_id, user_id, prompt_t, completion_t)
                    return text
                except Exception as e:
                    logger.error(
                        f"Fallo en Groq con {model_name}: {e}. "
                        "Pasando al siguiente..."
                    )

        raise Exception("Todos los modelos fallaron o no están configurados.")

    def _record(
        self,
        model_name: str,
        server_id: str,
        user_id: str,
        prompt_tokens: int,
        completion_tokens: int,
    ):
        """Registra el consumo de tokens en el servicio de monitoreo."""
        try:
            from domains.monitoring.service import monitoring_service

            monitoring_service.record_usage(
                model_name, server_id, user_id, prompt_tokens, completion_tokens
            )
        except Exception as e:
            logger.warning(f"No se pudo registrar el uso de tokens: {e}")

    async def _call_gemini(self, prompt: str, system_prompt: str) -> tuple[str, int, int]:
        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=system_prompt if system_prompt else None,
        )
        response = await model.generate_content_async(prompt)
        usage = response.usage_metadata
        prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
        completion_tokens = getattr(usage, "candidates_token_count", 0) or 0
        return str(response.text), prompt_tokens, completion_tokens

    async def _call_groq(
        self, prompt: str, system_prompt: str, model_name: str
    ) -> tuple[str, int, int]:
        from groq import AsyncGroq

        client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=model_name,
            messages=messages,  # type: ignore[arg-type]
        )
        text = response.choices[0].message.content or ""
        usage = response.usage
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        return text, prompt_tokens, completion_tokens


# Instancia única para ser usada en todo el proyecto
llm_pool = LLMPool()
