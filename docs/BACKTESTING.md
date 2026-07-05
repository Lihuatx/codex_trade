# 回测记录

## 当前结论

模拟盘 API、OMS、私有 WebSocket 和对账链路已经跑通，但策略层不能因此直接进入自动交易。当前正式回测显示：

- 1H 趋势过滤换手过高，手续费和滑点会显著侵蚀收益。
- 1D 低频趋势过滤全样本表现较好，但样本外表现不合格。
- 当前没有策略达到自动模拟盘交易验收标准。

## 数据

来源：OKX `GET /api/v5/market/history-candles`

采集命令：

```powershell
python scripts/collect_okx_history.py --db data/history_1d.sqlite3 --inst BTC-USDT --inst ETH-USDT --bar 1D --pages 12 --limit 300
python scripts/collect_okx_history.py --db data/history_1h.sqlite3 --inst BTC-USDT --inst ETH-USDT --bar 1H --pages 8 --limit 300
```

数据质量：

- BTC-USDT 1D：3189 根已确认 K 线，0 个质量问题。
- ETH-USDT 1D：3189 根已确认 K 线，0 个质量问题。
- BTC-USDT 1H：2399 根已确认 K 线，0 个质量问题。
- ETH-USDT 1H：2399 根已确认 K 线，0 个质量问题。

## 成本假设

```text
taker_fee_bps = 10
slippage_bps = 5
```

第一版回测默认保守按 taker 成交处理，不假设 maker 优势。

## 1H 结果摘要

区间：2026-03-27 到 2026-07-05。

BTC-USDT：

- Buy and hold：净收益 -4.93%，最大回撤 29.36%，交易 1 笔。
- 50H trend filter：净收益 -18.14%，最大回撤 24.11%，交易 145 笔，手续费约 131.54 USDT。

ETH-USDT：

- Buy and hold：净收益 -10.92%，最大回撤 37.89%，交易 1 笔。
- 50H trend filter：净收益 -12.02%，最大回撤 24.54%，交易 137 笔，手续费约 127.30 USDT。

判断：小时级趋势策略换手过高，不适合作为第一版模拟盘策略。

## 1D 结果摘要

区间：2017-10-10 到 2026-07-03。

BTC-USDT：

- Buy and hold：最终权益约 12822.98，最大回撤 83.48%。
- 200D trend filter：最终权益约 12068.87，最大回撤 63.40%，交易 62 笔，Profit factor 约 2.97。

ETH-USDT：

- Buy and hold：最终权益约 5962.32，最大回撤 93.92%。
- 200D trend filter：最终权益约 15591.70，最大回撤 68.80%，交易 50 笔，Profit factor 约 3.41。

判断：日线趋势过滤能降低部分极端回撤，但仍需样本外验证。

## 样本内 / 样本外

切分：前 70% 为样本内，后 30% 为样本外。

BTC-USDT 200D trend filter：

- 样本内：净收益 +578.68%，最大回撤 63.40%，Profit factor 约 2.51。
- 样本外：净收益 -6.45%，最大回撤 30.45%，Profit factor 约 0.84。

ETH-USDT 200D trend filter：

- 样本内：净收益 +991.63%，最大回撤 68.80%，Profit factor 约 5.74。
- 样本外：净收益 -23.37%，最大回撤 40.03%，Profit factor 约 0.45。

判断：200D trend filter 没有通过样本外验收，不能进入自动模拟盘交易。

## 策略验收门槛草案

策略进入自动模拟盘交易前，至少需要：

- 样本外 `net_pnl_after_fee > 0`。
- 样本外 `profit_factor > 1.2`。
- `fee / gross_pnl` 不应过高。
- 参数扫描不能只在单个孤立参数上表现好。
- 最大回撤要能用 300U 实盘预算承受。
- read-only 信号观测至少运行 7 天，信号和行情/风控/日志一致。

