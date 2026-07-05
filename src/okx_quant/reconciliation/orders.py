"""Order reconciliation rules."""

from __future__ import annotations

from dataclasses import dataclass

from okx_quant.domain.enums import OrderStatus


@dataclass(frozen=True)
class ExchangeOrderSnapshot:
    client_order_id: str
    status: OrderStatus
    exchange_order_id: str | None = None


@dataclass(frozen=True)
class ReconciliationIssue:
    code: str
    client_order_id: str
    local_status: str | None
    exchange_status: str | None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "code": self.code,
            "client_order_id": self.client_order_id,
            "local_status": self.local_status,
            "exchange_status": self.exchange_status,
        }


def reconcile_order_statuses(
    local_statuses: dict[str, OrderStatus],
    exchange_orders: list[ExchangeOrderSnapshot],
    *,
    flag_extra_exchange_orders: bool = True,
) -> list[ReconciliationIssue]:
    issues: list[ReconciliationIssue] = []
    exchange_by_client_id = {order.client_order_id: order for order in exchange_orders}

    for client_order_id, local_status in local_statuses.items():
        exchange_order = exchange_by_client_id.get(client_order_id)
        if exchange_order is None:
            issues.append(
                ReconciliationIssue(
                    code="missing_exchange_order",
                    client_order_id=client_order_id,
                    local_status=local_status.value,
                    exchange_status=None,
                )
            )
            continue
        if exchange_order.status != local_status:
            issues.append(
                ReconciliationIssue(
                    code="order_status_mismatch",
                    client_order_id=client_order_id,
                    local_status=local_status.value,
                    exchange_status=exchange_order.status.value,
                )
            )

    if flag_extra_exchange_orders:
        for client_order_id, exchange_order in exchange_by_client_id.items():
            if client_order_id not in local_statuses:
                issues.append(
                    ReconciliationIssue(
                        code="missing_local_order",
                        client_order_id=client_order_id,
                        local_status=None,
                        exchange_status=exchange_order.status.value,
                    )
                )

    return issues


def parse_okx_order_snapshots(payloads: list[dict[str, object]]) -> list[ExchangeOrderSnapshot]:
    snapshots: list[ExchangeOrderSnapshot] = []
    for payload in payloads:
        data = payload.get("data")
        if not isinstance(data, list):
            continue
        for item in data:
            if not isinstance(item, dict):
                continue
            client_order_id = str(item.get("clOrdId") or "")
            if not client_order_id:
                continue
            snapshots.append(
                ExchangeOrderSnapshot(
                    client_order_id=client_order_id,
                    exchange_order_id=str(item.get("ordId") or "") or None,
                    status=_map_exchange_state(str(item.get("state") or "")),
                )
            )
    return snapshots


def _map_exchange_state(state: str) -> OrderStatus:
    mapping = {
        "live": OrderStatus.ACCEPTED,
        "partially_filled": OrderStatus.PARTIALLY_FILLED,
        "filled": OrderStatus.FILLED,
        "canceled": OrderStatus.CANCELLED,
        "mmp_canceled": OrderStatus.CANCELLED,
    }
    return mapping.get(state, OrderStatus.UNKNOWN)
