# Step-by-Step Implementation

## Step 1 — Data parametrize (safe)
- Add `DataCollector.get_market_data(timeframe=None, limit=None)`; fallback to config.
- Refactor callers to pass mode parameters.

## Step 2 — Mode plumbing in main loop
- Add `BTCPumpDumpBot.current_mode` + `_mode_lock`.
- Add `_get_params_for_mode(mode)` and `analyze_market_with_mode(mode)`.
- Use new analyze in `monitoring_loop`.

## Step 3 — Telegram settings toggle
- Extend user settings with `'mode': 'swing'`.
- Add `toggle_mode` button in `/settings`.
- Implement `handle_toggle_mode`.
- (Optional) Admin global toggle → method on `BTCPumpDumpBot` guarded by lock.

## Step 4 — Intraday indicators
- Implement VWAP, orderbook imbalance; expose from `indicators.py`.
- Add volume spike logic via existing `volume_ratio`.
- Wire outputs into `calculate_all_indicators` result map.

## Step 5 — Rule-based enrichment
- Update `MLPredictor.rule_based_prediction` to consider VWAP/OB/volume spike/ATR.
- Keep thresholds conservative; ensure graceful defaults.

## Step 6 — Throttle and batch Telegram sends
- Add semaphore (≈20–25 msg/s) + `gather` batching in `send_signal_to_users`.
- Minimal sleep between batches to smooth bursts.

## Step 7 — DB performance defaults
- Enable WAL mode and useful indexes in `Database.init_db`.

## Step 8 — REST-safe stability
- Add FNG cache TTL=5m with retries/backoff.
- Add jittered sleep in monitoring loop (shorter base for day mode).

## Step 9 — Config knobs
- Add `DAY_TIMEFRAME='1m'`, `DAY_LIMIT=200`, optional `DAY_CHECK_INTERVAL=30`.
- Optional: `OB_IMBALANCE_THRESHOLD`, `VOLUME_SPIKE_RATIO`.

## Step 10 — Sanity tests
- Manual run: /start, /settings toggle, /status in both modes.
- Verify logs, DB writes, no rate limit errors, messages under 4096 chars.


