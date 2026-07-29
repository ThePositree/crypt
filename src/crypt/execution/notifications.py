# ruff: noqa: RUF001

"""Russian, operator-oriented Telegram notifications for live execution."""

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
_MAX_TECHNICAL_DETAIL = 1_200
_MAX_BLOCKING_REASONS = 5
_MAX_TELEGRAM_MESSAGE = 4_000
_MAX_ESCAPED_DYNAMIC_FIELD = 900


@dataclass(frozen=True)
class ExecutionTelegramNotifier:
    """Best-effort Russian-language notifier for live execution events."""

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
    ) -> bool:
        entries_allowed = (
            state.last_exchange_sync_ok and state.risk_base_continuity_status != "blocked"
        )
        lines = [
            _title(
                "Проверка бота",
                icon="🟢" if entries_allowed else "⚠️",
                status="ok" if entries_allowed else "blocked",
                dry_run=self._dry_run,
            ),
            f"Время проверки (UTC): {_esc(snapshot.fetched_at.isoformat())}",
            (
                "Баланс: "
                f"всего ${snapshot.balance.total:,.2f} · "
                f"доступно ${snapshot.balance.free:,.2f} · "
                f"в работе/маржа ${snapshot.balance.used:,.2f}"
            ),
            *(
                [f"Equity OKX: ${snapshot.balance.equity:,.2f} (с учётом нереализованного PnL)"]
                if snapshot.balance.equity is not None
                else []
            ),
            f"Позиции: бот — {len(state.all_open_positions())}, OKX — {len(snapshot.positions)}",
            f"Ордера: обычные — {len(snapshot.open_orders)}, защитные — {len(snapshot.algo_orders)}",
            f"Новые входы: {'разрешены' if entries_allowed else 'приостановлены'}",
            f"Риск-база месяца: ${state.monthly_risk_base:,.2f}",
            f"Проверка риск-базы: {_continuity_label(state.risk_base_continuity_status)}",
        ]
        if state.risk_base_continuity_error:
            lines.append(
                "Причина паузы риск-базы: "
                f"<code>{_esc(_short(state.risk_base_continuity_error, 280))}</code>"
            )
        if state.last_exchange_sync_errors:
            lines.append("Почему входы приостановлены:")
            lines.extend(
                f"• <code>{_esc(_short(reason, 240))}</code>"
                for reason in state.last_exchange_sync_errors[:_MAX_BLOCKING_REASONS]
            )
            if len(state.last_exchange_sync_errors) > _MAX_BLOCKING_REASONS:
                lines.append(
                    f"• и ещё {len(state.last_exchange_sync_errors) - _MAX_BLOCKING_REASONS} причин"
                )
        open_positions = state.all_open_positions()
        if open_positions:
            lines.append("")
            lines.append("Открытые сделки бота:")
            for pos in open_positions[:12]:
                lines.append(_position_line(pos))
            if len(open_positions) > 12:
                lines.append(f"… ещё {len(open_positions) - 12} сделок")
        return await self._send("\n".join(lines))

    async def send_entry_opened(self, pos: LivePosition) -> bool:
        protection = (
            f"Защита: SL ${pos.sl_price:,.4f} · цель TP ${pos.tp_price:,.4f}"
            if pos.fixed_take_profit_enabled
            else f"Защита: SL ${pos.sl_price:,.4f} · фиксированная цель TP не установлена"
        )
        trailing = (
            (
                "Плавающая защита: включится от "
                f"${pos.trail_activation_price:,.4f} · шаг ${pos.trail_callback_spread:,.4f}"
            )
            if pos.trail_activation_price is not None and pos.trail_callback_spread is not None
            else "Плавающая защита: выключена"
        )
        tp_adjustment = _tp_adjustment_line(pos.signal_event)
        text = "\n".join(
            [
                _title("Сделка открыта", icon="✅", status="ok", dry_run=self._dry_run),
                f"Инструмент: {_esc(pos.symbol)} · {_side_label(pos.is_long)}",
                f"Объём: {pos.contracts} контрактов · {pos.size:.4f} {_asset_label(pos.symbol)}",
                f"Цена входа: ${pos.entry_price:,.4f}",
                protection,
                *([tp_adjustment] if tp_adjustment else []),
                trailing,
                (
                    f"Ориентир ликвидации: ${pos.liquidation_price:,.4f}"
                    if pos.liquidation_price is not None
                    else "Ориентир ликвидации: пока недоступен"
                ),
                f"Маржа: ${pos.locked_margin:,.2f} · плечо: {pos.leverage:.0f}x",
                f"Риск-база месяца: ${pos.risk_base_capital:,.2f}",
                f"Стратегия: <code>{_esc(pos.selected_strategy or 'unknown')}</code>",
                f"Ордер: <code>{_esc(pos.entry_order_id or 'dry-run')}</code>",
            ]
        )
        return await self._send(text)

    async def send_entry_attempt(
        self,
        *,
        symbol: str,
        is_long: bool,
        strategy: str,
        signal_time: datetime,
        entry_price: float,
        sl_price: float,
    ) -> bool:
        return await self._send(
            "\n".join(
                [
                    _title("Найден сигнал", icon="🔎", status="pending", dry_run=self._dry_run),
                    "Сигнал передан на проверку; следующее сообщение подтвердит результат.",
                    f"Инструмент: {_esc(symbol)} · {_side_label(is_long)}",
                    f"Ориентир входа: ${entry_price:,.4f}",
                    f"Защитный стоп SL: ${sl_price:,.4f}",
                    f"Время сигнала (UTC): {_esc(signal_time.isoformat())}",
                    f"Стратегия: <code>{_esc(strategy or 'unknown')}</code>",
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
    ) -> bool:
        return await self._send(
            "\n".join(
                [
                    _title("Вход пропущен", icon="🚫", status="warning", dry_run=self._dry_run),
                    "Ордер не отправлен; деньги в этой сделке не задействованы.",
                    f"Инструмент: {_esc(symbol)} · {_side_label(is_long)}",
                    f"Причина: {_humanize_rejection(reason)}",
                    f"Стратегия: <code>{_esc(strategy or 'unknown')}</code>",
                    f"Техническая деталь: <code>{_esc(_short(reason, 420))}</code>",
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
    ) -> bool:
        return await self._send(
            "\n".join(
                [
                    _title(
                        "Цена входа отличается от плана",
                        icon="⚠️",
                        status="warning",
                        dry_run=self._dry_run,
                    ),
                    "Сделка уже открыта; это предупреждение, а не отказ от входа.",
                    f"Инструмент: {_esc(symbol)}",
                    f"Плановая цена H1: ${h1_open:,.4f}",
                    f"Цена перед отправкой: ${quote:,.4f}",
                    f"Фактическая цена входа: ${fill:,.4f}",
                    f"Отклонение от плана: {h1_fill_drift_pct:.3%}",
                    f"Отклонение от котировки: {quote_fill_drift_pct:.3%}",
                    f"Стратегия: <code>{_esc(strategy or 'unknown')}</code>",
                ]
            )
        )

    async def send_execution_error(self, *, context: str, detail: str) -> bool:
        status = "blocked" if _context_blocks_entries(context) else "warning"
        icon = "🛑" if status == "blocked" else "⚠️"
        impact = _humanize_error_impact(context)
        return await self._send(
            "\n".join(
                [
                    _title("Нужна проверка", icon=icon, status=status, dry_run=self._dry_run),
                    impact,
                    f"Что произошло: {_humanize_context(context)}",
                    f"Технический контекст: <code>{_esc(_short(context, 300))}</code>",
                    f"Техническая деталь: <code>{_esc(_short(detail, _MAX_TECHNICAL_DETAIL))}</code>",
                ]
            )
        )

    async def send_risk_base_continuity_blocked(
        self,
        *,
        reason: str,
        checkpoint_dir: str,
        state_path: str,
    ) -> bool:
        return await self._send(
            "\n".join(
                [
                    _title(
                        "Проверка риск-базы не пройдена",
                        icon="🛑",
                        status="blocked",
                        dry_run=self._dry_run,
                    ),
                    "Новые входы остановлены. Открытые сделки продолжают сопровождаться.",
                    "Причина: состояние месяца нельзя безопасно подтвердить после перезапуска.",
                    f"Техническая деталь: <code>{_esc(_short(reason, 700))}</code>",
                    f"Файл состояния: <code>{_esc(_short(state_path, 220))}</code>",
                    f"Каталог контрольных копий: <code>{_esc(_short(checkpoint_dir, 220))}</code>",
                ]
            )
        )

    async def send_missed_signal(
        self,
        *,
        symbol: str,
        is_long: bool,
        strategy: str,
        signal_time: datetime,
        entry_price: float,
        sl_price: float,
        blocking_reasons: list[str],
        cumulative_count: int,
    ) -> bool:
        reasons = "; ".join(_short(item, 180) for item in blocking_reasons[:3])
        return await self._send(
            "\n".join(
                [
                    _title(
                        "Сигнал пропущен из-за защиты",
                        icon="⚠️",
                        status="blocked",
                        dry_run=self._dry_run,
                    ),
                    "Ордер не отправлен: автоматическая защита временно остановила новые входы.",
                    f"Инструмент: {_esc(symbol)} · {_side_label(is_long)}",
                    f"Ориентир входа: ${entry_price:,.4f} · SL: ${sl_price:,.4f}",
                    f"Время сигнала (UTC): {_esc(signal_time.isoformat())}",
                    f"Стратегия: <code>{_esc(strategy or 'unknown')}</code>",
                    f"Причина защиты: <code>{_esc(reasons or 'unknown')}</code>",
                    f"Всего пропущено из-за защиты: {cumulative_count}",
                ]
            )
        )

    async def send_position_closed(self, pos: LivePosition) -> bool:
        lines = [
            _title("Сделка закрыта", icon="🏁", status="ok", dry_run=self._dry_run),
            f"Инструмент: {_esc(pos.symbol)} · {_side_label(pos.is_long)}",
            f"Причина: {_exit_reason_label(pos.exit_reason)}",
            f"Цена входа: ${pos.entry_price:,.4f}",
        ]
        if (
            pos.aggregate_entry_price is not None
            and abs(pos.aggregate_entry_price - pos.entry_price) > 1e-9
        ):
            lines.append(f"Средняя цена OKX: ${pos.aggregate_entry_price:,.4f}")
        if pos.exit_price is not None:
            lines.append(f"Цена выхода: ${pos.exit_price:,.4f}")
        if pos.realized_pnl is not None:
            lines.append(f"PnL: ${pos.realized_pnl:,.2f}")
        if pos.exit_fee is not None:
            lines.append(f"Комиссия за выход: ${pos.exit_fee:,.2f}")
        lines.extend(
            [
                f"Стратегия: <code>{_esc(pos.selected_strategy or 'unknown')}</code>",
                f"Позиция: <code>{_esc(pos.position_id[:8])}</code>",
            ]
        )
        return await self._send("\n".join(lines))

    async def _send(self, text: str) -> bool:
        import logging

        logger = logging.getLogger(__name__)
        text = _limit_telegram_message(text)
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                await self._bot.send_message(self._chat_id, text)
                return True
            except Exception as exc:
                if attempt == _MAX_RETRIES:
                    logger.error(
                        "Execution Telegram send failed after %d retries: %s", _MAX_RETRIES, exc
                    )
                    return False
                wait = (_RETRY_BACKOFF**attempt) * random.uniform(0.5, 1.5)
                logger.warning(
                    "Execution Telegram send attempt %d/%d failed (%s), retrying in %.1fs",
                    attempt,
                    _MAX_RETRIES,
                    exc,
                    wait,
                )
                await asyncio.sleep(wait)
        return False

    async def close(self) -> None:
        await self._bot.session.close()


def _title(heading: str, *, icon: str, status: str, dry_run: bool) -> str:
    mode = "ТЕСТОВЫЙ РЕЖИМ" if dry_run else "РЕАЛЬНЫЕ СДЕЛКИ"
    status_label = {
        "pending": "проверка",
        "ok": "всё в порядке",
        "warning": "предупреждение",
        "blocked": "входы остановлены",
    }[status]
    return f"<b>{icon} {heading}</b>\n<i>{mode} · {status_label}</i>"


def _side_label(is_long: bool) -> str:
    return "покупка — расчёт на рост" if is_long else "продажа — расчёт на снижение"


def _asset_label(symbol: str) -> str:
    asset = symbol.split("-", maxsplit=1)[0]
    return _esc(asset or "единиц актива")


def _continuity_label(status: str) -> str:
    return {
        "verified": "подтверждена",
        "recovered": "восстановлена из сохранённого якоря",
        "pending_rollover": "ожидается первый вход нового месяца",
        "adopted": "явно подтверждена при миграции",
        "rolled_over": "зафиксирована на новый месяц",
        "not_applicable": "не требуется в тестовом/немесячном режиме",
        "blocked": "не пройдена — новые входы остановлены",
    }.get(status, "ещё не подтверждена")


def _humanize_rejection(reason: str) -> str:
    lowered = reason.lower()
    if "margin" in lowered or "capital" in lowered:
        return "на счёте недостаточно свободных средств для безопасного объёма"
    if "leverage" in lowered or "liquidation" in lowered:
        return "объём или плечо не прошли проверку безопасности"
    if "already processed" in lowered:
        return "такой сигнал уже был обработан ранее"
    if "precision" in lowered or "rounding" in lowered:
        return "округление биржи сделало параметры сделки небезопасными"
    if "trailing" in lowered:
        return "не удалось безопасно подготовить плавающую защиту"
    if "risk" in lowered or "fee" in lowered or "exposure" in lowered:
        return "сделка не прошла встроенную проверку риска"
    return "сделка не прошла одну из защитных проверок"


def _context_blocks_entries(context: str) -> bool:
    lowered = context.lower()
    return "synchronization blocked" in lowered or "risk-base continuity blocked" in lowered


def _humanize_error_impact(context: str) -> str:
    lowered = context.lower()
    if "actual fill risk" in lowered:
        return "Сделка уже открыта. Цена исполнения изменила риск относительно плана; бот продолжает сопровождение."
    if "synchronization blocked" in lowered or "risk-base continuity blocked" in lowered:
        return "Новые входы временно остановлены до безопасной проверки состояния. Открытые сделки остаются под наблюдением."
    if "telegram" in lowered:
        return "Проблема с доставкой Telegram. Торговая логика и сохранение состояния продолжают работать отдельно."
    if "startup" in lowered:
        return "При запуске бота нужна проверка. Новые входы откроются только после нормальной работы защитных проверок."
    return (
        "Бот зафиксировал техническую проблему. Не считайте позицию защищённой, "
        "пока не сверите состояние и защитные ордера в OKX."
    )


def _humanize_context(context: str) -> str:
    lowered = context.lower()
    if "actual fill risk" in lowered:
        return "фактическая цена входа дала риск выше планового"
    if "exchange synchronization blocked" in lowered:
        return "локальное состояние не совпало с данными OKX"
    if "risk-base continuity blocked" in lowered:
        return "не удалось подтвердить сохранённую риск-базу месяца"
    if "h1 execution callback" in lowered:
        return "не удалось обработать новый час рынка"
    if "startup" in lowered:
        return "проверка при запуске"
    if "periodic service health check" in lowered:
        return "периодическая проверка связи"
    if "place entry" in lowered:
        return "не удалось отправить ордер на вход"
    if "set leverage" in lowered:
        return "биржа не подтвердила настройку плеча"
    if "ttl close" in lowered:
        return "не удалось вовремя закрыть сделку по лимиту времени"
    return "внутренняя проверка исполнения"


def _exit_reason_label(reason: str | None) -> str:
    raw = reason or "unknown"
    label = {
        "stop_loss": "сработал защитный стоп SL",
        "take_profit": "достигнута цель прибыли TP",
        "ttl_expired": "истёк лимит времени сделки",
        "exchange_reduced_unknown": "биржа сократила позицию; причину нужно проверить",
        "exchange_closed_unknown": "биржа закрыла позицию; причину нужно проверить",
        "unsafe_liquidation_buffer": "бот закрыл сделку из-за риска ликвидации",
    }.get(raw, "причина закрытия требует проверки")
    return f"{label} <code>[{_esc(raw)}]</code>"


def _position_line(pos: LivePosition) -> str:
    return (
        f"• {_esc(pos.symbol)} · {_side_label(pos.is_long)} · {pos.contracts} контрактов\n"
        f"  вход ${pos.entry_price:,.4f} · SL ${pos.sl_price:,.4f} · TP ${pos.tp_price:,.4f}"
    )


def _tp_adjustment_line(signal_event: dict[str, object]) -> str | None:
    if not bool(signal_event.get("tp_adjusted", False)):
        return None
    original = signal_event.get("original_rrr")
    effective = signal_event.get("effective_rrr")
    reason = str(signal_event.get("tp_adjustment_reason", "reachability"))
    return (
        f"Цель TP сокращена политикой достижимости: RRR {original} → {effective} "
        f"(<code>{_esc(reason)}</code>)"
    )


def _short(value: object, limit: int) -> str:
    text = str(value)
    return text if len(text) <= limit else f"{text[: limit - 1]}…"


def _esc(value: object) -> str:
    """Escape one dynamic field without splitting an HTML entity at the limit."""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n").replace("\n", " ↩ ")
    escaped: list[str] = []
    used = 0
    for char in text:
        encoded = html.escape(char, quote=False)
        if used + len(encoded) > _MAX_ESCAPED_DYNAMIC_FIELD - 1:
            escaped.append("…")
            break
        escaped.append(encoded)
        used += len(encoded)
    return "".join(escaped)


def _limit_telegram_message(text: str) -> str:
    """Keep a rendered message under Telegram's 4096-character HTML limit.

    Renderers keep every HTML tag within a single line. Limiting by complete
    lines therefore cannot leave a half-open ``<code>``/``<b>`` tag behind.
    Dynamic values are normalised to one line by ``_esc`` above.
    """
    if len(text) <= _MAX_TELEGRAM_MESSAGE:
        return text

    kept: list[str] = []
    omitted = False
    for line in text.splitlines():
        candidate = "\n".join([*kept, line])
        if len(candidate) <= _MAX_TELEGRAM_MESSAGE:
            kept.append(line)
        else:
            omitted = True

    if not omitted:
        return text
    suffix = "<i>… Часть технических деталей не поместилась в сообщение.</i>"
    while kept and len("\n".join([*kept, suffix])) > _MAX_TELEGRAM_MESSAGE:
        kept.pop()
    return "\n".join([*kept, suffix])
