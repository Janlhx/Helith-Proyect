from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Bot
    VERSION: str = "0.1.0"
    PREFIX: str = "h."
    DISCORD_TOKEN: str

    # Base de datos
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # LLMs
    GEMINI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    # Entorno
    ENVIRONMENT: str = "development"  # development | staging | production


settings = Settings()