from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    telegram_bot_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")

    # OKX — leave empty for public data (MVP); required for execution (M4+).
    okx_api_key: str = Field(default="")
    okx_api_secret: str = Field(default="")
    okx_api_passphrase: str = Field(default="")

    # Logging
    log_level: str = Field(default="INFO")

    # Symbols to monitor — comma-separated in .env, list in code.
    symbols: list[str] = Field(default=["SOL-USDT-SWAP", "TON-USDT-SWAP", "XPL-USDT-SWAP"])

    # Decision layer
    alert_confidence_threshold: int = Field(default=75, ge=0, le=100)
    cooldown_hours: int = Field(default=4, ge=0)

    # Storage
    data_dir: Path = Field(default=Path("data"))

    # Weights config — YAML file with per-regime engine weights.
    weights_path: Path = Field(default=Path("config/weights.yaml"))

    # OKX fetch retry / backoff — tunable without code changes.
    okx_max_retries: int = Field(default=5, ge=1)
    okx_retry_base_delay: float = Field(default=2.0, ge=0.0)
    okx_retry_max_delay: float = Field(default=60.0, ge=0.0)

    @field_validator("symbols", mode="before")
    @classmethod
    def _parse_symbols(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return list(v)

    @property
    def okx_is_authenticated(self) -> bool:
        return bool(self.okx_api_key and self.okx_api_secret and self.okx_api_passphrase)


def load_weights(path: Path) -> dict[str, Any]:
    """Load regime-conditional engine weights from a YAML file."""
    if not path.exists():
        raise FileNotFoundError(f"Weights file not found: {path}")
    with path.open("r") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Weights file must be a YAML mapping, got {type(data)}")
    return data


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return a singleton Settings instance (loaded once from .env)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
