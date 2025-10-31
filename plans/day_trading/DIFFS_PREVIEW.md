# Diffs Preview (concise)

- data_collector.py: add `get_market_data(timeframe=None, limit=None)` and use provided params instead of fixed config.

- main.py:
  - Add `current_mode` and `_mode_lock` in `BTCPumpDumpBot.__init__`.
  - Add `_get_params_for_mode(mode)` returning `{'timeframe': '1m', 'limit': 200}` for `day`.
  - Add `analyze_market_with_mode(mode)` that forwards params to data collector.
  - In `monitoring_loop`, read `mode` under lock and call new analyze method; add jittered sleep for `day`.

- telegram_bot.py:
  - Extend default `user_settings` with `'mode': 'swing'`.
  - In `/settings`, render mode and add `toggle_mode` button.
  - Implement `handle_toggle_mode` to flip `swing`/`day`.
  - Optionally: throttle/batch sends in `send_signal_to_users` using `asyncio.Semaphore` and batched `gather`.

- indicators.py:
  - Add `calculate_vwap(df)` and `orderbook_imbalance(orderbook)` helpers.
  - Include their outputs in `calculate_all_indicators` result map.

- ml_model.py:
  - In `rule_based_prediction`, consider VWAP side, OB imbalance threshold, volume spike with `volume_ratio`, and clamp with low ATR.

- database.py:
  - Enable WAL and add indexes in `init_db` (`journal_mode=WAL`, `synchronous=NORMAL`, indexes on timestamps`).
