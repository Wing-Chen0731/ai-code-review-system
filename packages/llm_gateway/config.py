from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    default_provider: str = "mock"
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql://user:pass@localhost:5432/gateway"
    budget_default_limit_usd: float = 100.0
    models_config_path: str = "config/models.yaml"
    prompt_dir: str = "prompts"
    schema_path: str = "config/schemas/code_review_finding.yaml"

