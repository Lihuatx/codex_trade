"""Market data quality checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from okx_quant.domain.market import Candle


@dataclass(frozen=True)
class DataQualityIssue:
    code: str
    message: str
    ts: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {"code": self.code, "message": self.message, "ts": self.ts}


def bar_to_timedelta(bar: str) -> timedelta:
    unit = bar[-1]
    value = int(bar[:-1])
    if unit == "m":
        return timedelta(minutes=value)
    if unit == "H":
        return timedelta(hours=value)
    if unit == "D":
        return timedelta(days=value)
    raise ValueError(f"Unsupported bar: {bar}")


def validate_candles(candles: list[Candle], *, bar: str) -> list[DataQualityIssue]:
    issues: list[DataQualityIssue] = []
    if not candles:
        return [DataQualityIssue("empty_series", "No candles available")]

    expected_delta = bar_to_timedelta(bar)
    previous: Candle | None = None

    for candle in candles:
        ts = candle.ts.isoformat()
        if not candle.confirm:
            issues.append(DataQualityIssue("unconfirmed_candle", "Candle is not confirmed", ts))
        if min(candle.open, candle.high, candle.low, candle.close) <= 0:
            issues.append(DataQualityIssue("non_positive_ohlc", "OHLC contains non-positive value", ts))
        if candle.high < max(candle.open, candle.close) or candle.low > min(candle.open, candle.close):
            issues.append(DataQualityIssue("ohlc_inconsistent", "High/low do not contain open/close", ts))
        if candle.volume < Decimal("0"):
            issues.append(DataQualityIssue("negative_volume", "Volume is negative", ts))

        if previous is not None:
            delta = candle.ts - previous.ts
            if delta <= timedelta(0):
                issues.append(DataQualityIssue("non_monotonic_timestamp", "Timestamp is not increasing", ts))
            elif delta > expected_delta:
                issues.append(
                    DataQualityIssue(
                        "missing_candle_gap",
                        f"Gap {delta} exceeds expected {expected_delta}",
                        previous.ts.isoformat(),
                    )
                )
        previous = candle

    return issues

