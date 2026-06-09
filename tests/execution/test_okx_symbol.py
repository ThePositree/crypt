"""Tests for OKX symbol conversion and dry-run order client logic."""

from __future__ import annotations

from crypt.execution.okx_order_client import _okx_to_ccxt_symbol


class TestSymbolConversion:
    def test_sol_swap(self) -> None:
        assert _okx_to_ccxt_symbol("SOL-USDT-SWAP") == "SOL/USDT:USDT"

    def test_ton_swap(self) -> None:
        assert _okx_to_ccxt_symbol("TON-USDT-SWAP") == "TON/USDT:USDT"

    def test_btc_swap(self) -> None:
        assert _okx_to_ccxt_symbol("BTC-USDT-SWAP") == "BTC/USDT:USDT"

    def test_passthrough_non_swap(self) -> None:
        assert _okx_to_ccxt_symbol("BTC-USDT") == "BTC-USDT"
