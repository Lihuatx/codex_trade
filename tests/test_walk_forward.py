from decimal import Decimal
import unittest

from okx_quant.backtest.walk_forward import rolling_windows, slice_window, decimal_metric


class DummyReport:
    def __init__(self, value: str | None) -> None:
        self.value = value

    def as_dict(self) -> dict[str, object]:
        return {"total_return": self.value, "trades": []}


class WalkForwardTests(unittest.TestCase):
    def test_rolling_windows(self) -> None:
        windows = rolling_windows(10, train_size=4, test_size=2, step_size=2)

        self.assertEqual(len(windows), 3)
        self.assertEqual(windows[0].train_start, 0)
        self.assertEqual(windows[0].test_end, 6)
        self.assertEqual(windows[-1].train_start, 4)
        self.assertEqual(windows[-1].test_end, 10)

    def test_slice_window(self) -> None:
        window = rolling_windows(6, train_size=3, test_size=2, step_size=1)[0]
        train, test = slice_window([1, 2, 3, 4, 5, 6], window)

        self.assertEqual(train, [1, 2, 3])
        self.assertEqual(test, [4, 5])

    def test_decimal_metric_handles_none(self) -> None:
        self.assertEqual(decimal_metric(DummyReport("0.12"), "total_return"), Decimal("0.12"))
        self.assertEqual(decimal_metric(DummyReport(None), "total_return"), Decimal("-Infinity"))


if __name__ == "__main__":
    unittest.main()
