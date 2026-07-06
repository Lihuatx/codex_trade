from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from okx_quant.backtest.backtestingpy_adapter import (
    _rolling_mean,
    candles_to_ohlcv,
    run_backtestingpy_trend_filter,
)
from okx_quant.domain.market import Candle


class BacktestingPyAdapterTests(unittest.TestCase):
    def test_candles_to_ohlcv(self) -> None:
        df = candles_to_ohlcv(_candles([Decimal("100"), Decimal("101")]))

        self.assertEqual(list(df.columns), ["Open", "High", "Low", "Close", "Volume"])
        self.assertEqual(len(df), 2)

    def test_run_trend_filter(self) -> None:
        closes = [Decimal("100") + Decimal(i) for i in range(30)]
        result = run_backtestingpy_trend_filter(
            _candles(closes),
            initial_cash=Decimal("1000"),
            ma_window=5,
            taker_fee_bps=Decimal("10"),
            slippage_bps=Decimal("5"),
        )

        self.assertEqual(result["engine"], "backtesting.py")
        self.assertGreaterEqual(result["number_of_trades"], 0)

    def test_run_trend_filter_uses_fractional_units(self) -> None:
        closes = [Decimal("50000") + Decimal(i * 100) for i in range(30)]
        result = run_backtestingpy_trend_filter(
            _candles(closes),
            initial_cash=Decimal("300"),
            ma_window=5,
            taker_fee_bps=Decimal("10"),
            slippage_bps=Decimal("5"),
        )

        self.assertEqual(result["fractional_unit"], "1E-8")
        self.assertGreater(result["number_of_trades"], 0)

    def test_rolling_mean_returns_writeable_array(self) -> None:
        result = _rolling_mean([1, 2, 3, 4, 5], 3)

        self.assertTrue(result.flags.writeable)


def _candles(closes: list[Decimal]) -> list[Candle]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        Candle(
            inst_id="BTC-USDT",
            bar="1D",
            ts=start + timedelta(days=i),
            open=close,
            high=close,
            low=close,
            close=close,
            volume=Decimal("1"),
            volume_ccy=Decimal("1"),
            volume_ccy_quote=None,
            confirm=True,
        )
        for i, close in enumerate(closes)
    ]


if __name__ == "__main__":
    unittest.main()
