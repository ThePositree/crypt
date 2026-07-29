"""Fail-closed continuity checks for the live monthly risk base."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from crypt.execution.position_state import (
    ExecutionState,
    MonthlyRiskBaseCheckpoint,
    RiskBaseCheckpointError,
    create_monthly_risk_base_checkpoint,
    load_monthly_risk_base_checkpoint,
)


class RiskBaseContinuityError(RuntimeError):
    """Raised when a live entry cannot prove its monthly sizing anchor."""


@dataclass(frozen=True)
class RiskBaseResolution:
    """The verified risk base and how the current state reached it."""

    risk_base: float
    action: Literal["verified", "recovered", "pending_rollover", "adopted", "rolled_over"]


class MonthlyRiskBaseContinuity:
    """Resolve a live monthly risk base from immutable checkpoint records."""

    def __init__(
        self,
        *,
        checkpoint_dir: Path,
        state_path: Path,
        allow_adopt_existing_state: bool,
        adopt_expected_month: str | None = None,
        adopt_expected_base: float | None = None,
    ) -> None:
        self._checkpoint_dir = checkpoint_dir
        self._state_path = state_path
        self._allow_adopt_existing_state = allow_adopt_existing_state
        self._adopt_expected_month = adopt_expected_month
        self._adopt_expected_base = adopt_expected_base

    @property
    def checkpoint_dir(self) -> Path:
        return self._checkpoint_dir

    def verify_startup(
        self,
        state: ExecutionState,
        *,
        now: datetime,
        exchange_sync_ok: bool,
    ) -> RiskBaseResolution:
        """Verify or restore the current UTC-month anchor before live entries run."""
        window = _month_key(now)
        checkpoint = self._load(window)
        if checkpoint is not None:
            return self._apply_checkpoint(
                state, window=window, risk_base=checkpoint.monthly_risk_base
            )

        if state.risk_window_month == window and _is_positive_finite(state.monthly_risk_base):
            if not self._allow_adopt_existing_state:
                raise RiskBaseContinuityError(
                    "current-month risk base exists only in mutable state; "
                    "set the one-deploy explicit adoption flag after confirming sync"
                )
            if not exchange_sync_ok:
                raise RiskBaseContinuityError(
                    "cannot adopt current-month mutable risk base while exchange sync is blocked"
                )
            if state.state_recovered_from_previous_snapshot:
                raise RiskBaseContinuityError(
                    "cannot adopt a risk base recovered from the previous mutable state snapshot"
                )
            self._assert_adoption_manifest(state, window=window)
            self._create(
                window=window,
                risk_base=state.monthly_risk_base,
                source="operator_adopted_existing_state",
                now=now,
            )
            return RiskBaseResolution(risk_base=state.monthly_risk_base, action="adopted")

        if state.risk_window_month is None or not _is_positive_finite(state.monthly_risk_base):
            raise RiskBaseContinuityError(
                "no current-month checkpoint and no prior persisted risk base; "
                "new live entries stay paused"
            )
        if _window_after(state.risk_window_month, window):
            raise RiskBaseContinuityError(
                "persisted risk window is later than the current UTC month"
            )

        previous = self._load(state.risk_window_month)
        if previous is None:
            raise RiskBaseContinuityError(
                "prior persisted risk base has no matching immutable checkpoint; "
                "new live entries stay paused"
            )
        self._assert_same_base(
            state_base=state.monthly_risk_base,
            checkpoint_base=previous.monthly_risk_base,
            window=state.risk_window_month,
        )
        return RiskBaseResolution(
            risk_base=state.monthly_risk_base,
            action="pending_rollover",
        )

    def resolve_for_entry(
        self,
        state: ExecutionState,
        *,
        entry_time: datetime,
        current_capital: float,
        exchange_sync_ok: bool,
    ) -> RiskBaseResolution:
        """Return an immutable current-month anchor before an order is persisted."""
        if not _is_positive_finite(current_capital):
            raise RiskBaseContinuityError(
                "cannot create a monthly anchor from non-finite or non-positive capital"
            )
        window = _month_key(entry_time)
        checkpoint = self._load(window)
        if checkpoint is not None:
            return self._apply_checkpoint(
                state, window=window, risk_base=checkpoint.monthly_risk_base
            )

        previous_window = state.risk_window_month
        if previous_window is None or not _is_positive_finite(state.monthly_risk_base):
            raise RiskBaseContinuityError(
                "no current-month checkpoint and no verified prior risk base; "
                "refusing to re-anchor from current balance"
            )
        if previous_window == window:
            raise RiskBaseContinuityError(
                "current-month mutable risk base has no checkpoint; "
                "refusing to re-anchor from current balance"
            )
        if _window_after(previous_window, window):
            raise RiskBaseContinuityError("persisted risk window is later than the entry UTC month")

        previous = self._load(previous_window)
        if previous is None:
            raise RiskBaseContinuityError(
                "previous risk window has no immutable checkpoint; refusing a monthly rollover"
            )
        self._assert_same_base(
            state_base=state.monthly_risk_base,
            checkpoint_base=previous.monthly_risk_base,
            window=previous_window,
        )

        if not exchange_sync_ok:
            raise RiskBaseContinuityError(
                "cannot create a new UTC-month risk anchor while exchange sync is blocked"
            )
        self._create(
            window=window,
            risk_base=current_capital,
            source="calendar_rollover",
            now=entry_time,
        )
        state.risk_window_month = window
        state.monthly_risk_base = current_capital
        state.state_recovered_from_previous_snapshot = False
        return RiskBaseResolution(risk_base=current_capital, action="rolled_over")

    def _load(self, window: tuple[int, int]) -> MonthlyRiskBaseCheckpoint | None:
        try:
            checkpoint = load_monthly_risk_base_checkpoint(self._checkpoint_dir, window)
        except RiskBaseCheckpointError as exc:
            raise RiskBaseContinuityError(str(exc)) from exc
        if checkpoint is not None:
            self._assert_checkpoint_state_path(checkpoint)
        return checkpoint

    def _assert_checkpoint_state_path(self, checkpoint: MonthlyRiskBaseCheckpoint) -> None:
        if not checkpoint.state_path:
            raise RiskBaseContinuityError("monthly risk checkpoint has no bound state path")
        expected = self._state_path.expanduser().resolve(strict=False)
        actual = Path(checkpoint.state_path).expanduser().resolve(strict=False)
        if actual != expected:
            raise RiskBaseContinuityError(
                "monthly risk checkpoint belongs to a different state path: "
                f"checkpoint={actual}, configured={expected}"
            )

    def _assert_adoption_manifest(
        self,
        state: ExecutionState,
        *,
        window: tuple[int, int],
    ) -> None:
        if self._adopt_expected_month is None or self._adopt_expected_base is None:
            raise RiskBaseContinuityError(
                "adoption requires explicit expected month and exact risk base"
            )
        expected_window = _parse_month(self._adopt_expected_month)
        if expected_window != window:
            raise RiskBaseContinuityError(
                "adoption expected month does not match the current UTC month: "
                f"expected={self._adopt_expected_month}, current={window[0]:04d}-{window[1]:02d}"
            )
        if not _is_positive_finite(self._adopt_expected_base):
            raise RiskBaseContinuityError("adoption expected risk base must be finite and positive")
        self._assert_same_base(
            state_base=state.monthly_risk_base,
            checkpoint_base=self._adopt_expected_base,
            window=window,
        )

    def _create(
        self,
        *,
        window: tuple[int, int],
        risk_base: float,
        source: str,
        now: datetime,
    ) -> None:
        try:
            create_monthly_risk_base_checkpoint(
                self._checkpoint_dir,
                risk_window_month=window,
                monthly_risk_base=risk_base,
                source=source,
                state_path=self._state_path,
                created_at=now,
            )
        except (OSError, RiskBaseCheckpointError, ValueError) as exc:
            raise RiskBaseContinuityError(
                f"could not persist immutable monthly risk checkpoint: {exc}"
            ) from exc

    def _apply_checkpoint(
        self,
        state: ExecutionState,
        *,
        window: tuple[int, int],
        risk_base: float,
    ) -> RiskBaseResolution:
        if state.risk_window_month == window and _is_positive_finite(state.monthly_risk_base):
            self._assert_same_base(
                state_base=state.monthly_risk_base,
                checkpoint_base=risk_base,
                window=window,
            )
            state.state_recovered_from_previous_snapshot = False
            return RiskBaseResolution(risk_base=risk_base, action="verified")
        if state.risk_window_month is not None and _window_after(state.risk_window_month, window):
            raise RiskBaseContinuityError(
                "persisted risk window is later than the checkpoint UTC month"
            )

        state.risk_window_month = window
        state.monthly_risk_base = risk_base
        state.state_recovered_from_previous_snapshot = False
        return RiskBaseResolution(risk_base=risk_base, action="recovered")

    @staticmethod
    def _assert_same_base(
        *,
        state_base: float,
        checkpoint_base: float,
        window: tuple[int, int],
    ) -> None:
        if not math.isclose(state_base, checkpoint_base, rel_tol=0.0, abs_tol=1e-9):
            raise RiskBaseContinuityError(
                "state and immutable checkpoint disagree for "
                f"{window[0]:04d}-{window[1]:02d}: "
                f"state={state_base:.12g}, checkpoint={checkpoint_base:.12g}"
            )


def _month_key(value: datetime) -> tuple[int, int]:
    value_utc = value.astimezone(UTC)
    return (value_utc.year, value_utc.month)


def _window_after(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left > right


def _is_positive_finite(value: float) -> bool:
    return math.isfinite(value) and value > 0


def _parse_month(value: str) -> tuple[int, int]:
    if len(value) != 7 or value[4] != "-":
        raise RiskBaseContinuityError(f"adoption expected month must use YYYY-MM, got {value!r}")
    try:
        year = int(value[:4])
        month = int(value[5:])
    except ValueError as exc:
        raise RiskBaseContinuityError(
            f"adoption expected month must use YYYY-MM, got {value!r}"
        ) from exc
    if not 1 <= month <= 12:
        raise RiskBaseContinuityError(f"adoption expected month must use YYYY-MM, got {value!r}")
    return (year, month)
