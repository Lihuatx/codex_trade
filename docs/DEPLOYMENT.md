# 服务器部署与运行

## 目标

72 小时 demo runner 和 dashboard 应运行在服务器上，本机只作为开发、部署和观察入口。dashboard 默认只绑定服务器 `127.0.0.1`，通过 SSH tunnel 查看，避免把交易监控面板直接暴露到公网。

## 本地 `.env.demo`

本地 `.env.demo` 需要包含：

```text
OKX_ENV=demo
OKX_API_KEY=...
OKX_API_SECRET=...
OKX_API_PASSPHRASE=...
OKX_SIMULATED_TRADING=1

IP=...
USER=...
SECRET_KEY=...
```

`IP / USER / SECRET_KEY` 只用于部署和 SSH 登录服务器；交易程序只依赖 OKX 和风控相关配置。不要把 `.env.demo` 提交到 Git。

## 服务器目录

默认部署目录：

```text
~/codex_trade
```

运行文件：

```text
logs/demo_rebalance_runner_72h.jsonl
logs/demo_rebalance_runner_72h.stdout.log
logs/demo_rebalance_runner_72h.stderr.log
logs/dashboard.stdout.log
logs/dashboard.stderr.log
data/demo_rebalance_runner.sqlite3
data/demo_rebalance_runner_state.json
reports/demo_rebalance_runner_72h.json
```

## 启动 runner

在服务器 `~/codex_trade` 下：

```bash
nohup .venv/bin/python scripts/run_demo_rebalance_runner.py \
  --env-file .env.demo \
  --db data/demo_rebalance_runner.sqlite3 \
  --state-file data/demo_rebalance_runner_state.json \
  --log-file logs/demo_rebalance_runner_72h.jsonl \
  --summary-file reports/demo_rebalance_runner_72h.json \
  --duration-hours 72 \
  --interval-seconds 900 \
  --execute \
  --override-read-only \
  > logs/demo_rebalance_runner_72h.stdout.log \
  2> logs/demo_rebalance_runner_72h.stderr.log &
```

第一期 runner 是链路 burn-in，不是策略收益验收。它验证再平衡意图、风控截断、OMS、OKX demo post_only 小单、撤单、订单状态对账、JSONL 日志和 dashboard 是否连续稳定。

## 启动 dashboard

在服务器 `~/codex_trade` 下：

```bash
nohup .venv/bin/python scripts/run_dashboard.py \
  --host 127.0.0.1 \
  --port 8765 \
  --db data/demo_rebalance_runner.sqlite3 \
  --log-file logs/demo_rebalance_runner_72h.jsonl \
  --summary-file reports/demo_rebalance_runner_72h.json \
  --state-file data/demo_rebalance_runner_state.json \
  > logs/dashboard.stdout.log \
  2> logs/dashboard.stderr.log &
```

## 查看实时日志

```bash
ssh -i <SECRET_KEY> <USER>@<IP> 'tail -f ~/codex_trade/logs/demo_rebalance_runner_72h.jsonl'
```

如果只想看普通 stdout / stderr：

```bash
ssh -i <SECRET_KEY> <USER>@<IP> 'tail -f ~/codex_trade/logs/demo_rebalance_runner_72h.stdout.log'
ssh -i <SECRET_KEY> <USER>@<IP> 'tail -f ~/codex_trade/logs/demo_rebalance_runner_72h.stderr.log'
```

## 查看 dashboard

在本机开一个 SSH tunnel：

```bash
ssh -i <SECRET_KEY> -L 8765:127.0.0.1:8765 <USER>@<IP>
```

然后浏览器打开：

```text
http://127.0.0.1:8765
```

健康检查 API：

```text
http://127.0.0.1:8765/api/status
```

## 停止服务

只停止本项目脚本：

```bash
pkill -f 'scripts/run_demo_rebalance_runner.py'
pkill -f 'scripts/run_dashboard.py'
```

停止前先确认没有同名手工调试进程。

## 部署纪律

- 每次部署前先确认本机没有残留 runner，避免 demo 账户重复下单。
- 服务器启动前先停止旧 runner / dashboard，只保留一套交易进程。
- dashboard 默认不公网暴露，只通过 SSH tunnel 访问。
- 服务器 `.env.demo` 权限应设置为 `600`。
- 远端日志、SQLite、state、summary 属于运行证据，不要随意删除。
