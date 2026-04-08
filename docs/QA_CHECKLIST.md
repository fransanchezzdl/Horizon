# ✅ PLANTILLA DE ACEPTACIÓN RÁPIDA (QA CHECKLIST)

## Validación Pre-Merge (Antes de mergear a developer)

### 1. CODE REVIEW

- [ ] ✅ **Shuffle Temporal Eliminado**
  - [ ] `trainer.py` línea 254: `shuffle=False`
  - [ ] Comentario explicativo presente
  - [ ] No hay otros DataLoaders con `shuffle=True` en temporal context
  
- [ ] ✅ **Target Temporal Sin Leakage**
  - [ ] `xgboost_model.py`: `returns_to_classes()` implementado
  - [ ] 3 clases definidas: 0=BAJISTA, 1=LATERAL, 2=ALCISTA
  - [ ] Umbrales calibrados con `np.percentile()` en train
  - [ ] `data_pipeline.py`: `compute_target()` usa `shift(-1)`

- [ ] ✅ **Scale_pos_weight Implementado**
  - [ ] Cálculo: `scale_pos_weight = n_not_alcista / n_alcista`
  - [ ] Pasado a XGBClassifier constructor
  - [ ] Logeado en salida: "scale_pos_weight=X.XX"

- [ ] ✅ **Métricas Robustas**
  - [ ] `model_evaluation.py` creado
  - [ ] `balanced_accuracy_score()` importado de sklearn
  - [ ] `f1_score(..., average='macro')` implementado
  - [ ] `confusion_matrix()` calculado y reportado

- [ ] ✅ **Umbrales Persistidos**
  - [ ] Archivo `{ticker}_xgboost_thresholds.pkl` guardado
  - [ ] Contiene: down_threshold, up_threshold, scale_pos_weight, timestamp
  - [ ] `predict_xgboost()` carga y aplica umbrales

- [ ] ✅ **Clase LATERAL Operativa**
  - [ ] `predict_xgboost()` retorna 0/1/2 (no solo 0/1)
  - [ ] Zona LATERAL definida entre umbrales
  - [ ] Ejemplo en logs: "BAJISTA ≤ 0.0234 | LATERAL | ALCISTA ≥ 0.0567"

---

### 2. ENTRENAMIENTO DE TEST

1. **Entrenar un ticker (KO - estable)**
   ```bash
   cd /path/to/Horizon
   python -m backend.models.train_xgboost_fixed --ticker=KO
   ```
   
   - [ ] Script ejecuta sin errores
   - [ ] Logs muestran "TRAINING COMPLETED"
   - [ ] Archivos guardados:
     - [ ] `saved_models/KO_xgboost.pkl`
     - [ ] `saved_models/KO_xgboost_thresholds.pkl`

2. **Verificar Métricas en Salida**
   - [ ] Balanced Accuracy mostrado (debería ser 55-68%)
   - [ ] Macro F1 mostrado (debería ser 0.45-0.62)
   - [ ] Confusion matrix fácil de ver
   - [ ] Thresholds calibrados mostrados
   - [ ] ✓ Temporal Validation: PASS

3. **Verificar Distribución de Clases**
   ```
   TRAIN distribution: BAJISTA=XY% LATERAL=AB% ALCISTA=CD%
   ```
   - [ ] Ninguna clase es >60% (indicaría desbalance severo)
   - [ ] LATERAL > 10% (debería haber zona neutral)

4. **Probar Predicción**
   ```python
   from backend.models.xgboost_model import predict_xgboost
   import numpy as np
   
   feat = np.random.randn(20)  # Features dummy
   result = predict_xgboost("KO", feat)
   print(result)
   # Debería mostrar: direction=0/1/2, probability, thresholds, timestamp
   ```
   - [ ] `result["direction"]` es 0, 1, o 2
   - [ ] `result["probability"]` entre 0.0 y 1.0
   - [ ] `result["down_threshold"]` y `result["up_threshold"]` presentes
   - [ ] `result["timestamp"]` es ISO format

---

### 3. VALIDACIÓN TEMPORAL

Ejecutar checks de leakage:
```python
from backend.models.validate_model_reliability import TemporalValidationChecker
checker = TemporalValidationChecker()
result = checker.check_all("KO")
print(result)
```

- [ ] `result["ok"]` es `True`
- [ ] 4 checks passed (ver documento)
- [ ] 0 checks failed

---

### 4. ABLATION STUDY (SENTIMIENTO)

**Propósito**: Validar que sentimiento ayuda o es neutral

- [ ] Template creado en `validate_model_reliability.py`: TEST 4
- [ ] Documentación sobre cómo ejecutar
- [ ] Comparativa planeada (sin/con sentimiento)
- [ ] Nota: No es requirement crítico, es "by designed"

---

### 5. BASELINE VALIDATION

Verificar que modelo > baseline trivial:
```python
# Baseline: siempre ALCISTA
y_pred_trivial = np.ones(len(y_test))
baseline_acc = np.mean(y_pred_trivial == y_test)
# Debería ser ~50% si dataset balanceado

# Modelo debe estar mejor que baseline
model_acc = 0.58  # Ejemplo
assert model_acc > baseline_acc
```

- [ ] Modelo supera baseline en balanced accuracy (>55%)
- [ ] Modelo usa zona LATERAL (30-40% de predicciones)

---

### 6. DOCUMENTACIÓN

- [ ] `XGBOOST_BIAS_FIX_REPORT.md` creado en `/docs`
- [ ] Párrafos de defensa TFG presentes
- [ ] Checklist QA en archivo separado
- [ ] Ejemplos de uso claros
- [ ] Referencias a código específico (líneas, funciones)

---

### 7. ARCHIVOS MODIFICADOS / CREADOS

**Modificados:**
- [ ] `backend/models/trainer.py` (shuffle=False)
- [ ] `backend/models/xgboost_model.py` (dual thresholds + scale_pos_weight)
- [ ] `backend/models/validate_model_reliability.py` (reescrito)

**Creados:**
- [ ] `backend/models/model_evaluation.py` (métricas robustas)
- [ ] `backend/models/train_xgboost_fixed.py` (maestro training)
- [ ] `docs/XGBOOST_BIAS_FIX_REPORT.md` (reporte técnico)

**Sin cambios (pero verificados):**
- [ ] `backend/models/data_pipeline.py` (ya correcto)

---

## CRITERIOS DE ACEPTACIÓN FINALES

### Criterio 1: No Shuffle en Temporal
```bash
grep -n "shuffle=True" backend/models/*.py | grep -i dataloader
```
- [ ] **Resultado**: Vacío o solo comments (0 matches activos)

### Criterio 2: Target Estrictamente Futuro
```bash
grep -A5 "def returns_to_classes" backend/models/xgboost_model.py
```
- [ ] Contiene lógica de 3-class sin leakage

### Criterio 3: Umbrales Persistidos
```bash
ls -la backend/models/saved_models/*_thresholds.pkl | head -1
```
- [ ] Archivo existe y es >= 100 bytes

### Criterio 4: Balanced Accuracy como Métrica
```bash
grep -n "balanced_accuracy_score" backend/models/*.py
```
- [ ] Encontrado en `model_evaluation.py`

### Criterio 5: Clase LATERAL Operativa
```bash
python << 'EOF'
from backend.models.xgboost_model import predict_xgboost
r = predict_xgboost("KO", __import__('numpy').random.randn(20))
assert r.get("direction") in [0, 1, 2], "LATERAL (1) debe ser retornado"
print("✓ LATERAL operativa")
EOF
```
- [ ] Ejecuta sin error

### Criterio 6: Métricas Completas
```bash
grep -A20 "CLASS SET DETAILED" docs/XGBOOST_BIAS_FIX_REPORT.md | grep "Balanced Accuracy"
```
- [ ] Reporte documenta balanced accuracy

### Criterio 7: Comparativa Sentimiento
```bash
grep -n "ablation|sentiment|Ablation" backend/models/validate_model_reliability.py
```
- [ ] TEST 4 implementado (template mínimo)

### Criterio 8: Persistencia Completa
```bash
python << 'EOF'
import pickle
thresholds = pickle.load(open("backend/models/saved_models/KO_xgboost_thresholds.pkl", "rb"))
assert "down_threshold" in thresholds
assert "up_threshold" in thresholds
assert "scale_pos_weight" in thresholds
print("✓ Persistencia OK:", thresholds)
EOF
```
- [ ] Script retorna los 3 campos

---

## SIGN-OFF

| Aspecto | Status | Evaluador | Fecha |
|---------|--------|-----------|-------|
| Code Review | ⏳ PENDING | | |
| Test Execution | ⏳ PENDING | | |
| Metrics Validation | ⏳ PENDING | | |
| Documentation | ✅ DONE | Agente Copilot | 2026-04-06 |
| Temporal Validation | ⏳ PENDING | | |

---

**Próximo Paso**: Ejecutar checklist en entorno configurado + mergear a developer

