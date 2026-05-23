from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_key: str = Field(default="", alias="SUPABASE_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")
    ws_max_connections: int = Field(default=10, alias="WS_MAX_CONNECTIONS")
    sim_timeout_ms: int = Field(default=3000, alias="SIM_TIMEOUT_MS")
    llm_timeout_ms: int = Field(default=10000, alias="LLM_TIMEOUT_MS")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
