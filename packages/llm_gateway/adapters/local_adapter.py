"""OpenAI-compatible local model adapter (Ollama/vLLM compatible endpoint)."""

from .openai_adapter import OpenAIProvider


class LocalModelProvider(OpenAIProvider):
    def __init__(self, base_url: str = "http://localhost:11434/v1", api_key: str = "local"):
        super().__init__(api_key=api_key, base_url=base_url)

