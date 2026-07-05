"""Market data domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Sequence


@dataclass(frozen=True)
class Candle:
    inst_id: str
    bar: str
    ts: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    volume_ccy: Decimal
    volume_ccy_quote: Decimal | None
    confirm: bool


def parse_okx_candle_row(inst_id: str, bar: str, row: Sequence[str]) -> Candle:
    """Parse OKX kline array.

    OKX documents the kline array with confirm as the final element. Current
    and history endpoints may differ on whether volCcyQuote is present, so the
    parser treats the last field as confirm and keeps volCcyQuote optional.
    """

    if len(row) not in {8, 9}:
        raise ValueError(f"Unexpected OKX candle row length: {len(row)}")

    ts_ms, open_, high, low, close, volume, volume_ccy = row[:7]
    volume_ccy_quote = row[7] if len(row) == 9 else None
    confirm = row[-1]

    return Candle(
        inst_id=inst_id,
        bar=bar,
        ts=datetime.fromtimestamp(int(ts_ms) / 1000, tz=timezone.utc),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal(volume),
        volume_ccy=Decimal(volume_ccy),
        volume_ccy_quote=Decimal(volume_ccy_quote) if volume_ccy_quote is not None else None,
        confirm=confirm == "1",
    )


def only_confirmed(candles: Sequence[Candle]) -> list[Candle]:
    return [candle for candle in candles if candle.confirm]


def parse_okx_ticker_last(payload: dict[str, object]) -> Decimal:
    item = _first_data_item(payload)
    return Decimal(str(item["last"]))


def parse_okx_order_book_top(payload: dict[str, object]) -> tuple[Decimal, Decimal]:
    item = _first_data_item(payload)
    bids = item.get("bids")
    asks = item.get("asks")
    if not isinstance(bids, list) or not bids:
        raise ValueError("OKX order book has no bids")
    if not isinstance(asks, list) or not asks:
        raise ValueError("OKX order book has no asks")
    best_bid = bids[0]
    best_ask = asks[0]
    if not isinstance(best_bid, list) or not isinstance(best_ask, list):
        raise ValueError("OKX order book top levels are malformed")
    return Decimal(str(best_bid[0])), Decimal(str(best_ask[0]))


def _first_data_item(payload: dict[str, object]) -> dict[str, object]:
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        raise ValueError("OKX payload has no data item")
    item = data[0]
    if not isinstance(item, dict):
        raise ValueError("OKX payload data item is not an object")
    return item
