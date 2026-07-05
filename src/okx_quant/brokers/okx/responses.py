"""Response parsing helpers for OKX trade endpoints."""

from __future__ import annotations

from dataclasses import dataclass

from okx_quant.brokers.okx.orders import map_okx_order_state
from okx_quant.domain.enums import OrderStatus


@dataclass(frozen=True)
class OKXOrderAck:
    client_order_id: str
    exchange_order_id: str | None
    s_code: str
    s_msg: str

    @property
    def ok(self) -> bool:
        return self.s_code == "0"


@dataclass(frozen=True)
class OKXOrderSnapshot:
    client_order_id: str
    exchange_order_id: str
    status: OrderStatus
    raw_state: str


def parse_order_ack(payload: dict[str, object]) -> OKXOrderAck:
    item = _first_data_item(payload)
    return OKXOrderAck(
        client_order_id=str(item.get("clOrdId") or ""),
        exchange_order_id=str(item.get("ordId") or "") or None,
        s_code=str(item.get("sCode") or ""),
        s_msg=str(item.get("sMsg") or ""),
    )


def parse_order_snapshot(payload: dict[str, object]) -> OKXOrderSnapshot:
    item = _first_data_item(payload)
    raw_state = str(item.get("state") or "")
    return OKXOrderSnapshot(
        client_order_id=str(item.get("clOrdId") or ""),
        exchange_order_id=str(item.get("ordId") or ""),
        status=map_okx_order_state(raw_state),
        raw_state=raw_state,
    )


def _first_data_item(payload: dict[str, object]) -> dict[str, object]:
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        raise ValueError("OKX response has no data item")
    item = data[0]
    if not isinstance(item, dict):
        raise ValueError("OKX response data item is not an object")
    return item

