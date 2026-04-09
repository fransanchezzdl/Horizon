# 🎯 PLAN: Optimizar Análisis de Sentimiento para XGBoost

## Problema Actual
- DistilRoBERTa es genérico (entrenado en redes sociales, no finanzas)
- Sentimiento sin lag (sincrónico, no predictivo)
- Sin normalización específica del dominio
- XGBoost trata sentimiento igual que features técnicas

## Solución: 3 Mejoras Clave

### ✅ OPCIÓN 1: FinBERT (Recomendado pero lento)
- Modelo pre-entrenado ESPECÍFICAMENTE para finanzas
- Entiende contexto financiero real
- **Problema**: ~200-300s por ticker adicional (muy lento)
- **Ventaja**: +5-8% improvement esperado

### ✅ OPCIÓN 2: Sentimiento Técnico + Temporal (Rápido y efectivo)
- Calcular sentimiento BINARIO (positivo/negativo) de noticias
- Agregar LAGS: sentimiento de hace 1-5 días (predictivo)
- Normalizar por volatilidad: noticias en épocas volátiles < noticias en calma
- **Ventaja**: +3-5% improvement, solo +20s/ticker
- **Este es el MEJOR BALANCE**

### ✅ OPCIÓN 3: Ensemble Híbrido
- Entrenar 2 XGBoost: uno técnico puro, uno con sentimiento
- Votar entre ambos (mayoría o promedio ponderado)
- **Ventaja**: Captura lo mejor de ambos mundos
- **Tiempo**: +50% pero resulado robusto

## Recomendación para tu TFG

**OPCIÓN 2** es la mejor:
```
✓ Rápida (solo +20s por ticker)
✓ Científica (lag, normalización)
✓ Mejora real (+3-5%)
✓ Justificable en TFG
✓ Reproducible sin APIs externas
```

## Implementación (Orden de prioridad)

1. **Feature 1**: Sentimiento DIARIO con lag 1-5 días
   - Script que extraiga noticias históricas (Alpha Vantage)
   - Calcule sentimiento básico (count positivos/negativos)
   - Cree features con lag

2. **Feature 2**: Normalización por volatilidad
   - Sentimiento fuerte en días tranquilos = más peso
   - Sentimiento en días volátiles = menos peso

3. **Feature 3**: Weights adaptativos en XGBoost
   - Dar mayor importancia a features de sentimiento
   - Penalizar si no mejoran recall

4. **Test**: Comparativa v4 puro vs v4+Sentimiento mejorado
   - Esperar +3-5% improvement en BA/Recall

---

## ¿Cuál opción prefieres?

a) **OPCIÓN 2 (RECOMENDADO)** - Sentimiento técnico con lag
b) **OPCIÓN 1** - FinBERT (mejor pero 3x más lento)
c) **OPCIÓN 3** - Ensemble (más robusto)
d) **Otra cosa** - Cuéntame tu idea
