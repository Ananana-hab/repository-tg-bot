
import logging
import pandas as pd
from datetime import datetime
import config
from database import Database

logger = logging.getLogger(__name__)

class PaperTrader:
    def __init__(self, db: Database):
        self.db = db
        # Simulated wallet (future improvement: store in DB)
        self.initial_balance = 10000.0 
        
    def open_position(self, signal_type, current_price, probability):
        """
        Открывает виртуальную позицию
        """
        # 1. Check active positions
        active_positions = self.db.get_active_positions()
        if not active_positions.empty:
            logger.info("Cannot open position: Active position already exists")
            return
        
        # 2. Risk Management (Simple)
        # Position size = 100% of portfolio (for now) or fixed USD
        quantity = 0.01 # Fake quantity BTC
        
        # 3. Calculate TP/SL
        # ATR-based or Percentage-based
        # Let's use simple fixed % from config or defaults
        sl_pct = 0.02 # 2% SL
        tp_pct = 0.04 # 4% TP (Risk:Reward 1:2)
        
        if signal_type == 'PUMP':
            side = 'LONG'
            stop_loss = current_price * (1 - sl_pct)
            take_profit = current_price * (1 + tp_pct)
        elif signal_type == 'DUMP':
            side = 'SHORT'
            stop_loss = current_price * (1 + sl_pct)
            take_profit = current_price * (1 - tp_pct)
        else:
            return
            
        # 4. Save to DB
        position_id = self.db.save_position(
            symbol=config.SYMBOL,
            side=side,
            entry_price=current_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        if position_id:
            logger.info(f"🟢 PAPER TRADE OPEN: {side} @ ${current_price:.2f} (TP: ${take_profit:.2f}, SL: ${stop_loss:.2f})")
            
    def update_positions(self, current_price):
        """
        Проверяет условия выхода (TP/SL) для открытых позиций
        """
        active = self.db.get_active_positions()
        if active.empty:
            return
            
        for _, row in active.iterrows():
            pos_id = row['id']
            side = row['side']
            entry = row['entry_price']
            sl = row['stop_loss']
            tp = row['take_profit']
            quantity = row['quantity']
            
            exit_reason = None
            
            # Check Exit Conditions
            if side == 'LONG':
                if current_price <= sl:
                    exit_reason = 'STOP_LOSS'
                elif current_price >= tp:
                    exit_reason = 'TAKE_PROFIT'
            elif side == 'SHORT':
                if current_price >= sl:
                    exit_reason = 'STOP_LOSS'
                elif current_price <= tp:
                    exit_reason = 'TAKE_PROFIT'
            
            if exit_reason:
                self._close_position(pos_id, side, entry, current_price, quantity, exit_reason)

    def _close_position(self, pos_id, side, entry_price, exit_price, quantity, reason):
        """
        Внутренний метод закрытия
        """
        # Calculate PnL
        if side == 'LONG':
            pnl = (exit_price - entry_price) * quantity
            pnl_pct = (exit_price - entry_price) / entry_price * 100
        else: # SHORT
            pnl = (entry_price - exit_price) * quantity
            pnl_pct = (entry_price - exit_price) / entry_price * 100
            
        # Log to DB
        self.db.close_position(
            position_id=pos_id,
            exit_price=exit_price,
            exit_reason=reason,
            pnl=pnl,
            pnl_percent=pnl_pct
        )
        
        icon = "🟢" if pnl > 0 else "🔴"
        logger.info(f"{icon} PAPER TRADE CLOSED: {side} {reason} | PnL: ${pnl:.2f} ({pnl_pct:.2f}%)")
