# ML Model Training Guide

## Быстрый старт

### 1. Сбор данных
Бот автоматически собирает данные в БД при работе. Убедитесь что есть минимум 30-45 дней истории.

### 2. Обучение модели
```bash
python train.py
```

Скрипт:
- Соберёт датасет из `price_data` (90 дней по умолчанию)
- Автоматически разметит примеры (PUMP/DUMP/NEUTRAL)
- Обучит Random Forest модель
- Сохранит модель в `models/btc_model.pkl`
- Покажет метрики качества

### 3. Включение ML модели
В `.env` файле:
```bash
USE_ML_MODEL=true
```

Или в `config.py`:
```python
USE_ML_MODEL = True
```

### 4. Проверка
Бот автоматически загрузит модель при старте. В логах увидите:
```
✅ ML model loaded from models/btc_model.pkl
```

## Параметры обучения

Настройки в `config.py`:

```python
ML_TRAINING_DAYS = 90  # Дней истории
ML_HORIZON_MINUTES = 60  # Горизонт прогноза
ML_PUMP_THRESHOLD = 2.5  # Порог для PUMP (%)
ML_DUMP_THRESHOLD = -2.5  # Порог для DUMP (%)
ML_N_ESTIMATORS = 200  # Количество деревьев
ML_MAX_DEPTH = 15  # Глубина дерева
```

## Требования к данным

- **Минимум**: 30-45 дней истории (для первого обучения)
- **Рекомендуется**: 90+ дней для стабильной модели
- **Идеально**: 180+ дней с разными рыночными условиями

## Метрики качества

Модель считается готовой если:
- F1 Macro ≥ 0.45
- Precision для PUMP/DUMP ≥ 0.55

Если метрики ниже - модель не будет использоваться, fallback на rule-based.

## Структура фичей

Модель использует 19 фичей (без RSI/MACD):
- Bollinger Bands (upper, lower, middle, position)
- EMA (50, 200)
- Volume (ratio, is_high)
- Momentum, ATR, VWAP
- Orderbook imbalance
- Fear & Greed Index
- Price changes (1h, 4h)
- Open Interest changes (5m, 1h, 4h)
- Current volume

## Переобучение

Рекомендуется переобучать модель:
- **Еженедельно** при активной торговле
- **Ежемесячно** для стабильного рынка

Просто запустите `python train.py` снова - модель обновится.

## Troubleshooting

### "Not enough historical data"
Нужно больше данных в БД. Запустите бота на несколько дней/недель.

### "Class X has only N samples"
Недостаточно примеров для класса. Уменьшите пороги (`ML_PUMP_THRESHOLD`, `ML_DUMP_THRESHOLD`) или соберите больше данных.

### Модель не загружается
Проверьте:
1. `USE_ML_MODEL=true` в `.env`
2. Файлы `models/btc_model.pkl` и `models/scaler.pkl` существуют
3. Права доступа к файлам

### Низкие метрики
- Соберите больше данных (180+ дней)
- Попробуйте другие пороги
- Проверьте качество данных в БД

