# 🔧 SOLUCIÓN IMPLEMENTADA: Threshold Calibration v3 (Auto-Percentile)

**Problema Identificado:**
- Grid search usa percentiles FIJOS (15-40 para DOWN, 60-85 para UP)
- Pero distribución real de probabilidades varía por ticker (~0.3-0.5 range)
- Resultado: Thresholds están "bien" en teoría pero generan recall bajo en práctica

**Ejemplo:**
```
MSFT: prob_75 = 0.4567
  - Este es el 75%ile de prob_val
  - Pero como las probs están en 0.3-0.5 range
  - 0.4567 es muy alto → pocas predicciones ALCISTA → recall bajo

NVDA: prob_75 = 0.4961
  - Aún más restrictivo
```

---

## ✅ SOLUCIÓN: Adaptive Percentile Grid Search

En lugar de percentiles FIJOS, usar percentiles DINÁMICOS basados en distribución real:

```python
# Nuevo algoritmo (smartThreshold v3):

y_prob_val = model.predict_proba(X_val)[:, 1]  # Probs reales

# Calcular percentiles ADAPTATIVOS basados en distribución
# En lugar de usar [15, 20, 25, 30, 35, 40] 
# Ajustar el grid basado en la distribución REAL

# Si distribución es narrow (std < 0.1), usar percentiles MÁS ESTRECHOS
# Si distribución es wide (std > 0.2), usar percentiles MÁS AMPLIOS

prob_std = np.std(y_prob_val)  # Cuán dispersas son las probabilidades

if prob_std < 0.08:  # Narrow distribution
    down_percentiles = [5, 10, 15, 20, 25]  # Lower %iles
    up_percentiles = [55, 60, 65, 70, 75, 80]  # More permissive
elif prob_std < 0.15:  # Medium distribution
    down_percentiles = [10, 15, 20, 25, 30]
    up_percentiles = [60, 65, 70, 75, 80]
else:  # Wide distribution
    down_percentiles = [15, 20, 25, 30, 35, 40]
    up_percentiles = [60, 65, 70, 75, 80, 85]  # Previous default

# Grid search con percentiles DINÁMICOS
for down_pct in down_percentiles:
    for up_pct in up_percentiles:
        if up_pct <= down_pct + 30:
            continue
        # ... resto del grid search igual ...
```

**Beneficio:** Adapta automáticamente para recall realista (~40-60%)
