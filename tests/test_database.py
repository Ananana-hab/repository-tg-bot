
import unittest
import sqlite3
import os
import sys
import tempfile
import shutil

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database

class TestDatabase(unittest.TestCase):
    def setUp(self):
        # Create a temp directory
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, 'test.db')
        self.db = Database(db_path=self.db_path)
        
    def tearDown(self):
        if self.db.conn:
            self.db.conn.close()
        # Remove temp dir
        shutil.rmtree(self.test_dir)

    def test_tables_creation(self):
        # Check if tables exist
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        tables = ['price_data', 'signals', 'users']
        for table in tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            self.assertIsNotNone(cursor.fetchone(), f"Table {table} not created")
        
        conn.close()

    def test_save_and_get_price_data(self):
        # Test saving price data
        indicators = {'rsi': 50.5, 'macd': 0.1, 'bb_position': 'inside', 'bb_upper': 51000, 'bb_lower': 49000, 'fear_greed': 50}
        self.db.save_price_data(
            price=50000.0,
            volume=100.0,
            indicators=indicators
        )
        
        # Verify it was saved
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT price, volume FROM price_data")
        row = cursor.fetchone()
        
        self.assertEqual(row[0], 50000.0)
        self.assertEqual(row[1], 100.0)
        conn.close()

    def test_user_management(self):
        user_id = 99999
        self.db.add_user(user_id, "testuser", "Test")
        
        # Verify user was created
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        self.assertEqual(row[0], "testuser")
        
        # Test subscription
        users = self.db.get_subscribed_users()
        self.assertIn(user_id, users)
        
        # Unsubscribe
        self.db.update_subscription(user_id, 0)
        users = self.db.get_subscribed_users()
        self.assertNotIn(user_id, users)
        
        conn.close()

