"""OKX private WebSocket login and subscription helpers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import time
from typing import Any, Iterable

import websockets

from okx_quant.brokers.okx.auth import sign_okx_request


OKX_DEMO_PRIVATE_WS_URLS = (
    "wss://wspap.okx.com:8443/ws/v5/private",
    "wss://wseeapap.okx.com:8443/ws/v5/private",
)
OKX_LIVE_PRIVATE_WS_URL = "wss://ws.okx.com:8443/ws/v5/private"
OKX_WS_LOGIN_PATH = "/users/self/verify"


@dataclass(frozen=True)
class OKXWSPrivateAuth:
    api_key: str
    secret_key: str
    passphrase: str


@dataclass(frozen=True)
class PrivateWSSubscription:
    channel: str
    inst_type: str = "ANY"
    inst_id: str | None = None

    def to_okx_arg(self) -> dict[str, str]:
        arg = {"channel": self.channel, "instType": self.inst_type}
        if self.inst_id:
            arg["instId"] = self.inst_id
        return arg


@dataclass(frozen=True)
class PrivateWSMessage:
    received_at: datetime
    payload: dict[str, Any]


def build_login_message(auth: OKXWSPrivateAuth, timestamp: str | None = None) -> dict[str, Any]:
    timestamp = timestamp or str(int(time.time()))
    sign = sign_okx_request(auth.secret_key, timestamp, "GET", OKX_WS_LOGIN_PATH)
    return {
        "op": "login",
        "args": [
            {
                "apiKey": auth.api_key,
                "passphrase": auth.passphrase,
                "timestamp": timestamp,
                "sign": sign,
            }
        ],
    }


def build_private_subscribe_message(subscriptions: Iterable[PrivateWSSubscription]) -> dict[str, Any]:
    args = [subscription.to_okx_arg() for subscription in subscriptions]
    if not args:
        raise ValueError("at least one subscription is required")
    return {"op": "subscribe", "args": args}


async def login_and_subscribe(
    *,
    url: str,
    auth: OKXWSPrivateAuth,
    subscriptions: Iterable[PrivateWSSubscription],
    max_messages: int = 5,
    timeout_seconds: float = 20.0,
) -> list[PrivateWSMessage]:
    messages: list[PrivateWSMessage] = []
    async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
        await ws.send(json.dumps(build_login_message(auth), separators=(",", ":")))
        login_payload = await _recv_json(ws, timeout_seconds)
        messages.append(PrivateWSMessage(datetime.now(timezone.utc), login_payload))
        if login_payload.get("event") != "login" or login_payload.get("code") != "0":
            return messages

        await ws.send(json.dumps(build_private_subscribe_message(subscriptions), separators=(",", ":")))
        while len(messages) < max_messages:
            payload = await _recv_json(ws, timeout_seconds)
            messages.append(PrivateWSMessage(datetime.now(timezone.utc), payload))
            if payload.get("event") == "subscribe":
                break
    return messages


async def _recv_json(ws: Any, timeout_seconds: float) -> dict[str, Any]:
    raw = await asyncio.wait_for(ws.recv(), timeout=timeout_seconds)
    if raw == "ping":
        await ws.send("pong")
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout_seconds)
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("OKX WebSocket message is not an object")
    return payload

