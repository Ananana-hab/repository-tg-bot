"""
Скрипт для обучения ML модели
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report, confusion_matrix, f1_score, precision_score, recall_score
import joblib
import json
import os
from datetime import datetime
from typing import Tuple
from dataset_builder import DatasetBuilder
import config
import logging

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)


class ModelTrainer:
    """Обучает ML модель на исторических данных"""
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.builder = DatasetBuilder()
        
    def prepare_features_from_dataset(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Подготавливает фичи и метки из датасета
        
        Args:
            df: DataFrame с датасетом
            
        Returns:
            (X, y) - фичи и метки
        """
        # Убираем не-фичи колонки
        feature_cols = [
            'bb_upper', 'bb_lower', 'bb_middle', 'bb_position_above', 'bb_position_below',
            'ema_50', 'ema_200', 'volume_ratio', 'is_high_volume',
            'momentum', 'atr', 'vwap', 'orderbook_imbalance',
            'fear_greed', 'current_volume', 'price_change_1h', 'price_change_4h',
            'oi_change_5m', 'oi_change_1h', 'oi_change_4h'
        ]
        
        X = df[feature_cols].values
        y = df['label'].values
        
        # Кодируем метки: PUMP=2, DUMP=0, NEUTRAL=1
        label_map = {'DUMP': 0, 'NEUTRAL': 1, 'PUMP': 2}
        y_encoded = np.array([label_map[label] for label in y])
        
        return X, y_encoded
    
    def train(self, dataset_path: str = None) -> bool:
        """
        Обучает модель
        
        Args:
            dataset_path: путь к датасету (если None, строит новый)
            
        Returns:
            True если обучение успешно
        """
        logger.info("=" * 50)
        logger.info("Starting ML model training")
        logger.info("=" * 50)
        
        # Загружаем или строим датасет
        if dataset_path and os.path.exists(dataset_path):
            logger.info(f"Loading dataset from {dataset_path}")
            if dataset_path.endswith('.parquet'):
                df = pd.read_parquet(dataset_path)
            else:
                df = pd.read_csv(dataset_path)
        else:
            logger.info("Building new dataset...")
            df = self.builder.build_dataset(
                days=config.ML_TRAINING_DAYS,
                horizon_minutes=config.ML_HORIZON_MINUTES,
                pump_threshold=config.ML_PUMP_THRESHOLD,
                dump_threshold=config.ML_DUMP_THRESHOLD,
                min_samples_per_class=config.ML_MIN_SAMPLES_PER_CLASS
            )
            
            if df is None:
                logger.error("Failed to build dataset")
                return False
            
            # Сохраняем датасет
            os.makedirs(config.MODEL_DIR, exist_ok=True)
            self.builder.save_dataset(df, f'{config.MODEL_DIR}/training_dataset.parquet')
        
        logger.info(f"Dataset loaded: {len(df)} samples")
        logger.info(f"Label distribution:\n{df['label'].value_counts()}")
        
        # Подготавливаем фичи
        X, y = self.prepare_features_from_dataset(df)
        logger.info(f"Features shape: {X.shape}")
        
        # Проверяем на NaN/Inf
        if np.isnan(X).any() or np.isinf(X).any():
            logger.warning("Found NaN/Inf in features, filling...")
            X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Разделение на train/test по времени (80/20)
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        logger.info(f"Train: {len(X_train)}, Test: {len(X_test)}")
        
        # Нормализация
        logger.info("Fitting scaler...")
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Создаём модель
        logger.info("Creating Random Forest model...")
        self.model = RandomForestClassifier(
            n_estimators=config.ML_N_ESTIMATORS,
            max_depth=config.ML_MAX_DEPTH,
            min_samples_leaf=config.ML_MIN_SAMPLES_LEAF,
            random_state=config.ML_RANDOM_STATE,
            class_weight='balanced',  # Балансировка классов
            n_jobs=-1  # Используем все ядра
        )
        
        # Обучение
        logger.info("Training model...")
        self.model.fit(X_train_scaled, y_train)
        
        # Предсказания
        y_pred_train = self.model.predict(X_train_scaled)
        y_pred_test = self.model.predict(X_test_scaled)
        
        # Метрики
        logger.info("\n" + "=" * 50)
        logger.info("TRAINING METRICS")
        logger.info("=" * 50)
        
        label_names = ['DUMP', 'NEUTRAL', 'PUMP']
        
        logger.info("\nTrain Set:")
        logger.info(classification_report(y_train, y_pred_train, target_names=label_names))
        
        logger.info("\nTest Set:")
        logger.info(classification_report(y_test, y_pred_test, target_names=label_names))
        
        # Детальные метрики
        f1_macro_test = f1_score(y_test, y_pred_test, average='macro')
        precision_pump = precision_score(y_test, y_pred_test, labels=[2], average='macro', zero_division=0)
        precision_dump = precision_score(y_test, y_pred_test, labels=[0], average='macro', zero_division=0)
        
        logger.info(f"\nKey Metrics:")
        logger.info(f"  F1 Macro (Test): {f1_macro_test:.4f}")
        logger.info(f"  Precision PUMP: {precision_pump:.4f}")
        logger.info(f"  Precision DUMP: {precision_dump:.4f}")
        
        # Проверяем минимальные пороги
        min_precision = min(precision_pump, precision_dump)
        if f1_macro_test < config.ML_MIN_F1_MACRO:
            logger.warning(f"⚠️ F1 Macro ({f1_macro_test:.4f}) below threshold ({config.ML_MIN_F1_MACRO})")
        if min_precision < config.ML_MIN_PRECISION:
            logger.warning(f"⚠️ Precision ({min_precision:.4f}) below threshold ({config.ML_MIN_PRECISION})")
        
        # Confusion matrix
        logger.info("\nConfusion Matrix (Test):")
        cm = confusion_matrix(y_test, y_pred_test, labels=[0, 1, 2])
        logger.info(f"\n{cm}")
        
        # Feature importance
        feature_names = [
            'bb_upper', 'bb_lower', 'bb_middle', 'bb_pos_above', 'bb_pos_below',
            'ema_50', 'ema_200', 'volume_ratio', 'is_high_volume',
            'momentum', 'atr', 'vwap', 'ob_imbalance',
            'fear_greed', 'volume', 'price_ch_1h', 'price_ch_4h',
            'oi_ch_5m', 'oi_ch_1h', 'oi_ch_4h'
        ]
        
        importances = self.model.feature_importances_
        top_features = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)[:10]
        
        logger.info("\nTop 10 Feature Importances:")
        for name, imp in top_features:
            logger.info(f"  {name}: {imp:.4f}")
        
        # Сохранение
        os.makedirs(config.MODEL_DIR, exist_ok=True)
        
        logger.info(f"\nSaving model to {config.MODEL_PATH}...")
        joblib.dump(self.model, config.MODEL_PATH)
        
        logger.info(f"Saving scaler to {config.SCALER_PATH}...")
        joblib.dump(self.scaler, config.SCALER_PATH)
        
        # Метаданные
        metadata = {
            'trained_at': datetime.now().isoformat(),
            'n_samples_train': len(X_train),
            'n_samples_test': len(X_test),
            'f1_macro_test': float(f1_macro_test),
            'precision_pump': float(precision_pump),
            'precision_dump': float(precision_dump),
            'horizon_minutes': config.ML_HORIZON_MINUTES,
            'pump_threshold': config.ML_PUMP_THRESHOLD,
            'dump_threshold': config.ML_DUMP_THRESHOLD,
            'n_features': X.shape[1],
            'feature_names': feature_names,
            'top_features': {name: float(imp) for name, imp in top_features}
        }
        
        with open(config.MODEL_METADATA_PATH, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Metadata saved to {config.MODEL_METADATA_PATH}")
        
        logger.info("\n" + "=" * 50)
        logger.info("✅ Training completed successfully!")
        logger.info("=" * 50)
        
        return True


if __name__ == '__main__':
    trainer = ModelTrainer()
    success = trainer.train()
    
    if success:
        print("\n✅ Model trained and saved!")
        print(f"   Model: {config.MODEL_PATH}")
        print(f"   Scaler: {config.SCALER_PATH}")
        print(f"   Metadata: {config.MODEL_METADATA_PATH}")
    else:
        print("\n❌ Training failed!")

