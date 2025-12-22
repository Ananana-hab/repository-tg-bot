
import pandas as pd
import numpy as np
import logging
import config
from database import Database
from indicators import TechnicalIndicators
from ml_model import MLPredictor
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("train_ml")

def train_model():
    """
    Main function to train the ML model
    """
    logger.info("Starting ML model training pipeline...")
    
    # 1. Load Data
    db = Database()
    # We need to fetch historical OHLCV. 
    # Current DB might store signals, but we need candle history.
    # database.py usually has methods to save/load price data, 
    # but the 'price_data' table might be just snapshots.
    # Ideally we should use the fetched history we store or re-fetch it.
    # For now, let's assume we can fetch history using data_collector logic or from the 'market_data' table if it exists.
    # In `main.py`, we save price data: self.db.save_price_data(...)
    
    # Let's check `database.py` to see what we have.
    # If no history table, we might need to fetch fresh history from binance for training.
    
    # To keep it robust, let's fetch fresh 90 days history using ccxt (DataCollector) or just separate script logic.
    # Since DataCollector is now async, using it here requires async.
    # Or simplified: use ccxt sync just for this script or re-use DataCollector in async run.
    
    # Let's first try to load from DB 'price_history' if available.
    # If not, we download.
    
    logger.info("Fetching historical data for training...")
    try:
        # Temporary: use direct CCXT sync for simple script execution
        import ccxt
        exchange = ccxt.binance()
        
        # Download 90 days of 5m data
        timeframe = '5m'
        limit = 1000 # batch size
        since = exchange.milliseconds() - (config.ML_TRAINING_DAYS * 24 * 60 * 60 * 1000)
        
        all_candles = []
        while since < exchange.milliseconds():
            candles = exchange.fetch_ohlcv(config.SYMBOL, timeframe, since, limit)
            if not candles:
                break
            all_candles.extend(candles)
            since = candles[-1][0] + 1
            print(f"Fetched {len(all_candles)} candles...", end='\r')
            
        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        logger.info(f"Total data points: {len(df)}")
        
    except Exception as e:
        import traceback
        logger.error(f"Failed to fetch data: {e}")
        traceback.print_exc()
        return

    # 2. Calculate Indicators
    logger.info("Calculating indicators...")
    # Utilize backtester logic or TechnicalIndicators
    # We need to calculate indicators for the whole dataframe
    # TechnicalIndicators methods usually take DF and return scalar or Series?
    # calculate_all_indicators in main.py takes DF and returns scalars for the last row.
    # We need VECTORIZED calculation for training. 
    # Luckily, `backtester.py` implemented some vectorized logic (simulate_trading).
    # We should use that or extend TechnicalIndicators to support full DF return.
    
    # For now, let's implement vectorized calc here (similar to backtester)
    df = calculate_indicators_vectorized(df)
    
    # DROP NaN (initial warming period)
    df.dropna(inplace=True)
    logger.info(f"Data points after dropna: {len(df)}")

    # 3. Label Data (Create Targets)
    # Target: 
    # 0 = DUMP (Price drops > X% in next 12 candles / 1h)
    # 1 = NEUTRAL
    # 2 = PUMP (Price rises > X% in next 12 candles / 1h)
    
    HORIZON = 12 # 1 hour for 5m candles
    THRESHOLD = 0.015 # 1.5% movement
    
    df['future_close'] = df['close'].shift(-HORIZON)
    df['price_change_future'] = (df['future_close'] - df['close']) / df['close']
    
    conditions = [
        (df['price_change_future'] > THRESHOLD),
        (df['price_change_future'] < -THRESHOLD)
    ]
    choices = [2, 0] # 2=PUMP, 0=DUMP
    df['target'] = np.select(conditions, choices, default=1) # 1=NEUTRAL
    
    # Drop last rows where future is NaN
    df.dropna(subset=['future_close'], inplace=True)
    
    logger.info("Class distribution:")
    logger.info(df['target'].value_counts())

    # 4. Prepare Features
    # We need to match `ml_model.py` prepare_features EXPECTATIONS.
    # ml_model.py expects: bb_upper, bb_lower, bb_middle, bb_position_above...
    # We need to map our DF columns to a numpy array for each row, or use sklearn on DF.
    
    # Let's verify ml_model features list again.
    # It constructs feature vector manually from a dict.
    # We must match that order exactly.
    
    predictor = MLPredictor()
    X = []
    y = []
    
    # This loop is slow but ensures 100% consistency with live inference prepare_features
    # Optimally we would vectorize this, but for < 50k rows it's acceptable for now.
    logger.info("Building feature vectors...")
    
    for i in range(len(df)):
        row = df.iloc[i]
        
        # Construct indicators dict mimicking what main.py passes
        indicators_dict = {
            'bb_upper': row['bb_upper'],
            'bb_lower': row['bb_lower'],
            'bb_middle': row['bb_middle'],
            'bb_position': row['bb_position'], # string!
            'ema_50': row['ema_50'],
            'ema_200': row['ema_200'],
            'volume_ratio': row['volume_ratio'],
            'is_high_volume': row['is_high_volume'],
            'momentum': row['momentum'],
            'atr': row['atr'],
            'vwap': row['vwap'],
            'orderbook_imbalance': 0, # Historical OB data missing usually
            'rsi': row['rsi'],
            'macd_crossover': row['macd_crossover'],
            'macd_histogram': row['macd_histogram']
        }
        
        market_data_dict = {
            'fear_greed': 50, # Fake history F&G
            'current_volume': row['volume'],
            'price_change_1h': row.get('pct_change_1h', 0) * 100,
            'price_change_4h': 0,
            'current_price': row['close']
        }
        
        try:
            features = predictor.prepare_features(indicators_dict, market_data_dict, mode='swing')
            X.append(features[0])
            y.append(int(row['target']))
        except Exception as e:
            continue
            
    X = np.array(X)
    y = np.array(y)
    
    # 5. Advanced Training (V2)
    logger.info(f"Training model on {len(X)} samples...")
    predictor.create_default_model()
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # --- V2 Improvements ---
    
    # A. Class Balancing with SMOTE
    logger.info("Applying SMOTE to balance classes...")
    try:
        from imblearn.over_sampling import SMOTE
        from imblearn.pipeline import Pipeline as ImbPipeline
        smote = SMOTE(random_state=42)
        X_train_res, y_train_res = smote.fit_resample(X_train, y_train)
        logger.info(f"Resampled training set shape: {X_train_res.shape}")
        
        # Check new distribution
        unique, counts = np.unique(y_train_res, return_counts=True)
        logger.info(f"New class distribution: {dict(zip(unique, counts))}")
        
    except ImportError:
        logger.error("imbalanced-learn not installed. Skipping SMOTE.")
        X_train_res, y_train_res = X_train, y_train

    # B. Hyperparameter Optimization with GridSearchCV
    from sklearn.model_selection import GridSearchCV
    from sklearn.ensemble import RandomForestClassifier
    
    logger.info("Starting GridSearchCV for Hyperparameter Tuning...")
    
    # Define parameter grid (Optimized for speed)
    param_grid = {
        'n_estimators': [100, 200],
        'max_depth': [10, 20, None],
        'min_samples_split': [2, 10],
        'class_weight': ['balanced', 'balanced_subsample']
    }
    
    rf = RandomForestClassifier(random_state=42) # Create an instance for GridSearchCV
    grid_search = GridSearchCV(
        estimator=rf, # Use the RandomForestClassifier instance
        param_grid=param_grid,
        cv=3, # Changed from 2
        n_jobs=1, # FIX: Set to 1 to avoid joblib TerminatedWorkerError on Windows
        verbose=2,
        scoring='f1_macro'
    )
    
    # Fit GridSearch on RESAMPLED data
    grid_search.fit(X_train_res, y_train_res)
    
    best_model = grid_search.best_estimator_
    logger.info(f"Best Parameters: {grid_search.best_params_}")
    
    # Update predictor with best model
    predictor.model = best_model
    
    # 6. Evaluate
    logger.info("Training complete. Evaluation on TEST set (original distribution):")
    y_pred = predictor.model.predict(X_test)
    
    print("Classification Report:")
    print(classification_report(y_test, y_pred, target_names=['DUMP', 'NEUTRAL', 'PUMP']))
    
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    # Fit scaler on training data
    logger.info("Fitting StandardScaler...")
    predictor.scaler.fit(X_train)
    
    # 7. Save
    os.makedirs('models', exist_ok=True)
    predictor.save_model()
    logger.info(f"Model saved to {predictor.model_path}")
    
    # Save scaler if used (not currently using scaler in separate file, but good practice if needed)
    # joblib.dump(scaler, 'models/scaler.pkl')

def calculate_indicators_vectorized(df):
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # BB
    df['bb_middle'] = df['close'].rolling(window=20).mean()
    df['bb_std'] = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['bb_middle'] + (2 * df['bb_std'])
    df['bb_lower'] = df['bb_middle'] - (2 * df['bb_std'])
    
    df['bb_position'] = 'inside'
    df.loc[df['close'] > df['bb_upper'], 'bb_position'] = 'above_upper'
    df.loc[df['close'] < df['bb_lower'], 'bb_position'] = 'below_lower'

    # EMA
    df['ema_50'] = df['close'].ewm(span=50).mean()
    df['ema_200'] = df['close'].ewm(span=200).mean()

    # MACD
    exp1 = df['close'].ewm(span=12).mean()
    exp2 = df['close'].ewm(span=26).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9).mean()
    df['macd_histogram'] = macd - signal
    
    df['macd_crossover'] = 'none'
    df.loc[(df['macd_histogram'] > 0) & (df['macd_histogram'].shift(1) <= 0), 'macd_crossover'] = 'bullish'
    df.loc[(df['macd_histogram'] < 0) & (df['macd_histogram'].shift(1) >= 0), 'macd_crossover'] = 'bearish'

    # Momentum (Close - Close 10 bars ago)
    df['momentum'] = df['close'].diff(10)

    # ATR
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['atr'] = true_range.rolling(14).mean()

    # Volume Ratio
    df['volume_ma'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma']
    df['is_high_volume'] = df['volume_ratio'] > 1.5
    
    # VWAP (approx)
    df['vwap'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
    
    df['pct_change_1h'] = df['close'].pct_change(12)
    
    return df

if __name__ == "__main__":
    train_model()
