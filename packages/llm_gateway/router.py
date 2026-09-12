from pathlib import Path
from typing import Any

import yaml


class ModelRouter:
    def __init__(self, config_path: str):
        self.config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))

    def route(self, task: str) -> dict[str, Any]:
        for route in self.config.get("routes", []):
            if route["task"] == task:
                return route
        raise ValueError(f"No route for task: {task}")

