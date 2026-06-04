from __future__ import annotations

from dataclasses import dataclass

from .risk_model import EntryContext


@dataclass
class ExitContext:
    """
    Context for exit-fee calculation.

    Parameters
    ----------
    exit_reason : str
        String representation of the exit reason. Typically corresponds to
        :class:`backtester.execution_sim.ExitReason` values such as
        ``\"take_profit\"``, ``\"stop_loss\"`` or ``\"ttl_expired\"``.
    """

    exit_reason: str


class FeeModel:
    """
    Abstract interface for commission models.

    Implementations encapsulate entry and exit fee calculations, making it
    possible to plug in alternative fee schemes without changing the core
    simulation engine.
    """

    def calculate_entry_fee(self, position_value: float, ctx: EntryContext) -> float:
        """
        Calculate entry commission for a new position.

        Parameters
        ----------
        position_value : float
            Notional value of the position at entry.
        ctx : EntryContext
            Context describing the potential trade.

        Returns
        -------
        float
            Entry fee in currency units.
        """

        raise NotImplementedError

    def calculate_exit_fee(
        self,
        exit_value: float,
        *,
        is_maker: bool,
        ctx: ExitContext,
    ) -> float:
        """
        Calculate exit commission for a closing trade.

        Parameters
        ----------
        exit_value : float
            Notional value of the position at exit.
        is_maker : bool
            True if exit is executed as a maker (limit) order, False for taker.
        ctx : ExitContext
            Context describing the exit event.

        Returns
        -------
        float
            Exit fee in currency units.
        """

        raise NotImplementedError


class StaticPercentFeeModel(FeeModel):
    """
    Percentage-based fee model mirroring the original ExecutionSim logic.

    The model applies:

    - taker_fee to entry commission;
    - maker_fee to exit commission for take-profit exits;
    - taker_fee to exit commission for all other exits.
    """

    def __init__(self, *, taker_fee: float, maker_fee: float) -> None:
        """
        Create a static percentage fee model.

        Parameters
        ----------
        taker_fee : float
            Taker fee rate applied to notional value (e.g. 0.001 for 0.1%).
        maker_fee : float
            Maker fee rate applied to notional value (e.g. 0.0002 for 0.02%).
        """

        self._taker_fee = taker_fee
        self._maker_fee = maker_fee

    def calculate_entry_fee(self, position_value: float, ctx: EntryContext) -> float:
        """
        Calculate entry commission using the configured taker fee.

        This reproduces the original behaviour where all entries were
        considered taker orders.
        """

        del ctx  # context is not used in the default implementation
        return position_value * self._taker_fee

    def calculate_exit_fee(
        self,
        exit_value: float,
        *,
        is_maker: bool,
        ctx: ExitContext,
    ) -> float:
        """
        Calculate exit commission using maker/taker fee depending on context.

        The default implementation uses:

        - maker fee when ``is_maker`` is True;
        - taker fee otherwise.
        """

        del ctx  # context is not used in the default implementation

        if is_maker:
            return exit_value * self._maker_fee

        return exit_value * self._taker_fee

