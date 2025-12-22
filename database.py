import sqlite3
import config
from datetime import datetime
import logging
import pandas as pd

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
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                -- User settings
                notifications_enabled INTEGER DEFAULT 1,
                min_probability INTEGER DEFAULT 70,
                signal_types TEXT DEFAULT 'PUMP,DUMP',
                trading_mode TEXT DEFAULT 'swing'
            )
        ''')
        
        # ✅ НОВОЕ: Таблица для хранения полных снимков рынка (для ML обучения)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                -- Price data
                price REAL NOT NULL,
                volume REAL NOT NULL,
                -- Technical indicators
                rsi REAL,
                macd REAL,
                macd_signal REAL,
                bb_upper REAL,
                bb_middle REAL,
                bb_lower REAL,
                ema_50 REAL,
                ema_200 REAL,
                atr REAL,
                momentum REAL,
                vwap REAL,
                -- Volume metrics
                volume_ratio REAL,
                volume_ma REAL,
                -- Market data
                fear_greed INTEGER,
                orderbook_imbalance REAL,
                -- Open Interest
                open_interest REAL,
                oi_change_5m REAL,
                oi_change_1h REAL,
                oi_change_4h REAL,
                -- Price changes
                price_change_1h REAL,
                price_change_4h REAL,
                price_change_24h REAL,
                -- Future prices (for labeling)
                future_price_1h REAL,
                future_price_4h REAL,
                label TEXT  -- PUMP, DUMP, NEUTRAL
            )
        ''')

        # ✅ НОВОЕ (Phase 3): Таблица для Paper Trading позиций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,         -- LONG / SHORT
                entry_price REAL NOT NULL,
                quantity REAL NOT NULL,
                stop_loss REAL,
                take_profit REAL,
                status TEXT DEFAULT 'OPEN', -- OPEN / CLOSED
                entry_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                exit_time DATETIME,
                exit_price REAL,
                exit_reason TEXT,           -- TP / SL / SIGNAL / MANUAL
                pnl REAL,                   -- Profit in USD
                pnl_percent REAL            -- Profit in %
            )
        ''')

        # Индексы для ускорения выборок
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_data_ts ON price_data(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_ts_type ON signals(timestamp, signal_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_subscribed ON users(subscribed)')
            # ✅ НОВОЕ: Индексы для market_snapshots
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_snapshots_ts ON market_snapshots(timestamp DESC)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_snapshots_label ON market_snapshots(label)')
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
                VALUES (?, ?, NULL, NULL, NULL, ?, ?, ?)
            ''', (
                price,
                volume,
                indicators.get('bb_upper'),
                indicators.get('bb_lower'),
                indicators.get('fear_greed')
            ))
    
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
    
    # ✅ НОВЫЕ МЕТОДЫ для настроек пользователя
    
    def get_user_settings(self, user_id):
        """Получает настройки пользователя из БД"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT notifications_enabled, min_probability, signal_types, trading_mode
                FROM users
                WHERE user_id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                signal_types_str = row[2] if row[2] else 'PUMP,DUMP'
                return {
                    'notifications': bool(row[0]),
                    'min_probability': row[1] if row[1] else 70,
                    'signal_types': signal_types_str.split(','),
                    'mode': row[3] if row[3] else 'swing'
                }
            else:
                # Возвращаем дефолтные настройки если пользователь не найден
                return {
                    'notifications': True,
                    'min_probability': 70,
                    'signal_types': ['PUMP', 'DUMP'],
                    'mode': 'swing'
                }
        except Exception as e:
            logger.error(f"Error getting user settings: {e}")
            return {
                'notifications': True,
                'min_probability': 70,
                'signal_types': ['PUMP', 'DUMP'],
                'mode': 'swing'
            }
    
    def update_user_settings(self, user_id, **kwargs):
        """
        Обновляет настройки пользователя в БД
        
        Args:
            user_id: ID пользователя
            **kwargs: notifications, min_probability, signal_types, mode
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Сначала проверяем, существует ли пользователь
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            user_exists = cursor.fetchone() is not None
            
            if not user_exists:
                # Создаем пользователя с дефолтными настройками
                cursor.execute("""
                    INSERT INTO users (user_id, username, first_name)
                    VALUES (?, ?, ?)
                """, (user_id, None, None))
            
            # Теперь обновляем настройки
            updates = []
            values = []
            
            if 'notifications' in kwargs:
                updates.append('notifications_enabled = ?')
                values.append(1 if kwargs['notifications'] else 0)
            
            if 'min_probability' in kwargs:
                updates.append('min_probability = ?')
                values.append(kwargs['min_probability'])
            
            if 'signal_types' in kwargs:
                updates.append('signal_types = ?')
                # Конвертируем список в строку
                signal_types = kwargs['signal_types']
                if isinstance(signal_types, list):
                    values.append(','.join(signal_types))
                else:
                    values.append(signal_types)
            
            if 'mode' in kwargs:
                updates.append('trading_mode = ?')
                values.append(kwargs['mode'])
            
            if updates:
                values.append(user_id)
                query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"
                cursor.execute(query, values)
                conn.commit()
                logger.debug(f"Updated settings for user {user_id}: {kwargs}")
            
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error updating user settings: {e}")
            return False
        
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
    
    # ✅ НОВЫЕ МЕТОДЫ для market_snapshots
    
    def save_market_snapshot(self, indicators, market_data):
        """
        Сохраняет полный снимок рынка для ML обучения
        
        Args:
            indicators: dict с техническими индикаторами
            market_data: dict с рыночными данными
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO market_snapshots (
                        price, volume,
                        rsi, macd, macd_signal,
                        bb_upper, bb_middle, bb_lower,
                        ema_50, ema_200,
                        atr, momentum, vwap,
                        volume_ratio, volume_ma,
                        fear_greed, orderbook_imbalance,
                        open_interest, oi_change_5m, oi_change_1h, oi_change_4h,
                        price_change_1h, price_change_4h, price_change_24h
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    market_data.get('current_price', 0),
                    market_data.get('current_volume', 0),
                    # Technical indicators
                    indicators.get('rsi', 0),
                    indicators.get('macd', 0),
                    indicators.get('macd_signal', 0),
                    indicators.get('bb_upper', 0),
                    indicators.get('bb_middle', 0),
                    indicators.get('bb_lower', 0),
                    indicators.get('ema_50', 0),
                    indicators.get('ema_200', 0),
                    indicators.get('atr', 0),
                    indicators.get('momentum', 0),
                    indicators.get('vwap', 0),
                    # Volume
                    indicators.get('volume_ratio', 1.0),
                    market_data.get('volume_ma', 0),
                    # Market data
                    market_data.get('fear_greed', 50),
                    indicators.get('orderbook_imbalance', 0),
                    # Open Interest
                    market_data.get('open_interest', 0),
                    market_data.get('oi_change_5m', 0),
                    market_data.get('oi_change_1h', 0),
                    market_data.get('oi_change_4h', 0),
                    # Price changes
                    market_data.get('price_change_1h', 0),
                    market_data.get('price_change_4h', 0),
                    market_data.get('stats_24h', {}).get('price_change_24h', 0)
                ))
                
                logger.debug(f"Market snapshot saved: price=${market_data.get('current_price', 0):,.2f}")
                
        except Exception as e:
            logger.error(f"Error saving market snapshot: {e}")
    
    def get_training_data(self, min_samples=100, labeled_only=True):
        """
        Получает данные для обучения ML модели
        
        Args:
            min_samples: минимальное количество примеров
            labeled_only: только размеченные данные (с label)
            
        Returns:
            pandas DataFrame или None
        """
        try:
            import pandas as pd
            
            conn = self.get_connection()
            
            query = """
                SELECT * FROM market_snapshots
                WHERE 1=1
            """
            
            if labeled_only:
                query += " AND label IS NOT NULL"
            
            query += " ORDER BY timestamp ASC"
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if len(df) < min_samples:
                logger.warning(f"Not enough training data: {len(df)} < {min_samples}")
                return None
            
            logger.info(f"Retrieved {len(df)} training samples")
            return df
            
        except Exception as e:
            logger.error(f"Error getting training data: {e}")
            return None
    
    def update_future_prices(self, hours_ago=1):
        """
        Обновляет future_price для старых записей и создает метки
        
        Args:
            hours_ago: обновить записи старше N часов
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Получаем записи без future_price старше hours_ago
            cursor.execute("""
                SELECT id, timestamp, price 
                FROM market_snapshots
                WHERE future_price_1h IS NULL
                AND timestamp < datetime('now', ?)
                ORDER BY timestamp ASC
                LIMIT 1000
            """, (f'-{hours_ago} hours',))
            
            records = cursor.fetchall()
            
            if not records:
                logger.debug("No records to update")
                conn.close()
                return
            
            updated = 0
            
            for record_id, timestamp, current_price in records:
                # Находим цену через 1 час
                cursor.execute("""
                    SELECT price FROM market_snapshots
                    WHERE timestamp >= datetime(?, '+1 hour')
                    ORDER BY timestamp ASC
                    LIMIT 1
                """, (timestamp,))
                
                future_1h = cursor.fetchone()
                
                # Находим цену через 4 часа
                cursor.execute("""
                    SELECT price FROM market_snapshots
                    WHERE timestamp >= datetime(?, '+4 hours')
                    ORDER BY timestamp ASC
                    LIMIT 1
                """, (timestamp,))
                
                future_4h = cursor.fetchone()
                
                if future_1h and future_4h:
                    future_price_1h = future_1h[0]
                    future_price_4h = future_4h[0]
                    
                    # Рассчитываем изменение цены
                    change_1h = ((future_price_1h - current_price) / current_price) * 100
                    
                    # Определяем метку
                    if change_1h >= 2.5:
                        label = 'PUMP'
                    elif change_1h <= -2.5:
                        label = 'DUMP'
                    else:
                        label = 'NEUTRAL'
                    
                    # Обновляем запись
                    cursor.execute("""
                        UPDATE market_snapshots
                        SET future_price_1h = ?,
                            future_price_4h = ?,
                            label = ?
                        WHERE id = ?
                    """, (future_price_1h, future_price_4h, label, record_id))
                    
                    updated += 1
            
            conn.commit()
            conn.close()
            
            if updated > 0:
                logger.info(f"Updated {updated} records with future prices and labels")
                
        except Exception as e:
            logger.error(f"Error updating future prices: {e}")
    
    def get_snapshot_stats(self):
        """Получает статистику по снимкам рынка"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN label IS NOT NULL THEN 1 END) as labeled,
                    COUNT(CASE WHEN label = 'PUMP' THEN 1 END) as pump_count,
                    COUNT(CASE WHEN label = 'DUMP' THEN 1 END) as dump_count,
                    COUNT(CASE WHEN label = 'NEUTRAL' THEN 1 END) as neutral_count,
                    MIN(timestamp) as first_snapshot,
                    MAX(timestamp) as last_snapshot
                FROM market_snapshots
            """)
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'total': row[0],
                    'labeled': row[1],
                    'pump_count': row[2],
                    'dump_count': row[3],
                    'neutral_count': row[4],
                    'first_snapshot': row[5],
                    'last_snapshot': row[6]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting snapshot stats: {e}")
            return None

    # ---------------------------------------------------------
    # Paper Trading (Positions) Methods
    # ---------------------------------------------------------
    def save_position(self, symbol, side, entry_price, quantity, stop_loss, take_profit):
        """Opens a new position"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO positions 
                (symbol, side, entry_price, quantity, stop_loss, take_profit, status)
                VALUES (?, ?, ?, ?, ?, ?, 'OPEN')
            ''', (symbol, side, entry_price, quantity, stop_loss, take_profit))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error saving position: {e}")
            return None
        finally:
            conn.close()

    def get_active_positions(self):
        """Returns all positions with STATUS = 'OPEN'"""
        conn = self.get_connection()
        try:
            df = pd.read_sql_query("SELECT * FROM positions WHERE status = 'OPEN'", conn)
            return df
        except Exception as e:
            logger.error(f"Error fetching active positions: {e}")
            return pd.DataFrame()
        finally:
            conn.close()

    def close_position(self, position_id, exit_price, exit_reason, pnl, pnl_percent):
        """Closes an existing position"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE positions 
                SET status = 'CLOSED', 
                    exit_price = ?, 
                    exit_time = CURRENT_TIMESTAMP, 
                    exit_reason = ?, 
                    pnl = ?, 
                    pnl_percent = ?
                WHERE id = ?
            ''', (exit_price, exit_reason, pnl, pnl_percent, position_id))
            conn.commit()
        except Exception as e:
            logger.error(f"Error closing position: {e}")
        finally:
            conn.close()