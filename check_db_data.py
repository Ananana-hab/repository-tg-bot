
import sqlite3
import pandas as pd

conn = sqlite3.connect('btc_signals.db')
df = pd.read_sql_query("SELECT * FROM price_data ORDER BY timestamp DESC LIMIT 10", conn)
print(df.columns)
print(df[['timestamp', 'price', 'rsi', 'macd']].head())
conn.close()
