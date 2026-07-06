# ROADMAP.md

## 一期目标

用 OKX 现货模拟盘跑通交易系统闭环，然后用 300 USDT 实盘额度验证真实订单、手续费、滑点、重启恢复和对账。

## 当前进度

- [x] 初始化 Git 仓库
- [x] 建立项目治理文档
- [x] 建立一期架构和依据文档
- [x] 建立核心代码骨架
- [x] 接入 OKX 公共 REST 行情
- [x] 接入 OKX 公共 WebSocket 行情
- [x] 建立 SQLite/PostgreSQL 事件表
- [x] 建立 K 线回测和成本模型
- [x] 建立分页历史 K 线采集
- [x] 建立回测报告和参数敏感性扫描
- [x] 建立样本内/样本外回测切分
- [x] 完成 BTC/ETH 1H 与 1D 初步正式回测
- [x] 接入 backtesting.py 单资产趋势过滤交叉验证
- [x] 修正 backtesting.py 加密资产小数单位适配并补测试
- [ ] 接入 vectorbt 交叉验证研究环境
- [x] 建立 optimistic/neutral/pessimistic 成本三档
- [x] 建立趋势过滤 walk-forward 回测
- [x] 建立 BTC/ETH/USDT 阈值再平衡回测
- [x] 建立再平衡样本内/样本外切分
- [x] 建立再平衡 walk-forward 回测
- [x] 完成 300U 低风险再平衡权重对照
- [x] 产出 read-only 观测候选策略
- [x] 建立 demo account 再平衡 read-only 信号预览
- [x] 建立 demo account 再平衡 read-only 风控截断预览
- [x] 跑通 demo 自动小单执行：rebalance signal -> cap -> risk -> OMS -> OKX post_only -> cancel -> reconciliation
- [x] 建立 demo 72 小时连续运行 runner
- [x] 建立 runner JSONL 结构化日志
- [x] 建立本地 dashboard 读取 JSONL / SQLite / summary / state
- [ ] 产出通过自动交易验收的模拟盘策略
- [x] 建立 OKX 现货订单 payload 干跑
- [x] 建立本地 OMS 订单/成交落库
- [x] 建立 K 线数据质量检查
- [x] 建立风控事件审计落库
- [x] 建立本地订单状态对账模拟
- [x] 准备 OKX 模拟盘私有接口连通性检查脚本
- [x] 接入 OKX 模拟盘私有 REST
- [x] 接入 OKX 模拟盘只读私有 REST 检查
- [x] 跑通 OKX 模拟盘下单-查询-撤单 REST 闭环
- [x] 跑通预交易风控到订单 payload 预览链路
- [x] 接入 OKX 私有订单 WebSocket
- [x] 跑通 OKX 私有 WS 订单事件 `live -> canceled`
- [x] 跑通模拟盘订单生命周期
- [ ] 跑通本地账本和 OKX 账单对账
- [ ] 模拟盘连续运行 72 小时
- [ ] 300U 小资金实盘验证

## 运行中

- 2026-07-06 Asia/Shanghai 本机 demo 72 小时 runner 已由用户手动停止，运行位置切换为服务器。
- 服务器部署、实时日志和 dashboard tunnel 记录在 `docs/DEPLOYMENT.md`。
- 2026-07-06 Asia/Shanghai 服务器代码部署和测试通过，但 OKX REST 网络验收失败：REST 域名解析到不可用的 link-local 地址，绕过 DNS 后 TLS 连接仍被 reset；demo 72 小时 runner 暂不启动，等待可访问 OKX Global API 的服务器或代理。

## 对账开发进度

### R0：领域模型

- [x] 订单状态枚举
- [x] OMS 状态机
- [x] 成交、订单、交易意图基础模型
- [x] 产品精度和最小下单量规则
- [x] 现货订单数量计算

### R1：事件落库

- [x] 初始 SQL schema 草案
- [x] 原始 OKX 消息表
- [x] 标准化订单事件表
- [x] 成交事件表
- [x] 余额快照表
- [x] 风控事件表

### R2：交易所同步

- [x] 查询未完成订单
- [x] 查询单笔订单
- [x] 查询历史订单
- [x] 查询成交明细
- [x] 查询账单流水
- [x] 本地订单与交易所订单比对

### R3：对账规则

- [x] 订单状态一致性检查
- [ ] 成交数量一致性检查
- [ ] 手续费币种和金额检查
- [ ] 余额变化检查
- [ ] 对账失败进入 `reconcile_required`

### R4：实盘验收

- [x] 本地订单状态机禁止非法状态跳转
- [x] 重启后不重复下单
- [ ] 部分成交可恢复
- [x] 撤单请求和最终撤单状态可区分
- [ ] 账单与本地 ledger 可解释
- [x] 对账失败时禁止新单

## 300U 实盘风控草案

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
