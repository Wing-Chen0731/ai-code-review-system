# Week 1 指标口径

本周提交的完整指标契约位于根目录 [`docs/metrics.md`](../../docs/metrics.md)。它定义了：

- 误报率 `FP / (TP + FP)`，只统计带 `feedback` 的 TP/FP；`unlabeled` 不进入分母。
- P95 从 `webhook_received` 到 `review_comment_published`，Worker 崩溃后的重试等待全部计入。
- 成本为 `input_tokens × input_price + output_tokens × output_price`；中等 PR 的 gpt-4o-mini 预算上限为 `$0.00300`。

