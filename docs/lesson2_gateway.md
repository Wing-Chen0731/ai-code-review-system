# 第二节课：大模型网关

本节把模型能力封装成 Provider 无关的后端基础设施，代码位于 `packages/llm_gateway/`。

## 运行方式

```bash
python -m pip install -r requirements-lesson2.txt
python -m pytest -q tests/llm_gateway tests/test_models.py
python -m compileall -q packages/llm_gateway
```

默认配置使用 `MockProvider`，因此不需要 API Key、Redis 或数据库即可跑通完整链路：Prompt 渲染 → 敏感信息脱敏 → 路由 → 超时/重试 → 熔断 → 结构化响应 → Token/成本记录 → 预算记账。

## 代码对应课程目标

| 课程目标 | 实现位置 |
|---|---|
| Provider 无关接口 | `adapters/base.py` |
| Mock / OpenAI / Anthropic / Local 适配器 | `adapters/` |
| 工厂与模型路由 | `factory.py`, `router.py`, `config/models.yaml` |
| 超时、指数退避、限流、熔断、降级 | `reliability.py` |
| 预算控制与用量记录 | `budget.py`, `usage_repository.py` |
| Prompt 与输出 Schema 版本化 | `prompt_manager.py`, `prompts/`, `config/schemas/` |
| 敏感信息脱敏 | `security.py` |
| trace_id、Token、成本、延迟日志 | `observability.py`, `gateway.py` |
| 契约测试与 CI Mock 基线 | `tests/llm_gateway/` |

真实 Provider 是可选路径；CI 和本地默认走 Mock，避免测试依赖密钥、网络和真实调用费用。

