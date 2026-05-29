from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_key: str = Field(default="", alias="SUPABASE_KEY")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")

    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")

    mimo_api_key: str = Field(default="", alias="MIMO_API_KEY")
    mimo_base_url: str = Field(default="https://opengateway.gitlawb.com/v1", alias="MIMO_BASE_URL")

    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    llm_provider: str = Field(default="mimo", alias="LLM_PROVIDER")
    llm_model: str = Field(default="", alias="LLM_MODEL")
    embedding_provider: str = Field(default="", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="", alias="EMBEDDING_MODEL")
    realtime_mode_required: bool = Field(default=False, alias="REALTIME_MODE_REQUIRED")
    seed_case_studies_on_startup: bool = Field(default=False, alias="SEED_CASE_STUDIES_ON_STARTUP")
    mobility_refresh_seconds: int = Field(default=604800, alias="MOBILITY_REFRESH_SECONDS")
    news_refresh_seconds: int = Field(default=900, alias="NEWS_REFRESH_SECONDS")
    land_value_refresh_seconds: int = Field(default=604800, alias="LAND_VALUE_REFRESH_SECONDS")
    jobs_refresh_seconds: int = Field(default=7776000, alias="JOBS_REFRESH_SECONDS")
    census_refresh_seconds: int = Field(default=2592000, alias="CENSUS_REFRESH_SECONDS")

    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")
    ws_max_connections: int = Field(default=10, alias="WS_MAX_CONNECTIONS")
    sim_timeout_ms: int = Field(default=60000, alias="SIM_TIMEOUT_MS")
    llm_timeout_ms: int = Field(default=10000, alias="LLM_TIMEOUT_MS")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def resolved_llm_model(self) -> str:
        if self.llm_model:
            return self.llm_model
        defaults = {
            "openai": "gpt-4o-mini",
            "gemini": "gemini-2.0-flash",
            "mimo": "mimo-v2.5-pro",
            "ollama": "llama3.2:4b",
        }
        return defaults.get(self.llm_provider, "mimo-v2.5-pro")

    @property
    def resolved_embedding_provider(self) -> str:
        return self.embedding_provider or self.llm_provider

    @property
    def resolved_embedding_model(self) -> str:
        if self.embedding_model:
            return self.embedding_model
        defaults = {
            "openai": "text-embedding-3-small",
            "gemini": "gemini-embedding-001",
            "mimo": "text-embedding-3-small",
            "ollama": "nomic-embed-text",
        }
        return defaults.get(self.llm_provider, "text-embedding-3-small")

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
