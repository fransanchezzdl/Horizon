# 📊 ANÁLISIS EN PROFUNDIDAD: Configuraciones Óptimas por Tipo de Activo

## 1. RESULTADOS OBSERVADOS (Con Configuración Segregada)

### STABLE Activos (KO, AAPL, GOOGL, MSFT, GC=F, SI=F, VXX):
```
Config: n_est=600, max_depth=5, lr=0.04, subsample=0.9, colsample=0.9, early_stop=25
```

| Ticker | BA % | Prec UP | Recall UP | Dir Acc | F1 | Observación |
|--------|------|---------|-----------|---------|----|----|
| VXX (estable) | 36.35% | 51.85% | 27.18% | 46.13% | 35.57% | ✅ Buena Precision |

**Patrón:** VXX muestra precision mejor (51%) pero recall bajo (27%). Estructura está funcionando bien.

---

### VOLATILE Activos (TSLA, NVDA, BTC-USD, ETH-USD, AMZN, BABA, INTC, META, NFLX):
```
Config: n_est=800, max_depth=3, lr=0.02, subsample=0.75, colsample=0.75, early_stop=40
```

| Ticker | BA % | Prec UP | Recall UP | Dir Acc | F1 | Observación |
|--------|------|---------|-----------|---------|----|----|
| TSLA (volatile) | 33.69% | 28.57% | 20.00% | 71.19% | 33.28% | ⚠️ Recall muy bajo |
| NFLX (volatile) | 36.87% | 23.81% | 26.79% | 65.02% | 28.53% | ⚠️ Precisión baja |

**Patrón:** Volatile sigue siendo problemático. Recall muy bajo, mayor regularización quizá sea excesiva.

---

## 2. INSIGHTS CLAVE

### ✅ Lo que FUNCIONA:
1. **Segregación por tipo SÍ está bien implementada** ✅
   - Logs muestran "Usando config STABLE/VOLATILE" correctamente
   - Cada modelo recibe configuración apropiadadd

2. **Stable actors**:
   - Mejor Precision (51% en VXX vs 28% en TSLA)
   - Más predictibilidad
   - Config menos regularizada ayuda

3. **Métricas Base**:
   - Todos alrededor de 33-37% BA (consistente)
   - Sin sesgo sistemático (ok)
   - Sin colapso a una sola clase (ok)

### ❌ Lo que MEJORA:
1. **Volatile está INFRA-regularizado en recall**
   - TSLA: Recall 20% (demasiado bajo)
   - NFLX: Recall 26% (bajo)
   - Posible: max_depth=3 es demasiado restrictivo

2. **Probability distribution problem**
   - Las probabilidades siguen siendo bajas (0.3-0.45 range)
   - Modelo es naturalmente incierto

---

## 3. CONFIGURACIONES ÓPTIMAS RECOMENDADAS

### OPCIÓN A: Mantener pero Ajustar (RECOMENDADO)

**STABLE (menos cambios, está bien):**
```python
XGBOOST_STABLE_CONFIG = {
    "n_estimators": 550,       # ↓ 600→550 (menos overfitting)
    "max_depth": 5,            # ✓ mantener
    "learning_rate": 0.045,    # ↑ 0.04→0.045 (aprende ligeramente mejor)
    "subsample": 0.92,         # ↑ 0.9→0.92 (menos regularización)
    "colsample_bytree": 0.92,  # ↑ 0.9→0.92
    "early_stopping_rounds": 25,  # ✓ mantener
}
```
→ **Esperado:** +0.5-1% en BA (precision se mantiene)

**VOLATILE (ajuste crítico para recall):**
```python
XGBOOST_VOLATILE_CONFIG = {
    "n_estimators": 700,       # ↓ 800→700 (menos evaluadores)
    "max_depth": 4,            # ↑ 3→4 (MÁS profundidad! CRÍTICO)
    "learning_rate": 0.025,    # ↑ 0.02→0.025 (learning rate ligeramente mejor)
    "subsample": 0.8,          # ↑ 0.75→0.8 (menos regularización drástica)
    "colsample_bytree": 0.8,   # ↑ 0.75→0.8
    "early_stopping_rounds": 35,  # ↓ 40→35 (menos paciencia)
}
```
→ **Esperado:** Recall TSLA 20%→28%, NFLX 26%→34% (+7-8%)

---

## 4. MEJORAS SIN CAMBIAR ESTRUCTURA (NO INVASIVAS)

### 4.1: Percentile-Based Feature Importance Weighting ⭐ (NUEVA)

**Actual:** Todas las features tienen igual peso en XGBoost

**Propuesta:** Ajustar `feature_importance` después del entrenamiento:
```python
# Después de train_xgboost(), normalizar features
importances = model.feature_importances_
top_features_mask = importances > np.percentile(importances, 70)

# Guardar top 30% features para inference
top_feature_indices = np.where(top_features_mask)[0]
```
→ **Beneficio:** Reducir ruido, mejorar generalización +1-2%

---

### 4.2: Dynamic Scale Pos Weight por Volatilidad ⭐ (NUEVA)

**Actual:** scale_pos_weight = n_not_alcista / n_alcista (fijo ~2.0)

**Propuesta:** Ajustar según volatilidad de mercado
```python
# Medir volatilidad del training set
y_train_volatility = np.std(y_train_continuous)

if y_train_volatility > 0.05:  # Highly volatile
    scale_pos_weight *= 1.3  # Más penalti
elif y_train_volatility < 0.02:  # Stable
    scale_pos_weight *= 0.9  # Menos penalti

# TSLA (volatile, σ≈0.067): scale_pos_weight = 2.0 × 1.3 = 2.6
# KO (stable, σ≈0.018): scale_pos_weight = 2.0 × 0.9 = 1.8
```
→ **Beneficio:** +1-3% mejor balance Precision/Recall en volatile

---

### 4.3: Adaptive Early Stopping Rounds ⭐ (NUEVA)

**Actual:** Fixed early_stopping (25/40 según tipo)

**Propuesta:** Adaptativo basado en validation loss:
```python
# En lugar de early_stopping_rounds fijo:
early_stop = 20 if balanced_acc > 0.40 else 40
```
→ **Beneficio:** Si modelo is improving, train longer. Si está atascado, stop rápido. +0.5-1%

---

### 4.4: Smart Threshold Calibration ⭐ (NUEVA - LA MÁS PROMETEDORA)

**Actual:** Umbrales percentile fijos (25/75)

**Propuesta:** Calibrar basado en validation confusion matrix
```python
# Después de predict_proba en validation:
# Encontrar thresholds que maximicen macro_f1 (no solo accuracy)
from sklearn.metrics import f1_score

for prob_down in np.arange(0.1, 0.5, 0.05):
    for prob_up in np.arange(prob_down+0.1, 0.9, 0.05):
        y_pred_test = np.ones(len(y_prob))
        y_pred_test[y_prob >= prob_up] = 2
        y_pred_test[y_prob <= prob_down] = 0
        
        f1 = f1_score(y_val, y_pred_test, average='macro')
        if f1 > best_f1:
            best_f1 = f1
            best_down = prob_down
            best_up = prob_up

# Guardar best thresholds, no percentiles
thresholds = {
    "prob_down": best_down,  # Data-driven, no 25%ile
    "prob_up": best_up,      # Data-driven, no 75%ile
}
```
→ **Beneficio:** +2-4% en recall (CRÍTICO!)

---

## 5. ROADMAP DE IMPLEMENTACIÓN (Sin Cambiar Estrcutura)

### Priority 1 (HIGH IMPACT - 5 min):
1. ✅ Cambiar VOLATILE max_depth 3→4 (fix inmediato recall bajo)
2. ✅ Ajustar subsample 0.75→0.8 (reduce regularización excesiva)

### Priority 2 (MEDIUM IMPACT - 15 min):
3. Implementar Smart Threshold Calibration (max_f1 basado)
4. Implementar Dynamic Scale Pos Weight (volatility-aware)

### Priority 3 (NICE TO HAVE - 20 min):
5. Feature Importance Weighting (top 30%)
6. Adaptive Early Stopping

---

## 6. BENCHMARK: Resultados Esperados Después de Cambios

### Con solo Priority 1 (5 min):
```
STABLE promedio: 36-37% → 36-37% (sin cambio, está bien)
VOLATILE promedio: 33-35% → 35-37% (↑ 2-3%)
OVERALL: 35% → 36% BA
```

### Con Priority 1 + 2 (20 min):
```
STABLE: 36% → 37-38%
VOLATILE: 35% → 37-39%
OVERALL: 36% → 37-38% BA
+3-5% Recall en VOLATILE (CRÍTICO!)
```

---

## 7. RECOMENDACIÓN FINAL

**Implementa Priority 1 + Priority 2 (total ~15 minutos):**

1. **Cambiar max_depth VOLATILE 3→4** (máximo beneficio/esfuerzo)
2. **Implementar Smart Threshold** (data-driven, no percentiles fijos)
3. **Re-entrenar todos (10 min)**

**Resultado esperado:**
- BA global: 36% → **37-38%** ✅
- Recall VOLATILE: 20-26% → **28-35%** ✅✅
- Sin cambiar arquitectura ✅
- Código limpio, reproducible ✅
