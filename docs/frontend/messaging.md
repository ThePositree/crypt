# Messaging

Status: established for Product Surface revision 1.
Revision: 1.
Approval source: owner Product Surface Approval on 2026-09-01.
Updated: 2026-09-01.

## Messaging Identity

- Directness: direct and task-led; lead with what the reader can understand or
  run, then explain the mechanism.
- Formality: professional peer-to-peer Russian without bureaucratic phrasing.
- Technical depth: expert; assume Python and crypto-trading fluency, explain
  only `crypt`-specific contracts and non-obvious execution semantics.
- Claim confidence: factual and source-backed. Distinguish guaranteed behavior,
  configured behavior, runtime truth, and planned or historical behavior.
- Emotional intensity: calm, curious, and reassuring; never urgent or hyped.
- Humor: light character-based workshop humor is allowed in labels and tips;
  never in risk warnings, failures, credentials, or live-money instructions.
- Relationship to the user: an experienced lab partner handing over a precise
  workbench, not a teacher explaining basic trading and not a vendor selling a
  profitable bot.
- Natural phrases: `Начните с безопасного dry-run`, `Откуда берутся данные`,
  `Что произойдёт при запуске`, `Граница между replay и live`, `Если свечей не
  хватает`, `OKX остаётся источником истины`.
- Foreign phrases: `торгуйте умнее`, `раскройте потенциал`, `революционная
  платформа`, `гарантированная безопасность`, `магия алгоритмов`, and generic
  calls to “maximize profits”.
- Owner preference signals: public Russian portal; deep documentation; direct
  quick-start entry; cozy workshop visual identity; no performance results.
- Private owner language not suitable for public copy: chat shorthand and
  profanity are translated into concise professional Russian.
- Evidence: owner onboarding on 2026-09-01 and repository product contracts.

## Global Messaging Contract

- Why it exists: turn a complex AI-first repository into a coherent current
  framework guide without exposing readers to internal documentation history.
- Audience: a developer who already trades crypto perpetuals.
- Starting state: technically capable but unsure how `crypt`'s research,
  replay, data, and live pieces connect.
- Intended leaving state: oriented, able to run the safe path, and able to find
  exact operational or extension details.
- Main idea: `crypt` provides an inspectable path from market data and strategy
  logic to exact replay and owner-controlled OKX execution.
- First messages: what the workbench contains; the fastest safe path; what the
  first command changes and does not change.
- Later messages: architecture, data contracts, strategy composition,
  backtester semantics, execution reconciliation, deployment, and extension.
- Objections to answer: staleness, parity, data availability, order safety,
  operational recovery, and which component owns truth.
- Required proof: current commands, module paths, setting names, failure modes,
  and source-derived diagrams.
- Natural action: begin Quick start or search for the exact command/setting.
- Generic-copy risks: decorative framework language and claims not tied to a
  visible mechanism.

## Page Message Trajectory

- Home: `I need an entry point` -> scope in one sentence -> Quick start action.
- Quick start: `I want it running` -> prerequisites -> bounded backtest ->
  artifact explanation -> safe dry-run -> live boundary.
- Concept pages: `I need a mental model` -> component role -> data/control flow
  -> invariants -> failures -> related task.
- Reference pages: `I need an exact answer` -> searchable inventory -> example
  -> default and effect -> safety note -> related guide.
- Troubleshooting: `something failed` -> identify symptom -> explain cause ->
  safe recovery -> verification.

## Text Hierarchy

- Level 1 main promise: `Разберите crypt и запустите безопасный dry-run.`
- Level 2 section arguments: each heading states the next piece of the system
  model, such as `Сначала подготовьте закрытые свечи` rather than `Данные`.
- Level 3 supporting copy: mechanisms, commands, examples, limitations, and
  source-of-truth boundaries.
- Level 4 action copy: `Начать быстрый старт`, `Скопировать команду`, `Открыть
  конфигурацию исполнения`, `Найти в документации`.
- Level 5 microcopy: short factual feedback such as `Команда скопирована`,
  `Ничего не найдено`, and `Dry-run не отправляет ордера`.

## Proof System

- Claim: the portal describes the current framework. Proof: facts map to
  current code and canonical specialist docs; outdated overview conflicts are
  excluded.
- Claim: the quick-start dry-run does not place orders. Proof: the documented
  command sets `EXECUTION_DRY_RUN=true`, and the execution settings/runtime
  behavior are explained beside it.
- Claim: backtest and live aim to share semantics. Proof: name the shared pure
  strategy/execution paths and explicitly document known runtime boundaries;
  do not imply perfect parity without evidence.
- Claim: missing data is handled deliberately. Proof: show concrete blocked,
  neutral, or fail-fast behavior and the corresponding recovery command.

## Objection Map

- `Это очередной сигнал-бот.` Answer on Home/Overview with the current research
  workbench, exact replay, and execution boundaries.
- `Документация может отставать от кода.` Answer through current-main scope,
  source manifests, and build-time coverage checks.
- `Dry-run случайно отправит ордер.` Answer immediately beside the command with
  mode settings, observable behavior, and the live-mode boundary.
- `Бэктест не равен бирже.` Answer on Architecture/Backtester/Live Execution by
  distinguishing shared decision logic from fills, fees, timing, sync, and OKX truth.
- `Непонятно, какие свечи нужны.` Answer on Quick start/Data with required
  timeframes, completeness checks, and generated backfill recovery commands.

## Microcopy Rules

- Buttons and links: name the destination or resulting action; avoid `Подробнее`.
- Navigation labels: short domain nouns; article headings carry the argument.
- Search: retain the query, show why a result matched, and offer useful routes
  on zero results.
- Code copy: confirm success without toast spam; on failure select the code and
  explain manual copying.
- Loading: local static search should be immediate; if its index is not ready,
  say `Поиск загружается` and keep navigation available.
- Empty states: explain what is absent and where to go next.
- Errors: state the failed boundary, likely cause, safe next action, and how to verify.
- Success: confirm exactly what changed; never imply a trade was placed during dry-run.
- Confirmations: none for site mutations; external/live commands use adjacent
  warnings in content rather than interactive fake confirmations.
- Tooltips and badges: supplement visible labels; do not carry essential safety content.

## Text Inventory

The exhaustive page/state/component inventory will be created with screen
contracts before Wireframe Approval. It must cover navigation, search, every
heading and paragraph, code controls, tabs, disclosures, diagrams, tips,
warnings, mobile labels, empty/error states, and previous/next links.

## Copy Review

- Scope reviewed: Product Surface revision 1 and global messaging direction.
- Text Inventory coverage: global patterns only; page-level inventory pending.
- Clarity: proposed pass.
- Specificity: grounded in actual `crypt` commands and boundaries.
- Information depth: contracted as deep authored documentation.
- Messaging Identity fit: proposed pass.
- Claim/proof fit: required proof mapped above.
- Objection coverage: five primary objections mapped.
- Action-copy strength: concrete action vocabulary established.
- Microcopy usefulness: state rules established; exact inventory pending.
- Coverage gaps: page-level copy and independent review await later gates.
- Slop risks: framework hype, profit language, overpromised parity, and decorative lore.
- Decision: approved as the global messaging direction for Product Surface revision 1.
- Date: 2026-09-01.
