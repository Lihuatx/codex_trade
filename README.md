# OKX Quant Lab

OKX 现货量化交易系统训练场。

第一期目标：先在模拟盘跑通行情、成本、策略意图、风控、OMS、账本和对账，再用 300 USDT 小资金实盘验证真实交易摩擦。

## 快速检查

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests
python scripts/check_okx_public.py
python scripts/collect_okx_rest.py --db data/market.sqlite3 --inst BTC-USDT --inst ETH-USDT --bar 1H --limit 20
python scripts/collect_okx_history.py --db data/history.sqlite3 --inst BTC-USDT --inst ETH-USDT --bar 1H --pages 10 --limit 300
python scripts/collect_okx_ws_public.py --db data/market.sqlite3 --inst BTC-USDT --max-messages 12
python scripts/run_backtest.py --db data/market.sqlite3 --strategy buy-and-hold --inst BTC-USDT --bar 1H
python scripts/run_backtest.py --db data/history.sqlite3 --strategy trend-filter --inst BTC-USDT --bar 1H --ma-window 50 --format markdown --output reports/btc_trend_1h.md
python scripts/run_backtest_sweep.py --db data/history.sqlite3 --inst BTC-USDT --bar 1H --ma-windows 10,20,50,100,200 --format csv --output reports/btc_trend_sweep.csv
python scripts/run_backtest_split.py --db data/history_1d.sqlite3 --strategy trend-filter --inst BTC-USDT --bar 1D --ma-window 200 --output reports/btc_trend_split_1d.json
python scripts/run_backtestingpy_trend.py --db data/history_1d.sqlite3 --inst BTC-USDT --bar 1D --ma-window 200 --fractional-unit 0.00000001 --output reports/btc_trend_backtestingpy_1d.json
python scripts/run_trend_walk_forward.py --db data/history_1d.sqlite3 --inst BTC-USDT --bar 1D --ma-windows 100,150,200,250 --output reports/btc_trend_walk_forward_1d.json
python scripts/run_rebalance_backtest.py --db data/history_1d.sqlite3 --bar 1D --weights USDT=0.5,BTC=0.25,ETH=0.25 --threshold 0.05 --output reports/rebalance_50_25_25_1d.json
python scripts/run_rebalance_split.py --db data/history_1d.sqlite3 --bar 1D --weights USDT=0.5,BTC=0.25,ETH=0.25 --threshold 0.05 --output reports/rebalance_50_25_25_split_1d.json
python scripts/run_rebalance_walk_forward.py --db data/history_1d.sqlite3 --bar 1D --thresholds 0.03,0.05,0.08,0.10 --weights USDT=0.5,BTC=0.25,ETH=0.25 --output reports/rebalance_walk_forward_1d.json
python scripts/preview_rebalance_signal.py --env-file .env.demo --weights USDT=0.9,BTC=0.05,ETH=0.05 --threshold 0.08 --max-order-notional 10 --max-total-crypto-exposure 30
python scripts/preview_okx_order.py --inst BTC-USDT --side buy --quote-notional 20 --bar 1H
python scripts/simulate_order_lifecycle.py --db data/oms_sim.sqlite3
python scripts/validate_market_data.py --db data/market.sqlite3 --inst BTC-USDT --bar 1H
python scripts/simulate_risk_check.py --db data/risk_sim.sqlite3 --side buy --notional 20
python scripts/simulate_reconciliation.py --db data/reconcile_sim.sqlite3
```

模拟盘 Key 准备好后：

```powershell
$env:PYTHONPATH='src'
python scripts/check_okx_private.py --env-file .env.demo --inst BTC-USDT
python scripts/snapshot_okx_account.py --env-file .env.demo --db data/account_snapshot.sqlite3
python scripts/demo_place_cancel_order.py --env-file .env.demo --db data/demo_orders.sqlite3 --execute
python scripts/preview_pretrade_flow.py --env-file .env.demo --inst BTC-USDT --notional 20 --override-read-only-for-preview
python scripts/check_okx_private_ws.py --env-file .env.demo
python scripts/demo_order_ws_lifecycle.py --env-file .env.demo --db data/demo_order_ws.sqlite3
python scripts/snapshot_okx_reconciliation_sources.py --env-file .env.demo --db data/reconciliation_sources.sqlite3 --inst BTC-USDT
python scripts/reconcile_okx_orders.py --env-file .env.demo --db data/demo_order_ws.sqlite3 --inst BTC-USDT
```

## 当前能力

- OKX 公共 REST 产品规则读取。
- OKX 历史 K 线读取和 `confirm` 过滤。
- OKX 公共 WebSocket 短采样落库。
- SQLite 本地事件库。
- 成本约束回测：buy-and-hold benchmark、趋势过滤策略。
- 趋势过滤参数敏感性扫描。
- 样本内/样本外回测切分；当前没有策略通过自动交易验收。
- `backtesting.py` 单资产趋势过滤小数单位交叉验证。
- Walk-forward 回测和 optimistic/neutral/pessimistic 成本三档。
- BTC/ETH/USDT 阈值再平衡组合回测。
- Demo account read-only 再平衡信号预览。
- OKX 现货限价单 payload 干跑生成，不触碰私有交易接口。
- OKX 模拟盘 REST 下单、查询、撤单闭环。
- OKX 模拟盘私有 WebSocket orders 频道事件闭环。
- 预交易风控到订单 payload 预览链路。
- 本地 OMS 生命周期模拟和订单/成交落库。
- 风控检查审计落库。
- 本地订单状态对账模拟。
- K 线数据质量检查。
- 产品精度和最小下单量模型。
- OMS 状态机。
- 预交易风控骨架。
- 初始事件/账本 SQL schema。

## 文档

- `AGENTS.md`：开发纪律和依据要求。
- `ROADMAP.md`：一期路线图和对账进度。
- `docs/EVIDENCE.md`：官方文档和开源项目依据记录。
- `docs/ARCHITECTURE.md`：模块架构。
- `docs/RISK_AND_OMS.md`：风控和订单状态机规格。
