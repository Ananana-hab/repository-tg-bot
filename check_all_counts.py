import sqlite3
import pandas as pd

def check_db():
    conn = sqlite3.connect('btc_signals.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]
    
    print(f"{'Table':<20} | {'Count':<10} | {'Latest Timestamp':<20}")
    print("-" * 55)
    
    for table in tables:
        if table == 'sqlite_sequence': continue
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            
            # Try to get latest timestamp if column exists
            cursor.execute(f"PRAGMA table_info({table})")
            cols = [c[1] for c in cursor.fetchall()]
            
            latest = "N/A"
            if 'timestamp' in cols:
                cursor.execute(f"SELECT MAX(timestamp) FROM {table}")
                latest = cursor.fetchone()[0]
            elif 'entry_time' in cols:
                cursor.execute(f"SELECT MAX(entry_time) FROM {table}")
                latest = cursor.fetchone()[0]
            elif 'joined_at' in cols:
                cursor.execute(f"SELECT MAX(joined_at) FROM {table}")
                latest = cursor.fetchone()[0]
            
            print(f"{table:<20} | {count:<10} | {latest}")
        except Exception as e:
            print(f"{table:<20} | Error: {e}")
            
    conn.close()

if __name__ == "__main__":
    check_db()
