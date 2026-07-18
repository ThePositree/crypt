from __future__ import annotations

import shutil
from typing import Any

import ccxt.async_support as ccxt
from loguru import logger

from crypt.config import Settings

_MIN_FREE_BYTES = 1 * 1024**3  # 1 GB


async def run_health_check(settings: Settings) -> list[str]:
    """
    Verify OKX connectivity and optional Telegram reachability on startup.

    Logs warnings for failures but never raises — a degraded start is better
    than no start.
    """
    issues: list[str] = []
    if issue := _check_disk_space(settings):
        issues.append(issue)
    issues.extend(await _check_okx(settings))
    if (
        settings.telegram_bot_token
        and settings.telegram_chat_id
        and (issue := await _check_telegram(settings))
    ):
        issues.append(issue)
    return issues


def _check_disk_space(settings: Settings) -> str | None:
    try:
        stat = shutil.disk_usage(settings.data_dir if settings.data_dir.exists() else ".")
        if stat.free < _MIN_FREE_BYTES:
            logger.warning(
                "Low disk space: {:.1f} GB free on data_dir filesystem (minimum 1 GB recommended)",
                stat.free / 1024**3,
            )
            return f"low disk space: {stat.free / 1024**3:.1f} GB free"
        logger.info("Disk space: {:.1f} GB free", stat.free / 1024**3)
    except Exception as exc:
        logger.warning("Disk space check failed: {}", exc)
        return f"disk space check failed: {exc}"
    return None


async def _check_okx(settings: Settings) -> list[str]:
    issues: list[str] = []
    exchange: ccxt.okx = ccxt.okx(
        {"enableRateLimit": True, "timeout": 30_000, "options": {"defaultType": "swap"}}
    )
    try:
        # fetch_time() is a lightweight public endpoint (GET /api/v5/public/time).
        await exchange.fetch_time()
        logger.info("OKX connectivity: OK")

        # Query only SWAP instruments. Loading every CCXT market can fail when
        # a transient malformed instrument has a null symbol component.
        try:
            response = await exchange.publicGetPublicInstruments({"instType": "SWAP"})
            okx_ids = _okx_swap_ids(response)
            for symbol in settings.symbols:
                if symbol in okx_ids:
                    logger.info("Symbol {} found on OKX", symbol)
                else:
                    logger.warning(
                        "Symbol {} NOT found on OKX — it may not exist or may be delisted. "
                        "Check SYMBOLS in .env.",
                        symbol,
                    )
                    issues.append(f"symbol {symbol} not found on OKX")
        except Exception as exc:
            logger.warning("Could not load OKX market list: {}", exc)
            issues.append(f"could not load OKX market list: {exc}")
    except Exception as exc:
        logger.warning("OKX connectivity check failed: {}", exc)
        issues.append(f"OKX connectivity check failed: {exc}")
    finally:
        await exchange.close()
    return issues


def _okx_swap_ids(response: Any) -> set[str]:
    """Extract valid instrument IDs from an OKX public instruments response."""
    if not isinstance(response, dict):
        return set()
    data = response.get("data")
    if not isinstance(data, list):
        return set()
    return {
        str(item["instId"])
        for item in data
        if isinstance(item, dict) and isinstance(item.get("instId"), str) and item["instId"]
    }


async def _check_telegram(settings: Settings) -> str | None:
    import httpx

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/getMe"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
        if resp.status_code == 200 and resp.json().get("ok"):
            logger.info("Telegram bot: OK ({})", resp.json()["result"].get("username"))
            return None
        logger.warning("Telegram bot check returned unexpected response: {}", resp.text[:200])
        return f"Telegram bot check failed: {resp.text[:200]}"
    except Exception as exc:
        logger.warning("Telegram connectivity check failed: {}", exc)
        return f"Telegram connectivity check failed: {exc}"
