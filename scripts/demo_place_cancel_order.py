"""Place and cancel one tiny OKX demo order.

The script refuses live mode. Default mode is dry-run; pass --execute to send
the order to OKX demo trading.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
import time

from okx_quant.brokers.okx.auth import OKXAuth
from okx_quant.brokers.okx.client import OKXRestClient
from okx_quant.brokers.okx.orders import OKXCancelOrderRequest, OKXPlaceOrderRequest
from okx_quant.brokers.okx.responses import parse_order_ack, parse_order_snapshot
from okx_quant.config import load_env_file, load_okx_settings
from okx_quant.domain.enums import OrderSide, OrderStatus, OrderType
from okx_quant.domain.instruments import InstrumentRules
from okx_quant.domain.market import parse_okx_candle_row
from okx_quant.domain.models import Order, new_client_order_id
from okx_quant.execution.order_sizer import size_spot_limit_order_by_quote_notional
from okx_quant.oms.manager import OrderManager
from okx_quant.storage.sqlite_store import SQLiteEventStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=".env.demo")
    parser.add_argument("--db", default="data/demo_orders.sqlite3")
    parser.add_argument("--inst", default="BTC-USDT")
    parser.add_argument("--quote-notional", default="20")
    parser.add_argument("--price-offset-bps", default="1000")
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env_file(args.env_file)
    settings = load_okx_settings()
    settings.validate_for_private_api()
    if settings.env != "demo" or not settings.simulated_trading:
        print({"ok": False, "reason": "script_refuses_non_demo_environment"})
        return 2

    client = OKXRestClient(
        auth=OKXAuth(
            api_key=settings.api_key,
            secret_key=settings.api_secret,
            passphrase=settings.passphrase,
            simulated_trading=settings.simulated_trading,
        )
    )
    instruments = client.get_public_instruments("SPOT").get("data", [])
    instrument = next(item for item in instruments if item.get("instId") == args.inst)
    rules = InstrumentRules.from_okx(instrument)
    candles = [
        parse_okx_candle_row(args.inst, "1H", row)
        for row in client.get_history_candles(args.inst, "1H", 5).get("data", [])
    ]
    latest = next(candle for candle in candles if candle.confirm)
    offset = Decimal(args.price_offset_bps) / Decimal("10000")
    price = rules.round_price(latest.close * (Decimal("1") - offset))
    sized = size_spot_limit_order_by_quote_notional(
        rules=rules,
        quote_notional=Decimal(args.quote_notional),
        reference_price=price,
    )
    client_order_id = new_client_order_id("dem")
    order_request = OKXPlaceOrderRequest(
        inst_id=args.inst,
        side=OrderSide.BUY,
        order_type=OrderType.POST_ONLY,
        size=sized.size,
        price=price,
        client_order_id=client_order_id,
    )
    payload = order_request.to_payload()

    if not args.execute:
        print(
            {
                "ok": True,
                "mode": "dry_run",
                "env": settings.env,
                "payload": payload,
                "rounded_notional": str(sized.rounded_notional),
            }
        )
        return 0

    with SQLiteEventStore(Path(args.db)) as store:
        store.initialize()
        manager = OrderManager(store)
        manager.create_order(
            Order(
                client_order_id=client_order_id,
                inst_id=args.inst,
                side=OrderSide.BUY,
                order_type=OrderType.POST_ONLY,
                size=sized.size,
                price=price,
            )
        )
        manager.apply_status(client_order_id=client_order_id, next_status=OrderStatus.SUBMITTED)

        place_ack = parse_order_ack(client.place_order(order_request))
        if not place_ack.ok:
            manager.apply_status(client_order_id=client_order_id, next_status=OrderStatus.REJECTED)
            store.commit()
            print({"ok": False, "stage": "place_order", "s_code": place_ack.s_code, "s_msg": place_ack.s_msg})
            return 1

        manager.apply_status(
            client_order_id=client_order_id,
            next_status=OrderStatus.ACCEPTED,
            exchange_order_id=place_ack.exchange_order_id,
        )
        time.sleep(1)
        before_cancel = parse_order_snapshot(client.get_order(inst_id=args.inst, client_order_id=client_order_id))

        manager.apply_status(client_order_id=client_order_id, next_status=OrderStatus.CANCEL_PENDING)
        cancel_ack = parse_order_ack(client.cancel_order(OKXCancelOrderRequest(args.inst, client_order_id)))
        if not cancel_ack.ok:
            store.commit()
            print({"ok": False, "stage": "cancel_order", "s_code": cancel_ack.s_code, "s_msg": cancel_ack.s_msg})
            return 1

        final_snapshot = _poll_order_status(client, args.inst, client_order_id)
        if final_snapshot.status == OrderStatus.CANCELLED:
            manager.apply_status(client_order_id=client_order_id, next_status=OrderStatus.CANCELLED)
        else:
            manager.apply_status(client_order_id=client_order_id, next_status=OrderStatus.UNKNOWN)
        store.commit()

        print(
            {
                "ok": final_snapshot.status == OrderStatus.CANCELLED,
                "env": settings.env,
                "client_order_id": client_order_id,
                "exchange_order_id": place_ack.exchange_order_id,
                "before_cancel_state": before_cancel.raw_state,
                "final_state": final_snapshot.raw_state,
                "orders": store.count("orders"),
                "db": str(Path(args.db).resolve()),
            }
        )
    return 0


def _poll_order_status(client: OKXRestClient, inst_id: str, client_order_id: str) -> object:
    snapshot = None
    for _ in range(5):
        snapshot = parse_order_snapshot(client.get_order(inst_id=inst_id, client_order_id=client_order_id))
        if snapshot.status == OrderStatus.CANCELLED:
            return snapshot
        time.sleep(1)
    if snapshot is None:
        raise RuntimeError("order status polling did not run")
    return snapshot


if __name__ == "__main__":
    sys.exit(main())

