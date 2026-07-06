# 依据记录

本文件记录开发中使用的外部依据。涉及交易接口、字段、订单状态、费率和精度的代码必须能追溯到这里。

## OKX 官方 API 文档

- 来源：https://app.okx.com/docs-v5/zh/
- 查询日期：2026-07-05
- 结论：
  - OKX 提供 REST 和 WebSocket API。
  - 2026-05-20 API 更新日志说明 `openapi.okx.com` 已作为 OKX Global 推荐 REST API 域名，功能上与 `www.okx.com` 等价；`www.okx.com` 仍可继续使用，WebSocket URL 不变。
  - WebSocket 公共频道无需登录，可订阅行情、交易数据、深度数据等。
  - WebSocket 订阅消息使用 `{"op":"subscribe","args":[{"channel":"tickers","instId":"BTC-USDT"}]}` 这类格式。
  - REST market data 提供 ticker 和 order book 接口，可用于下单前 spread/last price 检查。
  - 私有 REST 请求使用 `OK-ACCESS-KEY`、`OK-ACCESS-SIGN`、`OK-ACCESS-TIMESTAMP`、`OK-ACCESS-PASSPHRASE`。
  - 模拟盘请求需要使用模拟盘 API Key，并添加 `x-simulated-trading: 1`。
  - API Key 权限包含读取、交易、提现；交易系统不得开启提现权限。
  - 现货交易模式使用 `tdMode`，币币现货为 `cash`。
  - 下单接口支持 `clOrdId`、`market`、`limit`、`post_only`、`fok`、`ioc` 等概念。
  - K 线数据包含 `confirm` 字段，`1` 表示已完结。
  - 交易产品 K 线和历史 K 线返回数组顺序为 `[ts,o,h,l,c,vol,volCcy,volCcyQuote,confirm]`；部分文档段落出现不带 `volCcyQuote` 的描述，因此解析器以最后一位作为 `confirm`，并兼容 8/9 列。
  - 历史 K 线 `GET /api/v5/market/history-candles` 支持 `after`/`before` 分页；`after` 返回早于指定 `ts` 的数据，`before` 返回新于指定 `ts` 的数据；每次请求最大 `limit=300`。
  - 产品基础信息包含 `tickSz`、`lotSz`、`minSz` 等交易规则字段。
  - `GET /api/v5/public/instruments` 支持 `instId` 参数；单交易对执行链路应按 `instId` 缩小响应体，避免每轮下载全量 SPOT 产品表。
  - 账户手续费接口返回 maker/taker 费率。
  - 账户余额接口为 `GET /api/v5/account/balance`，返回账户下币种资产详情。
- 影响代码：
  - `src/okx_quant/config.py`
  - `src/okx_quant/brokers/okx/auth.py`
  - `src/okx_quant/brokers/okx/client.py`
  - `src/okx_quant/brokers/okx/ws_public.py`
  - `src/okx_quant/domain/instruments.py`
  - `src/okx_quant/domain/market.py`
  - `src/okx_quant/domain/account.py`
  - `scripts/collect_okx_history.py`

## 本地 OKX 公共 REST smoke test

- 来源：本机请求 `https://www.okx.com/api/v5/public/instruments?instType=SPOT`
- 查询日期：2026-07-05
- 结论：
  - 使用官方 `www.okx.com` REST base URL。
  - 本机使用 Python `urllib` 裸请求时返回 403。
  - 添加常规 `User-Agent` 后返回 200。
  - 本机公共 REST 偶发读超时，REST client 对网络/服务端临时失败做短重试。
  - OKX 签名路径必须和实际 request path 一致；无查询参数时不能追加尾随 `?`。
  - 该行为作为运行环境兼容处理，不改变 OKX 官方 API 语义。
- 影响代码：
  - `src/okx_quant/brokers/okx/client.py`

## OKX REST 推荐域名更新

- 来源：https://www.okx.com/docs-v5/log_en/#2026-05-20
- 查询日期：2026-07-06
- 结论：
  - OKX 官方更新日志说明 `https://openapi.okx.com` 是 OKX Global 用户推荐的 REST API base URL。
  - `https://www.okx.com` 仍可继续工作，不会弃用。
  - WebSocket URL `ws.okx.com`、`wspap.okx.com` 不变。
  - AWS 域名 `aws.okx.com` 已停止服务，不应作为 fallback。
- 影响代码：
  - `src/okx_quant/brokers/okx/client.py`
  - `.env.example`

## 本地 OKX 公共 WebSocket smoke test

- 来源：本机连接 `wss://ws.okx.com:8443/ws/v5/public`
- 查询日期：2026-07-05
- 结论：
  - `tickers`、`books5`、`trades` 公共频道可无密钥订阅。
  - 短采样消息可落入 SQLite `market_raw` 表。
  - 当前阶段只记录原始消息，不做订单簿增量合成。
- 影响代码：
  - `src/okx_quant/brokers/okx/ws_public.py`
  - `scripts/collect_okx_ws_public.py`

## OKX API Key 帮助中心

- 来源：https://www.okx.com/en-us/help/api-faq
- 查询日期：2026-07-05
- 结论：
  - Web 端 API Key 路径为 Profile -> API and connections -> Create API key。
  - App 端路径为 Menu -> API -> Create API key。
  - 模拟盘 API Key 路径为 Trading -> Demo Trading -> Personal Center -> Create Demo Account API key。
  - API Key 可以绑定 IP，权限包含 Read、Trade、Withdraw。
  - Passphrase 是创建 API Key 时填写的 API 口令，需要自己记住；忘记后无法找回，需要重新创建 API Key。
- 影响文档：
  - `docs/PROJECT_PLAN.md`
  - `scripts/check_okx_private.py`

## OKX 历史市场数据

- 来源：https://www.okx.com/en-sg/historical-data
- 查询日期：2026-07-05
- 结论：
  - OKX 提供 tick-level trade history、OHLC、funding rate、L2 order book 历史数据下载。
  - 一期先使用 REST 历史 K 线，后续可引入 L2 数据做更真实的滑点模型。
- 影响文档：
  - `docs/PROJECT_PLAN.md`

## TradingView 官方文档

- 来源：https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/
- 来源：https://www.tradingview.com/pine-script-docs/faq/alerts/
- 查询日期：2026-07-05
- 结论：
  - Webhook 只接受 80/443 端口。
  - 服务器处理超过 3 秒请求会被取消。
  - Webhook 可能偶发无法送达。
  - 3 分钟内超过 15 个 alert 会被暂停。
  - Strategy Tester 会展示 commission、slippage 等策略属性；回测必须显式模拟成本，避免收益虚高。
- 影响决策：
  - TradingView 只作为研究和辅助告警，不作为核心执行主源。

## OKX 交易费率规则

- 来源：https://www.okx.com/en-us/help/trading-fee-rules-faq
- 来源：https://www.okx.com/en-us/fees
- 查询日期：2026-07-05
- 结论：
  - Maker 是进入订单簿且没有立即成交的订单。
  - Taker 是立即和订单簿已有订单成交的订单。
  - 市价单通常按 taker 处理。
  - 限价单如果立即成交也按 taker 处理，只有挂入订单簿后成交才是 maker。
  - 第一版回测默认按 taker 成本做保守估算。
- 影响代码：
  - `src/okx_quant/backtest/cost_model.py`
  - `src/okx_quant/backtest/engine.py`

## OKX 下单字段和订单状态

- 来源：https://app.okx.com/docs-v5/zh/
- 来源：https://www.okx.com/docs-v5/en/
- 来源：https://www.okx.com/docs-v5/trick_en/
- 查询日期：2026-07-05
- 结论：
  - 下单接口路径为 `POST /api/v5/trade/order`。
  - 撤单接口路径为 `POST /api/v5/trade/cancel-order`。
  - 订单查询路径为 `GET /api/v5/trade/order`。
  - 现货交易模式使用 `tdMode="cash"`。
  - `clOrdId` 是用户自定义订单 ID，可用于查询、撤单和改单；在当前未完成订单中必须唯一。
  - `limit` 订单需要 `sz` 和 `px`。
  - 现货买卖限价单的 `sz` 是 base currency 数量。
  - `post_only` 只能提供流动性，若会立即成交则取消。
  - `ioc` 立即成交并取消剩余未成交数量。
  - `fok` 不能完全成交则直接取消。
  - 撤单接口返回成功只代表撤单请求被接受，最终状态以订单频道或订单查询为准。
  - 订单 WebSocket 中 `partially_filled` 和 `filled` 分别表示部分成交和完全成交。
  - 订单终态包括 `filled` 和 `canceled`。
  - `post_only`、`IOC` 等订单可能出现 `live -> canceled` 或 `live -> partially_filled -> canceled`，本地 OMS 不能只把 `canceled` 理解为本地主动撤单完成。
  - 私有 WebSocket 登录签名使用 `timestamp + GET + /users/self/verify`，timestamp 为 Unix 秒级时间戳。
  - 订单频道订阅使用 `{"channel":"orders","instType":"ANY"}` 或指定产品类型/产品 ID。
  - 订单频道不会在订阅时推送未完成订单初始快照，只会在订单状态变化时推送。
  - 如果需要订阅前的未完成订单，应调用 `GET /api/v5/trade/orders-pending`。
  - `GET /api/v5/trade/orders-pending` 只返回 `live` 和 `partially_filled`。
  - `GET /api/v5/trade/orders-history` 返回 `filled`、`canceled` 等历史订单。
  - `GET /api/v5/trade/fills` 返回成交明细。
  - `GET /api/v5/account/bills` 返回会导致账户余额变化的账单流水。
- 影响代码：
  - `src/okx_quant/brokers/okx/orders.py`
  - `src/okx_quant/brokers/okx/client.py`
  - `src/okx_quant/execution/order_sizer.py`
  - `scripts/preview_okx_order.py`
  - `scripts/demo_place_cancel_order.py`
  - `scripts/preview_pretrade_flow.py`
  - `src/okx_quant/brokers/okx/ws_private.py`
  - `scripts/check_okx_private_ws.py`
  - `scripts/snapshot_okx_reconciliation_sources.py`
  - `scripts/run_demo_rebalance_executor.py`
  - `src/okx_quant/oms/state_machine.py`
  - `src/okx_quant/risk/pre_trade.py`

## 成熟开源项目

- vectorbt：https://vectorbt.dev/
  - 结论：官方文档说明 vectorbt 基于 pandas/NumPy，适合快速分析大量参数、资产和时间切片。
  - 当前状态：本机 Python 3.13 环境安装 `vectorbt` 超过 180 秒未完成，尚未作为已验证交叉验证来源。后续建议在 Python 3.11 专用研究环境中验证。
- backtesting.py：https://kernc.github.io/backtesting.py/
  - 结论：官方文档说明 backtesting.py 使用 OHLC DataFrame 和 `Strategy` 子类运行单资产策略；`Backtest` 支持 `commission`、`spread`、`trade_on_close`、`exclusive_orders`、`finalize_trades` 等参数。
  - 结论：官方文档提示如果要交易 BTC 等小数单位资产，应使用 `backtesting.lib.FractionalBacktest`；其 `fractional_unit` 表示最小可交易单位，默认约等于一个 satoshi。
  - 结论：`Strategy.buy(size=...)` 中 `0 < size < 1` 表示按当前可用流动性比例下单，适合用来表达低频趋势过滤的接近满仓/空仓切换。
  - 当前状态：本机安装 `backtesting==0.6.5` 成功，用 `FractionalBacktest` 做单资产趋势过滤结果交叉验证。普通 `Backtest` 会在 BTC 这类高单价资产的小资金回测中产生整数单位约束扭曲，已在测试中覆盖。
- Freqtrade：https://github.com/freqtrade/freqtrade
  - 结论：成熟 crypto bot 通常包含 dry-run、backtesting、money management、WebUI/Telegram 管理，并建议先 dry-run。
- Hummingbot：https://github.com/hummingbot/hummingbot
  - 结论：成熟交易框架通过 connector 抽象 REST、WebSocket、订单、余额和行情。
- NautilusTrader：https://github.com/nautechsystems/nautilus_trader
  - 结论：生产级交易引擎强调事件驱动、订单管理、风控、回测与实盘语义一致。
- Jesse：https://github.com/jesse-ai/jesse
  - 结论：成熟策略框架会把 partial fills、risk management、metrics 作为核心能力。
- 查询日期：2026-07-05
- 影响设计：
  - `docs/ARCHITECTURE.md`
  - `src/okx_quant/backtest/backtestingpy_adapter.py`
  - `src/okx_quant/oms/state_machine.py`
  - `src/okx_quant/risk/pre_trade.py`
