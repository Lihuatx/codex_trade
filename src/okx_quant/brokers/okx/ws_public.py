"""OKX public WebSocket collector."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Any, Iterable

import websockets


OKX_PUBLIC_WS_URL = "wss://ws.okx.com:8443/ws/v5/public"


@dataclass(frozen=True)
class PublicWSSubscription:
    channel: str
    inst_id: str

    def to_okx_arg(self) -> dict[str, str]:
        return {"channel": self.channel, "instId": self.inst_id}


@dataclass(frozen=True)
class PublicWSMessage:
    received_at: datetime
    payload: dict[str, Any]

    @property
    def channel(self) -> str:
        arg = self.payload.get("arg")
        if isinstance(arg, dict):
            return str(arg.get("channel") or "")
        return str(self.payload.get("event") or "unknown")

    @property
    def inst_id(self) -> str | None:
        arg = self.payload.get("arg")
        if isinstance(arg, dict):
            inst_id = arg.get("instId")
            return str(inst_id) if inst_id else None
        return None


def build_subscribe_message(subscriptions: Iterable[PublicWSSubscription]) -> dict[str, Any]:
    args = [subscription.to_okx_arg() for subscription in subscriptions]
    if not args:
        raise ValueError("at least one subscription is required")
    return {"op": "subscribe", "args": args}


async def collect_public_messages(
    subscriptions: Iterable[PublicWSSubscription],
    *,
    max_messages: int,
    timeout_seconds: float = 30.0,
    url: str = OKX_PUBLIC_WS_URL,
) -> list[PublicWSMessage]:
    subscribe_message = build_subscribe_message(subscriptions)
    messages: list[PublicWSMessage] = []

    async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
        await ws.send(json.dumps(subscribe_message, separators=(",", ":")))
        while len(messages) < max_messages:
            raw = await asyncio.wait_for(ws.recv(), timeout=timeout_seconds)
            if raw == "pong":
                continue
            if raw == "ping":
                await ws.send("pong")
                continue
            payload = json.loads(raw)
            if isinstance(payload, dict):
                messages.append(PublicWSMessage(received_at=datetime.now(timezone.utc), payload=payload))

    return messages

