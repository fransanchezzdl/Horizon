# Estrategia de Selección de Features

## Problema Actual

El modelo con 27 features (9 base + 18 avanzadas) tiene **48.87% accuracy**, que es **PEOR** que el modelo con 9 features base (53.43%).

## Análisis de Correlación

Features ordenadas por correlación absoluta con el target:

### Top 10 (correlación > 0.04)
1. CMF: 0.0954 ✅
2. OBV: 0.0699 ✅
3. Aroon_Up: 0.0666 ✅
4. MACD: 0.0586 ✅ (base)
5. Close: 0.0499 ✅ (base)
6. Volume: 0.0476 ✅ (base)
7. DX: 0.0408 ✅
8. TSI: 0.0407 ✅
9. KST: 0.0405 ✅
10. Aroon_Down: 0.0402 ✅

### Medio (0.02 < correlación < 0.04)
11. EMA: 0.0391 ✅ (base)
12. CCI: 0.0391 ✅
13. CMO: 0.0368 ✅
14. Bollinger_PctB: 0.0330 ✅ (base)
15. Ultimate_Osc: 0.0310 ✅
16. Log_Return: 0.0286 ✅ (base)
17. ATR: 0.0267 ✅ (base)
18. RSI: 0.0248 ✅ (base)
19. Donchian_PctB: 0.0195 ⚠️
20. Keltner_PctB: 0.0177 ⚠️

### Bajo (correlación < 0.02)
21. Williams_R: 0.0145 ❌
22. Stochastic_K: 0.0119 ❌
23. ROC: 0.0102 ❌
24. Volume_Ratio: 0.0039 ❌ (base)
25. MFI: 0.0030 ❌
26. Stochastic_D: 0.0027 ❌
27. ADX: 0.0003 ❌

## Hipótesis

**Añadir 18 features causó:**
1. **Curse of dimensionality**: Espacio de búsqueda demasiado grande
2. **Ruido**: 7 features con correlación < 0.02 añaden ruido
3. **Dilución**: Features útiles se diluyen entre el ruido

## Estrategias de Mejora

### Estrategia 1: Selección Agresiva (Top 10 avanzadas)
- **Features**: 9 base + 10 avanzadas = 19 total
- **Avanzadas**: CMF, OBV, Aroon_Up, DX, TSI, KST, Aroon_Down, CCI, CMO, Ultimate_Osc
- **Eliminadas**: ADX, Stochastic_K/D, Williams_R, MFI, ROC, Keltner_PctB, Donchian_PctB
- **Ventaja**: Solo features con correlación > 0.03
- **Riesgo**: Podríamos perder información útil

### Estrategia 2: Selección Moderada (Top 13 avanzadas)
- **Features**: 9 base + 13 avanzadas = 22 total
- **Avanzadas**: Top 10 + Donchian_PctB, Keltner_PctB, Williams_R
- **Eliminadas**: ADX, Stochastic_K/D, MFI, ROC
- **Ventaja**: Balance entre información y ruido
- **Riesgo**: Moderado

### Estrategia 3: Todas las Features con Regularización
- **Features**: 27 (todas)
- **Cambios**: Aumentar dropout (0.1 → 0.3), añadir L2 regularization
- **Ventaja**: El modelo aprende a ignorar features irrelevantes
- **Riesgo**: Requiere más epochs y datos

### Estrategia 4: Feature Engineering Mejorado
- **Crear features combinadas**:
  - Momentum_Score = (TSI + CMO + KST) / 3
  - Trend_Score = (Aroon_Up - Aroon_Down) / 100
  - Volume_Pressure = CMF * OBV
- **Features**: 9 base + 3 combinadas = 12 total
- **Ventaja**: Reduce dimensionalidad manteniendo información
- **Riesgo**: Requiere experimentación

## Recomendación

**Probar Estrategia 2 (Selección Moderada)** porque:
1. Elimina las 5 features con menor correlación (< 0.02)
2. Mantiene 22 features con información útil
3. Reduce dimensionalidad sin ser demasiado agresivo
4. Balance óptimo entre información y ruido

## Implementación

1. Modificar `ADVANCED_TECHNICAL_COLS` en `config.py` para usar solo las 13 features seleccionadas
2. Reentrenar el modelo
3. Comparar accuracy con el modelo de 9 features base
4. Si accuracy < 53%, probar Estrategia 1 (más agresiva)
5. Si accuracy > 58%, probar añadir más features gradualmente

## Métricas de Éxito

- **Objetivo mínimo**: 55% accuracy (mejora sobre 53.43%)
- **Objetivo ideal**: 58-63% accuracy
- **Early stopping**: Aceptable si ocurre después de epoch 30 y accuracy > 55%
