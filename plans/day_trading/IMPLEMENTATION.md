# Implementation Outline

- Parameterize data collection with `get_market_data(timeframe=None, limit=None)`.
- Introduce mode state and helpers in `BTCPumpDumpBot` (`current_mode`, `_mode_lock`, `_get_params_for_mode`, `analyze_market_with_mode`).
- Update monitoring loop to use mode-aware analysis and jittered intervals.
- Telegram UI: add mode to settings, `toggle_mode` button, `handle_toggle_mode`.
- Indicators: add VWAP and orderbook imbalance helpers; include in indicators map.
- Rule-based: incorporate VWAP side, OB imbalance, volume spike, ATR clamp.
- Throttle Telegram sends with semaphore + batched gather.
- DB: enable WAL and add indexes in `init_db`.
- Stability: FNG 5m cache with retries; reduce high-frequency REST where possible.
