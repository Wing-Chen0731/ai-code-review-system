import logging
import time
import uuid
from typing import Any

from .adapters.base import ChatRequest, ChatResponse

logger = logging.getLogger("llm_gateway")


class CallLogger:
    def log_call(self, request: ChatRequest, response: ChatResponse, duration_ms: float, trace_id: str) -> dict[str, Any]:
        record = {
            "event": "llm_call",
            "trace_id": trace_id,
            "model": request.model,
            "provider_model": response.model,
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "estimated_cost_usd": response.usage.estimated_cost_usd,
            "duration_ms": round(duration_ms, 3),
            "finish_reason": response.finish_reason,
            "message_count": len(request.messages),
        }
        logger.info("llm_call %s", record)
        return record


def new_trace_id() -> str:
    return str(uuid.uuid4())


def elapsed_ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000

