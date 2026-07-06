# 监控与可视化

## 目标

日志和 dashboard 是交易系统的基础设施，不是 demo 阶段的临时工具。后续从 OKX demo 切到 live，或迁移到 QMT / A 股接口，也应继续保留同样的观测面：

```text
runner JSONL log
  -> local dashboard
  -> SQLite / ledger / reconciliation state
  -> operator decision
```

## JSONL 日志

72 小时 runner 会把每个周期写成一行 JSON：

```powershell
logs/demo_rebalance_runner_72h.jsonl
```

Windows 实时查看：

```powershell
Get-Content logs\demo_rebalance_runner_72h.jsonl -Wait
```

Linux / macOS 实时查看：

```bash
tail -f logs/demo_rebalance_runner_72h.jsonl
```

每个周期至少包含：

- cycle 编号。
- cycle 开始和结束时间。
- 本周期是否真实执行。
- one-shot executor 结果。
- 本地 runner state。
- 成功/失败和连续错误计数。

## 本地 Dashboard

启动命令：

```powershell
$env:PYTHONPATH='src'
python scripts/run_dashboard.py --host 127.0.0.1 --port 8765 --db data/demo_rebalance_runner.sqlite3 --log-file logs/demo_rebalance_runner_72h.jsonl --summary-file reports/demo_rebalance_runner_72h.json --state-file data/demo_rebalance_runner_state.json
```

浏览器打开：

```text
http://127.0.0.1:8765
```

API：

```text
http://127.0.0.1:8765/api/status
```

dashboard 当前展示：

- runner 健康状态。
- cycle、执行次数、连续错误数。
- 最近一次执行结果。
- 订单列表和本地 OMS 状态。
- 风控事件。
- 对账结果。
- 原始 runner JSONL 事件。

## 运行纪律

- dashboard 只读本地文件和 SQLite，不接收外部写入。
- dashboard 不读取或展示 API Key、Secret、Passphrase。
- runner / dashboard 文件路径应通过参数传入，live 阶段换路径即可复用。
- 如果 dashboard 显示 runner stale、对账 failed、订单 unknown，应停止新单并先排查。
