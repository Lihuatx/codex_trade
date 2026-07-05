"""Check OKX private REST connectivity with a local env file."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from okx_quant.brokers.okx.auth import OKXAuth
from okx_quant.brokers.okx.client import OKXRestClient
from okx_quant.config import load_env_file, load_okx_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=".env.demo")
    parser.add_argument("--inst", default="BTC-USDT")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    env_path = Path(args.env_file)
    if not env_path.exists():
        print(
            {
                "ok": False,
                "reason": "env_file_missing",
                "env_file": str(env_path.resolve()),
                "next_step": "copy .env.example to .env.demo and fill OKX demo API key/secret/passphrase",
            }
        )
        return 2

    load_env_file(env_path)
    settings = load_okx_settings()
    try:
        settings.validate_for_private_api()
    except ValueError as exc:
        print({"ok": False, "reason": "invalid_private_api_settings", "error": str(exc)})
        return 2

    client = OKXRestClient(
        auth=OKXAuth(
            api_key=settings.api_key,
            secret_key=settings.api_secret,
            passphrase=settings.passphrase,
            simulated_trading=settings.simulated_trading,
        )
    )
    fee_payload = client.get_trade_fee("SPOT", args.inst)
    print(
        {
            "ok": fee_payload.get("code") == "0",
            "env": settings.env,
            "simulated_trading": settings.simulated_trading,
            "inst": args.inst,
            "code": fee_payload.get("code"),
            "data_count": len(fee_payload.get("data", [])),
        }
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

