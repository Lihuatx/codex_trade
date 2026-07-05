# OKX 量化系统一期计划

## 定位

第一期是交易系统验证，不是收益承诺。目标是在 OKX 模拟盘和 300U 小资金实盘中验证：

- 行情能持续接入和恢复。
- 策略只输出意图，不直接下单。
- 风控能拒绝危险订单。
- OMS 能处理订单生命周期。
- 本地账本能和交易所账单对上。
- 实盘摩擦成本能进入回测和复盘。

## 交易边界

- 只做现货：`BTC-USDT`、`ETH-USDT`。
- 不做合约、杠杆、期权、网格马丁、跨所套利。
- 模拟盘跑通后再进入实盘。
- 实盘额度上限为 300 USDT。
- 单笔实盘初始上限 20 USDT。

## 一期阶段

1. 系统规格：数据表、订单状态机、成本模型、风控规则。
2. 只读行情：OKX REST + WebSocket，K 线只用已完成数据。
3. 回测：benchmark、阈值再平衡、低频趋势过滤。
4. 模拟盘：下单、撤单、部分成交、重启恢复。
5. 对账：订单、成交、手续费、余额。
6. 实盘：先 read-only，再小单，再扩展到 300U 暴露上限。

## API Key 获取

模拟盘：

```text
OKX -> Trading -> Demo Trading -> Personal Center -> Create Demo Account API key
```

实盘：

```text
OKX Web -> Profile -> API and connections -> Create API key
OKX App -> Menu -> API -> Create API key
```

权限只选 `Read + Trade`，不要选 `Withdraw`。实盘建议使用专用子账户，并尽量绑定服务器 IP。

Passphrase 是创建 API Key 时你自己填写的 API 口令，不是系统生成的 Secret Key。详情页通常不会再次显示 Passphrase；如果忘记，只能重新创建一组 API Key。
