"""Walk-forward window helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, Sequence, TypeVar


T = TypeVar("T")


class DictReport(Protocol):
    def as_dict(self) -> dict[str, object]:
        ...


@dataclass(frozen=True)
class WalkForwardWindow:
    index: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int

    @property
    def train_count(self) -> int:
        return self.train_end - self.train_start

    @property
    def test_count(self) -> int:
        return self.test_end - self.test_start


def rolling_windows(
    total_count: int,
    *,
    train_size: int,
    test_size: int,
    step_size: int | None = None,
) -> list[WalkForwardWindow]:
    if train_size <= 0:
        raise ValueError("train_size must be positive")
    if test_size <= 0:
        raise ValueError("test_size must be positive")
    step = step_size or test_size
    if step <= 0:
        raise ValueError("step_size must be positive")

    windows: list[WalkForwardWindow] = []
    start = 0
    index = 0
    while start + train_size + test_size <= total_count:
        train_end = start + train_size
        test_end = train_end + test_size
        windows.append(WalkForwardWindow(index, start, train_end, train_end, test_end))
        start += step
        index += 1
    return windows


def slice_window(items: Sequence[T], window: WalkForwardWindow) -> tuple[list[T], list[T]]:
    return (
        list(items[window.train_start : window.train_end]),
        list(items[window.test_start : window.test_end]),
    )


def compact_report(report: DictReport) -> dict[str, object]:
    data = report.as_dict()
    data.pop("trades", None)
    return data


def decimal_metric(report: DictReport, key: str) -> Decimal:
    data = report.as_dict()
    value = data[key]
    if value is None:
        return Decimal("-Infinity")
    return Decimal(str(value))
