"""Account balance models."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class AccountBalance:
    ccy: str
    equity: Decimal
    available: Decimal
    frozen: Decimal


def parse_okx_account_balances(payload: dict[str, object]) -> list[AccountBalance]:
    balances: list[AccountBalance] = []
    data = payload.get("data")
    if not isinstance(data, list):
        return balances
    for account in data:
        if not isinstance(account, dict):
            continue
        details = account.get("details")
        if not isinstance(details, list):
            continue
        for item in details:
            if not isinstance(item, dict):
                continue
            ccy = str(item.get("ccy") or "")
            if not ccy:
                continue
            balances.append(
                AccountBalance(
                    ccy=ccy,
                    equity=Decimal(str(item.get("eq") or "0")),
                    available=Decimal(str(item.get("availBal") or item.get("availEq") or "0")),
                    frozen=Decimal(str(item.get("frozenBal") or "0")),
                )
            )
    return balances

