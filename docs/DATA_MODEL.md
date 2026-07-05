# 数据模型草案

## market_raw

保存交易所原始消息，便于重放和排错。

```text
id
source
channel
inst_id
received_at
payload_json
```

## candles

标准化 K 线。策略只允许使用 `confirm = 1` 的已完成 K 线。

```text
inst_id
bar
ts
open
high
low
close
volume
confirm
source
```

## trade_intents

策略输出的交易意图，不是订单。

```text
intent_id
strategy_id
inst_id
side
notional_ccy
reason
created_at
```

## orders

本地 OMS 订单。

```text
client_order_id
exchange_order_id
inst_id
side
order_type
price
size
status
created_at
updated_at
```

## fills

成交明细。

```text
fill_id
client_order_id
exchange_order_id
inst_id
side
price
size
fee
fee_ccy
liquidity
filled_at
```

## account_snapshots

账户快照。

```text
snapshot_id
taken_at
ccy
equity
available
frozen
source
```

## reconciliation_runs

对账批次。

```text
run_id
started_at
finished_at
status
summary
```

