# 指标口径与验收标准

本文件定义阶段 1 的可计算契约。所有时间、token 数和反馈都必须写入结构化事件日志，不能依赖人工从文本日志猜测。

## 1. 误报率 False Alarm Rate

公式：

```text
False Alarm Rate = FP / (TP + FP)
```

统计单位是“已发布 finding”，统计窗口为自然日或指定评测批次。分母只包含已经获得用户反馈的 finding；没有反馈的 finding 记为 `UNLABELED`，不能当作 TP 或 FP，也不能偷偷计入分母。

### 日志区分规则

交付层在评论发布后写入 `finding_published` 事件，用户通过 GitHub reaction、评论命令或 Web UI 提交 `feedback` 字段。允许值为：

- `true_positive`：用户确认问题真实存在、评论有帮助，计 1 个 TP。
- `false_positive`：用户确认问题不存在、误报或不适用，计 1 个 FP。
- `fixed`：用户确认问题真实存在且已修复，仍计 1 个 TP。
- `unlabeled`：尚未标注，不参与当前窗口分母。

伪查询：

```sql
SELECT
  SUM(CASE WHEN feedback IN ('false_positive') THEN 1 ELSE 0 END)::float /
  NULLIF(SUM(CASE WHEN feedback IN ('true_positive', 'fixed', 'false_positive') THEN 1 ELSE 0 END), 0)
    AS false_alarm_rate
FROM finding_feedback
WHERE created_at >= :window_start AND created_at < :window_end;
```

验收：给定 8 个 TP、2 个 FP 和任意数量的 UNLABELED，结果必须是 `2 / (8 + 2) = 20%`。

## 2. 端到端时延 P95

单条任务的时延定义为：

```text
latency_ms = timestamp(review_comment_published) - timestamp(webhook_received)
```

P95 是窗口内所有“成功回写”任务的 latency_ms 的 nearest-rank 第 95 百分位：排序后取位置 `ceil(0.95 * N)`（位置从 1 开始）。时间戳统一使用 UTC，精度至少为毫秒。

### Worker 挂掉时如何计算

- Worker 崩溃但任务最终重试成功：从最初的 `webhook_received` 到最终 `review_comment_published`，崩溃和排队时间全部计入；不能从 Worker 重启时间重新起算。
- Worker 永久失败且没有评论回写：不产生成功 latency，不进入 P95；同时写入 `review_failed`，另算失败率和恢复时间。
- 超过 SLA 的任务后来成功：仍进入 P95，反映用户真实等待时间。
- 若 webhook 已接收但事件日志缺失关键时间戳：标记 `measurement_invalid`，不补估、不静默丢弃，并告警。

验收：构造 20 条成功任务，按升序排列后第 `ceil(0.95*20)=19` 条的毫秒值必须作为 P95。

## 3. 单次审查成本

公式：

```text
cost_usd = (input_tokens × input_price_per_token)
          + (output_tokens × output_price_per_token)
```

本文示例选用 `gpt-4o-mini` 的预算单价（通过环境变量配置，实际价格变化时以账单/官方价格配置为准）：输入 `$0.00015 / 1K tokens`，输出 `$0.00060 / 1K tokens`。

针对中等规模 PR（约 `+200/-50` 行），阶段 1 预算按最坏但可控的上下文上限估算：

- 输入上限：12,000 tokens（diff、相关文件窗口、规则、系统提示和安全标记）。
- 输出上限：2,000 tokens（结构化 findings 与证据）。

```text
12,000 / 1,000 × $0.00015 = $0.00180
 2,000 / 1,000 × $0.00060 = $0.00120
预估成本上限 = $0.00300 / 次
```

实现时从 LLM response usage 读取真实 `prompt_tokens` 和 `completion_tokens`，按调用时的价格配置落库；重试、二次模型判断和失败调用也必须分别记账。这里的 `$0.00300` 是单次一次调用的预算上限，不是包含人工复核或更贵模型升级后的全链路保证。

