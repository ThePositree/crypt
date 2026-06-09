#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

export MPLCONFIGDIR=/tmp/matplotlib UV_CACHE_DIR=/tmp/uv-cache

ROOT="results/v3_robust_overnight_$(date +%Y%m%d)"
mkdir -p "${ROOT}"
SOL_WINDOWS=(
  --window sol_2025_01:SOL-USDT-SWAP:2025-01-01:2025-02-01
  --window sol_2025_02:SOL-USDT-SWAP:2025-02-01:2025-03-01
  --window sol_2025_03:SOL-USDT-SWAP:2025-03-01:2025-04-01
  --window sol_2025_04:SOL-USDT-SWAP:2025-04-01:2025-05-01
  --window sol_2025_05:SOL-USDT-SWAP:2025-05-01:2025-06-01
  --window sol_2025_06:SOL-USDT-SWAP:2025-06-01:2025-07-01
  --window sol_2025_07:SOL-USDT-SWAP:2025-07-01:2025-08-01
  --window sol_2025_08:SOL-USDT-SWAP:2025-08-01:2025-09-01
  --window sol_2025_09:SOL-USDT-SWAP:2025-09-01:2025-10-01
  --window sol_2025_10:SOL-USDT-SWAP:2025-10-01:2025-11-01
  --window sol_2025_11:SOL-USDT-SWAP:2025-11-01:2025-12-01
  --window sol_2025_12:SOL-USDT-SWAP:2025-12-01:2026-01-01
)
run_candidate() {
  local TAG="$1"
  local STRATEGY="$2"
  local OUT="$ROOT/$TAG"
  mkdir -p "$OUT"
  echo "=== [$TAG] Phase 1: baseline compare-fixed (SL-first, rrr=1.25 ttl=36) ==="
  uv run backtester compare-fixed \
    --data-dir data \
    --primary-timeframe 1h \
    --strategy "$STRATEGY" \
    --output "$OUT/01_baseline_compare" \
    --rrr 1.25 --ttl 36 --risk-percent 1.0 \
    --risk-base-period monthly \
    --jobs 3 \
    "${SOL_WINDOWS[@]}"
  echo "=== [$TAG] Phase 2: full-year Optuna tp_pct (1200 trials) ==="
  uv run backtester optimize \
    --data-source crypt-parquet \
    --data-dir data \
    --primary-timeframe 1h \
    --symbol SOL-USDT-SWAP \
    --from 2025-01-01 --to 2026-01-01 \
    --strategy "$STRATEGY" \
    --output "$OUT/02_optuna_full_year" \
    --trials 1200 \
    --target total_return_pct \
    --exit-geometry tp_pct \
    --structural-sl-mode ignore \
    --risk-base-period monthly \
    --tp-move-pct-low 0.006 --tp-move-pct-high 0.020 --tp-move-pct-step 0.002 \
    --rrr-low 1.25 --rrr-high 5.0 --rrr-step 0.25 \
    --ttl-low 12 --ttl-high 48 --ttl-step 12 \
    --risk-percent-low 1.0 --risk-percent-high 2.0 --risk-percent-step 0.25 \
    --no-strategy-param-search \
    --no-daily-limit-search \
    --no-trading-window-search \
    --export-best-run
  BEST_DIR="$(ls -td "$OUT"/02_optuna_full_year/*/best_run 2>/dev/null | head -1)"
  BEST_JSON="$(ls -td "$OUT"/02_optuna_full_year/*/best_trial.json 2>/dev/null | head -1)"
  if [[ -z "$BEST_JSON" ]]; then
    echo "ERROR: no best_trial.json for $TAG"; return 1
  fi
  TP="$(python3 -c "import json; print(json.load(open('$BEST_JSON'))['params']['tp_move_pct'])")"
  RRR="$(python3 -c "import json; print(json.load(open('$BEST_JSON'))['params']['rrr'])")"
  TTL="$(python3 -c "import json; p=json.load(open('$BEST_JSON'))['params']; print(p.get('ttl', p.get('position_ttl_bars', 36)))")"
  RISK="$(python3 -c "import json; print(json.load(open('$BEST_JSON'))['params']['risk_percent'])")"
  echo "Best: tp=$TP rrr=$RRR ttl=$TTL risk=$RISK"
  echo "=== [$TAG] Phase 3: 12-month compare-fixed with Optuna best (continuous mandate) ==="
  uv run backtester compare-fixed \
    --data-dir data \
    --primary-timeframe 1h \
    --strategy "$STRATEGY" \
    --output "$OUT/03_optuna_best_compare" \
    --exit-geometry tp_pct \
    --structural-sl-mode ignore \
    --risk-base-period monthly \
    --tp-move-pct "$TP" \
    --rrr "$RRR" --ttl "$TTL" --risk-percent "$RISK" \
    --jobs 3 \
    "${SOL_WINDOWS[@]}"
  echo "=== [$TAG] DONE ==="
  echo "  baseline:  $OUT/01_baseline_compare/*/mandate_summary.md"
  echo "  optuna:    $BEST_JSON"
  echo "  best run:  $BEST_DIR"
  echo "  mandate:   $OUT/03_optuna_best_compare/*/mandate_summary.md"
}
run_candidate nr4_vwap strategies/backtester/crypt_ensemble_h1_discovery_nr4_vwap_robust.json
echo "All done. Root: $ROOT"