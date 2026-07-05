"""Fetch public OKX metadata for a symbol.

This script does not require API keys. It is a manual smoke check for public
REST access and instrument metadata parsing.
"""

from __future__ import annotations

from decimal import Decimal

from okx_quant.brokers.okx.client import OKXRestClient
from okx_quant.domain.instruments import InstrumentRules
from okx_quant.domain.market import only_confirmed, parse_okx_candle_row


def main() -> None:
    client = OKXRestClient()
    payload = client.get_public_instruments("SPOT")
    instruments = payload.get("data", [])
    btc = next(item for item in instruments if item.get("instId") == "BTC-USDT")
    rules = InstrumentRules.from_okx(btc)
    print(
        {
            "inst_id": rules.inst_id,
            "tick_size": str(rules.tick_size),
            "lot_size": str(rules.lot_size),
            "min_size": str(rules.min_size),
            "rounded_example": str(rules.round_price(Decimal("12345.678901"))),
        }
    )
    candle_payload = client.get_history_candles("BTC-USDT", "1H", 5)
    candles = [
        parse_okx_candle_row("BTC-USDT", "1H", row)
        for row in candle_payload.get("data", [])
    ]
    print(
        {
            "history_candles": len(candles),
            "confirmed": len(only_confirmed(candles)),
            "latest_ts": candles[0].ts.isoformat() if candles else None,
        }
    )


if __name__ == "__main__":
    main()
