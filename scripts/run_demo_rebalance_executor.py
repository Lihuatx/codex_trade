"""Run one risk-capped rebalance order in OKX demo trading.

This is intentionally a one-shot executor. It refuses live mode, refuses to
place a new order when the local DB has active orders, and places only a small
passive post_only limit order generated from the read-only rebalance signal.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sys
import time
from uuid import uuid4

from okx_quant.brokers.okx.auth import OKXAuth
from okx_quant.brokers.okx.client import OKXRestClient
from okx_quant.brokers.okx.orders import OKXCancelOrderRequest
from okx_quant.brokers.okx.responses import OKXOrderSnapshot, parse_order_ack, parse_order_snapshot
from okx_quant.config import load_env_file, load_okx_settings
from okx_quant.domain.account import parse_okx_account_balances
from okx_quant.domain.enums import OrderStatus, OrderType
from okx_quant.domain.instruments import InstrumentRules
from okx_quant.domain.market import parse_okx_order_book_top, parse_okx_ticker_last
from okx_quant.domain.models import Order, TradeIntent, new_client_order_id
from okx_quant.execution.demo_rebalance_executor import (
    active_local_orders,
    build_passive_post_only_order,
    select_first_actionable_intent,
)
from okx_quant.oms.manager import OrderManager
from okx_quant.portfolio.rebalance_signal import PortfolioAsset, cap_rebalance_intents, generate_rebalance_signal
from okx_quant.reconciliation.orders import parse_okx_order_snapshots, reconcile_order_statuses
from okx_quant.risk.pre_trade import MarketSnapshot, PortfolioSnapshot, PreTradeRiskEngine, RiskLimits
from okx_quant.storage.sqlite_store import SQLiteEventStore


TERMINAL_STATUSES = {
    OrderStatus.FILLED,
    OrderStatus.CANCELLED,
    OrderStatus.REJECTED,
    OrderStatus.EXPIRED,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=".env.demo")
    parser.add_argument("--db", default="data/demo_rebalance_executor.sqlite3")
    parser.add_argument("--weights", default="USDT=0.9,BTC=0.05,ETH=0.05")
    parser.add_argument("--threshold", default="0.08")
    parser.add_argument("--min-trade-notional", default="10")
    parser.add_argument("--max-order-notional", default="10")
    parser.add_argument("--max-total-crypto-exposure", default="30")
    parser.add_argument("--max-daily-loss", default="5")
    parser.add_argument("--max-spread-bps", default="20")
    parser.add_argument("--max-price-deviation-bps", default="30")
    parser.add_argument("--stale-market-data-seconds", type=int, default=10)
    parser.add_argument("--price-offset-bps", default="2")
    parser.add_argument("--cancel-after-seconds", type=float, default=3.0)
    parser.add_argument("--poll-timeout-seconds", type=float, default=20.0)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--override-read-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env_file(args.env_file)
    settings = load_okx_settings()
    settings.validate_for_private_api()
    if settings.env != "demo" or not settings.simulated_trading:
        print_json({"ok": False, "reason": "script_refuses_non_demo_environment"})
        return 2

    client = OKXRestClient(
        auth=OKXAuth(settings.api_key, settings.api_secret, settings.passphrase, settings.simulated_trading)
    )
    target_weights = _parse_weights(args.weights)

    with SQLiteEventStore(Path(args.db)) as store:
        store.initialize()
        latest_reconciliation_status = store.latest_reconciliation_status()
        if latest_reconciliation_status == "failed":
            print_json(
                {
                    "ok": False,
                    "reason": "latest_reconciliation_failed",
                    "db": str(Path(args.db).resolve()),
                }
            )
            return 2

        active_orders = active_local_orders(store.list_order_statuses())
        if active_orders:
            print_json(
                {
                    "ok": False,
                    "reason": "active_local_orders_exist",
                    "active_orders": {key: value.value for key, value in active_orders.items()},
                    "db": str(Path(args.db).resolve()),
                }
            )
            return 2

        signal = _build_signal(client, target_weights, Decimal(args.threshold), Decimal(args.min_trade_notional))
        capped_intents = cap_rebalance_intents(
            signal,
            max_order_notional=Decimal(args.max_order_notional),
            max_total_crypto_exposure=Decimal(args.max_total_crypto_exposure),
            min_trade_notional=Decimal(args.min_trade_notional),
        )
        selected = select_first_actionable_intent(capped_intents)
        if selected is None:
            print_json(
                {
                    "ok": True,
                    "stage": "no_actionable_intent",
                    "env": settings.env,
                    "read_only": not args.execute,
                    "signal": signal.as_dict(),
                    "risk_capped_intents": [item.as_dict() for item in capped_intents],
                }
            )
            return 0

        now = datetime.now(timezone.utc)
        inst_id = f"{selected.intent.asset}-USDT"
        rules = _instrument_rules(client, inst_id)
        last = parse_okx_ticker_last(client.get_ticker(inst_id))
        bid, ask = parse_okx_order_book_top(client.get_order_book(inst_id, 5))
        trade_intent = TradeIntent(
            strategy_id="demo-rebalance-90-5-5",
            inst_id=inst_id,
            side=selected.intent.side,
            notional=selected.capped_notional_usdt,
            reference_price=last,
            reason=selected.intent.reason,
            created_at=now,
        )
        risk = PreTradeRiskEngine(
            RiskLimits(
                max_total_crypto_exposure=Decimal(args.max_total_crypto_exposure),
                max_order_notional=Decimal(args.max_order_notional),
                max_daily_loss=Decimal(args.max_daily_loss),
                max_spread_bps=Decimal(args.max_spread_bps),
                max_price_deviation_bps=Decimal(args.max_price_deviation_bps),
                stale_market_data_seconds=args.stale_market_data_seconds,
                read_only_mode=args.execute and not args.override_read_only,
                kill_switch=settings.kill_switch,
            )
        )
        decision = risk.evaluate(
            trade_intent,
            MarketSnapshot(inst_id, bid=bid, ask=ask, last=last, observed_at=now),
            PortfolioSnapshot(_crypto_exposure(signal), Decimal("0")),
            now,
        )
        client_order_id = new_client_order_id("drb")
        store.insert_risk_event(
            event_id=f"{client_order_id}-risk",
            created_at=now,
            inst_id=inst_id,
            approved=decision.approved,
            reasons=decision.reasons,
        )
        if not decision.approved:
            store.commit()
            print_json(
                {
                    "ok": False,
                    "stage": "risk_rejected",
                    "risk": {"approved": decision.approved, "reasons": list(decision.reasons)},
                    "signal": signal.as_dict(),
                    "risk_capped_intents": [item.as_dict() for item in capped_intents],
                    "db": str(Path(args.db).resolve()),
                }
            )
            return 1

        prepared = build_passive_post_only_order(
            capped_intent=selected,
            trade_intent=trade_intent,
            rules=rules,
            bid=bid,
            ask=ask,
            price_offset_bps=Decimal(args.price_offset_bps),
            client_order_id=client_order_id,
        )
        if not args.execute:
            store.commit()
            print_json(
                {
                    "ok": True,
                    "stage": "dry_run",
                    "env": settings.env,
                    "read_only": True,
                    "market": {"bid": str(bid), "ask": str(ask), "last": str(last)},
                    "risk": {"approved": decision.approved, "reasons": list(decision.reasons)},
                    "signal": signal.as_dict(),
                    "risk_capped_intents": [item.as_dict() for item in capped_intents],
                    "order_payload": prepared.request.to_payload(),
                    "rounded_notional": str(prepared.sized_order.rounded_notional),
                    "db": str(Path(args.db).resolve()),
                }
            )
            return 0

        result = _execute_prepared_order(client, store, prepared, args)
        print_json(result)
        return 0 if result["ok"] else 1


def _execute_prepared_order(
    client: OKXRestClient,
    store: SQLiteEventStore,
    prepared,
    args: argparse.Namespace,
) -> dict[str, object]:
    manager = OrderManager(store)
    request = prepared.request
    manager.create_order(
        Order(
            client_order_id=request.client_order_id,
            inst_id=request.inst_id,
            side=request.side,
            order_type=OrderType.POST_ONLY,
            size=request.size,
            price=request.price,
        )
    )
    manager.apply_status(client_order_id=request.client_order_id, next_status=OrderStatus.SUBMITTED)

    place_ack = parse_order_ack(client.place_order(request))
    if not place_ack.ok:
        manager.apply_status(client_order_id=request.client_order_id, next_status=OrderStatus.REJECTED)
        store.commit()
        return {
            "ok": False,
            "stage": "place_order",
            "s_code": place_ack.s_code,
            "s_msg": place_ack.s_msg,
            "client_order_id": request.client_order_id,
            "db": str(Path(args.db).resolve()),
        }

    manager.apply_status(
        client_order_id=request.client_order_id,
        next_status=OrderStatus.ACCEPTED,
        exchange_order_id=place_ack.exchange_order_id,
    )

    time.sleep(args.cancel_after_seconds)
    snapshot = _poll_order_status(client, request.inst_id, request.client_order_id, timeout_seconds=2.0)
    _sync_snapshot(manager, store, snapshot)

    if store.get_order_status(request.client_order_id) not in TERMINAL_STATUSES:
        manager.apply_status(client_order_id=request.client_order_id, next_status=OrderStatus.CANCEL_PENDING)
        cancel_ack = parse_order_ack(client.cancel_order(OKXCancelOrderRequest(request.inst_id, request.client_order_id)))
        if not cancel_ack.ok:
            store.commit()
            return {
                "ok": False,
                "stage": "cancel_order",
                "s_code": cancel_ack.s_code,
                "s_msg": cancel_ack.s_msg,
                "client_order_id": request.client_order_id,
                "exchange_order_id": place_ack.exchange_order_id,
                "local_status": store.get_order_status(request.client_order_id).value,
                "db": str(Path(args.db).resolve()),
            }

    final_snapshot = _poll_order_status(
        client,
        request.inst_id,
        request.client_order_id,
        timeout_seconds=args.poll_timeout_seconds,
    )
    _sync_snapshot(manager, store, final_snapshot)

    local_status = store.get_order_status(request.client_order_id)
    if local_status not in TERMINAL_STATUSES:
        manager.apply_status(client_order_id=request.client_order_id, next_status=OrderStatus.UNKNOWN)
        local_status = OrderStatus.UNKNOWN

    issues = _reconcile_single_order(client, store, request.inst_id, request.client_order_id, local_status)
    store.commit()
    return {
        "ok": local_status in TERMINAL_STATUSES and not issues,
        "stage": "executed",
        "client_order_id": request.client_order_id,
        "exchange_order_id": place_ack.exchange_order_id,
        "side": request.side.value,
        "ord_type": request.order_type.value,
        "price": str(request.price),
        "size": str(request.size),
        "rounded_notional": str(prepared.sized_order.rounded_notional),
        "final_exchange_state": final_snapshot.raw_state,
        "local_status": local_status.value,
        "reconciliation_issues": [issue.as_dict() for issue in issues],
        "orders": store.count("orders"),
        "risk_events": store.count("risk_events"),
        "reconciliation_runs": store.count("reconciliation_runs"),
        "db": str(Path(args.db).resolve()),
    }


def _sync_snapshot(manager: OrderManager, store: SQLiteEventStore, snapshot: OKXOrderSnapshot) -> None:
    if snapshot.status == OrderStatus.UNKNOWN:
        return
    current = store.get_order_status(snapshot.client_order_id)
    if current == snapshot.status:
        return
    if current in TERMINAL_STATUSES:
        return
    manager.apply_status(
        client_order_id=snapshot.client_order_id,
        next_status=snapshot.status,
        exchange_order_id=snapshot.exchange_order_id,
    )


def _poll_order_status(
    client: OKXRestClient,
    inst_id: str,
    client_order_id: str,
    *,
    timeout_seconds: float,
) -> OKXOrderSnapshot:
    deadline = time.monotonic() + timeout_seconds
    last_snapshot: OKXOrderSnapshot | None = None
    while time.monotonic() <= deadline:
        last_snapshot = parse_order_snapshot(client.get_order(inst_id=inst_id, client_order_id=client_order_id))
        if last_snapshot.status in TERMINAL_STATUSES:
            return last_snapshot
        time.sleep(1)
    if last_snapshot is None:
        raise RuntimeError("order polling did not run")
    return last_snapshot


def _reconcile_single_order(
    client: OKXRestClient,
    store: SQLiteEventStore,
    inst_id: str,
    client_order_id: str,
    local_status: OrderStatus,
):
    pending = client.get_orders_pending(inst_type="SPOT", inst_id=inst_id, limit=100)
    history = client.get_orders_history(inst_type="SPOT", inst_id=inst_id, limit=100)
    exchange_orders = parse_okx_order_snapshots([pending, history])
    issues = reconcile_order_statuses(
        {client_order_id: local_status},
        exchange_orders,
        flag_extra_exchange_orders=False,
    )
    now = datetime.now(timezone.utc)
    store.insert_reconciliation_run(
        run_id=uuid4().hex,
        started_at=now,
        finished_at=datetime.now(timezone.utc),
        status="failed" if issues else "passed",
        summary={
            "client_order_id": client_order_id,
            "local_status": local_status.value,
            "exchange_orders": len(exchange_orders),
            "issue_count": len(issues),
            "issues": [issue.as_dict() for issue in issues],
        },
    )
    return issues


def _build_signal(
    client: OKXRestClient,
    target_weights: dict[str, Decimal],
    threshold: Decimal,
    min_trade_notional: Decimal,
):
    balances = {balance.ccy: balance for balance in parse_okx_account_balances(client.get_balance())}
    assets = [
        PortfolioAsset(
            asset=asset,
            quantity=balances.get(asset).available if balances.get(asset) else Decimal("0"),
            price_usdt=parse_okx_ticker_last(client.get_ticker(f"{asset}-USDT")),
        )
        for asset in target_weights
        if asset != "USDT"
    ]
    return generate_rebalance_signal(
        cash_usdt=balances.get("USDT").available if balances.get("USDT") else Decimal("0"),
        assets=assets,
        target_weights=target_weights,
        threshold=threshold,
        min_trade_notional=min_trade_notional,
    )


def _instrument_rules(client: OKXRestClient, inst_id: str) -> InstrumentRules:
    instruments = client.get_public_instruments("SPOT").get("data", [])
    instrument = next(item for item in instruments if item.get("instId") == inst_id)
    return InstrumentRules.from_okx(instrument)


def _crypto_exposure(signal) -> Decimal:
    return signal.equity_usdt * sum(weight for asset, weight in signal.weights.items() if asset != "USDT")


def _parse_weights(raw: str) -> dict[str, Decimal]:
    result: dict[str, Decimal] = {}
    for item in raw.split(","):
        key, value = item.split("=", 1)
        result[key.strip()] = Decimal(value.strip())
    return result


def print_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
