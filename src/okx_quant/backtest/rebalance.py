"""Multi-asset threshold rebalancing backtest."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from okx_quant.backtest.cost_model import ExecutionCostModel
from okx_quant.domain.enums import OrderSide
from okx_quant.domain.market import Candle


@dataclass(frozen=True)
class RebalanceTrade:
    ts: str
    asset: str
    side: str
    price: Decimal
    size: Decimal
    notional: Decimal
    fee: Decimal
    reason: str

    def as_dict(self) -> dict[str, str]:
        return {
            "ts": self.ts,
            "asset": self.asset,
            "side": self.side,
            "price": str(self.price),
            "size": str(self.size),
            "notional": str(self.notional),
            "fee": str(self.fee),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class RebalanceReport:
    strategy: str
    assets: tuple[str, ...]
    bar: str
    initial_cash: Decimal
    final_equity: Decimal
    net_pnl: Decimal
    total_return: Decimal
    total_fee: Decimal
    turnover: Decimal
    max_drawdown: Decimal
    number_of_trades: int
    fee_to_gross_pnl: Decimal | None
    average_trade_edge: Decimal | None
    first_ts: str
    last_ts: str
    target_weights: dict[str, Decimal]
    trades: list[RebalanceTrade] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "strategy": self.strategy,
            "assets": list(self.assets),
            "bar": self.bar,
            "initial_cash": str(self.initial_cash),
            "final_equity": str(self.final_equity),
            "net_pnl": str(self.net_pnl),
            "total_return": str(self.total_return),
            "total_fee": str(self.total_fee),
            "turnover": str(self.turnover),
            "max_drawdown": str(self.max_drawdown),
            "number_of_trades": self.number_of_trades,
            "fee_to_gross_pnl": _decimal_or_none(self.fee_to_gross_pnl),
            "average_trade_edge": _decimal_or_none(self.average_trade_edge),
            "first_ts": self.first_ts,
            "last_ts": self.last_ts,
            "target_weights": {asset: str(weight) for asset, weight in self.target_weights.items()},
            "trades": [trade.as_dict() for trade in self.trades],
        }


class ThresholdRebalanceBacktest:
    def __init__(self, cost_model: ExecutionCostModel) -> None:
        self._cost_model = cost_model

    def run(
        self,
        candles_by_asset: dict[str, list[Candle]],
        *,
        target_weights: dict[str, Decimal],
        threshold: Decimal,
        initial_cash: Decimal,
        min_trade_notional: Decimal = Decimal("10"),
    ) -> RebalanceReport:
        _validate_target_weights(target_weights)
        if "USDT" not in target_weights:
            raise ValueError("target_weights must include USDT")
        if threshold <= 0:
            raise ValueError("threshold must be positive")

        aligned = align_candles(candles_by_asset)
        if not aligned:
            raise ValueError("no aligned candles")

        assets = tuple(asset for asset in target_weights if asset != "USDT")
        state = _RebalanceState(cash=initial_cash, positions={asset: Decimal("0") for asset in assets})
        equity_curve: list[Decimal] = []

        for index, row in enumerate(aligned):
            prices = {asset: row[asset].close for asset in assets}
            equity = state.equity(prices)
            current_weights = state.weights(prices)
            should_rebalance = index == 0 or any(
                abs(current_weights.get(asset, Decimal("0")) - weight) >= threshold
                for asset, weight in target_weights.items()
            )
            if should_rebalance:
                _rebalance_once(
                    state,
                    row_ts=next(iter(row.values())).ts.isoformat(),
                    prices=prices,
                    target_weights=target_weights,
                    min_trade_notional=min_trade_notional,
                    cost_model=self._cost_model,
                )
            equity_curve.append(state.equity(prices))

        final_prices = {asset: aligned[-1][asset].close for asset in assets}
        final_equity = state.equity(final_prices)
        net_pnl = final_equity - initial_cash
        gross_pnl = net_pnl + state.total_fee
        return RebalanceReport(
            strategy="threshold_rebalance",
            assets=assets,
            bar=next(iter(candles_by_asset.values()))[0].bar,
            initial_cash=initial_cash,
            final_equity=final_equity,
            net_pnl=net_pnl,
            total_return=net_pnl / initial_cash if initial_cash else Decimal("0"),
            total_fee=state.total_fee,
            turnover=state.turnover,
            max_drawdown=_max_drawdown(equity_curve),
            number_of_trades=len(state.trades),
            fee_to_gross_pnl=(state.total_fee / abs(gross_pnl)) if gross_pnl != 0 else None,
            average_trade_edge=(net_pnl / state.turnover) if state.turnover else None,
            first_ts=next(iter(aligned[0].values())).ts.isoformat(),
            last_ts=next(iter(aligned[-1].values())).ts.isoformat(),
            target_weights=target_weights,
            trades=state.trades,
        )


def align_candles(candles_by_asset: dict[str, list[Candle]]) -> list[dict[str, Candle]]:
    by_asset_ts = {
        asset: {candle.ts: candle for candle in candles}
        for asset, candles in candles_by_asset.items()
    }
    common_ts: set[object] | None = None
    for rows in by_asset_ts.values():
        keys = set(rows)
        common_ts = keys if common_ts is None else common_ts & keys
    if not common_ts:
        return []
    return [
        {asset: rows[ts] for asset, rows in by_asset_ts.items()}
        for ts in sorted(common_ts)
    ]


@dataclass
class _RebalanceState:
    cash: Decimal
    positions: dict[str, Decimal]
    total_fee: Decimal = Decimal("0")
    turnover: Decimal = Decimal("0")
    trades: list[RebalanceTrade] = field(default_factory=list)

    def equity(self, prices: dict[str, Decimal]) -> Decimal:
        return self.cash + sum(self.positions[asset] * prices[asset] for asset in self.positions)

    def weights(self, prices: dict[str, Decimal]) -> dict[str, Decimal]:
        equity = self.equity(prices)
        if equity <= 0:
            return {"USDT": Decimal("0"), **{asset: Decimal("0") for asset in self.positions}}
        weights = {"USDT": self.cash / equity}
        weights.update({asset: self.positions[asset] * prices[asset] / equity for asset in self.positions})
        return weights


def _rebalance_once(
    state: _RebalanceState,
    *,
    row_ts: str,
    prices: dict[str, Decimal],
    target_weights: dict[str, Decimal],
    min_trade_notional: Decimal,
    cost_model: ExecutionCostModel,
) -> None:
    equity = state.equity(prices)
    target_values = {asset: equity * weight for asset, weight in target_weights.items()}

    for asset, position in list(state.positions.items()):
        current_value = position * prices[asset]
        target_value = target_values.get(asset, Decimal("0"))
        excess = current_value - target_value
        if excess >= min_trade_notional:
            _sell_asset(state, row_ts, asset, excess, prices[asset], cost_model, "threshold_rebalance")

    equity = state.equity(prices)
    target_values = {asset: equity * weight for asset, weight in target_weights.items()}
    for asset in state.positions:
        current_value = state.positions[asset] * prices[asset]
        target_value = target_values.get(asset, Decimal("0"))
        deficit = target_value - current_value
        if deficit >= min_trade_notional:
            _buy_asset(state, row_ts, asset, deficit, prices[asset], cost_model, "threshold_rebalance")


def _buy_asset(
    state: _RebalanceState,
    ts: str,
    asset: str,
    target_notional: Decimal,
    reference_price: Decimal,
    cost_model: ExecutionCostModel,
    reason: str,
) -> None:
    available_notional = state.cash / (Decimal("1") + cost_model.taker_fee_rate)
    notional = min(target_notional, available_notional)
    if notional <= 0:
        return
    fill_price = cost_model.fill_price(OrderSide.BUY, reference_price)
    fee = cost_model.fee(notional)
    size = notional / fill_price
    state.cash -= notional + fee
    state.positions[asset] += size
    state.total_fee += fee
    state.turnover += notional
    state.trades.append(RebalanceTrade(ts, asset, OrderSide.BUY.value, fill_price, size, notional, fee, reason))


def _sell_asset(
    state: _RebalanceState,
    ts: str,
    asset: str,
    target_notional: Decimal,
    reference_price: Decimal,
    cost_model: ExecutionCostModel,
    reason: str,
) -> None:
    fill_price = cost_model.fill_price(OrderSide.SELL, reference_price)
    max_notional = state.positions[asset] * fill_price
    notional = min(target_notional, max_notional)
    if notional <= 0:
        return
    size = notional / fill_price
    fee = cost_model.fee(notional)
    state.positions[asset] -= size
    state.cash += notional - fee
    state.total_fee += fee
    state.turnover += notional
    state.trades.append(RebalanceTrade(ts, asset, OrderSide.SELL.value, fill_price, size, notional, fee, reason))


def _validate_target_weights(target_weights: dict[str, Decimal]) -> None:
    total = sum(target_weights.values(), Decimal("0"))
    if total != Decimal("1"):
        raise ValueError(f"target weights must sum to 1, got {total}")
    if any(weight < 0 for weight in target_weights.values()):
        raise ValueError("target weights cannot be negative")


def _max_drawdown(equity_curve: list[Decimal]) -> Decimal:
    peak: Decimal | None = None
    max_dd = Decimal("0")
    for equity in equity_curve:
        if peak is None or equity > peak:
            peak = equity
        if peak and peak > 0:
            drawdown = (peak - equity) / peak
            if drawdown > max_dd:
                max_dd = drawdown
    return max_dd


def _decimal_or_none(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None

