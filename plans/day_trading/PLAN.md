# Day Trading Mode — Plan

## Scope
- Add switchable "day" mode for BTC-only analysis without breaking existing swing mode.
- Respect existing architecture: async PTB v20+, ccxt, SQLite (WAL), structured logging, config-driven.
- Non-blocking runtime; rate limits safe; minimal risk of regressions.

## Goals
- Runtime toggle of analysis mode via Telegram settings (user-level; optional global toggle).
- Parameterized data collection (timeframe/limit) for day mode.
- Add intraday indicators: VWAP, orderbook imbalance, volume spike; integrate into rule-based scoring.
- Throttled/batched Telegram broadcasting.
- REST-safe path (with caching/jitter) and optional WebSocket path (future).

## Success Criteria
- No unhandled exceptions introduced; event loop remains responsive.
- Rate limits respected (Telegram and exchange).
- Signals in day mode reflect intraday context (VWAP/OB/volume/ATR).
- Clear on/off UX for the mode in /settings.

## Non-Goals (Phase 1)
- No training new ML; keep rule-based + features enrichment.
- No ccxt.pro integration (speculative Phase 2).


