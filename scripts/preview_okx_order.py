"""Build an OKX spot limit order payload without placing it."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json

from okx_quant.brokers.okx.client import OKXRestClient
from okx_quant.brokers.okx.orders import OKXPlaceOrderRequest
from okx_quant.domain.enums import OrderSide, OrderType
from okx_quant.domain.instruments import InstrumentRules
from okx_quant.domain.market import parse_okx_candle_row
from okx_quant.domain.models import new_client_order_id
from okx_quant.execution.order_sizer import size_spot_limit_order_by_quote_notional


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inst", default="BTC-USDT")
    parser.add_argument("--side", choices=["buy", "sell"], default="buy")
    parser.add_argument("--quote-notional", default="20")
    parser.add_argument("--bar", default="1H")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = OKXRestClient()
    instruments = client.get_public_instruments("SPOT").get("data", [])
    instrument = next(item for item in instruments if item.get("instId") == args.inst)
    rules = InstrumentRules.from_okx(instrument)

    candle_payload = client.get_history_candles(args.inst, args.bar, 5)
    candles = [
        parse_okx_candle_row(args.inst, args.bar, row)
        for row in candle_payload.get("data", [])
    ]
    latest = next(candle for candle in candles if candle.confirm)
    price = rules.round_price(latest.close)
    sized = size_spot_limit_order_by_quote_notional(
        rules=rules,
        quote_notional=Decimal(args.quote_notional),
        reference_price=price,
    )
    order = OKXPlaceOrderRequest(
        inst_id=args.inst,
        side=OrderSide(args.side),
        order_type=OrderType.LIMIT,
        size=sized.size,
        price=price,
        client_order_id=new_client_order_id("dry"),
    )
    print(
        json.dumps(
            {
                "rules": {
                    "tick_size": str(rules.tick_size),
                    "lot_size": str(rules.lot_size),
                    "min_size": str(rules.min_size),
                },
                "latest_confirmed": latest.confirm,
                "reference_price": str(price),
                "requested_quote_notional": args.quote_notional,
                "rounded_notional": str(sized.rounded_notional),
                "payload": order.to_payload(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
