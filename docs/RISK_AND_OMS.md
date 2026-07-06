# 风控与 OMS 规格

## 策略输出

策略只能输出交易意图：

```text
TradeIntent(
  strategy_id,
  inst_id,
  side,
  notional,
  reference_price,
  reason
)
```

## 风控拒单条件

- `kill_switch = true`
- `read_only_mode = true`
- 行情时间超过 `stale_market_data_seconds`
- 单笔名义金额超过 `max_order_notional`
- 总加密资产暴露超过 `max_total_crypto_exposure`
- 最新价和信号参考价偏离超过 `max_price_deviation_bps`
- 买一卖一价差超过 `max_spread_bps`
- 日内亏损超过 `max_daily_loss`
- 订单频率超过限制
- `reconcile_required = true`

## OMS 原则

- 每笔订单必须有本地生成的 `clOrdId`。
- 请求成功不代表最终成交。
- 撤单请求成功不代表最终撤单。
- 私有订单频道和 REST 查询结果优先于本地推断。
- 订单进入 `Unknown` 后禁止新单，直到对账恢复。
- OKX 可能在没有本地主动撤单请求时把 `post_only` / `IOC` 等订单推到 `canceled` 终态，因此状态机允许 `Accepted -> Cancelled` 和 `PartiallyFilled -> Cancelled`。
- 自动执行器启动时，如果本地 DB 存在活跃订单或最近一次对账失败，必须拒绝新单。
- 72 小时 runner 不直接实现交易逻辑，只调度 one-shot 自动执行器；每个周期都必须重新经过信号、风控、OMS、下单、撤单和对账。
- 72 小时 runner 默认 `min_seconds_between_executions = 10800`、`max_executions_per_day = 8`、`max_consecutive_errors = 3`，连续错误达到阈值必须停机。

## 实盘初始限制

```text
target_read_only_weights = USDT 90%, BTC 5%, ETH 5%
max_total_crypto_exposure = 30 USDT
max_order_notional = 10 USDT
max_daily_loss = 5 USDT
max_orders_per_day = 10
max_orders_per_hour = 3
min_seconds_between_orders = 600
max_spread_bps = 20
max_price_deviation_bps = 30
stale_market_data_seconds = 10
```
