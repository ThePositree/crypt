# v1_all24 — v1 exact all-24 split-RRR portfolio
MPLCONFIGDIR=/tmp/matplotlib \
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester run \
  --from 2021-12-18T00:00:00Z \
  --to 2026-06-29T14:00:00Z \
  --strategy strategies/archive/filtered_donor_portfolio_post_adr0058_all24_v1.json \
  --output /tmp/crypt_archive_reproduction/post_adr0058_portfolio_all24_split_rrr

# v2_reduced_risk1 — v2 reduced risk-capped cut
MPLCONFIGDIR=/tmp/matplotlib \
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester run \
  --from 2021-12-18T00:00:00Z \
  --to 2026-06-29T14:00:00Z \
  --strategy strategies/archive/filtered_donor_portfolio_post_adr0058_reduced_v2_risk1.json \
  --output /tmp/crypt_archive_reproduction/post_adr0058_portfolio_reduced_v2_risk1

# v3_return_first — v3 return-first positive-v1 cut
MPLCONFIGDIR=/tmp/matplotlib \
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester run \
  --from 2021-12-18T00:00:00Z \
  --to 2026-06-29T14:00:00Z \
  --strategy strategies/archive/filtered_donor_portfolio_post_adr0058_return_first_v3.json \
  --output /tmp/crypt_archive_reproduction/post_adr0058_portfolio_return_first_v3

# v4_positive_v3 — v4 positive-v3 donor cut
MPLCONFIGDIR=/tmp/matplotlib \
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester run \
  --from 2021-12-18T00:00:00Z \
  --to 2026-06-29T14:00:00Z \
  --strategy strategies/archive/filtered_donor_portfolio_post_adr0058_return_first_v4_positive_v3.json \
  --output /tmp/crypt_archive_reproduction/post_adr0058_portfolio_return_first_v4_positive_v3

# v5_filtered_v3 — v5 filtered-v3 tail-control branch
MPLCONFIGDIR=/tmp/matplotlib \
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester run \
  --from 2021-12-18T00:00:00Z \
  --to 2026-06-29T14:00:00Z \
  --strategy strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v5_filtered_v3.json \
  --output /tmp/crypt_archive_reproduction/post_adr0058_portfolio_tail_control_v5_filtered_v3

# v6_drop_negative_v5 — v6 drop v5 net-negative donors
MPLCONFIGDIR=/tmp/matplotlib \
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester run \
  --from 2021-12-18T00:00:00Z \
  --to 2026-06-29T14:00:00Z \
  --strategy strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json \
  --output /tmp/crypt_archive_reproduction/post_adr0058_portfolio_tail_control_v6_drop_negative_v5

# v7_apr2026 — v7 April-2026 tail-control branch
MPLCONFIGDIR=/tmp/matplotlib \
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester run \
  --from 2021-12-18T00:00:00Z \
  --to 2026-06-29T14:00:00Z \
  --strategy strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v7_apr2026.json \
  --output /tmp/crypt_archive_reproduction/post_adr0058_portfolio_tail_control_v7_apr2026
