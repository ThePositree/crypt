#!/usr/bin/env sh
set -eu

export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"
export PYTHONPATH="${PYTHONPATH:-/app/src}"
export NUMBA_DISABLE_JIT="${NUMBA_DISABLE_JIT:-1}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/matplotlib}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"

export DATA_DIR="${DATA_DIR:-/app/data}"
export EXECUTION_DATA_DIR="${EXECUTION_DATA_DIR:-${DATA_DIR}}"
export EXECUTION_STATE_PATH="${EXECUTION_STATE_PATH:-${DATA_DIR}/live_positions.json}"
export LOG_DIR="${LOG_DIR:-${DATA_DIR}/logs}"
export EXECUTION_STRATEGY_CONFIG="${EXECUTION_STRATEGY_CONFIG:-strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json}"

mkdir -p "$DATA_DIR" "$LOG_DIR" "$MPLCONFIGDIR" "$UV_CACHE_DIR"

uv run --no-dev python -m crypt.runtime.deploy_preflight
exec uv run --no-dev python -u -m crypt --execution-only
