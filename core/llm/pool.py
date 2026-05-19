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
        self.anthropic_enabled = (
            bool(settings.ANTHROPIC_API_KEY)
            and settings.ANTHROPIC_API_KEY != "your_anthropic_key"
        )
        self.groq_enabled = (
            bool(settings.GROQ_API_KEY)
            and settings.GROQ_API_KEY != "your_groq_key"
        )

        logger.info(
            f"Pool inicializado: Gemini={self.gemini_enabled}, "
            f"Anthropic={self.anthropic_enabled}, Groq={self.groq_enabled}"
        )

    async def generate_response(
        self, prompt: str, system_prompt: str = ""
    ) -> str:
        """Genera respuesta usando el pool de modelos con fallback."""

        # 1. Nivel Primario: Gemini
        if self.gemini_enabled:
            try:
                logger.info("Intentando generar respuesta con Gemini (Primario)...")
                return await self._call_gemini(prompt, system_prompt)
            except Exception as e:
                logger.error(
                    f"Fallo en Gemini: {e}. Pasando a Fallback 1 (Anthropic)..."
                )

        # 2. Fallback 1: Anthropic (Claude Haiku)
        if self.anthropic_enabled:
            try:
                logger.info(
                    "Intentando generar respuesta con Anthropic (Fallback 1)..."
                )
                return await self._call_anthropic(prompt, system_prompt)
            except Exception as e:
                logger.error(
                    f"Fallo en Anthropic: {e}. Pasando a Fallback 2 (Groq)..."
                )

        # 3. Fallback 2: Groq (Llama 3.1 70B)
        if self.groq_enabled:
            try:
                logger.info(
                    "Intentando generar respuesta con Groq (Fallback 2)..."
                )
                return await self._call_groq(prompt, system_prompt)
            except Exception as e:
                logger.error(f"Fallo en Groq: {e}. No hay más modelos disponibles.")

        raise Exception("Todos los modelos fallaron o no están configurados.")

    async def _call_gemini(self, prompt: str, system_prompt: str) -> str:
        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system_prompt if system_prompt else None,
        )
        # Usamos la versión asíncrona
        response = await model.generate_content_async(prompt)
        return response.text

    async def _call_anthropic(self, prompt: str, system_prompt: str) -> str:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            system=system_prompt if system_prompt else None,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    async def _call_groq(self, prompt: str, system_prompt: str) -> str:
        from groq import AsyncGroq

        client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=messages,
        )
        return response.choices[0].message.content


# Instancia única para ser usada en todo el proyecto
llm_pool = LLMPool()
