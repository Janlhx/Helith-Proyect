import logging

from core.llm.pool import llm_pool
from core.llm.prompts import HELITH_PERSONALITY
from domains.conversation.repository import conversation_repo

logger = logging.getLogger("helith.conversation.service")


class ConversationService:
    """Orquesta la lógica de conversación del bot."""

    async def process_message(
        self, channel_id: str, user_id: str, message_content: str
    ) -> str:
        """Procesa un mensaje de conversación.

        1. Guarda el mensaje del usuario.
        2. Recupera el historial para dar contexto.
        3. Llama al pool de LLMs.
        4. Guarda la respuesta del bot.
        5. Retorna la respuesta.
        """
        # 1. Guardar mensaje del usuario
        conversation_repo.save_message(
            channel_id, user_id, "user", message_content
        )

        # 2. Recuperar historial (últimos 10 mensajes)
        # Esto incluye el mensaje que acabamos de guardar
        history = conversation_repo.get_history(channel_id, limit=10)

        # 3. Construir el prompt combinando el historial
        # Formateamos el historial como un diálogo
        full_prompt = ""
        for msg in history:
            role_label = (
                "Tú (Helith):" if msg["role"] == "assistant" else "Usuario:"
            )
            full_prompt += f"{role_label} {msg['content']}\n"

        logger.info(
            f"Generando respuesta para el canal {channel_id} "
            f"con {len(history)} mensajes de contexto."
        )

        try:
            # 4. Generar respuesta usando el pool y la personalidad
            response = await llm_pool.generate_response(
                prompt=full_prompt, system_prompt=HELITH_PERSONALITY
            )

            # 5. Guardar respuesta de Helith
            conversation_repo.save_message(
                channel_id, "helith", "assistant", response
            )

            return response
        except Exception as e:
            logger.error(f"Error en ConversationService: {e}")
            return "Me cuesta procesar eso ahora mismo. Inténtalo de nuevo."


conversation_service = ConversationService()
