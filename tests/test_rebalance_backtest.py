from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from okx_quant.backtest.cost_model import ExecutionCostModel
from okx_quant.backtest.rebalance import ThresholdRebalanceBacktest, align_candles
from okx_quant.domain.market import Candle


class RebalanceBacktestTests(unittest.TestCase):
    def test_align_candles_uses_common_timestamps(self) -> None:
        btc = _candles("BTC-USDT", [Decimal("100"), Decimal("110")])
        eth = _candles("ETH-USDT", [Decimal("10"), Decimal("11")])

        aligned = align_candles({"BTC": btc, "ETH": eth})

        self.assertEqual(len(aligned), 2)
        self.assertEqual(aligned[0]["BTC"].close, Decimal("100"))
        self.assertEqual(aligned[0]["ETH"].close, Decimal("10"))

    def test_threshold_rebalance_runs(self) -> None:
        btc = _candles("BTC-USDT", [Decimal("100"), Decimal("150"), Decimal("120"), Decimal("200")])
        eth = _candles("ETH-USDT", [Decimal("10"), Decimal("12"), Decimal("8"), Decimal("11")])
        engine = ThresholdRebalanceBacktest(ExecutionCostModel(Decimal("10"), Decimal("0")))

        report = engine.run(
            {"BTC": btc, "ETH": eth},
            target_weights={"USDT": Decimal("0.5"), "BTC": Decimal("0.25"), "ETH": Decimal("0.25")},
            threshold=Decimal("0.05"),
            initial_cash=Decimal("1000"),
            min_trade_notional=Decimal("1"),
        )

        self.assertGreater(report.number_of_trades, 0)
        self.assertGreater(report.total_fee, Decimal("0"))
        self.assertEqual(report.assets, ("BTC", "ETH"))

    def test_rejects_weights_not_summing_to_one(self) -> None:
        engine = ThresholdRebalanceBacktest(ExecutionCostModel(Decimal("10"), Decimal("0")))

        with self.assertRaises(ValueError):
            engine.run(
                {"BTC": _candles("BTC-USDT", [Decimal("100"), Decimal("101")])},
                target_weights={"USDT": Decimal("0.8"), "BTC": Decimal("0.3")},
                threshold=Decimal("0.05"),
                initial_cash=Decimal("1000"),
            )


def _candles(inst_id: str, closes: list[Decimal]) -> list[Candle]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        Candle(
            inst_id=inst_id,
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

