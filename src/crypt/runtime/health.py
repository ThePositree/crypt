from __future__ import annotations

import shutil

import ccxt.async_support as ccxt
from loguru import logger

from crypt.config import Settings

_MIN_FREE_BYTES = 1 * 1024**3  # 1 GB


async def run_health_check(settings: Settings) -> None:
    """
    Verify OKX connectivity and optional Telegram reachability on startup.

    Logs warnings for failures but never raises — a degraded start is better
    than no start.
    """
    _check_disk_space(settings)
    await _check_okx(settings)
    if settings.telegram_bot_token and settings.telegram_chat_id:
        await _check_telegram(settings)


def _check_disk_space(settings: Settings) -> None:
    try:
        stat = shutil.disk_usage(settings.data_dir if settings.data_dir.exists() else ".")
        if stat.free < _MIN_FREE_BYTES:
            logger.warning(
                "Low disk space: {:.1f} GB free on data_dir filesystem (minimum 1 GB recommended)",
                stat.free / 1024**3,
            )
        else:
            logger.info("Disk space: {:.1f} GB free", stat.free / 1024**3)
    except Exception as exc:
        logger.warning("Disk space check failed: {}", exc)


async def _check_okx(settings: Settings) -> None:
    exchange: ccxt.okx = ccxt.okx({"enableRateLimit": True, "options": {"defaultType": "swap"}})
    try:
        # fetch_time() is a lightweight public endpoint (GET /api/v5/public/time).
        await exchange.fetch_time()
        logger.info("OKX connectivity: OK")

        # Verify each configured symbol exists.
        # CCXT keyed dict uses normalised symbols (e.g. "SOL/USDT:USDT"), but
        # the raw OKX instId (e.g. "SOL-USDT-SWAP") lives in market["id"].
        try:
            markets = await exchange.load_markets()
            okx_ids = {m["id"] for m in markets.values()}
            for symbol in settings.symbols:
                if symbol in okx_ids:
                    logger.info("Symbol {} found on OKX", symbol)
                else:
                    logger.warning(
                        "Symbol {} NOT found on OKX — it may not exist or may be delisted. "
                        "Check SYMBOLS in .env.",
                        symbol,
                    )
        except Exception as exc:
            logger.warning("Could not load OKX market list: {}", exc)
    except Exception as exc:
        logger.warning("OKX connectivity check failed: {}", exc)
    finally:
        await exchange.close()


async def _check_telegram(settings: Settings) -> None:
    import httpx

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/getMe"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
        if resp.status_code == 200 and resp.json().get("ok"):
            logger.info("Telegram bot: OK ({})", resp.json()["result"].get("username"))
        else:
            logger.warning("Telegram bot check returned unexpected response: {}", resp.text[:200])
    except Exception as exc:
        logger.warning("Telegram connectivity check failed: {}", exc)
