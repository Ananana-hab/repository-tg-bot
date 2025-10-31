# Design Notes

## Architecture alignment
- Keep existing modules; extend via parameters and small helpers.
- Avoid blocking calls in event loop; keep REST-safe approach for now.

## Mode handling
- Source of truth: `BTCPumpDumpBot.current_mode` for runtime; user-level mode in `TelegramBot.user_settings` for UI.
- Main loop reads `current_mode` under lock to choose params.

## Indicators
- VWAP: rolling cumulative (tp*vol / vol).
- Orderbook imbalance: (Σbid_vol − Σask_vol) / (Σtotal).
- Volume spike: reuse `volume_ratio` thresholds.

## Scoring additions (rule-based)
- +1 if price > VWAP; −1 if < VWAP.
- ±1 if OB imbalance beyond ±0.1.
- +1 if strong volume spike (ratio > 1.8) in direction of signal.
- ATR low → clamp score near neutral to reduce false signals.

## Rate limits & stability
- Telegram: semaphore + batch gather; respect 4096 char limit.
- Exchange: FNG cache (5m), jittered loop sleeps, retry on transient errors.


