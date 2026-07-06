"""Cross-validation helpers using backtesting.py.

This adapter is intentionally scoped to single-asset OHLC strategies. It is
used to compare broad behavior against the in-house low-frequency backtester,
not to assert penny-identical fills.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
from backtesting import Strategy
from backtesting.lib import FractionalBacktest

from okx_quant.domain.market import Candle


def candles_to_ohlcv(candles: list[Candle]) -> pd.DataFrame:
    rows = [
        {
            "Open": float(candle.open),
            "High": float(candle.high),
            "Low": float(candle.low),
            "Close": float(candle.close),
            "Volume": float(candle.volume),
            "ts": candle.ts,
        }
        for candle in candles
    ]
    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError("candles cannot be empty")
    df = df.set_index(pd.DatetimeIndex(df.pop("ts")))
    return df


class TrendFilterBTStrategy(Strategy):
    ma_window = 200

    def init(self) -> None:
        self.ma = self.I(_rolling_mean, self.data.Close, self.ma_window)

    def next(self) -> None:
        current_ma = self.ma[-1]
        close = self.data.Close[-1]
        if pd.isna(current_ma):
            return
        if close > current_ma:
            if not self.position:
                self.buy(size=0.999)
        elif self.position:
            self.position.close()


def run_backtestingpy_trend_filter(
    candles: list[Candle],
    *,
    initial_cash: Decimal,
    ma_window: int,
    taker_fee_bps: Decimal,
    slippage_bps: Decimal,
    fractional_unit: Decimal = Decimal("0.00000001"),
) -> dict[str, Any]:
    df = candles_to_ohlcv(candles)
    commission = float(taker_fee_bps / Decimal("10000"))
    spread = float(slippage_bps / Decimal("10000"))
    bt = FractionalBacktest(
        df,
        TrendFilterBTStrategy,
        cash=float(initial_cash),
        commission=commission,
        spread=spread,
        trade_on_close=True,
        exclusive_orders=True,
        finalize_trades=True,
        fractional_unit=float(fractional_unit),
    )
    stats = bt.run(ma_window=ma_window)
    return {
        "engine": "backtesting.py",
        "ma_window": ma_window,
        "initial_cash": str(initial_cash),
        "fractional_unit": str(fractional_unit),
        "final_equity": str(stats["Equity Final [$]"]),
        "return_pct": str(stats["Return [%]"]),
        "max_drawdown_pct": str(stats["Max. Drawdown [%]"]),
        "number_of_trades": int(stats["# Trades"]),
        "win_rate_pct": str(stats["Win Rate [%]"]),
        "profit_factor": str(stats["Profit Factor"]),
        "exposure_time_pct": str(stats["Exposure Time [%]"]),
    }


def _rolling_mean(values: Any, window: int) -> np.ndarray:
    result = pd.Series(values).rolling(window).mean().to_numpy(dtype=float, copy=True)
    result.setflags(write=True)
    return result
