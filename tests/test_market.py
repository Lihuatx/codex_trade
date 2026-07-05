from decimal import Decimal
import unittest

from okx_quant.domain.market import (
    only_confirmed,
    parse_okx_candle_row,
    parse_okx_order_book_top,
    parse_okx_ticker_last,
)


class CandleParsingTests(unittest.TestCase):
    def test_parse_nine_field_okx_candle(self) -> None:
        candle = parse_okx_candle_row(
            "BTC-USDT",
            "1H",
            [
                "1597026383085",
                "3.721",
                "3.743",
                "3.677",
                "3.708",
                "8422410",
                "22698348.04828491",
                "12698348.04828491",
                "1",
            ],
        )

        self.assertTrue(candle.confirm)
        self.assertEqual(candle.close, Decimal("3.708"))
        self.assertEqual(candle.volume_ccy_quote, Decimal("12698348.04828491"))

    def test_parse_eight_field_okx_candle(self) -> None:
        candle = parse_okx_candle_row(
            "BTC-USDT",
            "1H",
            [
                "1597026383085",
                "3.721",
                "3.743",
                "3.677",
                "3.708",
                "8422410",
                "22698348.04828491",
                "0",
            ],
        )

        self.assertFalse(candle.confirm)
        self.assertIsNone(candle.volume_ccy_quote)

    def test_only_confirmed_filters_open_candles(self) -> None:
        closed = parse_okx_candle_row(
            "BTC-USDT",
            "1H",
            ["1", "1", "1", "1", "1", "1", "1", "1"],
        )
        open_ = parse_okx_candle_row(
            "BTC-USDT",
            "1H",
            ["1", "1", "1", "1", "1", "1", "1", "0"],
        )

        self.assertEqual(only_confirmed([closed, open_]), [closed])

    def test_parse_ticker_last_and_order_book_top(self) -> None:
        self.assertEqual(parse_okx_ticker_last({"data": [{"last": "100.1"}]}), Decimal("100.1"))
        self.assertEqual(
            parse_okx_order_book_top({"data": [{"bids": [["99.9", "1"]], "asks": [["100.2", "1"]]}]}),
            (Decimal("99.9"), Decimal("100.2")),
        )


if __name__ == "__main__":
    unittest.main()
