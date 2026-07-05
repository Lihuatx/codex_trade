"""Preview signal -> risk -> order payload without placing an order."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import json

from okx_quant.brokers.okx.client import OKXRestClient
from okx_quant.brokers.okx.orders import OKXPlaceOrderRequest
from okx_quant.config import load_env_file, load_okx_settings
from okx_quant.domain.enums import OrderSide, OrderType
from okx_quant.domain.instruments import InstrumentRules
from okx_quant.domain.market import parse_okx_order_book_top, parse_okx_ticker_last
from okx_quant.domain.models import TradeIntent, new_client_order_id
from okx_quant.execution.order_sizer import size_spot_limit_order_by_quote_notional
from okx_quant.risk.pre_trade import MarketSnapshot, PortfolioSnapshot, PreTradeRiskEngine, RiskLimits


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=".env.demo")
    parser.add_argument("--inst", default="BTC-USDT")
    parser.add_argument("--side", choices=["buy", "sell"], default="buy")
    parser.add_argument("--notional", default="20")
    parser.add_argument("--current-exposure", default="0")
    parser.add_argument("--daily-pnl", default="0")
    parser.add_argument("--override-read-only-for-preview", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_env_file(args.env_file)
    settings = load_okx_settings()

    client = OKXRestClient()
    instruments = client.get_public_instruments("SPOT").get("data", [])
    instrument = next(item for item in instruments if item.get("instId") == args.inst)
    rules = InstrumentRules.from_okx(instrument)

    last = parse_okx_ticker_last(client.get_ticker(args.inst))
    bid, ask = parse_okx_order_book_top(client.get_order_book(args.inst, 5))
    now = datetime.now(timezone.utc)
    side = OrderSide(args.side)
    intent = TradeIntent(
        strategy_id="manual-preview",
        inst_id=args.inst,
        side=side,
        notional=Decimal(args.notional),
        reference_price=last,
        reason="pretrade-preview",
        created_at=now,
    )
    engine = PreTradeRiskEngine(
        RiskLimits(
            max_total_crypto_exposure=settings.live_capital_limit_usdt,
            max_order_notional=Decimal("20"),
            max_daily_loss=Decimal("10"),
            max_spread_bps=Decimal("20"),
            max_price_deviation_bps=Decimal("30"),
            stale_market_data_seconds=10,
            read_only_mode=settings.read_only_mode and not args.override_read_only_for_preview,
            kill_switch=settings.kill_switch,
        )
    )
    decision = engine.evaluate(
        intent,
        MarketSnapshot(args.inst, bid=bid, ask=ask, last=last, observed_at=now),
        PortfolioSnapshot(Decimal(args.current_exposure), Decimal(args.daily_pnl)),
        now,
    )

    order_payload = None
    if decision.approved:
        price = rules.round_price(bid if side == OrderSide.BUY else ask)
        sized = size_spot_limit_order_by_quote_notional(
            rules=rules,
            quote_notional=Decimal(args.notional),
            reference_price=price,
        )
        order_payload = OKXPlaceOrderRequest(
            inst_id=args.inst,
            side=side,
            order_type=OrderType.POST_ONLY,
            size=sized.size,
            price=price,
            client_order_id=new_client_order_id("pre"),
        ).to_payload()

    print(
        json.dumps(
            {
                "env": settings.env,
                "simulated_trading": settings.simulated_trading,
                "read_only_mode_effective": settings.read_only_mode and not args.override_read_only_for_preview,
                "market": {
                    "bid": str(bid),
                    "ask": str(ask),
                    "last": str(last),
                },
                "risk": {
                    "approved": decision.approved,
                    "reasons": list(decision.reasons),
                },
                "order_payload": order_payload,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

