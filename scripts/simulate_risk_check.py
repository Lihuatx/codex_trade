"""Run and persist a sample pre-trade risk check."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from okx_quant.domain.enums import OrderSide
from okx_quant.domain.models import TradeIntent
from okx_quant.risk.pre_trade import MarketSnapshot, PortfolioSnapshot, PreTradeRiskEngine, RiskLimits
from okx_quant.storage.sqlite_store import SQLiteEventStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/risk_sim.sqlite3")
    parser.add_argument("--side", choices=["buy", "sell"], default="buy")
    parser.add_argument("--notional", default="20")
    parser.add_argument("--read-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    now = datetime.now(timezone.utc)
    intent = TradeIntent(
        strategy_id="risk-sim",
        inst_id="BTC-USDT",
        side=OrderSide(args.side),
        notional=Decimal(args.notional),
        reference_price=Decimal("60000"),
        reason="local-risk-smoke",
        created_at=now,
    )
    engine = PreTradeRiskEngine(
        RiskLimits(
            max_total_crypto_exposure=Decimal("300"),
            max_order_notional=Decimal("20"),
            max_daily_loss=Decimal("10"),
            max_spread_bps=Decimal("20"),
            max_price_deviation_bps=Decimal("30"),
            stale_market_data_seconds=10,
            read_only_mode=args.read_only,
        )
    )
    decision = engine.evaluate(
        intent,
        MarketSnapshot(
            inst_id="BTC-USDT",
            bid=Decimal("59995"),
            ask=Decimal("60005"),
            last=Decimal("60000"),
            observed_at=now,
        ),
        PortfolioSnapshot(total_crypto_exposure=Decimal("0"), daily_pnl=Decimal("0")),
        now,
    )

    with SQLiteEventStore(Path(args.db)) as store:
        store.initialize()
        store.insert_risk_event(
            event_id=uuid4().hex,
            created_at=now,
            inst_id=intent.inst_id,
            approved=decision.approved,
            reasons=decision.reasons,
        )
        store.commit()
        print(
            {
                "db": str(Path(args.db).resolve()),
                "approved": decision.approved,
                "reasons": decision.reasons,
                "risk_events": store.count("risk_events"),
            }
        )


if __name__ == "__main__":
    main()

