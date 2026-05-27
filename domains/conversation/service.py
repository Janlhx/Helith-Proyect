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
        """Process a conversation message.

        1. Generate embedding of the user's query.
        2. Retrieve relevant semantic memories from the server.
        3. Perform web search if the router heuristic indicates it.
        4. Save the user message to history and memories.
        5. Build the prompt with history and dynamic context.
        6. Call the LLM pool with Helith's personality.
        7. Save the bot response to history and memories.
        8. Return the generated response.
        """
        # 1. Generate embedding for the user's query
        user_embedding = await generate_embedding(message_content)

        # 2. Retrieve semantic memories (top 3, similarity >= 0.7)
        memories = conversation_repo.search_memories(
            server_id=server_id,
            query_embedding=user_embedding,
            limit=3,
            threshold=0.7,
        )

        memory_context = ""
        if memories:
            memory_context = "\n".join(
                f"- Past: {mem['content']}" for mem in memories
            )
            logger.info(
                f"Retrieved {len(memories)} semantic memories "
                f"for server {server_id}."
            )

        # 3. Real-time queries (Tavily) if necessary
        search_context = ""
        search_triggered = intent_router.needs_web_search(message_content)
        if search_triggered:
            search_query = intent_router.build_search_query(message_content)
            logger.info(
                f"Tavily trigger activated. Query: '{search_query}' "
                f"(original: '{message_content}')"
            )
            search_context = await tavily_search.search(search_query)

        # 4. Save user message to history and memories
        conversation_repo.save_message(channel_id, user_id, "user", message_content)
        conversation_repo.save_memory(
            server_id=server_id,
            channel_id=channel_id,
            user_id=user_id,
            content=message_content,
            embedding=user_embedding,
        )

        # 5. Retrieve recent conversation history (last 10 messages)
        history = conversation_repo.get_history(channel_id, limit=10)

        # Build dynamic system prompt (now only static + general rule)
        system_prompt = HELITH_PERSONALITY
        if memory_context or search_context:
            system_prompt += (
                "\n\nINSTRUCCIÓN CRÍTICA DE CONTEXTO:\n"
                "A continuación, en tu historial de chat se te proporcionarán datos "
                "contextuales (Búsqueda web o Memorias pasadas). Úsalos como "
                "TU PROPIO CONOCIMIENTO. NUNCA digas que no tienes acceso a "
                "internet o que no estás segura. Responde con total confianza."
            )

        # Formatear el historial como un diálogo y añadir los contextos al inicio
        full_prompt = ""
        
        if search_triggered:
            if search_context:
                full_prompt += (
                    "[DATOS DE BÚSQUEDA WEB PARA LA PREGUNTA ACTUAL]\n"
                    f"{search_context}\n\n"
                )
            else:
                full_prompt += (
                    "[NOTA INTERNA]\n"
                    "El usuario pidió datos actuales pero no se encontraron "
                    "resultados. Sé honesta y dilo brevemente.\n\n"
                )
                
        if memory_context:
            full_prompt += (
                "[MEMORIAS RECUPERADAS DEL SERVIDOR]\n"
                f"{memory_context}\n\n"
            )

        full_prompt += "--- HISTORIAL DE CHAT ---\n"
        for msg in history:
            role_label = "Tú (Helith):" if msg["role"] == "assistant" else "Usuario:"
            full_prompt += f"{role_label} {msg['content']}\n"

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
