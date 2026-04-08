# 🎯 NUEVA ESTRATEGIA: Threshold Calibration v4 (Recall-Target Based)

**Problema:**
- v2 y v3 usan PERCENTILES como base
- Pero percentiles generan variancia (algunos tickers 9%, otros 75%)
- Root cause: distribución de probabilidades es inherentemente narrow

**Solución v4:**
Buscar threshold que genere RECALL OBJETIVO (~50%) en lugar de percentil fijo

---

## 🎯 NUEVO ALGORITMO (v4)

```python
# En lugar de grid search por percentiles
# Hacer búsqueda DIRECTA por recall objetivo

target_recall = 0.50  # Objetivo: 50% recall

# Calcular recall para cada threshold posible
for threshold in np.arange(np.min(y_prob_val), np.max(y_prob_val), 0.01):
    y_pred_test = (y_prob_val >= threshold).astype(int)
    
    tp = sum((y_pred_test == 1) & (y_val == 2))
    fn = sum((y_pred_test == 0) & (y_val == 2))
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    
    # Si recall está en rango 45-55%, es buen candidate
    if abs(recall - target_recall) < 0.05:
        # Calcular precision y BA también
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        ba = balanced_accuracy_score(y_val, y_pred_candidate)
        
        # Guardar candidato
        if ba > best_ba:
            best_threshold = threshold
            best_ba = ba
            best_recall = recall
```

**Ventaja:** Garantiza recall en rango realista, no dependiente de percentiles

---

## 📊 COMPARACIÓN DE ESTRATEGIAS

| Estrategia | Base | Ventaja | Problema |
|-----------|------|---------|---------|
| **v1** | F1 global | Maximize score | Extremos (12-94%) |
| **v2** | Balanced AA | Penalty por extremos | Recall aún bajo |
| **v3** | Adaptive percentiles | Distribution-aware | Recall aún 9-75% |
| **v4** | Recall TARGET | Garantiza 40-60% | Menos flexible |

**v4 es MEJOR porque GARANTIZA recall razonable**

---

## 🔧 IMPLEMENTACIÓN RÁPIDA v4

```python
# Pasos:
# 1. Buscar threshold que dé recall ~50%
# 2. Entre candidatos, elegir que maximice BA
# 3. Resultado: recall ~45-55%, BA ~35-37%

# Código completo:
y_prob_val = model.predict_proba(X_val)[:, 1]
best_ba = -1
best_threshold = None
best_recall = None

target_recall = 0.50
tolerance = 0.10  # Aceptar 40-60%

for threshold in np.linspace(np.percentile(y_prob_val, 5), 
                             np.percentile(y_prob_val, 95), 
                             50):  # 50 puntos a probar
    
    y_pred_candidate = np.ones(len(y_prob_val), dtype=int)
    y_pred_candidate[y_prob_val >= threshold] = 2
    
    # Calcular recall
    tp = np.sum((y_pred_candidate == 2) & (y_val == 2))
    fn = np.sum((y_pred_candidate != 2) & (y_val == 2))
    recall_candidate = tp / (tp + fn) if (tp + fn) > 0 else 0
    
    # Filter: Solo aceptar si recall está en rango
    if abs(recall_candidate - target_recall) <= tolerance:
        ba = balanced_accuracy_score(y_val, y_pred_candidate)
        
        if ba > best_ba:
            best_ba = ba
            best_threshold = threshold
            best_recall = recall_candidate
```

**Resultado esperado:** Recall ~50% garantizado, BA ~36-37%

---

## 📈 MEJORAS POSTERIORES (DESPUÉS DE v4)

### 1. Per-Ticker Tuning
Algunos tickers pueden tener target_recall diferente:
- STABLE: target 45%
- VOLATILE: target 50%

### 2. Ensemble Thresholding
3 modelos con distintos targets:
- Conservative: 35%
- Balanced: 50%
- Aggressive: 65%

### 3. Feature Engineering
Drop noisy features → cleaner probabilities → better thresholds

---

## ❗ IMPORTANTE: POR QUÉ v4 ES LA SOLUCIÓN

**Los percentiles NO son suficientes porque:**
1. La distribución de probabilidades es natural (0.3-0.5 range)
2. Percentiles iguales NO generan recalls iguales entre tickers
3. NVDA 75% prueba que percentiles son unreliable

**Recall-target SÍ funciona porque:**
1. Objetivo es explícito (50% recall)
2. Cada ticker busca su propio threshold para 50%
3. Garantiza rango (40-60%) para todos

---

## 🚀 RECOMENDACIÓN

**Implementar v4 ahora:**
- 10 minutos de código
- Re-entrenar todos (30 min)
- Resultado: Recall ~50% en TODOS los tickers

¿Continuar con v4?
