
import unittest
import sqlite3
import pandas as pd
from database import Database
from paper_trader import PaperTrader
import os

class TestPaperTrading(unittest.TestCase):
    def setUp(self):
        # Use main DB or test DB? Let's use main for manual verification or mock.
        # Ideally mock, but let's test integration with SQLite file.
        self.db = Database()
        self.trader = PaperTrader(self.db)
        
    def test_full_cycle(self):
        print("Testing Paper Trading Cycle...")
        
        # 1. Open Position
        price_entry = 50000.0
        print(f"Opening LONG at ${price_entry}")
        self.trader.open_position('PUMP', price_entry, 0.85)
        
        active = self.db.get_active_positions()
        self.assertFalse(active.empty)
        pos = active.iloc[-1]
        self.assertEqual(pos['entry_price'], 50000.0)
        self.assertEqual(pos['status'], 'OPEN')
        print(f"Position opened: ID={pos['id']}, TP={pos['take_profit']}, SL={pos['stop_loss']}")
        
        # 2. Update - No Action
        current_price = 51000.0 # +2%
        self.trader.update_positions(current_price)
        active = self.db.get_active_positions()
        self.assertFalse(active.empty) # Still open
        print("Price moves to $51,000 (No Trigger). Position still OPEN.")

        # 3. Update - Take Profit Hit
        # TP was 50000 * 1.04 = 52000
        current_price = 52500.0 # +5%
        print(f"Price moves to ${current_price} (Hit TP).")
        self.trader.update_positions(current_price)
        
        active = self.db.get_active_positions()
        self.assertTrue(active.empty) # Should be closed
        
        # Verify closure
        conn = self.db.get_connection()
        closed = pd.read_sql_query(f"SELECT * FROM positions WHERE id={pos['id']}", conn).iloc[0]
        conn.close()
        
        self.assertEqual(closed['status'], 'CLOSED')
        self.assertEqual(closed['exit_reason'], 'TAKE_PROFIT')
        self.assertGreater(closed['pnl'], 0)
        print(f"Position CLOSED. PnL: ${closed['pnl']:.2f} ({closed['pnl_percent']:.2f}%)")
        print("✅ Paper Trading Verification Passed!")

if __name__ == '__main__':
    unittest.main()
