# Week 1 Prompt Injection 防御

完整白皮书位于根目录 [`docs/security_whitepaper.md`](../../docs/security_whitepaper.md)。核心设计是 Gateway 的 `Sanitizer` 生成不可变 `SanitizedContext`，Worker 采用不可信输入隔离、工具 allowlist、短期只读凭据、硬超时和发布前二次校验。

