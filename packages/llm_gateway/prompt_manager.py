from pathlib import Path
from typing import Any

import yaml


class PromptManager:
    def __init__(self, prompt_dir: str):
        self.prompt_dir = Path(prompt_dir)
        self._cache: dict[str, dict[str, Any]] = {}

    def load(self, name: str, version: str) -> dict[str, Any]:
        key = f"{name}:{version}"
        if key not in self._cache:
            path = self.prompt_dir / name / f"{version}.yaml"
            self._cache[key] = yaml.safe_load(path.read_text(encoding="utf-8"))
        return self._cache[key]

    def render(self, name: str, version: str, **kwargs: str) -> str:
        prompt = self.load(name, version)
        return prompt["user_prompt_template"].format(**kwargs)

