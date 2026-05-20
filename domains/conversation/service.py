import logging

from core.llm.embeddings import generate_embedding
from core.llm.pool import llm_pool
from core.llm.prompts import HELITH_PERSONALITY
from core.tools.search import tavily_search
from domains.bot.router import intent_router
from domains.conversation.repository import conversation_repo

logger = logging.getLogger("helith.conversation.service")


class ConversationService:
    """Orquesta la lógica de conversación del bot."""

    async def process_message(
        self,
        channel_id: str,
        server_id: str,
        user_id: str,
        message_content: str,
    ) -> str:
        """Procesa un mensaje de conversación.

        1. Genera embedding de la consulta del usuario.
        2. Recupera memorias semánticas relevantes del servidor.
        3. Realiza una búsqueda web si la heurística del router lo indica.
        4. Guarda el mensaje del usuario en el historial y en las memorias.
        5. Construye el prompt con el historial y el contexto dinámico.
        6. Llama al pool de LLMs con la personalidad de Helith.
        7. Guarda la respuesta del bot en el historial y en las memorias.
        8. Retorna la respuesta generada.
        """
        # 1. Generar embedding para la consulta del usuario
        user_embedding = await generate_embedding(message_content)

        # 2. Recuperar memorias semánticas (top 3, similitud >= 0.7)
        memories = conversation_repo.search_memories(
            server_id=server_id,
            query_embedding=user_embedding,
            limit=3,
            threshold=0.7,
        )

        memory_context = ""
        if memories:
            memory_context = "\n".join(
                f"- Pasado: {mem['content']}" for mem in memories
            )
            logger.info(
                f"Recuperadas {len(memories)} memorias semánticas "
                f"para el servidor {server_id}."
            )

        # 3. Consultas en tiempo real (Tavily) si es necesario
        search_context = ""
        if intent_router.needs_web_search(message_content):
            logger.info(
                f"Trigger de búsqueda Tavily activado para: '{message_content}'"
            )
            search_context = await tavily_search.search(message_content)

        # 4. Guardar mensaje del usuario en historial y memorias
        conversation_repo.save_message(channel_id, user_id, "user", message_content)
        conversation_repo.save_memory(
            server_id=server_id,
            channel_id=channel_id,
            user_id=user_id,
            content=message_content,
            embedding=user_embedding,
        )

        # 5. Recuperar historial de conversación reciente (últimos 10 mensajes)
        history = conversation_repo.get_history(channel_id, limit=10)

        # Formatear el historial como un diálogo
        full_prompt = ""
        for msg in history:
            role_label = "Tú (Helith):" if msg["role"] == "assistant" else "Usuario:"
            full_prompt += f"{role_label} {msg['content']}\n"

        # Construir system prompt dinámico con los contextos adicionales
        system_prompt = HELITH_PERSONALITY
        if memory_context:
            system_prompt += (
                f"\n\nCONTEXTO DE MEMORIA SEMÁNTICA (Pasado en este servidor):\n"
                f"{memory_context}\n"
                f"Usa esto como memoria si te preguntan sobre interacciones pasadas. "
                f"Sigue siendo concisa."
            )
        if search_context:
            system_prompt += (
                f"\n\nINFORMACIÓN EN TIEMPO REAL RECIENTE (Tavily):\n"
                f"{search_context}\n"
                f"Usa esta información concisa para responder con "
                f"datos actuales si es relevante. "
                f"Sé extremadamente breve (máximo 3 líneas)."
            )

        logger.info(
            f"Generando respuesta para canal {channel_id} con "
            f"{len(history)} mensajes de historial."
        )

        try:
            # 6. Generar respuesta usando el pool de LLMs
            response = await llm_pool.generate_response(
                prompt=full_prompt,
                system_prompt=system_prompt,
                server_id=server_id,
                user_id=user_id,
            )

            # 7. Guardar respuesta del bot en historial y memorias
            conversation_repo.save_message(channel_id, "helith", "assistant", response)
            assistant_embedding = await generate_embedding(response)
            conversation_repo.save_memory(
                server_id=server_id,
                channel_id=channel_id,
                user_id="helith",
                content=response,
                embedding=assistant_embedding,
            )

            return response
        except Exception as e:
            logger.error(f"Error en ConversationService: {e}")
            return "Me cuesta procesar eso ahora mismo. Inténtalo de nuevo."


conversation_service = ConversationService()
