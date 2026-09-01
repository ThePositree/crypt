# Documentation Portal Text Inventory

Status: wireframe-phase inventory complete; production body-copy expansion pending.
Revision: 1.
Updated: 2026-09-01.

Every literal or repeated text pattern visible in Wireframe revision 1 is
inventoried below. Gray bars represent future body copy and therefore carry no
unreviewed text. Production implementation requires expansion of this inventory
for every authored paragraph, code sample, state, diagram label, and alt text.

## Global Shell

| Location | Exact text/pattern | Job | Decision |
| --- | --- | --- | --- |
| Skip link | `К содержанию` | bypass repeated navigation | keep |
| Brand | `crypt` | return Home and identify product | keep |
| Search | `Поиск по документации`, mobile `Поиск` | open global search | keep |
| Shortcut | `⌘K`; behavior also supports `/` and `Ctrl+K` | expose keyboard access | keep with platform adaptation |
| Sidebar heading | `ДОКУМЕНТАЦИЯ` | label global navigation | keep |
| ToC heading | `НА ЭТОЙ СТРАНИЦЕ` | label article anchors | keep |
| Mobile controls | `Разделы`, `Содержание` | open navigation/ToC drawers | keep |
| Pager | `Предыдущая`, `Следующая` plus destination | navigate learning sequence | rewrite in production to include destination |
| Copy control | `Копировать` | copy exact command | keep; success becomes `Команда скопирована` |
| Warning | `Важно` | identify safety or contract boundary | keep with specific body copy |
| Diagram nodes | `Источник`, `Контракт`, `Решение`, `Результат` | generic flow scaffold | replace with page-specific source-backed labels |
| Character placeholder | role plus guidance purpose | reserve contextual illustration | replace with accessible authored illustration/alt text |

## Navigation Labels

`Главная`; `Быстрый старт`; `Что такое crypt`; `Архитектура`; `Данные`;
`Стратегии`; `Бэктестер`; `Исследования`; `Live execution`; `CLI`;
`Конфигурация`; `Разработка и тестирование`; `Решение проблем`.

Job: identify every approved destination with domain-specific language. Verdict:
keep. English technical terms remain where they are natural to the expert audience.

## Page-level Inventory

| Page | H1 | Lead | Section headings | Character role | Verdict |
| --- | --- | --- | --- | --- | --- |
| Home | `Главная` | `Начните с безопасного пути от установки до dry-run.` | `Что такое crypt`; `Маршрут запуска`; `Разделы документации` | researcher/workshop guide | keep |
| Quick Start | `Быстрый старт` | `Установите crypt, подготовьте данные, запустите бэктест и безопасный dry-run.` | `Установка`; `Данные`; `Бэктест`; `Dry-run` | researcher/workshop guide | keep |
| Overview | `Что такое crypt` | `Исследовательский workbench, точный replay и owner-controlled execution в одной системе.` | `Границы системы`; `Что входит`; `Что не входит` | researcher/workshop guide | rewrite lead to reduce mixed-language density |
| Architecture | `Архитектура` | `Проследите путь данных и решений от OKX или Parquet до артефактов и исполнения.` | `Карта системы`; `Поток данных`; `Источники истины`; `Отказы` | researcher/workshop guide | keep |
| Data | `Данные` | `Подготовьте закрытые свечи и проверьте полноту локального Parquet-хранилища.` | `Источники`; `Таймфреймы`; `Backfill`; `Ошибки данных` | researcher/workshop guide | keep |
| Strategies | `Стратегии` | `Разберите конфигурацию, registry, signals и границу execution context.` | `Контракт стратегии`; `Конфигурация`; `Registry`; `Расширение` | researcher/workshop guide | rewrite lead in consistent Russian/technical vocabulary |
| Backtester | `Бэктестер` | `Запустите точный replay и поймите warmup, accounting и набор артефактов.` | `Модель replay`; `Команда run`; `Границы времени`; `Артефакты` | backtester robot | rewrite lead while preserving exact flags later |
| Research | `Исследования` | `Выберите optimize или DSS и поймите механику без публикации результатов.` | `Выбор workflow`; `Optimize`; `DSS`; `Ограничения` | researcher/workshop guide | keep with command typography |
| Live Execution | `Live execution` | `Разберите dry-run, H1 scheduling, OKX sync, safety и recovery.` | `Режимы`; `Синхронизация`; `Orders и fills`; `Railway`; `Recovery` | live operator | rewrite into Russian with technical names retained locally |
| CLI | `CLI` | `Найдите поддерживаемую команду, флаг, default и точный пример.` | `Индекс команд`; `Backtester`; `Runtime и data`; `Flags` | researcher/workshop guide | rewrite `default` to `значение по умолчанию` |
| Configuration | `Конфигурация` | `Найдите setting, default, эффект и границу риска.` | `Приоритет`; `Base settings`; `Execution`; `Railway` | researcher/workshop guide | rewrite lead in Russian |
| Development | `Разработка и тестирование` | `Найдите модуль и проверьте изменение поддерживаемыми командами.` | `Структура`; `Workflow`; `Проверки`; `Расширение` | researcher/workshop guide | keep; localize heading `Workflow` |
| Troubleshooting | `Решение проблем` | `Сопоставьте симптом с причиной, безопасным восстановлением и проверкой.` | `Установка`; `Данные`; `Backtester`; `OKX и sync`; `Railway` | researcher/workshop guide | keep; use exact subsystem terms within entries |

## Messaging Review

- Semantic trajectory: pass for every page.
- Main promise: task-led and specific to `crypt`.
- Proof placement: contracted beside commands, diagrams, and safety claims.
- Objections: bot framing, staleness, parity, data availability, and dry-run
  safety are assigned to the pages where they arise.
- Generic-copy risk: low in page hierarchy; future body copy remains subject to
  exhaustive production Text Inventory and independent Copy QA.
- Mixed-language density: identified above for rewrite before implementation;
  technical identifiers remain verbatim where precision requires them.
