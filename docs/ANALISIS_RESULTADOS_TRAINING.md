# 📊 ANÁLISIS DE RESULTADOS - 12 Tickers Entrenados

**Fecha:** 2026-04-08  
**Status:** Training completed, analyzing results  

---

## 🎯 RESULTADOS OBSERVADOS

### STABLE ASSETS (max_depth=5)

| Ticker | BA % | Precision | Recall | Signal | Análisis |
|--------|------|-----------|--------|--------|----------|
| AAPL   | 41.1% | 37.5%  | 16.5% | BAJISTA | ⚠️ Recall bajo |
| GOOGL  | 31.7% | 19.2%  | 15.6% | BAJISTA | ⚠️ Recall muy bajo, precision baja |
| KO     | 35.8% | 50.0%  | 9.6%  | ALCISTA | ⚠️ Recall extremadamente bajo |
| MSFT   | 37.6% | 40.0%  | 15.1% | ALCISTA | ⚠️ Recall bajo |
| **AVG** | **36.5%** | **36.7%** | **14.2%** | - | ⚠️ Recall muy bajo vs expectativa |

**Problema:** Recall stable está 14-16%, esperaba 40-55%

---

### VOLATILE ASSETS (max_depth=4)

| Ticker | BA % | Precision | Recall | Signal | Análisis |
|--------|------|-----------|--------|--------|----------|
| AMZN   | 38.3% | N/A    | N/A    | LATERAL | ⚠️ Datos incompletos |
| BABA   | 31.3% | 25.5%  | 18.1%  | ALCISTA | ⚠️ Recall bajo |
| INTC   | 35.9% | N/A    | N/A    | LATERAL | ⚠️ Datos incompletos |
| META   | 49.0% | N/A    | N/A    | LATERAL | ⭐ BA alta pero datos incompletos |
| NFLX   | 35.3% | N/A    | N/A    | LATERAL | ⚠️ Datos incompletos |
| NVDA   | 33.3% | 32.6%  | 75.0%  | ALCISTA | ✅ Recall ALTO pero precision baja |
| TSLA   | 36.7% | N/A    | N/A    | LATERAL | ⚠️ Datos incompletos |
| VXX    | 36.1% | 50.0%  | 8.5%   | LATERAL | ⚠️ Recall muy bajo |
| **AVG** | **37.2%** | **36.0%** | **32.8%** | - | ⚠️ NVDA extremo distorsiona average |

**Problema 1:** Recall inconsistent (8.5% VXX vs 75% NVDA)  
**Problema 2:** Muchos tickers sin datos de precision/recall guardados  
**Problema 3:** NVDA 75% es outlier extremo

---

## 🔍 INVESTIGACIÓN

### ¿Por qué Recall está muy bajo?

**Hipótesis 1:** Thresholds demasiado altos
- Si UP threshold está al 90%ile, casi nunca predice ALCISTA
- Result: Recall muy bajo (<20%)

**Hipótesis 2:** Grid search no está penalizando correctamente
- Penalties no se aplicaron como esperado
- O grid search eligió thresholds muy restrictivos

**Hipótesis 3:** Training data tiene poca variación
- Si validation set tiene poca ALCISTA, thresholds se ajustan conservadores

### ¿Por qué NVDA tiene 75% recall?

**Posible causa:** Grid search encontró thresholds muy permisivos
- DOWN muy bajo, UP muy alto (o incluso > 1)
- Result: Predice ALCISTA frecuentemente

---

## ⚠️ ANOMALÍAS CRÍTICAS

### 1. Recall extremadamente bajo en STABLE (14.2%)
- **Esperado:** 40-55%
- **Observado:** 9.6% - 16.5%
- **Delta:** -60% vs expectativa
- **Causa probable:** Thresholds UP demasiado altos

### 2. NVDA tiene recall 75% (OUTLIER)
- **Esperado:** 40-60%
- **Observado:** 75%
- **Delta:** +15% sobre rango
- **Causa probable:** Thresholds DOWN muy bajo

### 3. Datos incompletos de precision/recall
- **AMZN, INTC, META, NFLX, TSLA:** No guardan precision/recall
- **Causa probable:** Error en saving o calculation

### 4. META tiene BA inusitadamente alta (49%)
- **Esperado:** 35-37%
- **Observado:** 49%
- **Posible causa:** Dataset problema o lucky split

---

## 🎯 ROOT CAUSE: Smart Threshold v2 Issue

### Sospecha Principal:
Penalty functions en smart threshold NO están funcionando correctamente.

**Evidencia:**
1. Recall 9.6% - 16.5% no debería pasar penalty (-0.05)
2. NVDA 75% debería haber sido penalizado
3. Grid search debería haber seleccionado range 40-60%

### Debug Necesario:
```python
# En xgboost_model.py, líneas 175-223:
# Verificar que:
# 1. if 0.4 <= recall_candidate <= 0.6: score += 0.03  
#    ↑ Este bonus se está aplicando?
# 2. elif recall < 0.15 or recall > 0.90: score -= 0.05
#    ↑ Esta penalización se está aplicando?
# 3. Qué threshold está siendo seleccionado como BEST?
```

---

## 💡 MEJORAS PROPUESTAS (SIN CAMBIAR ARQUITECTURA)

### 1. FIX: Verificar + Debuggar Smart Threshold v2 (CRÍTICO)

**Paso 1:** Agregar logging detallado
```python
# En train_xgboost(), después grid search:
print(f"DEBUG Grid Search Results for {ticker}:")
print(f"  Best down: {best_down:.4f}, Best up: {best_up:.4f}")
print(f"  Best BA: {best_ba:.4f}")
print(f"  Best recall: {best_recall_up:.4f}")
print(f"  Combinations probadas: X de 36")
```

**Paso 2:** Re-entrenar con logging MSFT (sample)para ver qué pasó

---

### 2. ALTERNATIVA: Volver a Smart Threshold v1 pero con constraints

Si v2 está roto, podemos usar v1 pero restringiendo:

```python
# Percentile-based pero restringido
down_target = np.percentile(y_prob_val, 25)  # ~25%ile
up_target = np.percentile(y_prob_val, 75)    # ~75%ile

# Pero validar en test que recall cae en 30-70% range
y_test_pred = predict(y_prob_val)
recall_test = calculate_recall(y_test_pred)

if recall_test < 0.30 or recall_test > 0.70:
    # Ajustar thresholds dinámicamente
    if recall_test < 0.30:
        up_target = up_target - 0.05  # More permissive
    elif recall_test > 0.70:
        up_target = up_target + 0.05  # More restrictive
```

---

### 3. MEJORAR: Per-Ticker Fine-Tuning

En lugar de configs fijas stable/volatile, calibrar por tipo:

```python
# Basado en y_train volatility:
train_std = np.std(y_train_continuous)

if train_std > 0.08:  # Highly volatile
    config = "EXTRA_VOLATILE"  # max_depth=3, subsample=0.7
elif train_std > 0.05:  # Moderate volatile
    config = "VOLATILE"  # max_depth=4, subsample=0.8
elif train_std > 0.02:  # Stable
    config = "STABLE"  # max_depth=5, subsample=0.92
else:  # Very stable
    config = "SUPER_STABLE"  # max_depth=6, subsample=0.95
```

---

### 4. NUEVO: Ensemble Voting para Thresholds

En lugar de único threshold, usar votación:

```python
# Calcular 3 diferentes thresholds:
# - Conservative (recall ~30%): UP=80%ile
# - Balanced (recall ~50%): UP=70%ile
# - Aggressive (recall ~70%): UP=60%ile

# Predecir con 3 modelos distintos
pred_conservative = model.predict_proba() >= conservative_up
pred_balanced = model.predict_proba() >= balanced_up
pred_aggressive = model.predict_proba() >= aggressive_up

# Voting: si 2/3 votan ALCISTA → clásificar ALCISTA
final_pred = (pred_conservative + pred_balanced + pred_aggressive > 1)
```

---

### 5. NEW: Feature Importance Auto-Selection

Drop bajo-importancia features:

```python
# Después de entrenar:
importances = model.feature_importances_
top_features_threshold = np.percentile(importances, 50)

selected_features = [f for f, imp in zip(feature_cols, importances) 
                     if imp > top_features_threshold]

# Re-entrenar solo con top 50% features
# Esperado: +2-5% recall improvement
```

---

## 🎯 PRÓXIMO PASO RECOMENDADO

### Opción A: Quick Debug (15 min)
1. Agregar logging a Smart Threshold v2
2. Re-entrenar MSFT (sample) con debug
3. Ver qué thresholds está seleccionando
4. Fix si hay bug

### Opción B: Fallback + Iterate (20 min)
1. Revertir a Smart Threshold v1 (percentile-based)
2. Pero agregar post-training check
3. Si recall < 30%, mover UP threshold down
4. Re-entrenar todos

---

## 📊 MÉTRICAS ESPERADAS vs OBSERVADAS

| Métrica | Esperado | Observado | Delta | Status |
|---------|----------|-----------|-------|--------|
| BA STABLE | 36-37% | 36.5% | +0.5% | ✅ Good |
| BA VOLATILE | 35-37% | 37.2% | +0.2% | ✅ Good |
| Recall STABLE | 40-55% | 14.2% | -75% 😱 | ❌ FAIL |
| Recall VOLATILE | 40-60% | 32.8% | -18% | ⚠️ Below |
| Extremos | 40-60% band | 8.5%-75% | Wide | ❌ FAIL |

**Overall:** BA está bien, pero Recall está mal distribuido

---

## 🔧 RECOMENDACIÓN FINAL

**PASO 1:** Debug Smart Threshold v2 (verificar que penalties se aplican)  
**PASO 2:** Si funciona → fine-tune grid search ranges  
**PASO 3:** Si no → fallback a v1 + post-training validation  
**PASO 4:** Re-train con buena configuración  
**PASO 5:** Después, evaluar mejora 2-3 (ensemble voting, feature selection)

¿Empezamos por debug o fallback?
