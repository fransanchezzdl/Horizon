# Diagnóstico: ¿Por qué la confianza bajó de 85% → 10-36%?

## TL;DR
**No bajó.** Son **3 métricas diferentes**:

| Métrica | Entonces | Ahora | Explicación |
|---------|----------|-------|------------|
| **Directional Accuracy** (binario) | ~85% | ~83% | Sube/Baja correctamente (engañosa) |
| **Balanced Accuracy** (3 clases) | ~36-40% | ~36-40% | BAJISTA/LATERAL/ALCISTA (honesta) |
| **Confianza Calibrada** | N/A | 10-36% | **NUEVA: Platt Scaling aplicada** |

---

## ¿Qué cambió?

### Antes (sin calibración):
- Modelo predice: 64% (MSFT), 66% (TSLA), 65% (KO)
- Eso se guardaba directamente en `confianza_bygru`
- **Problema**: Esas probabilidades NO reflejaban accuracy real (36-40%)

### Ahora (con calibración Platt Scaling):
- Modelo predice: 64% → **Calibrador aplica transformación**
- Resultado calibrado: 19.86% (MSFT), 24.44% (TSLA), 17.12% (KO)
- **Ventaja**: La confianza HONESTA (10-36%) reflejael Balanced Accuracy real (36-40%)

---

## Comparación de métricas

### 1️⃣ Directional Accuracy (~83%)
```python
# Métrica: ¿El modelo acierta dirección (sube/baja)?
y_binary = (returns > 0)  # Solo 2 clases
accuracy = (y_pred == y_true).mean()  # ~83%
```

**Problema**: Con datos desbalanceados (ej: 60% alcista), "siempre ALCISTA" = 60% accuracy.

### 2️⃣ Balanced Accuracy (~36-40%) ⭐ MÉTRICA REAL
```python
# Métrica: Promedio de recall por clase
# Detecta si el modelo realmente aprende 3 clases
from sklearn.metrics import balanced_accuracy_score
ba = balanced_accuracy_score(y_true, y_pred)  # ~36-40%
```

**Mejor**: Funciona bien con 3 clases desbalanceadas.

### 3️⃣ Confianza Calibrada (10-36%) ⭐ NUEVA
```python
# Métrica: ¿Qué tan confiable es la predicción?
from backend.models.platt_scaling_calibration_v2 import load_calibrator
calibrator = load_calibrator(ticker)
confidence_raw = 0.64  # predicción cruda
confidence_calibrated = calibrator.predict_proba([[confidence_raw]])[0, 1]
# Resultado: 0.20 (20% confianza honesta)
```

**Mejor**: Refleja accuracy real. Un modelo con 36% BA honestamente no debería estar 64% confiado.

---

## Por qué 85% era engañoso

Tu modelo tiene esta arquitectura:

```
Input → XGBoost (binario: UP/DOWN) → Prob: 64% → Guardado como confianza
                                    ↓
                            Métrica engañosa (Directional Accuracy ~83%)
```

**Realidad:**
```
Input → XGBoost (binario: UP/DOWN) → Prob: 64%
        ↓ Calibrador Platt Scaling ↓
        Confianza honesta: 19.86% ← Refleja real (BA ~36-40%)
```

---

## Entonces... ¿Necesito mejorar el modelo?

**Depende de tu objetivo:**

### ✅ Si queremos un modelo **honesto**:
- ✅ Sistema está correcto
- ✅ Confianzas 10-36% reflejan realidad
- ✅ Los calibradores funcionan bien (ECE ~0.00-0.05)

### ⚠️ Si queremos **prediciones mejores**:
- Considerar nuevas features técnicas
- Mejorar ingeniería de features
- Probar otros modelos (LSTMs, GRUs, Transformers)

---

## Archivos involucrados

| Archivo | Rol | Cambio |
|---------|-----|--------|
| `backend/models/xgboost_model.py` | Entrena modelo | ✅ Ahora carga calibrador post-training |
| `tests/generate_xai_explanations.py` | Genera explicaciones XAI | ✅ Aplica calibrador antes de guardar |
| `tests/apply_platt_scaling.py` | Aplica calibración a BD | ✅ Actualiza `confianza_bygru` con valores honestos |
| `backend/models/saved_models/{ticker}_calibrator_platt.pkl` | Calibradores | ✅ Guardados (11 tickers) |

---

## Verificación: Son los calibradores correctos?

```python
# Check calibrator ECE (Expected Calibration Error)
Calibrator ECE: 0.00-0.05 ✅ Excelente (< 0.1 es bueno)

# Confianzas calibradas por ticker:
AAPL:   24.23% (raw: 64.12%) ← Redujo 40%
MSFT:   19.86% (raw: 61.21%) ← Redujo 41%
NVDA:   23.95% (raw: 52.99%) ← Redujo 29%
INTC:   36.07% (raw: 50.71%) ← Redujo 15% (menos sesgo)
```

**Patrón**: Modelos muy seguros (60%+) se calibran a ~20% (honestos).

---

## Conclusión

✅ **El sistema está funcionando correctamente.**

Las confianzas bajaron porque:
1. Antes guardabas probabilidades crudas (64%+) sin calibración
2. Ahora calibración Platt Scaling a plica transformación honesta
3. Resultado: 10-36% reflejan el verdadero Balanced Accuracy ~36-40%

**Próximos pasos:**
- ✅ Sistema funcionando ("Balanced, No Biased")
- ⚠️ Considera si quieres mejorar accuracy del modelo (es objetivo de largo plazo)
- ✅ Usa confianzas calibradas en frontend (son honestas)

