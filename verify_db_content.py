
import sqlite3
import pandas as pd
import os
import sys
from datetime import datetime

# Add parent directory to path to import config if needed, though we just check the DB file directly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

DB_PATH = 'btc_signals.db'

def verify_database():
    print(f"VERIFYING database: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database file not found at {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check tables existence
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tables found: {', '.join(tables)}")
        
        # 1. Check price_data
        if 'price_data' in tables:
            count = cursor.execute("SELECT COUNT(*) FROM price_data").fetchone()[0]
            print(f"price_data rows: {count}")
            
            if count > 0:
                print("   Last 3 entries:")
                df = pd.read_sql_query("SELECT * FROM price_data ORDER BY timestamp DESC LIMIT 3", conn)
                print(df[['timestamp', 'price', 'volume']].to_string(index=False))
        else:
            print("ERROR: Table 'price_data' MISSING")

        # 2. Check signals
        if 'signals' in tables:
            count = cursor.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
            try:
                print(f"signals rows: {count}")
                
                if count > 0:
                    print("   Last 3 signals:")
                    df = pd.read_sql_query("SELECT * FROM signals ORDER BY timestamp DESC LIMIT 3", conn)
                    # Check if columns exist before printing
                    cols = [c for c in ['timestamp', 'signal_type', 'probability', 'confidence'] if c in df.columns]
                    print(df[cols].to_string(index=False))
            except Exception as e:
                print(f"Error reading signals table: {e}")
        else:
            print("ERROR: Table 'signals' MISSING")

        # 3. Check users
        if 'users' in tables:
            count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            print(f"users rows: {count}")
        else:
            print("ERROR: Table 'users' MISSING")

        # 4. Check market_snapshots
        if 'market_snapshots' in tables:
            count = cursor.execute("SELECT COUNT(*) FROM market_snapshots").fetchone()[0]
            print(f"market_snapshots rows: {count}")
            
            if count > 0:
                 # Check how many are labeled (future price updated)
                labeled_count = cursor.execute("SELECT COUNT(*) FROM market_snapshots WHERE label IS NOT NULL").fetchone()[0]
                print(f"   Labeled snapshots: {labeled_count} (ready for training)")
        else:
            print("WARNING: Table 'market_snapshots' MISSING")
            
        conn.close()
        print("Verification complete")
        
    except Exception as e:
        print(f"Error during verification: {e}")

if __name__ == "__main__":
    verify_database()
