from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Bot
    VERSION: str = "1.0.0"
    PREFIX: str = "h."
    DISCORD_TOKEN: str = ""
    DASHBOARD_PASSWORD: str = ""

    # Database
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # LLMs
    GEMINI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    NVIDIA_API_KEY: str = ""
    TAVILY_API_KEY: str = ""

    # osu! API v2
    OSU_CLIENT_ID: int = 0
    OSU_CLIENT_SECRET: str = ""
    OSU_MOCK_MODE: bool = False

    # Environment
    ENVIRONMENT: str = "development"  # development | staging | production


settings = Settings()
