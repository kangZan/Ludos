"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for the Ludos deduction system."""

    # LLM
    llm_model: str = "deepseek-reasoner"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"

    # System
    secret_pressure_threshold: int = 80
    max_rounds: int = 20
    log_level: str = "INFO"
    language: str = "zh-CN"

    # Database
    db_url: str = ""

    # Environment
    env: str = "development"
    tool_plugins: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def is_production(self) -> bool:
        return self.env == "production"


settings = Settings()
