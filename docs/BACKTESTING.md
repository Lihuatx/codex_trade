# 回测记录

## 当前结论

模拟盘 API、OMS、私有 WebSocket 和对账链路已经跑通，但策略层不能因此直接进入自动交易。当前正式回测显示：

- 1H 趋势过滤换手过高，手续费和滑点会显著侵蚀收益。
- 1D 低频趋势过滤全样本表现较好，但样本外表现不合格。
- `backtesting.py` 已完成 1D 单资产趋势过滤交叉验证，结论与自研引擎方向一致，但不能替代样本外验收。
- BTC/ETH/USDT 阈值再平衡样本外表现优于趋势过滤，可进入 read-only 信号观测，但还不能直接自动交易。

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

## backtesting.py 交叉验证

用途：验证自研日线趋势过滤回测的大方向是否被另一个成熟框架支持。

命令：

```powershell
python scripts/run_backtestingpy_trend.py --db data/history_1d.sqlite3 --inst BTC-USDT --bar 1D --ma-window 200 --fractional-unit 0.00000001 --output reports/btc_trend_backtestingpy_1d.json
python scripts/run_backtestingpy_trend.py --db data/history_1d.sqlite3 --inst ETH-USDT --bar 1D --ma-window 200 --fractional-unit 0.00000001 --output reports/eth_trend_backtestingpy_1d.json
```

适配说明：

- 使用 `backtesting.lib.FractionalBacktest`，默认 `fractional_unit = 0.00000001`，避免 BTC/ETH 在小资金账户中被整数单位撮合规则扭曲。
- `commission = 10 bps`，`spread = 5 bps`，`trade_on_close = True`，`exclusive_orders = True`，`finalize_trades = True`。
- `backtesting.py` 使用浮点数和自身撮合语义，所以只作为交叉验证，不作为资金账本或实盘订单语义的来源。
- 交易笔数口径不同：自研报告统计买入和卖出执行，`backtesting.py` 的 `# Trades` 统计已完成的 round-trip trade。

结果：

| 标的 | 自研最终权益 | backtesting.py 最终权益 | 自研最大回撤 | backtesting.py 最大回撤 | 自研交易执行 | backtesting.py round-trip |
|---|---:|---:|---:|---:|---:|---:|
| BTC-USDT | 12068.87 | 12240.72 | 63.40% | 63.18% | 62 | 31 |
| ETH-USDT | 15591.70 | 15909.31 | 68.80% | 68.63% | 50 | 25 |

判断：交叉验证支持“日线趋势过滤在全样本上大致可复现”的结论，但不改变样本外不合格的事实。后续策略研究应优先扩展 walk-forward、成本三档和再平衡策略交叉验证，而不是因为全样本好看就进入自动交易。

## BTC/ETH/USDT 阈值再平衡

配置：

```text
USDT = 50%
BTC = 25%
ETH = 25%
rebalance_threshold = 5%
min_trade_notional = 10 USDT
```

全样本区间：2017-10-10 到 2026-07-03。

- 最终权益约 6608.20。
- 净收益约 +560.82%。
- 最大回撤约 59.79%。
- 交易 197 笔。
- 总手续费约 22.17 USDT。
- Fee / gross PnL 约 0.39%。

样本内 / 样本外：

- 样本内：净收益约 +439.29%，最大回撤约 59.79%，交易 165 笔。
- 样本外：净收益约 +25.26%，最大回撤约 35.20%，交易 37 笔。

判断：阈值再平衡比当前趋势过滤更适合作为第一版 read-only 观测策略。它仍不应直接自动交易，原因是：

- 回撤仍然较大。
- 当前回测没有建模盘口深度、限价单不成交、账户真实余额变化和税费外部因素。
- 需要先跑 read-only 信号观测，确认实时行情、账户权重、目标仓位和风控日志一致。

## 策略验收门槛草案

策略进入自动模拟盘交易前，至少需要：

- 样本外 `net_pnl_after_fee > 0`。
- 样本外 `profit_factor > 1.2`。
- `fee / gross_pnl` 不应过高。
- 参数扫描不能只在单个孤立参数上表现好。
- 最大回撤要能用 300U 实盘预算承受。
- read-only 信号观测至少运行 7 天，信号和行情/风控/日志一致。

当前建议：

- 暂不启动自动模拟盘策略交易。
- BTC/ETH/USDT 再平衡 read-only 信号预览已实现。
- read-only 观测通过后，再考虑 demo 小单自动再平衡。

## Walk-forward 与成本三档

新增滚动 walk-forward 检查：

```powershell
python scripts/run_trend_walk_forward.py --db data/history_1d.sqlite3 --inst BTC-USDT --bar 1D --ma-windows 100,150,200,250 --output reports/btc_trend_walk_forward_1d.json
python scripts/run_trend_walk_forward.py --db data/history_1d.sqlite3 --inst ETH-USDT --bar 1D --ma-windows 100,150,200,250 --output reports/eth_trend_walk_forward_1d.json
python scripts/run_rebalance_walk_forward.py --db data/history_1d.sqlite3 --bar 1D --thresholds 0.03,0.05,0.08,0.10 --weights USDT=0.5,BTC=0.25,ETH=0.25 --output reports/rebalance_walk_forward_1d.json
```

窗口设置：

- 训练窗口：1095 根 1D K 线。
- 测试窗口：365 根 1D K 线。
- 步进：365 根 1D K 线。
- 每个测试窗口只使用前一个训练窗口选出的参数。

默认成本三档：

| 场景 | taker fee | spread | slippage |
|---|---:|---:|---:|
| optimistic | 8 bps | 2 bps | 2 bps |
| neutral | 10 bps | 5 bps | 5 bps |
| pessimistic | 15 bps | 10 bps | 15 bps |

中性成本结果摘要：

| 策略 | 测试窗口 | 正收益窗口 | 平均测试收益 | 最差测试收益 | 最差测试回撤 |
|---|---:|---:|---:|---:|---:|
| BTC trend filter | 5 | 3 | +5.70% | -9.98% | 41.67% |
| ETH trend filter | 5 | 2 | +15.50% | -24.99% | 56.86% |
| BTC/ETH/USDT threshold rebalance | 5 | 4 | +55.10% | -32.66% | 46.94% |

判断：

- 再平衡仍是当前更适合作为 read-only 观测的候选策略。
- 再平衡的滚动测试并不稳定到可以直接自动交易；最差一年测试收益约 -32.66%，最差测试回撤约 46.94%。
- 如果进入 300U 小资金实盘，第一版应继续降低风险暴露，比如提高 USDT 权重、限制单笔订单和总 crypto exposure，而不是照搬 `50/25/25` 组合自动下单。
- 趋势过滤策略的参数选择并不稳定，仍不应进入自动交易。

## 300U 低风险权重对照

为匹配“先验证交易链路，不追收益”的目标，对再平衡策略增加低 crypto exposure 权重对照：

```powershell
python scripts/run_rebalance_walk_forward.py --db data/history_1d.sqlite3 --bar 1D --thresholds 0.03,0.05,0.08,0.10 --weights USDT=0.7,BTC=0.15,ETH=0.15 --output reports/rebalance_walk_forward_70_15_15_1d.json
python scripts/run_rebalance_walk_forward.py --db data/history_1d.sqlite3 --bar 1D --thresholds 0.03,0.05,0.08,0.10 --weights USDT=0.8,BTC=0.1,ETH=0.1 --output reports/rebalance_walk_forward_80_10_10_1d.json
python scripts/run_rebalance_walk_forward.py --db data/history_1d.sqlite3 --bar 1D --thresholds 0.03,0.05,0.08,0.10 --weights USDT=0.9,BTC=0.05,ETH=0.05 --output reports/rebalance_walk_forward_90_5_5_1d.json
```

中性成本结果摘要：

| 权重 | 正收益窗口 | 平均测试收益 | 最差测试收益 | 最差测试回撤 | 平均交易数 |
|---|---:|---:|---:|---:|---:|
| USDT/BTC/ETH = 50/25/25 | 4/5 | +55.10% | -32.66% | 46.94% | 11.0 |
| USDT/BTC/ETH = 70/15/15 | 4/5 | +32.76% | -18.28% | 30.96% | 8.0 |
| USDT/BTC/ETH = 80/10/10 | 4/5 | +17.72% | -15.19% | 21.58% | 5.2 |
| USDT/BTC/ETH = 90/5/5 | 4/5 | +9.10% | -6.38% | 9.59% | 3.6 |

判断：第一阶段 300U 不建议用 `50/25/25`。更合理的 read-only 候选是 `USDT=90%, BTC=5%, ETH=5%`，它牺牲收益弹性来换取更低回撤和更少订单，更符合验证 API、OMS、账本、对账的目标。

Read-only 信号命令：

```powershell
python scripts/preview_rebalance_signal.py --env-file .env.demo --weights USDT=0.9,BTC=0.05,ETH=0.05 --threshold 0.08 --max-order-notional 10 --max-total-crypto-exposure 30
```

注意：该脚本只读取账户余额和行情，输出目标再平衡意图和 300U 风控截断后的预览，不会下单。

Demo 自动小单执行命令：

```powershell
python scripts/run_demo_rebalance_executor.py --env-file .env.demo --db data/demo_rebalance_executor.sqlite3
python scripts/run_demo_rebalance_executor.py --env-file .env.demo --db data/demo_rebalance_executor.sqlite3 --execute --override-read-only
```

2026-07-06 验收记录：

- 已用 OKX demo 执行 `BTC-USDT sell post_only` 小单。
- 单笔名义金额约 10 USDT。
- 最终交易所状态：`canceled`。
- 本地 OMS 状态：`cancelled`。
- 订单状态对账：0 个 issue。
- 该执行器仍是 one-shot 小单验证，不是 72 小时连续 runner。
