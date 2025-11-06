import sqlite3
import config
from datetime import datetime
import logging

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path=config.DB_PATH):
        self.db_path = db_path
        self.init_db()
        self.conn = None
    
    def __enter__(self):
        """Контекстный менеджер для безопасной работы с БД"""
        self.conn = self.get_connection()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Безопасное закрытие соединения"""
        if self.conn:
            try:
                if exc_type is None:
                    self.conn.commit()
                else:
                    self.conn.rollback()
            finally:
                self.conn.close()
                self.conn = None
    
    def get_connection(self):
        """Создает подключение к базе данных"""
        return sqlite3.connect(self.db_path)
    
    def init_db(self):
        """Инициализирует таблицы в базе данных"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Режим WAL и параметры надёжности/скорости
        try:
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
        except Exception as e:
            logger.warning(f"PRAGMA setup failed: {e}")

        # Таблица для хранения исторических данных
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                price REAL NOT NULL,
                volume REAL NOT NULL,
                rsi REAL,
                macd REAL,
                macd_signal REAL,
                bb_upper REAL,
                bb_lower REAL,
                fear_greed_index INTEGER
            )
        ''')
        
        # Таблица для хранения сигналов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                signal_type TEXT NOT NULL,
                probability REAL NOT NULL,
                price REAL NOT NULL,
                confidence TEXT,
                actual_result TEXT,
                result_price REAL,
                result_timestamp DATETIME
            )
        ''')
        
        # Таблица для пользователей бота
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                subscribed INTEGER DEFAULT 1,
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Индексы для ускорения выборок
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_data_ts ON price_data(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_ts_type ON signals(timestamp, signal_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_subscribed ON users(subscribed)')
        except Exception as e:
            logger.warning(f"Index creation failed: {e}")
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def save_price_data(self, price, volume, indicators):
        """Сохраняет данные о цене и индикаторах"""
        with self as db:
            cursor = db.conn.cursor()
            
            cursor.execute('''
                INSERT INTO price_data (price, volume, rsi, macd, macd_signal, bb_upper, bb_lower, fear_greed_index)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                price,
                volume,
                indicators.get('rsi'),
                indicators.get('macd'),
                indicators.get('macd_signal'),
                indicators.get('bb_upper'),
                indicators.get('bb_lower'),
                indicators.get('fear_greed')
            ))
    
    def save_signal(self, signal_type, probability, price, confidence):
        """Сохраняет сгенерированный сигнал"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO signals (signal_type, probability, price, confidence)
            VALUES (?, ?, ?, ?)
        ''', (signal_type, probability, price, confidence))
        
        signal_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Signal saved: {signal_type} with probability {probability:.2%}")
        return signal_id
    
    def update_signal_result(self, signal_id, actual_result, result_price):
        """Обновляет результат сигнала после проверки"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE signals
            SET actual_result = ?, result_price = ?, result_timestamp = ?
            WHERE id = ?
        ''', (actual_result, result_price, datetime.now(), signal_id))
        
        conn.commit()
        conn.close()
    
    def get_recent_data(self, limit=100):
        """Получает последние N записей данных"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM price_data
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        data = cursor.fetchall()
        conn.close()
        return data
    
    def get_signal_accuracy(self, days=7):
        """Рассчитывает точность сигналов за последние N дней"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                signal_type,
                COUNT(*) as total,
                SUM(CASE WHEN actual_result = 'correct' THEN 1 ELSE 0 END) as correct
            FROM signals
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            AND actual_result IS NOT NULL
            GROUP BY signal_type
        ''', (days,))
        
        results = cursor.fetchall()
        conn.close()
        
        accuracy = {}
        for signal_type, total, correct in results:
            if total > 0:
                accuracy[signal_type] = (correct / total) * 100
        
        return accuracy
    
    def add_user(self, user_id, username=None, first_name=None):
        """Добавляет нового пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
        ''', (user_id, username, first_name))
        
        conn.commit()
        conn.close()
    
    def get_subscribed_users(self):
        """Возвращает список подписанных пользователей"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id FROM users WHERE subscribed = 1')
        users = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return users
    
    def update_subscription(self, user_id, subscribed):
        """Обновляет статус подписки пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET subscribed = ? WHERE user_id = ?
        ''', (1 if subscribed else 0, user_id))
        
        conn.commit()
        conn.close()
        
    def save_signal(self, signal_type, probability, price, confidence):
        """Сохраняет информацию о сигнале в БД"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO signals (signal_type, probability, price, confidence)
                    VALUES (?, ?, ?, ?)
                """, (signal_type, probability, price, confidence))
                conn.commit()
                logger.info(f"Signal saved: {signal_type} ({probability:.1%})")
        except Exception as e:
            logger.error(f"Error saving signal: {e}")

    def get_signals_stats(self, days=30):
        """Получает статистику сигналов за последние N дней"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем статистику по типам сигналов
                cursor.execute("""
                    SELECT 
                        signal_type,
                        COUNT(*) as total,
                        AVG(probability) as avg_probability,
                        AVG(CASE WHEN confidence = 'HIGH' THEN 1 ELSE 0 END) as high_confidence_ratio
                    FROM signals 
                    WHERE timestamp >= datetime('now', ?)
                    GROUP BY signal_type
                """, (f'-{days} days',))
                
                stats = {
                    'PUMP': {'count': 0, 'avg_probability': 0, 'high_confidence': 0},
                    'DUMP': {'count': 0, 'avg_probability': 0, 'high_confidence': 0}
                }
                
                for row in cursor.fetchall():
                    signal_type, count, avg_prob, high_conf = row
                    if signal_type in stats:
                        stats[signal_type].update({
                            'count': count,
                            'avg_probability': avg_prob,
                            'high_confidence': high_conf * 100  # в процентах
                        })
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting signals stats: {e}")
            return None