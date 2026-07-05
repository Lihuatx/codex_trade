# 开发说明

## 本地启动

当前阶段不需要 API Key，可以先运行测试：

```powershell
python -m unittest discover -s tests
```

公共接口 smoke test：

```powershell
$env:PYTHONPATH='src'
python scripts/check_okx_public.py
python scripts/collect_okx_rest.py --db data/market.sqlite3 --inst BTC-USDT --inst ETH-USDT --bar 1H --limit 20
python scripts/collect_okx_history.py --db data/history.sqlite3 --inst BTC-USDT --inst ETH-USDT --bar 1H --pages 10 --limit 300
python scripts/collect_okx_ws_public.py --db data/market.sqlite3 --inst BTC-USDT --max-messages 12
python scripts/run_backtest.py --db data/market.sqlite3 --strategy buy-and-hold --inst BTC-USDT --bar 1H
python scripts/run_backtest.py --db data/history.sqlite3 --strategy trend-filter --inst BTC-USDT --bar 1H --ma-window 50 --format markdown --output reports/btc_trend_1h.md
python scripts/run_backtest_sweep.py --db data/history.sqlite3 --inst BTC-USDT --bar 1H --ma-windows 10,20,50,100,200 --format csv --output reports/btc_trend_sweep.csv
python scripts/run_backtest_split.py --db data/history_1d.sqlite3 --strategy trend-filter --inst BTC-USDT --bar 1D --ma-window 200 --output reports/btc_trend_split_1d.json
python scripts/preview_okx_order.py --inst BTC-USDT --side buy --quote-notional 20 --bar 1H
python scripts/simulate_order_lifecycle.py --db data/oms_sim.sqlite3
python scripts/validate_market_data.py --db data/market.sqlite3 --inst BTC-USDT --bar 1H
python scripts/simulate_risk_check.py --db data/risk_sim.sqlite3 --side buy --notional 20
python scripts/simulate_reconciliation.py --db data/reconcile_sim.sqlite3
```

后续进入模拟盘时：

```powershell
Copy-Item .env.example .env.demo
```

然后手动填写 OKX 模拟盘 API Key、Secret 和 Passphrase。

OKX 的 Passphrase 是创建 API Key 时你自己填写的 API 口令，不是系统生成的 Secret Key。详情页通常不会再次显示它；如果没有保存或记不住，需要重新创建 API Key。

填写后可运行只读私有接口检查：

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

## 目录

```text
src/okx_quant/
  brokers/okx/       OKX REST/WebSocket 适配层
  domain/            交易领域模型
  oms/               订单状态机
  risk/              预交易风控
  storage/           SQLite 事件库和数据表
tests/               单元测试
docs/                项目文档和依据
```
