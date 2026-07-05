"""Runtime settings loaded from environment variables."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import os
from pathlib import Path


@dataclass(frozen=True)
class OKXSettings:
    env: str
    api_key: str
    api_secret: str
    passphrase: str
    simulated_trading: bool
    live_capital_limit_usdt: Decimal
    read_only_mode: bool
    kill_switch: bool

    @property
    def is_live(self) -> bool:
        return self.env == "live"

    def validate_for_private_api(self) -> None:
        missing = [
            name
            for name, value in {
                "OKX_API_KEY": self.api_key,
                "OKX_API_SECRET": self.api_secret,
                "OKX_API_PASSPHRASE": self.passphrase,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(f"Missing private API settings: {', '.join(missing)}")
        if self.is_live and self.simulated_trading:
            raise ValueError("live environment cannot use simulated trading header")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_okx_settings() -> OKXSettings:
    env = os.getenv("OKX_ENV", "demo").strip().lower()
    if env not in {"demo", "live"}:
        raise ValueError("OKX_ENV must be demo or live")

    return OKXSettings(
        env=env,
        api_key=os.getenv("OKX_API_KEY", ""),
        api_secret=os.getenv("OKX_API_SECRET", ""),
        passphrase=os.getenv("OKX_API_PASSPHRASE", ""),
        simulated_trading=_env_bool("OKX_SIMULATED_TRADING", env == "demo"),
        live_capital_limit_usdt=Decimal(os.getenv("LIVE_CAPITAL_LIMIT_USDT", "300")),
        read_only_mode=_env_bool("READ_ONLY_MODE", True),
        kill_switch=_env_bool("KILL_SWITCH", False),
    )


def load_env_file(path: str | Path, *, override: bool = True) -> None:
    env_path = Path(path)
    if not env_path.exists():
        raise FileNotFoundError(env_path)

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"Invalid env line: {raw_line}")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if override or key not in os.environ:
            os.environ[key] = value

