import logging

from core.config import settings

logger = logging.getLogger("helith.llm")


class LLMPool:
    """Manages the LLM pool with fallback logic."""

    def __init__(self):
        # Verify which API keys are available
        self.gemini_enabled = (
            bool(settings.GEMINI_API_KEY)
            and settings.GEMINI_API_KEY != "your_gemini_key"
        )
        self.nvidia_enabled = (
            bool(settings.NVIDIA_API_KEY)
            and settings.NVIDIA_API_KEY != "your_nvidia_nim_key"
        )
        self.groq_enabled = (
            bool(settings.GROQ_API_KEY) and settings.GROQ_API_KEY != "your_groq_key"
        )

        logger.info(
            f"Pool initialized: Gemini={self.gemini_enabled}, "
            f"NVIDIA={self.nvidia_enabled}, Groq={self.groq_enabled}"
        )

    async def generate_response(
        self,
        prompt: str,
        system_prompt: str = "",
        server_id: str = "unknown",
        user_id: str = "unknown",
    ) -> str:
        """Generates a response using the model pool with fallback."""

        # 1. Nivel Primario: Gemini
        if self.gemini_enabled:
            try:
                logger.info("Attempting to generate response with Gemini (Primary)...")
                text, prompt_t, completion_t = await self._call_gemini(
                    prompt, system_prompt
                )
                self._record(
                    "gemini-2.5-flash", server_id, user_id, prompt_t, completion_t
                )
                return text
            except Exception as e:
                logger.error(
                    f"Gemini failed: {e}. Trying the next available model..."
                )

        # 2. Nivel Secundario: NVIDIA NIM
        if self.nvidia_enabled:
            # Updated models — real build.nvidia.com catalog (May 2026)
            # Order: speed + quality first, lightweight as last resort
            nvidia_models = [
                # Active MoE 284B/13B, 1M ctx — fastest and most capable
                "deepseek-ai/deepseek-v4-flash",
                # Native NVIDIA MoE, hyper-optimized for NIM
                "nvidia/nemotron-3-super-120b-a12b",
                # Lightweight and fast — last resort
                "google/gemma-4-31b-it",
            ]
            for model_name in nvidia_models:
                try:
                    logger.info(
                        f"Attempting to generate response with NVIDIA NIM ({model_name})..."
                    )
                    text, prompt_t, completion_t = await self._call_nvidia(
                        prompt, system_prompt, model_name
                    )
                    self._record(
                        f"nvidia/{model_name}",
                        server_id,
                        user_id,
                        prompt_t,
                        completion_t,
                    )
                    return text
                except Exception as e:
                    logger.error(
                        f"NVIDIA NIM failed with {model_name}: "
                        f"{e}. Moving to the next..."
                    )

        # 3. Nivel Terciario: Pool de Groq
        if self.groq_enabled:
            # List of models to try in order
            groq_models = [
                "llama-3.3-70b-versatile",
                "deepseek-r1-distill-llama-70b",
                "llama-3.1-8b-instant",
                "meta-llama/llama-4-scout-17b-16e-instruct",
            ]

            for model_name in groq_models:
                try:
                    logger.info(
                        f"Attempting to generate response with Groq ({model_name})..."
                    )
                    text, prompt_t, completion_t = await self._call_groq(
                        prompt, system_prompt, model_name
                    )
                    self._record(model_name, server_id, user_id, prompt_t, completion_t)
                    return text
                except Exception as e:
                    logger.error(
                        f"Groq failed with {model_name}: {e}. Moving to the next..."
                    )

        raise Exception("All models failed or are not configured.")

    def _record(
        self,
        model_name: str,
        server_id: str,
        user_id: str,
        prompt_tokens: int,
        completion_tokens: int,
    ):
        """Records token consumption in the monitoring service."""
        try:
            from domains.monitoring.service import monitoring_service

            monitoring_service.record_usage(
                model_name, server_id, user_id, prompt_tokens, completion_tokens
            )
        except Exception as e:
            logger.warning(f"Could not record token usage: {e}")

    async def _call_gemini(
        self, prompt: str, system_prompt: str
    ) -> tuple[str, int, int]:
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

    async def _call_nvidia(
        self, prompt: str, system_prompt: str, model_name: str
    ) -> tuple[str, int, int]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=settings.NVIDIA_API_KEY,
            base_url="https://integrate.api.nvidia.com/v1",
        )
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=model_name,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=1024,
        )
        text = response.choices[0].message.content or ""
        usage = response.usage
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        return text, prompt_tokens, completion_tokens

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


# Singleton instance to be used throughout the project
llm_pool = LLMPool()
