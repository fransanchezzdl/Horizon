# Guía de la Flag USE_SENTIMENT

## Resumen

El sistema Horizon ahora soporta dos modos de operación mediante la flag `USE_SENTIMENT`:

1. **Modo Clásico** (`USE_SENTIMENT=False`): Solo análisis técnico con BiGRU + XGBoost
2. **Modo Híbrido** (`USE_SENTIMENT=True`): Análisis técnico + análisis de sentimiento de noticias

## Configuración

### Archivo: `backend/.env`

```env
# Desactivar análisis de sentimiento (modo clásico)
USE_SENTIMENT=False

# O activar análisis de sentimiento (modo híbrido)
USE_SENTIMENT=True
FINNHUB_API_KEY=tu_api_key_aqui
```

## Diferencias entre Modos

### Modo Clásico (USE_SENTIMENT=False)

**Features utilizadas:**
- **Activos estables**: 9 features
  - Close, Volume, RSI, MACD, EMA, Bollinger_PctB, ATR, Log_Return, Volume_Ratio

- **Activos volátiles**: 11 features (9 base + 2 contexto)
  - Las 9 anteriores + VIX_Close, NASDAQ_Return

**Ventajas:**
- ✅ No requiere API key de Finnhub
- ✅ Entrenamiento más rápido
- ✅ Sin límites de rate-limiting
- ✅ Funciona offline

**Desventajas:**
- ❌ Solo señales técnicas (ignora noticias fundamentales)
- ❌ Puede perder eventos importantes (earnings, anuncios)

### Modo Híbrido (USE_SENTIMENT=True)

**Features utilizadas:**
- **Activos estables**: 12 features (9 base + 3 sentimiento)
  - Las 9 del modo clásico + sentiment_score, sentiment_magnitude, news_volume

- **Activos volátiles**: 14 features (11 base + 3 sentimiento)
  - Las 11 del modo clásico + sentiment_score, sentiment_magnitude, news_volume

**Ventajas:**
- ✅ Combina análisis técnico y fundamental
- ✅ Captura impacto de noticias en el precio
- ✅ Mejor accuracy en eventos importantes

**Desventajas:**
- ❌ Requiere API key de Finnhub (gratuita disponible)
- ❌ Límite de 60 llamadas/minuto (tier gratuito)
- ❌ Entrenamiento más lento (descarga de noticias)
- ❌ Requiere conexión a internet

## Cómo Funciona Internamente

### 1. Configuración (config.py)

```python
USE_SENTIMENT = os.getenv("USE_SENTIMENT", "True").lower() == "true"

def get_feature_cols(ticker: str) -> list:
    """Retorna features según tipo de activo y flag USE_SENTIMENT."""
    if ticker in TICKERS["volatile"]:
        base = VOLATILE_WITH_SENTIMENT_COLS if USE_SENTIMENT else VOLATILE_FEATURE_COLS
    else:
        base = BASE_WITH_SENTIMENT_COLS if USE_SENTIMENT else BASE_FEATURE_COLS
    return base.copy()
```

### 2. Pipeline de Datos (data_pipeline.py)

```python
def compute_features(df, include_market_context, ticker):
    # ... calcular features técnicas ...
    
    # Añadir features de sentimiento si está habilitado
    if USE_SENTIMENT and ticker:
        try:
            from .sentiment import compute_historical_sentiment
            sentiment_df = compute_historical_sentiment(ticker, start_date, end_date)
            # Agregar sentiment_score, sentiment_magnitude, news_volume
            for col in SENTIMENT_FEATURE_COLS:
                tech_df[col] = sentiment_df[col].values
        except Exception as exc:
            # Si falla, usar valores neutros (0.0, 0.0, 0)
            logging.warning("Usando valores neutros de sentimiento")
```

### 3. Entrenamiento (ensemble.py)

El entrenamiento es **automático** según la flag:
- Lee `USE_SENTIMENT` de config
- Llama a `get_feature_cols(ticker)` que retorna el número correcto de features
- Entrena modelos con el número correcto de input_dim

### 4. Predicción (ensemble.py)

La predicción también es **automática**:
- Lee `USE_SENTIMENT` de config
- Llama a `get_feature_cols(ticker)` para saber qué features usar
- Si `USE_SENTIMENT=True`, calcula sentimiento de últimos 7 días
- Si `USE_SENTIMENT=False`, solo usa features técnicas

## Cambiar entre Modos

### Opción 1: Cambiar la Flag y Re-entrenar

```bash
# 1. Cambiar en backend/.env
USE_SENTIMENT=True  # o False

# 2. Re-entrenar modelos
python train_model.py
```

**Importante**: Los modelos entrenados con una configuración NO son compatibles con la otra. Debes re-entrenar.

### Opción 2: Mantener Ambos Modelos

Puedes mantener dos conjuntos de modelos:

```bash
# Entrenar con sentimiento
USE_SENTIMENT=True
python train_model.py
# Guarda en: backend/models/saved_models/KO_model_*.pth (12 features)

# Renombrar modelos
mv backend/models/saved_models backend/models/saved_models_with_sentiment

# Entrenar sin sentimiento
USE_SENTIMENT=False
python train_model.py
# Guarda en: backend/models/saved_models/KO_model_*.pth (9 features)

# Renombrar modelos
mv backend/models/saved_models backend/models/saved_models_classic
```

Luego cambiar entre ellos según necesites.

## Degradación Graceful

El sistema está diseñado para **degradar gracefully** si hay problemas con el análisis de sentimiento:

1. **Sin API key**: Usa valores neutros (0.0, 0.0, 0) automáticamente
2. **Rate limit excedido**: Usa valores neutros y continúa
3. **Error de red**: Usa valores neutros y continúa
4. **FinBERT no disponible**: Usa valores neutros y continúa

Esto significa que incluso con `USE_SENTIMENT=True`, el sistema **nunca falla** por problemas de sentimiento.

## Recomendaciones

### Para Desarrollo/Testing
```env
USE_SENTIMENT=False
```
- Entrenamiento más rápido
- Sin dependencias externas
- Ideal para iterar rápidamente

### Para Producción
```env
USE_SENTIMENT=True
FINNHUB_API_KEY=tu_api_key_real
```
- Mejor accuracy
- Captura eventos fundamentales
- Recomendado para trading real

## Verificar Configuración Actual

```python
from backend.models.config import USE_SENTIMENT, get_feature_cols

print(f"USE_SENTIMENT: {USE_SENTIMENT}")
print(f"Features para KO: {len(get_feature_cols('KO'))} features")
print(f"Features para BTC-USD: {len(get_feature_cols('BTC-USD'))} features")
```

Salida esperada:
```
# Con USE_SENTIMENT=False
USE_SENTIMENT: False
Features para KO: 9 features
Features para BTC-USD: 11 features

# Con USE_SENTIMENT=True
USE_SENTIMENT: True
Features para KO: 12 features
Features para BTC-USD: 14 features
```

## Troubleshooting

### Error: "not in index" durante entrenamiento
**Causa**: Modelos entrenados con una configuración, pero intentando predecir con otra.
**Solución**: Re-entrenar modelos con la configuración actual.

### Error: "API limit reached"
**Causa**: Límite de Finnhub excedido (60 llamadas/minuto).
**Solución**: 
- Esperar 1 minuto
- O cambiar a `USE_SENTIMENT=False` temporalmente
- O usar una API key de pago

### Sentimiento siempre en 0.0
**Causa**: API key no configurada o inválida.
**Solución**: Verificar `FINNHUB_API_KEY` en `.env`
