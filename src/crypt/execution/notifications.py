"""Telegram notifications for live execution state changes."""

from __future__ import annotations

import asyncio
import html
import random
from dataclasses import dataclass
from datetime import datetime

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from crypt.config import Settings
from crypt.execution.exchange_sync import ExchangeSnapshot
from crypt.execution.position_state import ExecutionState, LivePosition

_MAX_RETRIES = 3
_RETRY_BACKOFF = 2.0


@dataclass(frozen=True)
class ExecutionTelegramNotifier:
    """Best-effort Telegram notifier for live execution events."""

    _bot: Bot
    _chat_id: str
    _dry_run: bool

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        dry_run: bool,
    ) -> ExecutionTelegramNotifier | None:
        if not settings.telegram_bot_token or not settings.telegram_chat_id:
            return None
        bot = Bot(
            token=settings.telegram_bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        return cls(_bot=bot, _chat_id=settings.telegram_chat_id, _dry_run=dry_run)

    async def send_daily_sync_report(
        self,
        *,
        snapshot: ExchangeSnapshot,
        state: ExecutionState,
    ) -> None:
        lines = [
            _title("FULL SYNC", ok=state.last_exchange_sync_ok, dry_run=self._dry_run),
            f"Time: {_esc(snapshot.fetched_at.isoformat())}",
            (
                "Balance: "
                f"total ${snapshot.balance.total:,.2f} | "
                f"free ${snapshot.balance.free:,.2f} | "
                f"used ${snapshot.balance.used:,.2f}"
            ),
            f"Position mode: {'long/short' if snapshot.position_mode_hedged else 'NOT long/short'}",
            f"Local open positions: {len(state.all_open_positions())}",
            f"Exchange positions: {len(snapshot.positions)}",
            f"Regular orders: {len(snapshot.open_orders)}",
            f"Algo orders: {len(snapshot.algo_orders)}",
            f"Sync: {'OK' if state.last_exchange_sync_ok else 'BLOCKED'}",
        ]
        if state.last_exchange_sync_errors:
            lines.append("Blocking reasons:")
            lines.extend(f"- {_esc(reason)}" for reason in state.last_exchange_sync_errors)
        open_positions = state.all_open_positions()
        if open_positions:
            lines.append("")
            lines.append("Local positions:")
            for pos in open_positions[:12]:
                lines.append(_position_line(pos))
            if len(open_positions) > 12:
                lines.append(f"... +{len(open_positions) - 12} more")
        await self._send("\n".join(lines))

    async def send_entry_opened(self, pos: LivePosition) -> None:
        side = "LONG" if pos.is_long else "SHORT"
        protection = (
            f"SL: ${pos.sl_price:,.4f} | TP: ${pos.tp_price:,.4f}"
            if pos.fixed_take_profit_enabled
            else f"SL: ${pos.sl_price:,.4f} | fixed TP: not placed"
        )
        trailing = (
            (
                f"Trailing: activePx ${pos.trail_activation_price:,.4f} | "
                f"callback ${pos.trail_callback_spread:,.4f}"
            )
            if pos.trail_activation_price is not None and pos.trail_callback_spread is not None
            else "Trailing: disabled"
        )
        text = "\n".join(
            [
                _title("ENTRY", ok=True, dry_run=self._dry_run),
                f"{_esc(pos.symbol)} {side}",
                f"Contracts: {pos.contracts} | size: {pos.size:.4f}",
                f"Entry: ${pos.entry_price:,.4f}",
                protection,
                trailing,
                (
                    f"Estimated liquidation: ${pos.liquidation_price:,.4f}"
                    if pos.liquidation_price is not None
                    else "Estimated liquidation: unavailable"
                ),
                f"Margin: ${pos.locked_margin:,.2f} | leverage: {pos.leverage:.0f}x",
                f"Risk base: ${pos.risk_base_capital:,.2f}",
                f"Order: {_esc(pos.entry_order_id or 'dry-run')}",
            ]
        )
        await self._send(text)

    async def send_entry_attempt(
        self,
        *,
        symbol: str,
        is_long: bool,
        strategy: str,
        signal_time: datetime,
        entry_price: float,
        sl_price: float,
    ) -> None:
        side = "LONG" if is_long else "SHORT"
        await self._send(
            "\n".join(
                [
                    _title("ENTRY ATTEMPT", ok=None, dry_run=self._dry_run),
                    f"{_esc(symbol)} {side}",
                    f"Strategy: {_esc(strategy or 'unknown')}",
                    f"Signal: {_esc(signal_time.isoformat())}",
                    f"Expected entry: ${entry_price:,.4f}",
                    f"Structural SL: ${sl_price:,.4f}",
                ]
            )
        )

    async def send_entry_rejected(
        self,
        *,
        symbol: str,
        is_long: bool,
        strategy: str,
        reason: str,
    ) -> None:
        side = "LONG" if is_long else "SHORT"
        await self._send(
            "\n".join(
                [
                    _title("ENTRY REJECTED", ok=False, dry_run=self._dry_run),
                    f"{_esc(symbol)} {side}",
                    f"Strategy: {_esc(strategy or 'unknown')}",
                    f"Reason: {_esc(reason)}",
                ]
            )
        )

    async def send_entry_drift_alert(
        self,
        *,
        symbol: str,
        strategy: str,
        h1_open: float,
        quote: float,
        fill: float,
        h1_fill_drift_pct: float,
        quote_fill_drift_pct: float,
    ) -> None:
        await self._send(
            "\n".join(
                [
                    _title("ENTRY DRIFT", ok=True, dry_run=self._dry_run),
                    f"{_esc(symbol)}",
                    f"Strategy: {_esc(strategy or 'unknown')}",
                    f"H1 open: ${h1_open:,.4f}",
                    f"Pre-submit quote: ${quote:,.4f}",
                    f"Actual fill: ${fill:,.4f}",
                    f"H1-to-fill drift: {h1_fill_drift_pct:.3%}",
                    f"Quote-to-fill drift: {quote_fill_drift_pct:.3%}",
                    "Result: entry executed",
                ]
            )
        )

    async def send_execution_error(self, *, context: str, detail: str) -> None:
        await self._send(
            "\n".join(
                [
                    _title("EXECUTION ERROR", ok=False, dry_run=self._dry_run),
                    f"Context: {_esc(context)}",
                    f"Error: {_esc(detail[:2000])}",
                ]
            )
        )

    async def send_position_closed(self, pos: LivePosition) -> None:
        side = "LONG" if pos.is_long else "SHORT"
        lines = [
            _title("EXIT", ok=True, dry_run=self._dry_run),
            f"{_esc(pos.symbol)} {side}",
            f"Reason: {_esc(pos.exit_reason or 'unknown')}",
            f"Entry: ${pos.entry_price:,.4f}",
        ]
        if (
            pos.aggregate_entry_price is not None
            and abs(pos.aggregate_entry_price - pos.entry_price) > 1e-9
        ):
            lines.append(f"OKX side average: ${pos.aggregate_entry_price:,.4f}")
        if pos.exit_price is not None:
            lines.append(f"Exit: ${pos.exit_price:,.4f}")
        if pos.realized_pnl is not None:
            lines.append(f"PnL: ${pos.realized_pnl:,.2f}")
        if pos.exit_fee is not None:
            lines.append(f"Exit fee: ${pos.exit_fee:,.2f}")
        lines.append(f"Position: {_esc(pos.position_id[:8])}")
        await self._send("\n".join(lines))

    async def _send(self, text: str) -> None:
        import logging

        logger = logging.getLogger(__name__)
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                await self._bot.send_message(self._chat_id, text)
                return
            except Exception as exc:
                if attempt == _MAX_RETRIES:
                    logger.error(
                        "Execution Telegram send failed after %d retries: %s", _MAX_RETRIES, exc
                    )
                    return
                wait = (_RETRY_BACKOFF**attempt) * random.uniform(0.5, 1.5)
                logger.warning(
                    "Execution Telegram send attempt %d/%d failed (%s), retrying in %.1fs",
                    attempt,
                    _MAX_RETRIES,
                    exc,
                    wait,
                )
                await asyncio.sleep(wait)

    async def close(self) -> None:
        await self._bot.session.close()


def _title(kind: str, *, ok: bool | None, dry_run: bool) -> str:
    marker = "DRY RUN" if dry_run else "LIVE"
    status = "PENDING" if ok is None else ("OK" if ok else "BLOCKED")
    return f"<b>{kind}</b> [{marker}] [{status}]"


def _position_line(pos: LivePosition) -> str:
    side = "LONG" if pos.is_long else "SHORT"
    return (
        f"- {_esc(pos.symbol)} {side} {pos.contracts} contracts | "
        f"entry ${pos.entry_price:,.4f} | SL ${pos.sl_price:,.4f} | TP ${pos.tp_price:,.4f}"
    )


def _esc(value: object) -> str:
    return html.escape(str(value), quote=False)
