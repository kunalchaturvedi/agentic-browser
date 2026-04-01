from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Agentic Browser"
    app_env: str = "development"
    debug: bool = True
    host: str = "127.0.0.1"
    port: int = 8000
    app_base_url: str = "http://127.0.0.1:8000"

    tavily_api_key: str = ""
    tavily_search_endpoint: str = "https://api.tavily.com/search"
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment_name: str = ""
    azure_openai_planner_deployment_name: str = ""
    azure_openai_synthesis_deployment_name: str = ""
    azure_openai_api_version: str = "2025-01-01-preview"
    azure_openai_timeout_seconds: float = 15.0
    azure_openai_synthesis_timeout_seconds: float = 90.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def planner_deployment_name(self) -> str:
        return self.azure_openai_planner_deployment_name or self.azure_openai_deployment_name

    @property
    def synthesis_deployment_name(self) -> str:
        return self.azure_openai_synthesis_deployment_name or self.azure_openai_deployment_name


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
