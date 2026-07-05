"""Preview BTC/ETH/USDT rebalance signal from OKX account balances."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json

from okx_quant.brokers.okx.auth import OKXAuth
from okx_quant.brokers.okx.client import OKXRestClient
from okx_quant.config import load_env_file, load_okx_settings
from okx_quant.domain.account import parse_okx_account_balances
from okx_quant.domain.market import parse_okx_ticker_last
from okx_quant.portfolio.rebalance_signal import PortfolioAsset, generate_rebalance_signal


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=".env.demo")
    parser.add_argument("--weights", default="USDT=0.5,BTC=0.25,ETH=0.25")
    parser.add_argument("--threshold", default="0.05")
    parser.add_argument("--min-trade-notional", default="10")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_env_file(args.env_file)
    settings = load_okx_settings()
    settings.validate_for_private_api()
    client = OKXRestClient(
        auth=OKXAuth(settings.api_key, settings.api_secret, settings.passphrase, settings.simulated_trading)
    )
    balances = {balance.ccy: balance for balance in parse_okx_account_balances(client.get_balance())}
    target_weights = _parse_weights(args.weights)
    assets = [
        PortfolioAsset(
            asset=asset,
            quantity=balances.get(asset).available if balances.get(asset) else Decimal("0"),
            price_usdt=parse_okx_ticker_last(client.get_ticker(f"{asset}-USDT")),
        )
        for asset in target_weights
        if asset != "USDT"
    ]
    signal = generate_rebalance_signal(
        cash_usdt=balances.get("USDT").available if balances.get("USDT") else Decimal("0"),
        assets=assets,
        target_weights=target_weights,
        threshold=Decimal(args.threshold),
        min_trade_notional=Decimal(args.min_trade_notional),
    )
    print(
        json.dumps(
            {
                "env": settings.env,
                "simulated_trading": settings.simulated_trading,
                "read_only": True,
                "signal": signal.as_dict(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _parse_weights(raw: str) -> dict[str, Decimal]:
    result: dict[str, Decimal] = {}
    for item in raw.split(","):
        key, value = item.split("=", 1)
        result[key.strip()] = Decimal(value.strip())
    return result


if __name__ == "__main__":
    main()

