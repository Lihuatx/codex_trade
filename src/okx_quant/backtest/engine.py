"""Minimal long-only backtest engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from okx_quant.backtest.cost_model import ExecutionCostModel
from okx_quant.domain.enums import OrderSide
from okx_quant.domain.market import Candle


@dataclass(frozen=True)
class BacktestTrade:
    ts: str
    side: str
    price: Decimal
    size: Decimal
    notional: Decimal
    fee: Decimal
    reason: str

    def as_dict(self) -> dict[str, str]:
        return {
            "ts": self.ts,
            "side": self.side,
            "price": str(self.price),
            "size": str(self.size),
            "notional": str(self.notional),
            "fee": str(self.fee),
            "reason": self.reason,
        }


@dataclass
class BacktestReport:
    strategy: str
    inst_id: str
    bar: str
    initial_cash: Decimal
    final_equity: Decimal
    gross_pnl: Decimal
    net_pnl: Decimal
    total_fee: Decimal
    turnover: Decimal
    max_drawdown: Decimal
    number_of_trades: int
    exposure_time: Decimal
    total_return: Decimal
    fee_to_gross_pnl: Decimal | None
    average_trade_edge: Decimal | None
    win_rate: Decimal | None
    profit_factor: Decimal | None
    average_win: Decimal | None
    average_loss: Decimal | None
    max_consecutive_losses: int
    first_ts: str
    last_ts: str
    trades: list[BacktestTrade] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "strategy": self.strategy,
            "inst_id": self.inst_id,
            "bar": self.bar,
            "initial_cash": str(self.initial_cash),
            "final_equity": str(self.final_equity),
            "gross_pnl": str(self.gross_pnl),
            "net_pnl": str(self.net_pnl),
            "total_fee": str(self.total_fee),
            "turnover": str(self.turnover),
            "max_drawdown": str(self.max_drawdown),
            "number_of_trades": self.number_of_trades,
            "exposure_time": str(self.exposure_time),
            "total_return": str(self.total_return),
            "fee_to_gross_pnl": _decimal_or_none(self.fee_to_gross_pnl),
            "average_trade_edge": _decimal_or_none(self.average_trade_edge),
            "win_rate": _decimal_or_none(self.win_rate),
            "profit_factor": _decimal_or_none(self.profit_factor),
            "average_win": _decimal_or_none(self.average_win),
            "average_loss": _decimal_or_none(self.average_loss),
            "max_consecutive_losses": self.max_consecutive_losses,
            "first_ts": self.first_ts,
            "last_ts": self.last_ts,
            "trades": [trade.as_dict() for trade in self.trades],
        }


class BacktestEngine:
    def __init__(self, cost_model: ExecutionCostModel) -> None:
        self._cost_model = cost_model

    def run_buy_and_hold(self, candles: list[Candle], initial_cash: Decimal) -> BacktestReport:
        if not candles:
            raise ValueError("candles cannot be empty")
        state = _BacktestState(cash=initial_cash)
        self._buy_all(state, candles[0], "initial_buy")
        equity_curve = [state.equity(candle.close) for candle in candles]
        return self._report("buy_and_hold", candles, initial_cash, state, equity_curve, exposure_count=len(candles))

    def run_trend_filter(
        self,
        candles: list[Candle],
        initial_cash: Decimal,
        ma_window: int,
    ) -> BacktestReport:
        if ma_window < 2:
            raise ValueError("ma_window must be at least 2")
        if len(candles) < ma_window:
            raise ValueError("not enough candles for ma_window")

        state = _BacktestState(cash=initial_cash)
        equity_curve: list[Decimal] = []
        exposure_count = 0
        closes: list[Decimal] = []

        for candle in candles:
            closes.append(candle.close)
            if len(closes) >= ma_window:
                moving_average = sum(closes[-ma_window:], Decimal("0")) / Decimal(ma_window)
                if candle.close > moving_average and state.position <= 0:
                    self._buy_all(state, candle, "close_above_ma")
                elif candle.close < moving_average and state.position > 0:
                    self._sell_all(state, candle, "close_below_ma")
            if state.position > 0:
                exposure_count += 1
            equity_curve.append(state.equity(candle.close))

        return self._report("trend_filter", candles, initial_cash, state, equity_curve, exposure_count)

    def _buy_all(self, state: "_BacktestState", candle: Candle, reason: str) -> None:
        if state.cash <= 0:
            return
        notional = state.cash / (Decimal("1") + self._cost_model.taker_fee_rate)
        fill_price = self._cost_model.fill_price(OrderSide.BUY, candle.close)
        size = notional / fill_price
        fee = self._cost_model.fee(notional)
        state.cash -= notional + fee
        state.position += size
        state.total_fee += fee
        state.turnover += notional
        state.trades.append(
            BacktestTrade(
                ts=candle.ts.isoformat(),
                side=OrderSide.BUY.value,
                price=fill_price,
                size=size,
                notional=notional,
                fee=fee,
                reason=reason,
            )
        )

    def _sell_all(self, state: "_BacktestState", candle: Candle, reason: str) -> None:
        if state.position <= 0:
            return
        fill_price = self._cost_model.fill_price(OrderSide.SELL, candle.close)
        notional = state.position * fill_price
        fee = self._cost_model.fee(notional)
        size = state.position
        state.cash += notional - fee
        state.position = Decimal("0")
        state.total_fee += fee
        state.turnover += notional
        state.trades.append(
            BacktestTrade(
                ts=candle.ts.isoformat(),
                side=OrderSide.SELL.value,
                price=fill_price,
                size=size,
                notional=notional,
                fee=fee,
                reason=reason,
            )
        )

    def _report(
        self,
        strategy: str,
        candles: list[Candle],
        initial_cash: Decimal,
        state: "_BacktestState",
        equity_curve: list[Decimal],
        exposure_count: int,
    ) -> BacktestReport:
        final_equity = state.equity(candles[-1].close)
        gross_pnl = final_equity - initial_cash + state.total_fee
        net_pnl = final_equity - initial_cash
        closed_trade_stats = _closed_trade_stats(state.trades)
        return BacktestReport(
            strategy=strategy,
            inst_id=candles[0].inst_id,
            bar=candles[0].bar,
            initial_cash=initial_cash,
            final_equity=final_equity,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            total_fee=state.total_fee,
            turnover=state.turnover,
            max_drawdown=_max_drawdown(equity_curve),
            number_of_trades=len(state.trades),
            exposure_time=Decimal(exposure_count) / Decimal(len(candles)),
            total_return=net_pnl / initial_cash if initial_cash else Decimal("0"),
            fee_to_gross_pnl=_fee_to_gross_pnl(state.total_fee, gross_pnl),
            average_trade_edge=net_pnl / state.turnover if state.turnover else None,
            win_rate=closed_trade_stats.win_rate,
            profit_factor=closed_trade_stats.profit_factor,
            average_win=closed_trade_stats.average_win,
            average_loss=closed_trade_stats.average_loss,
            max_consecutive_losses=closed_trade_stats.max_consecutive_losses,
            first_ts=candles[0].ts.isoformat(),
            last_ts=candles[-1].ts.isoformat(),
            trades=state.trades,
        )


@dataclass
class _BacktestState:
    cash: Decimal
    position: Decimal = Decimal("0")
    total_fee: Decimal = Decimal("0")
    turnover: Decimal = Decimal("0")
    trades: list[BacktestTrade] = field(default_factory=list)

    def equity(self, mark_price: Decimal) -> Decimal:
        return self.cash + self.position * mark_price


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


@dataclass(frozen=True)
class _ClosedTradeStats:
    win_rate: Decimal | None
    profit_factor: Decimal | None
    average_win: Decimal | None
    average_loss: Decimal | None
    max_consecutive_losses: int


def _closed_trade_stats(trades: list[BacktestTrade]) -> _ClosedTradeStats:
    round_trip_pnls: list[Decimal] = []
    open_buy_cost: Decimal | None = None
    for trade in trades:
        if trade.side == OrderSide.BUY.value:
            open_buy_cost = trade.notional + trade.fee
        elif trade.side == OrderSide.SELL.value and open_buy_cost is not None:
            round_trip_pnls.append(trade.notional - trade.fee - open_buy_cost)
            open_buy_cost = None

    if not round_trip_pnls:
        return _ClosedTradeStats(None, None, None, None, 0)

    wins = [pnl for pnl in round_trip_pnls if pnl > 0]
    losses = [pnl for pnl in round_trip_pnls if pnl < 0]
    gross_win = sum(wins, Decimal("0"))
    gross_loss_abs = abs(sum(losses, Decimal("0")))
    return _ClosedTradeStats(
        win_rate=Decimal(len(wins)) / Decimal(len(round_trip_pnls)),
        profit_factor=(gross_win / gross_loss_abs) if gross_loss_abs > 0 else None,
        average_win=(gross_win / Decimal(len(wins))) if wins else None,
        average_loss=(sum(losses, Decimal("0")) / Decimal(len(losses))) if losses else None,
        max_consecutive_losses=_max_consecutive_losses(round_trip_pnls),
    )


def _max_consecutive_losses(pnls: list[Decimal]) -> int:
    current = 0
    worst = 0
    for pnl in pnls:
        if pnl < 0:
            current += 1
            worst = max(worst, current)
        else:
            current = 0
    return worst


def _fee_to_gross_pnl(total_fee: Decimal, gross_pnl: Decimal) -> Decimal | None:
    if gross_pnl == 0:
        return None
    return total_fee / abs(gross_pnl)


def _decimal_or_none(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None
