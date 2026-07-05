"""Validate OKX demo order updates through the private orders WebSocket."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import time

import websockets

from okx_quant.brokers.okx.auth import OKXAuth
from okx_quant.brokers.okx.client import OKXRestClient
from okx_quant.brokers.okx.orders import OKXCancelOrderRequest, OKXPlaceOrderRequest, map_okx_order_state
from okx_quant.brokers.okx.responses import parse_order_ack
from okx_quant.brokers.okx.ws_private import (
    OKXWSPrivateAuth,
    OKX_DEMO_PRIVATE_WS_URLS,
    PrivateWSSubscription,
    build_login_message,
    build_private_subscribe_message,
)
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
    parser.add_argument("--db", default="data/demo_order_ws.sqlite3")
    parser.add_argument("--url", default=OKX_DEMO_PRIVATE_WS_URLS[0])
    parser.add_argument("--inst", default="BTC-USDT")
    parser.add_argument("--quote-notional", default="20")
    parser.add_argument("--price-offset-bps", default="1000")
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    load_env_file(args.env_file)
    settings = load_okx_settings()
    settings.validate_for_private_api()
    if settings.env != "demo" or not settings.simulated_trading:
        print({"ok": False, "reason": "script_refuses_non_demo_environment"})
        return

    rest = OKXRestClient(
        auth=OKXAuth(settings.api_key, settings.api_secret, settings.passphrase, settings.simulated_trading)
    )
    order_request, rounded_notional = _build_post_only_buy(rest, args.inst, Decimal(args.quote_notional), Decimal(args.price_offset_bps))

    events: list[dict[str, object]] = []
    statuses: list[str] = []
    cancel_task: asyncio.Task[None] | None = None
    place_ack = None

    with SQLiteEventStore(Path(args.db)) as store:
        store.initialize()
        manager = OrderManager(store)
        manager.create_order(
            Order(
                client_order_id=order_request.client_order_id,
                inst_id=args.inst,
                side=OrderSide.BUY,
                order_type=OrderType.POST_ONLY,
                size=order_request.size,
                price=order_request.price,
            )
        )
        manager.apply_status(client_order_id=order_request.client_order_id, next_status=OrderStatus.SUBMITTED)

        async with websockets.connect(args.url, ping_interval=20, ping_timeout=20) as ws:
            auth = OKXWSPrivateAuth(settings.api_key, settings.api_secret, settings.passphrase)
            await ws.send(json.dumps(build_login_message(auth), separators=(",", ":")))
            login_payload = await _recv_json(ws, args.timeout_seconds)
            if login_payload.get("event") != "login" or login_payload.get("code") != "0":
                print({"ok": False, "stage": "ws_login", "payload": _redact(login_payload)})
                return

            await ws.send(
                json.dumps(
                    build_private_subscribe_message([PrivateWSSubscription(channel="orders", inst_type="ANY")]),
                    separators=(",", ":"),
                )
            )
            subscribe_payload = await _recv_json(ws, args.timeout_seconds)
            if subscribe_payload.get("event") != "subscribe":
                print({"ok": False, "stage": "ws_subscribe", "payload": _redact(subscribe_payload)})
                return

            place_ack = parse_order_ack(await asyncio.to_thread(rest.place_order, order_request))
            if not place_ack.ok:
                manager.apply_status(client_order_id=order_request.client_order_id, next_status=OrderStatus.REJECTED)
                store.commit()
                print({"ok": False, "stage": "place_order", "s_code": place_ack.s_code, "s_msg": place_ack.s_msg})
                return
            manager.apply_status(
                client_order_id=order_request.client_order_id,
                next_status=OrderStatus.ACCEPTED,
                exchange_order_id=place_ack.exchange_order_id,
            )

            cancel_task = asyncio.create_task(_cancel_after_delay(rest, args.inst, order_request.client_order_id, 1.0))
            deadline = time.monotonic() + args.timeout_seconds
            while time.monotonic() < deadline:
                try:
                    payload = await _recv_json(ws, max(0.1, deadline - time.monotonic()))
                except TimeoutError:
                    break
                store.insert_market_raw(
                    source="okx_ws_private",
                    channel=_message_channel(payload),
                    inst_id=args.inst,
                    payload=_redact(payload),
                    received_at=datetime.now(timezone.utc),
                )
                for item in _order_items(payload):
                    if item.get("clOrdId") != order_request.client_order_id:
                        continue
                    state = str(item.get("state") or "")
                    statuses.append(state)
                    events.append({"state": state, "ordId": item.get("ordId"), "clOrdId": item.get("clOrdId")})
                    if map_okx_order_state(state) == OrderStatus.CANCELLED:
                        manager.apply_status(client_order_id=order_request.client_order_id, next_status=OrderStatus.CANCEL_PENDING)
                        manager.apply_status(client_order_id=order_request.client_order_id, next_status=OrderStatus.CANCELLED)
                        store.commit()
                        print(
                            {
                                "ok": True,
                                "client_order_id": order_request.client_order_id,
                                "exchange_order_id": place_ack.exchange_order_id,
                                "rounded_notional": str(rounded_notional),
                                "statuses": statuses,
                                "events": events,
                                "orders": store.count("orders"),
                                "raw_ws_rows": store.count("market_raw"),
                                "db": str(Path(args.db).resolve()),
                            }
                        )
                        return
            if cancel_task is not None:
                await cancel_task
            store.commit()
            print(
                {
                    "ok": False,
                    "reason": "canceled_event_not_observed",
                    "client_order_id": order_request.client_order_id,
                    "exchange_order_id": place_ack.exchange_order_id if place_ack else None,
                    "statuses": statuses,
                    "events": events,
                    "raw_ws_rows": store.count("market_raw"),
                }
            )


def _build_post_only_buy(
    rest: OKXRestClient,
    inst_id: str,
    quote_notional: Decimal,
    price_offset_bps: Decimal,
) -> tuple[OKXPlaceOrderRequest, Decimal]:
    instruments = rest.get_public_instruments("SPOT").get("data", [])
    instrument = next(item for item in instruments if item.get("instId") == inst_id)
    rules = InstrumentRules.from_okx(instrument)
    candles = [
        parse_okx_candle_row(inst_id, "1H", row)
        for row in rest.get_history_candles(inst_id, "1H", 5).get("data", [])
    ]
    latest = next(candle for candle in candles if candle.confirm)
    price = rules.round_price(latest.close * (Decimal("1") - price_offset_bps / Decimal("10000")))
    sized = size_spot_limit_order_by_quote_notional(rules=rules, quote_notional=quote_notional, reference_price=price)
    return (
        OKXPlaceOrderRequest(
            inst_id=inst_id,
            side=OrderSide.BUY,
            order_type=OrderType.POST_ONLY,
            size=sized.size,
            price=price,
            client_order_id=new_client_order_id("wsd"),
        ),
        sized.rounded_notional,
    )


async def _cancel_after_delay(rest: OKXRestClient, inst_id: str, client_order_id: str, delay_seconds: float) -> None:
    await asyncio.sleep(delay_seconds)
    await asyncio.to_thread(rest.cancel_order, OKXCancelOrderRequest(inst_id=inst_id, client_order_id=client_order_id))


async def _recv_json(ws: object, timeout_seconds: float) -> dict[str, object]:
    raw = await asyncio.wait_for(ws.recv(), timeout=timeout_seconds)
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("WebSocket payload is not an object")
    return payload


def _message_channel(payload: dict[str, object]) -> str:
    arg = payload.get("arg")
    if isinstance(arg, dict):
        return str(arg.get("channel") or "unknown")
    return str(payload.get("event") or "unknown")


def _order_items(payload: dict[str, object]) -> list[dict[str, object]]:
    data = payload.get("data")
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _redact(payload: dict[str, object]) -> dict[str, object]:
    clean = dict(payload)
    if clean.get("event") == "login":
        clean.pop("args", None)
    return clean


if __name__ == "__main__":
    asyncio.run(main())

