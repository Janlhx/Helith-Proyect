import logging

from domains.admin.service import HelpMenuView, admin_service

logger = logging.getLogger("helith.admin.router")


class AdminRouter:
    """Enruta comandos administrativos con prefijo."""

    async def handle_message(self, message, content: str) -> dict | str:
        """Procesa un comando admin y retorna un Embed/View o un string."""
        try:
            logger.info(f"AdminRouter procesando: '{content}'")
            parts = content.split()
            if not parts:
                return "Comando vacío."

            cmd = parts[0].lower()

            if cmd in ["h.help", "h.ayuda"]:
                if len(parts) > 1:
                    # Búsqueda específica, evadiendo el menú desplegable
                    arg = parts[1]
                    embed = admin_service.get_specific_help(arg)
                    return {"embed": embed}

                # Panel interactivo general
                embed = admin_service.get_help_embed("home")
                view = HelpMenuView()
                return {"embed": embed, "view": view}

            return f"Comando '{cmd}' no reconocido. Prueba con `h.help`."
        except Exception as e:
            logger.error(f"Error en AdminRouter: {e}")
            return "Ocurrió un error al procesar el comando administrativo."


admin_router = AdminRouter()
