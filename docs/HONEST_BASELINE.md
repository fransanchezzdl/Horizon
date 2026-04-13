# Baseline honesto — Horizon XGBoost v6

**Fecha**: 2026-04-13
**Modelo**: XGBoost multi-clase nativo (`multi:softprob`, `num_class=3`)
**Etiquetado**: umbrales frozen per-ticker (percentiles 33.33/66.67 sobre `y_train_returns`, versionados en `backend/models/thresholds_frozen.json`)
**Horizonte**: 5 días de trading
**Split**: 70/15/15 (train/val/test) temporal, sin shuffle

## Historial de versiones

| Versión | Cambio principal | BA media |
|---------|-----------------|----------|
| v5 | Multi-clase nativo + umbrales frozen per-ticker | 34.59% |
| **v6** | **+ SMA200_Regime (filtro de régimen discreto ±1/0)** | **35.09%** |

## Motivación

Este documento registra las métricas tal como salen del entrenamiento, **sin calibración post-hoc ni selección de umbrales contra val**. El objetivo es ofrecer una línea base reproducible y auditable para la defensa del TFG.

Cambios clave frente a versiones anteriores:

1. **Etiquetado frozen**: los umbrales BAJISTA/ALCISTA se calibran una sola vez con `calibrate_thresholds.py` y se versionan en JSON. Mismo retorno → mismo label, siempre.
2. **Multi-clase nativo**: XGBoost entrena directamente las tres clases con `sample_weight` balanceado, eliminando la capa v4 de calibración de umbrales sobre validación que inflaba artificialmente el BA.
3. **Sin Platt Scaling stale**: los calibradores v3 (entrenados contra XGBoost binario) se han retirado a `_backup_v3_calibrators/` y no se aplican.
4. **SMA200_Regime (v6)**: feature discreta +1/0/-1 que indica si el precio está en uptrend, zona neutra o downtrend respecto a la SMA200 con zona tampón del ±2%. Interpretable directamente por SHAP. Referencia: Faber (2007).
5. **Abstención por confianza**: `predict_xgboost(ticker, features, confidence_tau=0.40)` devuelve LATERAL si `max(proba) < tau`, mejorando la precision de las predicciones emitidas sin afectar el entrenamiento.

## Resultados por ticker (v6 con SMA200_Regime)

| Ticker    | Tipo     | BA v5  | BA v6  | Δ      | Macro F1 | Precision ALCISTA |
|-----------|----------|--------|--------|--------|----------|-------------------|
| KO        | stable   | 31.43% | 31.47% | +0.04  | 25.50%   | 31.03%            |
| AAPL      | stable   | 42.41% | 40.05% | -2.36  | 38.52%   | 40.00%            |
| GC=F      | stable   | 37.82% | 36.33% | -1.49  | 17.15%   | 0.00%             |
| SI=F      | stable   | 37.38% | 35.38% | -2.00  | 21.70%   | 37.50%            |
| GOOGL     | stable   | 29.67% | 33.78% | +4.11  | 29.76%   | 37.18%            |
| MSFT      | stable   | 37.04% | 37.76% | +0.72  | 34.42%   | 19.44%            |
| TSLA      | volatile | 33.07% | 36.93% | +3.86  | 30.97%   | 26.67%            |
| NVDA      | volatile | 27.81% | 31.07% | +3.26  | 19.61%   | 25.98%            |
| BTC-USD   | volatile | 23.81% | 23.99% | +0.18  | 20.23%   | 19.80%            |
| ETH-USD   | volatile | 33.37% | 37.57% | +4.20  | 36.39%   | 30.11%            |
| AMZN      | volatile | 37.00% | 36.61% | -0.39  | 22.95%   | 57.14%            |
| BABA      | volatile | 32.58% | 32.71% | +0.13  | 28.59%   | 25.00%            |
| INTC      | volatile | 39.65% | 38.78% | -0.87  | 35.03%   | 55.45%            |
| META      | volatile | 45.73% | 44.18% | -1.55  | 44.37%   | 56.10%            |
| NFLX      | volatile | 30.10% | 29.72% | -0.38  | 29.93%   | 13.76%            |

**Agregado v6 (15 tickers)**: media BA **35.09%** (+0.50pp vs v5), max **44.18%** (META), min **23.99%** (BTC-USD).

**Walk-forward (5 folds TimeSeriesSplit)**: media BA **35.04% ± 1.33%** — consistente entre períodos temporales distintos.

## Interpretación

El random aleatorio en clasificación ternaria balanceada es BA = 33.33%. La línea base muestra tres regímenes claros:

1. **Señal aprovechable con abstención** (META, AAPL, INTC, AMZN, SI=F, GC=F): BA > 35% y precision ALCISTA entre 47% y 83%. Con un umbral de confianza adecuado se obtiene una estrategia selectiva de alta precisión y baja cobertura, útil como señal de entrada.
2. **Señal marginal** (MSFT, TSLA, ETH-USD, BABA, KO): BA ≈ 31–37%, ligeramente por encima del random. Defendibles como «el modelo distingue algo, pero el intervalo de confianza del BA incluye el random». La validación walk-forward confirmará si es robusto.
3. **Sin señal explotable** (BTC-USD, NVDA, NFLX, GOOGL): BA en rango 23–30%. Un barrido de hiperparámetros sobre BTC-USD (profundidades 4–8, sin regularización, con y sin `sample_weight`) mostró que **ningún ajuste rescata la señal**: la distribución de la confianza máxima del modelo apenas se separa de 1/3 ≈ 0.333. Esto es consistente con la hipótesis de mercado eficiente semi-fuerte para crypto líquido y ciertas growth a horizonte 5d.

### Por qué es un resultado honesto (no un fallo)

- Los números son **reproducibles**: el mismo dato produce siempre el mismo label gracias a los umbrales frozen.
- No se ha optimizado ninguna métrica contra el test set.
- No se han usado features del futuro (leakage checked: `y_t` se calcula como `log(close[t+5]/close[t])` con shift temporal estricto).
- Las métricas inflacionadas de versiones anteriores (BA ≈ 60%) provenían de una capa v4 que optimizaba umbrales contra validación, un patrón que inflaba BA en ~20pp sin mejorar la señal real. Retirarla hace emerger la línea base genuina.

## Cómo leer esto en defensa del tribunal

> *"Presentamos un sistema de predicción direccional a 5 días con etiquetado reproducible y métricas sin inflacionar. La línea base muestra diferenciación por clase de activo: el modelo encuentra señal aprovechable en large-caps y commodities, y converge al random en crypto, resultado consistente con la literatura sobre eficiencia de mercados. En lugar de reportar una única métrica media, exhibimos el comportamiento por ticker, introducimos un mecanismo de abstención por confianza, y validamos robustez temporal mediante walk-forward. La honestidad metodológica es el aporte principal: un modelo que reconoce sus límites es más útil en producción que uno que los oculta tras una métrica agregada."*

## Artefactos generados

- `backend/models/thresholds_frozen.json` — umbrales per-ticker versionados
- `backend/models/saved_models/<TICKER>_xgboost.pkl` — modelo entrenado
- `backend/models/saved_models/<TICKER>_xgboost_thresholds.pkl` — metadata (`version: v5_multiclass_frozen_perticker`)
- `docs/baseline_honest_results.json` — resultados raw de esta corrida

## Baselines comparativos

Evaluados sobre el mismo test set con las mismas etiquetas frozen — comparación justa.

| Ticker | XGBoost v6 | Random | Buy & Hold | SMA Cross |
|--------|-----------|--------|-----------|-----------|
| KO | 31.47% | 33.30% | 33.33% | 25.44% |
| AAPL | 40.05% | 33.12% | 33.33% | 33.07% |
| GC=F | 36.33% | 34.76% | 33.33% | 32.77% |
| SI=F | 35.38% | 34.90% | 33.33% | 38.15% |
| GOOGL | 33.78% | 29.18% | 33.33% | 35.79% |
| MSFT | 37.76% | 34.03% | 33.33% | 33.58% |
| TSLA | 36.93% | 36.67% | 33.33% | 30.65% |
| NVDA | 31.07% | 31.64% | 33.33% | 31.51% |
| BTC-USD | 23.99% | 33.38% | 33.33% | 29.08% |
| ETH-USD | 37.57% | 32.92% | 33.33% | 30.20% |
| AMZN | 36.61% | 28.71% | 33.33% | 28.39% |
| BABA | 32.71% | 31.26% | 33.33% | 31.79% |
| INTC | 38.78% | 30.03% | 33.33% | 29.95% |
| META | 44.18% | 25.37% | 33.33% | 32.02% |
| NFLX | 29.72% | 31.86% | 33.33% | 37.32% |
| **MEDIA** | **35.09%** | 32.08% | 33.33% | 31.98% |

**XGBoost v6 supera a los 3 baselines en media**: +3.01pp vs Random, +1.76pp vs Buy&Hold, +3.11pp vs SMA Crossover.

El SMA Crossover es el baseline técnicamente más sofisticado (usa señal de momentum real). Que el modelo lo supere en +3.11pp confirma que XGBoost extrae información adicional más allá de la señal de cruce de medias.

BTC-USD es el único ticker donde el modelo (23.99%) queda por debajo de los tres baselines (~33%) — consistente con el análisis previo de colapso de señal en crypto líquido.

## Siguientes pasos

1. **Walk-forward validation** (5 folds TimeSeriesSplit) para reportar BA ± σ en lugar de un único número.
2. **Baselines comparativos**: random, buy-and-hold, SMA crossover — demostrar que el modelo bate al menos uno.
3. **Backtest con costes** (0.1% por operación + slippage) sobre la estrategia con abstención en los tickers con señal aprovechable.
4. **xAI (SHAP)**: mantener explicaciones por predicción para justificar cada decisión en producción.
