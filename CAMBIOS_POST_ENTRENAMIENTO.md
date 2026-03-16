# Cambios: Guardado de Datos Post-Entrenamiento Sin Sentimiento

## Descripción
después de entrenar el modelo sin sentimiento (`sentiment_flag = false`), se guardan automáticamente en la tabla `activos` de Supabase los datos relevantes.

## Campos Guardados

| Campo | Tipo | Descripción | Fuente |
|-------|------|-------------|--------|
| `precio` | NUMERIC | Precio actual del día en Yahoo Finance | `current_price` del ensemble |
| `senal_ia` | TEXT | Tendencia predicha (ALCISTA/BAJISTA/LATERAL) | `trend` del ensemble |
| `confianza_bygru` | NUMERIC(5,4) | Confianza del modelo (0-1) | `confidence` del ensemble (proporción de modelos que acuerdan) |
| `grafico_prediccion` | JSONB | Cajon desastre con todas las métricas adicionales | Conjunto de datos agregados |

## Contenido de `grafico_prediccion`

El campo `grafico_prediccion` contiene un JSON con:

### Métricas de Predicción
```json
{
  "predicted_price": 79.45,
  "price_upper": 80.12,
  "price_lower": 78.78,
  "predicted_return": 0.0142,
  "predicted_return_pct": 1.42,
  
  // Meta-ensemble (BiGRU + XGBoost)
  "meta_trend": "ALCISTA",
  "meta_score": 0.8234,
  
  // XGBoost
  "xgboost_direction": "ALCISTA",
  "xgboost_probability": 0.7823,
  
  // Información del ensemble
  "n_individual_models": 5,
  
  // Métricas del entrenamiento (opcional)
  "training_metrics": {
    "avg_val_loss": 0.001234,
    "avg_directional_accuracy": 0.7834,
    "avg_mae": 0.4521,
    "avg_rmse": 0.6234,
    "dynamic_threshold": 0.0125,
    "xgb_directional_accuracy": 0.75
  }
}
```

## Cambios en el Código

### 1. `backend/services/activo_update_service.py`
**Nuevo método:** `guardar_datos_post_entrenamiento()`

```python
@staticmethod
def guardar_datos_post_entrenamiento(
    ticker: str,
    ensemble_prediction: Dict,
    training_metrics: Optional[Dict] = None
) -> bool:
    """
    Guarda datos post-entrenamiento en tabla activos.
    - precio: precio actual del ensemble
    - senal_ia: trend del ensemble
    - confianza_bygru: confidence del ensemble
    - grafico_prediccion: JSON con todas las métricas
    """
```

**Parámetros:**
- `ticker`: Símbolo del activo (ej: "AAPL")
- `ensemble_prediction`: Dict retornado por `predict_ensemble()` con trend, confidence, current_price, etc.
- `training_metrics`: Dict opcional con avg_val_loss, avg_directional_accuracy, etc.

**Retorna:** `bool` (True si fue exitosa la actualización)

### 2. `backend/models/train_all.py`
**Cambios:**
- Importa `predict_ensemble` del módulo ensemble
- Importa `activo_update_service` si `USE_SENTIMENT = False`
- Después de entrenar cada ticker:
  1. Llama a `predict_ensemble(ticker)` para obtener predicciones
  2. Llama a `guardar_datos_post_entrenamiento()` para guardar en BD
  3. Marca en el resumen si se guardó exitosamente (💾 o ❌)

**Salida en consola:**
```
✅ KO         | Val Loss: 0.001234 | Dir. Acc: 78.34% | ... Tiempo: 45.2s 💾
```

## Uso

### Opción 1: Entrenar TODO automáticamente y guardar en BD
```bash
# Requiere: USE_SENTIMENT = False en config.py
python -m backend.models.train_all
```

### Opción 2: Guardar datos manualmente desde código
```python
from backend.models.ensemble import predict_ensemble
from backend.services import activo_update_service
from backend.models.train_all import train_ensemble

# Entrenar
training_metrics = train_ensemble("AAPL")

# Obtener predicciones
prediction = predict_ensemble("AAPL")

# Guardar en BD
activo_update_service.guardar_datos_post_entrenamiento(
    "AAPL",
    prediction,
    training_metrics
)
```

## Flujo Completo

```
1. train_ensemble("AAPL")
   ├─ Entrena 5 modelos BiGRU
   ├─ Entrena XGBoost
   └─ Retorna métricas de entrenamiento

2. predict_ensemble("AAPL")  [NUEVO]
   ├─ Carga los 5 modelos entrenados
   ├─ Descarga datos recientes de Yahoo Finance
   ├─ Calcula predicciones
   ├─ Calcula meta-ensemble (BiGRU + XGBoost)
   └─ Retorna trend, confidence, current_price, etc.

3. guardar_datos_post_entrenamiento()  [NUEVO]
   ├─ Extrae: precio, senal_ia, confianza
   ├─ Construye JSON de grafico_prediccion
   └─ Actualiza tabla activos en Supabase

4. Resumen final
   └─ Muestra 💾 si se guardó, ❌ si falló
```

## Configuración Necesaria

En `backend/models/config.py`:
```python
USE_SENTIMENT = False  # Debe ser False para activar guardado en BD
```

## Notas de Implementación

- **Seguridad de datos:** Todas las conversiones a float se hacen con manejo de excepciones
- **Validación:** Se valida que la señal sea ALCISTA/BAJISTA/LATERAL
- **Logs:** Impresa mensajes de éxito (✅) y error (❌) en consola
- **Independencia:** Si falla el guardado en BD, el entrenamiento NO se interrumpe
- **Cajon desastre:** El campo `grafico_prediccion` es flexible y puede contener cualquier métrica futura

## Troubleshooting

### Error: "No se puede usar BD"
- Especifica si estás dentro del backend (requiere módulo disponible)
- Verifica que las credenciales de Supabase estén configuradas en `.env`

### Error: "Datos insuficientes"
- `predict_ensemble()` necesita al menos 60 días de datos para algunos activos
- Verifica que Yahoo Finance tenga datos para ese ticker

### La tabla activos no se actualiza
- Verifica que el ticker exista en la tabla activos
- Revisa los logs de error en consola para ver el motivo exacto
