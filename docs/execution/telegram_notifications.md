# Telegram notifications for operators

This is the presentation contract for Telegram messages emitted by the live
executor and the legacy decision-alert sink. It does not change trading logic:
OKX state, order placement, and local persistence always happen independently
of Telegram delivery.

## Goal

Telegram is the owner's quick view of money and safety, not a log viewer. The
default operator copy is Russian, explains the practical consequence first,
and keeps enough canonical identifiers to investigate a message in Railway or
OKX later.

Repository prose remains English. Russian literals in this document and the
renderer are localized product copy, not a second documentation language.

## Shared rules

- Use concise Russian headings and labels. Keep `PnL`, `SL`, `TP`, `OKX`,
  tickers, prices, percentages, leverage, and IDs unchanged.
- Explain direction as `покупка — расчёт на рост` or `продажа — расчёт на
  снижение` rather than relying on `LONG` / `SHORT` alone.
- Show a human explanation before a raw reason or exception. Canonical error,
  strategy, order, and position IDs remain in a short technical-detail line.
- Escape all dynamic text before HTML rendering. Limit lists and raw details
  so one Telegram message never exceeds the platform's 4096-character limit.
- `DRY RUN` and real-money mode must be unmistakable. No message may make a
  paper trade look like a real trade.
- The execution log remains the full forensic record. Telegram is best effort;
  a failed notification never cancels an order or a state write. The daily
  report is only marked delivered after Telegram accepts it.

## Live-execution messages

| Event | User-facing heading | Essential content | Technical detail retained |
| --- | --- | --- | --- |
| Daily reconciliation | `Проверка бота` | balance, local/exchange counts, whether new entries are allowed | blocking mismatch codes |
| Actionable signal | `Найден сигнал` | asset, direction, expected entry, stop | strategy id, UTC signal time |
| Opened trade | `Сделка открыта` | direction, actual entry, SL/TP, size, margin, leverage, risk base | order id, strategy id |
| Rejected signal | `Вход пропущен` | the plain-language reason and that no order was opened | raw rejection reason, strategy id |
| Fill drift | `Цена входа отличается от плана` | expected vs actual price and that the trade is already open | percentage drift, strategy id |
| Execution warning/error | `Нужна проверка` | what happened and whether entries are paused | raw context and exception text |
| Closed trade | `Сделка закрыта` | reason in plain language, entry/exit, PnL, fee | raw exit reason, position id |
| Signal prevented by a safety block | `Сигнал пропущен из-за защиты` | asset, direction, expected entry, why new entries were paused | canonical log key `MISSED SIGNAL`, strategy id, UTC signal time, blocker codes, cumulative count |

`actual fill risk` is a warning, not a blocked order: the message must say that
the trade remains open under the configured alert-only drift policy. Likewise,
an entry-drift alert must never be labelled as a failed trade.

The exit renderer maps common machine reasons to Russian explanations:
`stop_loss` → protective stop, `take_profit` → profit target,
`ttl_expired` → time limit, and unknown exchange reductions/closures → an
explicit request to review the exchange. It also retains the raw reason.

## Legacy decision alerts

The H4 decision sink uses the same Russian wrapper: a plain-language direction,
confidence, market regime, and a conspicuous Russian explanation when weights
are not calibrated. It retains the required canonical `[UNCALIBRATED]` marker.
Its generated engine rationale is escaped and length-bounded rather than being
mistaken for a trading instruction. The live Railway service normally runs with
`--execution-only`, so this legacy path does not drive live orders.

## Acceptance

- Every live notification type is rendered in Russian with prices, PnL, and
  identifiers intact.
- A non-technical reader can tell whether money was put at risk, a trade was
  closed, or new entries are paused from the first two lines.
- Escaping and message-length tests cover dynamic error/rationale text.
- A blocked actionable signal produces both its existing durable log record
  and one Telegram notification with its cumulative count. Repeated callbacks
  for the same deterministic signal id must not inflate the count or spam the
  operator; the persisted recent-id history is bounded.
