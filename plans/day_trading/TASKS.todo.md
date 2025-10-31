# Tasks & Acceptance Criteria

## Tasks
1. Parameterize `DataCollector.get_market_data(timeframe, limit)`
2. Add mode state + lock, `_get_params_for_mode`, `analyze_market_with_mode`
3. Add Telegram settings toggle `toggle_mode` + handler
4. Implement VWAP and orderbook imbalance; expose in indicators result
5. Extend rule-based scoring (VWAP/OB/volume spike/ATR clamp)
6. Throttle & batch Telegram sends (semaphore + gather)
7. Enable WAL + add DB indexes
8. FNG 5m cache with retries; jittered sleep for day mode
9. Add config knobs for day mode
10. Manual sanity tests

## Acceptance Criteria
- Mode toggle appears in /settings and switches between SWING/DAY
- Monitoring loop adapts timeframe/limit without restart
- No unhandled exceptions in logs during normal run
- No Telegram flood errors; messages < 4096 chars
- Indicators include VWAP and OB imbalance; scoring reflects them
- DB not locked under normal load; WAL active; indexes present


