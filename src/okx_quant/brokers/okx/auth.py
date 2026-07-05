"""OKX REST authentication helpers."""

from __future__ import annotations

from base64 import b64encode
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac


def okx_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sign_okx_request(secret_key: str, timestamp: str, method: str, request_path: str, body: str = "") -> str:
    message = f"{timestamp}{method.upper()}{request_path}{body}"
    digest = hmac.new(secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
    return b64encode(digest).decode("ascii")


@dataclass(frozen=True)
class OKXAuth:
    api_key: str
    secret_key: str
    passphrase: str
    simulated_trading: bool

    def headers(self, method: str, request_path: str, body: str = "") -> dict[str, str]:
        timestamp = okx_timestamp()
        headers = {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": sign_okx_request(self.secret_key, timestamp, method, request_path, body),
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
        }
        if self.simulated_trading:
            headers["x-simulated-trading"] = "1"
        return headers

