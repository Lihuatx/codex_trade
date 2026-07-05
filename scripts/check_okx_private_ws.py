"""Check OKX private WebSocket login and orders subscription."""

from __future__ import annotations

import argparse
import asyncio
import json

from okx_quant.brokers.okx.ws_private import (
    OKX_DEMO_PRIVATE_WS_URLS,
    OKX_LIVE_PRIVATE_WS_URL,
    OKXWSPrivateAuth,
    PrivateWSSubscription,
    login_and_subscribe,
)
from okx_quant.config import load_env_file, load_okx_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=".env.demo")
    parser.add_argument("--url", action="append", dest="urls", default=None)
    parser.add_argument("--inst-type", default="ANY")
    return parser.parse_args()


async def run() -> None:
    args = parse_args()
    load_env_file(args.env_file)
    settings = load_okx_settings()
    settings.validate_for_private_api()
    urls = args.urls
    if urls is None:
        urls = list(OKX_DEMO_PRIVATE_WS_URLS if settings.env == "demo" else (OKX_LIVE_PRIVATE_WS_URL,))

    auth = OKXWSPrivateAuth(settings.api_key, settings.api_secret, settings.passphrase)
    results = []
    for url in urls:
        try:
            messages = await login_and_subscribe(
                url=url,
                auth=auth,
                subscriptions=[PrivateWSSubscription(channel="orders", inst_type=args.inst_type)],
                max_messages=3,
                timeout_seconds=15,
            )
            sanitized = [_sanitize_message(message.payload) for message in messages]
            ok = any(msg.get("event") == "login" and msg.get("code") == "0" for msg in sanitized)
            subscribed = any(msg.get("event") == "subscribe" for msg in sanitized)
            results.append({"url": url, "ok": ok, "subscribed": subscribed, "messages": sanitized})
            if ok and subscribed:
                break
        except Exception as exc:
            results.append({"url": url, "ok": False, "subscribed": False, "error": type(exc).__name__, "message": str(exc)})

    print(json.dumps({"env": settings.env, "simulated_trading": settings.simulated_trading, "results": results}, ensure_ascii=False, indent=2))


def _sanitize_message(payload: dict[str, object]) -> dict[str, object]:
    clean = dict(payload)
    if "args" in clean and clean.get("event") == "login":
        clean["args"] = "[redacted]"
    return clean


if __name__ == "__main__":
    asyncio.run(run())

