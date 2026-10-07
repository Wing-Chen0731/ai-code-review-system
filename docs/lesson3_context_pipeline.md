# 第三节课：代码上下文管道运行说明

本节将 GitHub PR 事件转换为可追踪的 `PullRequestTask`，再经过 Diff、AST、语义分块、离线向量检索、混合检索和上下文压缩，最终生成 `ReviewContext`。

## 本地验证

```powershell
python -m pip install -r requirements-lesson3.txt
python -m pytest -q
python -m compileall -q packages integrations experiments tests
python -m experiments.retrieval_comparison
```

真实 GitHub 请求需要 `GITHUB_TOKEN`，但单元测试和集成测试使用 Mock 客户端，不依赖网络、数据库或向量服务。

## 代码入口

- `integrations/github/webhook.py`：签名校验、事件过滤和幂等去重。
- `integrations/github/client.py`：PR、文件列表、固定 commit 内容和代码搜索。
- `packages/context/diff_parser.py`：解析 Hunk 头并保留新旧行号映射。
- `packages/context/ast_analyzer.py`：Python 符号表、调用图和反向调用图。
- `packages/context/builder.py`：组装 DiffContext、CodeReference 和 token 预算。
- `packages/context/retriever.py`：关键词、向量和 RRF 混合检索。
- `packages/context/governance.py`：二进制、生成物和敏感路径治理。
