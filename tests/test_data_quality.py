from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from okx_quant.data_quality import bar_to_timedelta, validate_candles
from okx_quant.domain.market import Candle


class DataQualityTests(unittest.TestCase):
    def test_bar_to_timedelta(self) -> None:
        self.assertEqual(bar_to_timedelta("1m"), timedelta(minutes=1))
        self.assertEqual(bar_to_timedelta("4H"), timedelta(hours=4))
        self.assertEqual(bar_to_timedelta("1D"), timedelta(days=1))

    def test_valid_candles_have_no_issues(self) -> None:
        candles = [_candle(0), _candle(1)]

        self.assertEqual(validate_candles(candles, bar="1H"), [])

    def test_detects_unconfirmed_and_gap(self) -> None:
        candles = [_candle(0), _candle(3, confirm=False)]

        issues = validate_candles(candles, bar="1H")

        self.assertIn("unconfirmed_candle", {issue.code for issue in issues})
        self.assertIn("missing_candle_gap", {issue.code for issue in issues})

    def test_detects_inconsistent_ohlc(self) -> None:
        candle = _candle(0, high=Decimal("99"))

        issues = validate_candles([candle], bar="1H")

        self.assertIn("ohlc_inconsistent", {issue.code for issue in issues})


def _candle(hour: int, *, high: Decimal = Decimal("101"), confirm: bool = True) -> Candle:
    close = Decimal("100")
    return Candle(
        inst_id="BTC-USDT",
        bar="1H",
        ts=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(hours=hour),
        open=close,
        high=high,
        low=Decimal("99"),
        close=close,
        volume=Decimal("1"),
        volume_ccy=Decimal("1"),
        volume_ccy_quote=None,
        confirm=confirm,
    )


if __name__ == "__main__":
    unittest.main()

