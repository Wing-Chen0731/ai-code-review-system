# Week 1 置信度路由

完整流程图与边界条件位于根目录 [`docs/routing_strategy.md`](../../docs/routing_strategy.md)。阶段 1 的固定策略为：规则预筛后，`confidence > 0.85` 自动发布；`0.5 < confidence <= 0.85` 升级更贵模型并在不确定时人工复核；`confidence <= 0.5` 保存 Draft。

