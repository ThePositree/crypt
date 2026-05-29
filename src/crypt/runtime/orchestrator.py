from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from loguru import logger

from crypt.aggregator.ensemble import aggregate
from crypt.aggregator.weights import WeightsConfig
from crypt.config import Settings
from crypt.data.context import ContextBuilder
from crypt.data.ingestor import Ingestor
from crypt.data.store import ParquetStore
from crypt.decision.filters import DecisionFilter
from crypt.engines.derivatives import DerivativesEngine
from crypt.engines.meanrev import MeanRevEngine
from crypt.engines.regime import RegimeEngine
from crypt.engines.trend import TrendEngine
from crypt.engines.volatility import VolatilityEngine
from crypt.exchange.okx import OKXClient
from crypt.models import EvaluationContext, Regime, Signal, Timeframe, VolRegime
from crypt.sinks.base import BaseSink
from crypt.sinks.console import ConsoleSink
from crypt.sinks.execution_stub import ExecutionStub
from crypt.sinks.jsonlog import JsonLogSink
from crypt.sinks.telegram import TelegramSink


class Orchestrator:
    """
    Main control object: wires up all components and drives the tick loop.

    One Orchestrator instance lives for the lifetime of the process.
    Call ``bootstrap()`` once on startup, then ``tick()`` on every H4 boundary.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

        # Exchange + storage
        self._exchange = OKXClient(
            api_key=settings.okx_api_key,
            api_secret=settings.okx_api_secret,
            api_passphrase=settings.okx_api_passphrase,
            max_retries=settings.okx_max_retries,
            retry_base_delay=settings.okx_retry_base_delay,
            retry_max_delay=settings.okx_retry_max_delay,
        )
        self._store = ParquetStore(settings.data_dir)
        self._ingestor = Ingestor(self._exchange, self._store, settings.symbols)
        self._ctx_builder = ContextBuilder(self._store)

        # Engines
        self._trend = TrendEngine()
        self._meanrev = MeanRevEngine()
        self._derivatives = DerivativesEngine()
        self._volatility = VolatilityEngine()
        self._regime = RegimeEngine()

        # Aggregator weights
        self._weights = WeightsConfig.load(settings.weights_path)

        # Decision filter
        self._filter = DecisionFilter(
            confidence_threshold=settings.alert_confidence_threshold,
            cooldown_hours=settings.cooldown_hours,
        )

        # Sinks
        self._sinks: list[BaseSink] = self._build_sinks(settings)

    def _build_sinks(self, cfg: Settings) -> list[BaseSink]:
        sinks: list[BaseSink] = []

        log_path = cfg.data_dir / "verdicts.jsonl"
        sinks.append(JsonLogSink(log_path))
        sinks.append(ConsoleSink())
        sinks.append(ExecutionStub())

        if cfg.telegram_bot_token and cfg.telegram_chat_id:
            sinks.append(
                TelegramSink(
                    cfg.telegram_bot_token,
                    cfg.telegram_chat_id,
                    uncalibrated=cfg.uncalibrated,
                )
            )
        else:
            logger.warning("Telegram not configured — alerts will be console-only")

        return sinks

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    async def bootstrap(self) -> None:
        """
        Cold-start: pull enough history for all indicators to warm up.
        Called once before the scheduler starts.
        """
        logger.info("Bootstrap: fetching initial history for {}", self._settings.symbols)
        await self._ingestor.ingest_all()
        logger.info("Bootstrap complete")

    async def tick(self) -> None:
        """
        Called on every H4 boundary: ingest fresh data, evaluate all symbols.
        """
        logger.info("Tick started")
        await self._ingestor.ingest_all()

        symbols = self._settings.symbols
        n = len(symbols)
        tasks = [self._evaluate_symbol(sym) for sym in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        ok = partial = failed = 0
        for sym, res in zip(symbols, results, strict=True):
            if isinstance(res, BaseException):
                logger.error("tick: _evaluate_symbol {} raised: {}", sym, res)
                failed += 1
            elif res == "partial":
                partial += 1
            elif res == "failed":
                failed += 1
            else:
                ok += 1

        logger.info(
            "Tick complete: {}/{} symbols OK, {} partial (missing data), {} failed",
            ok,
            n,
            partial,
            failed,
        )

    async def close(self) -> None:
        """Graceful shutdown: close exchange session and all sinks."""
        await self._exchange.close()
        for sink in self._sinks:
            try:
                await sink.close()
            except Exception as exc:
                logger.error("Sink close error: {}", exc)

    # ------------------------------------------------------------------
    # Per-symbol evaluation
    # ------------------------------------------------------------------

    async def _evaluate_symbol(self, symbol: str) -> str:
        """
        Returns "ok", "partial", or raises on hard failure.
        "partial" means the context was built but some data series were empty.
        """
        try:
            tick_time = datetime.now(tz=UTC)
            ctx = self._ctx_builder.build(symbol, tick_time)
            h4 = ctx.candles.get(Timeframe.H4)
            d1 = ctx.candles.get(Timeframe.D1)
            is_partial = (h4 is None or h4.empty) or (d1 is None or d1.empty)
            await self._run_engines_and_dispatch(ctx)
            return "partial" if is_partial else "ok"
        except Exception as exc:
            logger.error("Evaluation failed for {}: {}", symbol, exc)
            return "failed"

    async def _run_engines_and_dispatch(self, ctx: EvaluationContext) -> None:
        # 1. Volatility engine first — sets ctx.vol_regime for regime engine.
        vol_signal = self._volatility.evaluate(ctx)
        vol_regime: VolRegime = str(vol_signal.meta.get("vol_regime", "normal"))  # type: ignore[assignment]
        ctx.vol_regime = vol_regime

        # 2. Regime engine.
        regime_signal = self._regime.evaluate(ctx)
        regime_str = str(regime_signal.meta.get("regime", "RANGING"))
        regime = Regime(regime_str)

        # 3. Directional engines (can run in parallel — they are pure functions).
        trend_signal, meanrev_signal, deriv_signal = await asyncio.gather(
            asyncio.to_thread(self._trend.evaluate, ctx),
            asyncio.to_thread(self._meanrev.evaluate, ctx),
            asyncio.to_thread(self._derivatives.evaluate, ctx),
        )

        all_signals: list[Signal] = [
            trend_signal,
            meanrev_signal,
            deriv_signal,
            vol_signal,
            regime_signal,
        ]

        # 4. Aggregate.
        verdict = aggregate(
            signals=all_signals,
            regime=regime,
            weights_cfg=self._weights,
            symbol=ctx.symbol,
            vol_regime=vol_regime,
        )

        # 5. Decision layer.
        guarded_verdict = self._filter.apply_guard(verdict)
        should_alert = self._filter.should_alert(guarded_verdict)

        # 6. Dispatch to sinks.
        sink_results = await asyncio.gather(
            *[sink.emit(guarded_verdict, should_alert) for sink in self._sinks],
            return_exceptions=True,
        )
        for sink, res in zip(self._sinks, sink_results, strict=True):
            if isinstance(res, BaseException):
                logger.error("sink {}: {}", type(sink).__name__, res)

        if should_alert:
            self._filter.record_alert(guarded_verdict)
