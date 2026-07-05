from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from okx_quant.backtest.cost_model import ExecutionCostModel
from okx_quant.backtest.engine import BacktestEngine
from okx_quant.domain.enums import OrderSide
from okx_quant.domain.market import Candle


class CostModelTests(unittest.TestCase):
    def test_fill_price_applies_directional_slippage(self) -> None:
        model = ExecutionCostModel(taker_fee_bps=Decimal("10"), slippage_bps=Decimal("5"))

        self.assertEqual(model.fill_price(OrderSide.BUY, Decimal("100")), Decimal("100.0500"))
        self.assertEqual(model.fill_price(OrderSide.SELL, Decimal("100")), Decimal("99.9500"))
        self.assertEqual(model.fee(Decimal("1000")), Decimal("1.000"))


class BacktestEngineTests(unittest.TestCase):
    def test_buy_and_hold_reports_fee_and_trade(self) -> None:
        candles = _candles([Decimal("100"), Decimal("110")])
        engine = BacktestEngine(ExecutionCostModel(Decimal("10"), Decimal("0")))

        report = engine.run_buy_and_hold(candles, Decimal("1000"))

        self.assertEqual(report.number_of_trades, 1)
        self.assertGreater(report.total_fee, Decimal("0"))
        self.assertGreater(report.final_equity, Decimal("1000"))
        self.assertEqual(report.win_rate, None)
        self.assertGreater(report.total_return, Decimal("0"))

    def test_trend_filter_trades_on_ma_crosses(self) -> None:
        candles = _candles(
            [
                Decimal("100"),
                Decimal("101"),
                Decimal("102"),
                Decimal("103"),
                Decimal("99"),
                Decimal("98"),
            ]
        )
        engine = BacktestEngine(ExecutionCostModel(Decimal("10"), Decimal("0")))

        report = engine.run_trend_filter(candles, Decimal("1000"), ma_window=3)

        self.assertGreaterEqual(report.number_of_trades, 2)
        self.assertGreater(report.total_fee, Decimal("0"))
        self.assertIsNotNone(report.win_rate)
        self.assertIsNotNone(report.average_trade_edge)


def _candles(closes: list[Decimal]) -> list[Candle]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        Candle(
            inst_id="BTC-USDT",
            bar="1H",
            ts=start + timedelta(hours=i),
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
