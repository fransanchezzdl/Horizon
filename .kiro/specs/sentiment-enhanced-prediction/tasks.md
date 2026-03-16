# Plan de Implementación: Sentiment-Enhanced Prediction

## Descripción General

Este plan implementa un sistema híbrido de predicción financiera que combina análisis técnico (BiGRU ensemble) con análisis de sentimiento de noticias (FinBERT + Finnhub) y clasificación tabular (XGBoost). El objetivo es superar significativamente el accuracy actual del ~50% mediante la integración de señales técnicas y fundamentales en un meta-ensemble adaptativo.

**Lenguaje de implementación:** Python

**Arquitectura:** BiGRU Ensemble + XGBoost + Meta-Ensemble con pesos configurables

**Componentes principales:**
- Módulo de análisis de sentimiento (FinBERT + Finnhub API)
- Pipeline de features técnicas + sentimiento
- Ensemble de 5 modelos BiGRU con variaciones
- Clasificador XGBoost para dirección binaria
- Meta-ensemble con zona neutral configurable
- Sistema de persistencia de artefactos

## Tareas

- [x] 1. Configurar dependencias y estructura del proyecto
  - Crear archivo requirements.txt con todas las dependencias necesarias: torch, transformers, xgboost, yfinance, finnhub-python, scikit-learn, pandas, numpy, hypothesis (para property tests)
  - Configurar variables de entorno en config.py: FINNHUB_API_KEY, SAVED_MODELS_DIR, USE_SENTIMENT
  - Definir constantes de configuración: META_ENSEMBLE_WEIGHTS, META_ENSEMBLE_SIGMOID_SCALE, META_ENSEMBLE_TREND_DELTA
  - Definir STABLE_CONFIG y VOLATILE_CONFIG con parámetros de entrenamiento
  - Definir ENSEMBLE_VARIATIONS para activos estables y volátiles
  - Definir XGBOOST_CONFIG con hiperparámetros del clasificador
  - _Requisitos: 6.2, 6.3, 10.1, 10.3, 10.4_

- [x] 2. Implementar módulo de análisis de sentimiento
  - [x] 2.1 Crear sentiment_analyzer.py con funciones de carga de modelos
    - Implementar _get_finbert() con patrón singleton para cargar ProsusAI/finbert en CPU
    - Implementar _get_finnhub_client() con inicialización del cliente Finnhub
    - Manejar caso donde FINNHUB_API_KEY no está configurada (retornar None)
    - _Requisitos: 1.3, 7.1_

  - [ ]* 2.2 Escribir property test para carga de modelos
    - **Property 2: API Error Resilience**
    - **Valida: Requisitos 1.4, 7.2**

  - [x] 2.3 Implementar _analyze_headlines() para análisis con FinBERT
    - Truncar titulares a 512 caracteres para evitar errores de tokenización
    - Calcular sentiment_score promedio en rango [-1.0, 1.0]
    - Calcular sentiment_magnitude como confianza promedio en rango [0.0, 1.0]
    - Retornar valores neutros (0.0, 0.0) si FinBERT no puede cargarse
    - _Requisitos: 1.3, 1.7, 7.3_

  - [ ]* 2.4 Escribir unit tests para _analyze_headlines()
    - Test con lista vacía de titulares
    - Test con titulares muy largos (>512 caracteres)
    - Test con caracteres especiales
    - Test cuando FinBERT no está disponible

  - [x] 2.5 Implementar compute_historical_sentiment()
    - Descargar noticias desde Finnhub para rango de fechas
    - Manejar errores de API con logging de warnings y valores neutros
    - Aplicar forward-fill limitado a 5 días para fechas sin noticias
    - Retornar DataFrame con índice de fechas y columnas: sentiment_score, sentiment_magnitude, news_volume
    - _Requisitos: 1.1, 1.2, 1.4, 7.2_

  - [ ]* 2.6 Escribir property test para compute_historical_sentiment()
    - **Property 1: Sentiment Features Calculation**
    - **Valida: Requisitos 1.1**

  - [x] 2.7 Implementar get_daily_sentiment() para inferencia
    - Obtener noticias de los últimos N días (configurable, default 7)
    - Agregar sentimiento de todos los titulares
    - Retornar diccionario con sentiment_score, sentiment_magnitude, news_volume, available
    - _Requisitos: 5.2_

  - [ ]* 2.8 Escribir unit tests para get_daily_sentiment()
    - Test con diferentes valores de days_back
    - Test cuando no hay noticias disponibles
    - Test con API key inválida

- [ ] 3. Checkpoint - Verificar módulo de sentimiento
  - Asegurar que todos los tests pasen, preguntar al usuario si surgen dudas.

- [ ] 4. Implementar pipeline de features técnicas
  - [ ] 4.1 Crear features.py con función download_data()
    - Descargar datos históricos desde Yahoo Finance usando yfinance
    - Lanzar ValueError con mensaje descriptivo si ticker es inválido
    - Lanzar ValueError si no hay suficientes datos históricos
    - _Requisitos: 7.4, 7.5_

  - [ ]* 4.2 Escribir unit tests para download_data()
    - Test con ticker válido
    - Test con ticker inválido
    - Test con rango de fechas sin datos

  - [ ] 4.3 Implementar compute_features() para indicadores técnicos
    - Calcular 9 features base: Close, Volume, RSI, MACD, EMA, Bollinger_PctB, ATR, Log_Return, Volume_Ratio
    - Si include_market_context=True, agregar VIX_Close y NASDAQ_Return
    - Manejar valores NaN con forward-fill
    - Retornar DataFrame con todas las features calculadas
    - _Requisitos: 6.4_

  - [ ]* 4.4 Escribir unit tests para compute_features()
    - Test de cálculo correcto de cada indicador técnico
    - Test con datos que contienen NaN
    - Test con include_market_context=True y False
    - Test con precios extremos

  - [ ] 4.5 Implementar get_asset_type() para clasificación de activos
    - Clasificar ticker como "stable" o "volatile" basado en lista predefinida
    - Retornar "stable" por defecto para tickers desconocidos
    - _Requisitos: 6.1_

  - [ ] 4.6 Implementar get_feature_cols() para determinar features según configuración
    - Retornar 9 features base para activos estables sin sentimiento
    - Retornar 12 features para activos estables con sentimiento
    - Retornar 11 features para activos volátiles sin sentimiento (9 base + 2 contexto)
    - Retornar 14 features para activos volátiles con sentimiento (11 + 3 sentimiento)
    - _Requisitos: 1.5, 1.6, 6.7_

  - [ ]* 4.7 Escribir property test para get_feature_cols()
    - **Property 3: Feature Count by Asset Type**
    - **Valida: Requisitos 1.5, 1.6**

  - [ ] 4.8 Implementar prepare_data() para preparación completa de datos
    - Descargar datos históricos
    - Calcular features técnicas
    - Integrar features de sentimiento si USE_SENTIMENT=True
    - Normalizar con StandardScaler
    - Dividir en train/val/test (70/15/15)
    - Calcular threshold dinámico como percentil 60 de |y_train|
    - Convertir a tensores de PyTorch con shape [n_samples, window_size, n_features]
    - Retornar diccionario con X_train, y_train, X_val, y_val, X_test, y_test, scaler, dynamic_threshold, feature_cols
    - _Requisitos: 1.1, 3.3_

  - [ ]* 4.9 Escribir property test para threshold dinámico
    - **Property 7: Dynamic Threshold Calculation**
    - **Valida: Requisitos 3.3**

  - [ ] 4.10 Implementar prepare_data_multi_window() para optimización
    - Descargar datos UNA VEZ por ticker
    - Reutilizar datos descargados para todas las variaciones de window_size
    - Retornar diccionario mapeando window_size a datos preparados
    - _Requisitos: 3.1, 3.2_

  - [ ]* 4.11 Escribir unit tests para prepare_data_multi_window()
    - Verificar que no hay descargas redundantes (mock de download_data)
    - Test con múltiples window_sizes
    - Verificar que cada window_size tiene datos correctos

- [ ] 5. Checkpoint - Verificar pipeline de features
  - Asegurar que todos los tests pasen, preguntar al usuario si surgen dudas.

- [ ] 6. Implementar modelo BiGRU y ensemble
  - [ ] 6.1 Crear model.py con clase HorizonBiGRU
    - Definir arquitectura: nn.GRU bidireccional + capa fully connected
    - Constructor con parámetros: input_dim, hidden_dim, num_layers, dropout
    - Método forward() que retorna retorno logarítmico predicho
    - _Requisitos: Diseño - Arquitectura BiGRU_

  - [ ]* 6.2 Escribir unit tests para HorizonBiGRU
    - Test de inicialización con diferentes parámetros
    - Test de forward pass con diferentes batch sizes
    - Test de output shape correcto

  - [ ] 6.3 Implementar train_single_model() para entrenamiento individual
    - Configurar optimizer (Adam) y loss function (MSELoss)
    - Implementar loop de entrenamiento con early stopping
    - Calcular métricas en conjunto de validación: val_loss, directional_accuracy, MAE, RMSE
    - Retornar modelo entrenado y métricas
    - _Requisitos: 4.1, 4.3_

  - [ ]* 6.4 Escribir unit tests para train_single_model()
    - Test con datos sintéticos pequeños
    - Test de early stopping
    - Verificar que métricas están en rangos válidos

  - [ ] 6.5 Implementar evaluate_model() para cálculo de métricas
    - Calcular directional_accuracy comparando sign(predicted) con sign(true)
    - Calcular precision_up y recall_up para clase ALCISTA
    - Calcular MAE y RMSE
    - _Requisitos: 4.1, 4.2, 4.3_

  - [ ]* 6.6 Escribir property tests para métricas
    - **Property 10: Directional Accuracy Calculation**
    - **Property 11: Precision and Recall Calculation**
    - **Property 12: MAE and RMSE Calculation**
    - **Valida: Requisitos 4.1, 4.2, 4.3**

  - [ ] 6.7 Implementar calculate_ensemble_weights() basado en val_loss
    - Calcular weight_i = (1 / val_loss_i) / sum(1 / val_loss_j)
    - Normalizar para que sumen 1.0
    - _Requisitos: 8.4_

  - [ ]* 6.8 Escribir unit tests para calculate_ensemble_weights()
    - Test con diferentes val_loss values
    - Verificar que pesos suman 1.0
    - Test con val_loss muy dispares

- [ ] 7. Implementar clasificador XGBoost
  - [ ] 7.1 Crear xgboost_model.py con función train_xgboost()
    - Extraer último timestep de cada ventana como features tabulares
    - Crear etiquetas binarias: 1 si retorno > 0, 0 en caso contrario
    - Entrenar XGBClassifier con XGBOOST_CONFIG
    - Calcular xgb_directional_accuracy, xgb_precision_up, xgb_recall_up en test set
    - Extraer feature_importance del modelo entrenado
    - Guardar modelo como {ticker}_xgboost.pkl
    - Retornar diccionario con métricas y feature_importance
    - _Requisitos: 3.5, 3.7, 4.4, 8.5_

  - [ ]* 7.2 Escribir unit tests para train_xgboost()
    - Test con datos sintéticos
    - Verificar que feature_importance tiene todas las features
    - Test de guardado y carga del modelo

  - [ ] 7.3 Implementar predict_xgboost() para inferencia
    - Cargar modelo desde {ticker}_xgboost.pkl
    - Lanzar FileNotFoundError si modelo no existe
    - Predecir dirección y probabilidad
    - Retornar diccionario con direction (0 o 1) y probability [0.0, 1.0]
    - _Requisitos: 5.4, 7.6_

  - [ ]* 7.4 Escribir unit tests para predict_xgboost()
    - Test con modelo guardado
    - Test cuando modelo no existe
    - Verificar rangos de probability

- [x] 8. Implementar meta-ensemble
  - [x] 8.1 Crear meta_ensemble.py con función sigmoid_transform()
    - Implementar fórmula: prob = 1 / (1 + exp(-return * scale))
    - Usar META_ENSEMBLE_SIGMOID_SCALE como parámetro de escala
    - _Requisitos: 2.2, 10.5_

  - [ ]* 8.2 Escribir property test para sigmoid_transform()
    - **Property 5: Sigmoid Transformation**
    - **Valida: Requisitos 2.2**

  - [x] 8.3 Implementar combine_predictions() para combinación ponderada
    - Convertir retorno BiGRU a probabilidad usando sigmoid_transform()
    - Obtener probabilidad XGBoost directamente
    - Calcular score final: w_bigru * prob_bigru + w_xgb * prob_xgb
    - Validar que pesos suman 1.0
    - _Requisitos: 2.1, 2.3, 2.4, 10.2_

  - [ ]* 8.4 Escribir property tests para combine_predictions()
    - **Property 4: Meta-Ensemble Combination Formula**
    - **Property 20: Meta-Ensemble Weights Validation**
    - **Valida: Requisitos 2.1, 10.2**

  - [x] 8.5 Implementar classify_trend() para clasificación de tendencia
    - Aplicar lógica: score > 0.5 + delta → ALCISTA, score < 0.5 - delta → BAJISTA, else → LATERAL
    - Usar META_ENSEMBLE_TREND_DELTA como parámetro delta
    - _Requisitos: 2.5, 2.6, 2.7, 2.8, 10.6_

  - [ ]* 8.6 Escribir property test para classify_trend()
    - **Property 6: Trend Classification Logic**
    - **Valida: Requisitos 2.5, 2.6, 2.7**

  - [ ]* 8.7 Escribir unit tests para casos edge de meta-ensemble
    - Test con pesos que no suman 1.0 (debe lanzar ValueError)
    - Test con delta = 0 (sin zona neutral)
    - Test con scores exactamente en los umbrales
    - Test con retornos extremos

- [ ] 9. Checkpoint - Verificar modelos y meta-ensemble
  - Asegurar que todos los tests pasen, preguntar al usuario si surgen dudas.

- [ ] 10. Implementar pipeline de entrenamiento completo
  - [ ] 10.1 Crear training.py con función train_ensemble()
    - Determinar tipo de activo (stable/volatile) usando get_asset_type()
    - Obtener configuración y ENSEMBLE_VARIATIONS correspondientes
    - Preparar datos con prepare_data_multi_window() para todas las variaciones
    - Entrenar cada modelo BiGRU con su variación específica
    - Calcular pesos del ensemble basados en val_loss
    - Entrenar modelo XGBoost con mismo dataset
    - Calcular naive baseline accuracy (clase más frecuente)
    - _Requisitos: 3.1, 3.2, 3.3, 3.5, 4.5, 6.1, 6.5_

  - [ ]* 10.2 Escribir property test para naive baseline
    - **Property 13: Naive Baseline Calculation**
    - **Valida: Requisitos 4.5**

  - [ ] 10.3 Implementar save_training_artifacts() para persistencia
    - Crear directorio SAVED_MODELS_DIR si no existe
    - Guardar cada modelo BiGRU como {ticker}_model_{idx}.pth
    - Guardar scaler como {ticker}_scaler.pkl
    - Guardar threshold dinámico como {ticker}_threshold.pkl
    - Guardar pesos del ensemble como {ticker}_weights.pkl
    - Guardar modelo XGBoost (ya guardado en train_xgboost)
    - _Requisitos: 8.1, 8.2, 8.3, 8.4, 8.5, 8.7_

  - [ ]* 10.4 Escribir property test para persistencia de artefactos
    - **Property 8: Threshold Persistence Round-Trip**
    - **Property 18: Model Artifacts Persistence**
    - **Valida: Requisitos 3.4, 8.1, 8.2, 8.3, 8.4, 8.5**

  - [ ] 10.5 Implementar generate_training_report() para informe JSON
    - Incluir ticker, asset_type, trained_at (timestamp UTC)
    - Incluir n_models, config_used, feature_cols, dynamic_threshold
    - Incluir metrics: avg_val_loss, avg_directional_accuracy, avg_mae, avg_rmse, avg_precision_up, avg_recall_up, naive_baseline_accuracy
    - Incluir xgboost_metrics: xgb_directional_accuracy, xgb_precision_up, xgb_recall_up, feature_importance
    - Incluir individual_models: array con métricas de cada modelo (model_idx, seed, variation, val_loss, epochs_trained, directional_accuracy, mae, rmse, precision_up, recall_up)
    - Guardar como {ticker}_report.json
    - _Requisitos: 3.6, 3.7, 4.6, 8.6, 9.1, 9.6_

  - [ ]* 10.6 Escribir property test para estructura del informe
    - **Property 9: Training Report Structure**
    - **Valida: Requisitos 3.6, 3.7, 4.6, 8.6, 9.1, 9.6**

  - [ ]* 10.7 Escribir unit tests para train_ensemble()
    - Test con ticker de prueba pequeño
    - Verificar que todos los artefactos se guardan
    - Verificar estructura del informe JSON
    - Test de logging durante entrenamiento

- [ ] 11. Implementar servicio de predicción
  - [ ] 11.1 Crear prediction.py con función load_models()
    - Cargar todos los modelos BiGRU desde {ticker}_model_{idx}.pth
    - Cargar scaler desde {ticker}_scaler.pkl
    - Cargar threshold desde {ticker}_threshold.pkl
    - Cargar pesos del ensemble desde {ticker}_weights.pkl
    - Cargar modelo XGBoost desde {ticker}_xgboost.pkl
    - Lanzar FileNotFoundError con mensaje descriptivo si algún archivo no existe
    - Implementar caché de modelos para evitar recargas
    - _Requisitos: 7.6, 9.7_

  - [ ]* 11.2 Escribir unit tests para load_models()
    - Test con modelos existentes
    - Test cuando falta algún archivo
    - Test de caché (segunda carga debe ser más rápida)

  - [ ] 11.3 Implementar prepare_recent_data() para datos de inferencia
    - Descargar datos recientes del ticker (ventana máxima requerida)
    - Calcular features técnicas
    - Obtener sentimiento de últimos 7 días usando get_daily_sentiment()
    - Normalizar con scaler guardado
    - Retornar features normalizadas y datos de sentimiento
    - _Requisitos: 5.1, 5.2, 5.3_

  - [ ]* 11.4 Escribir unit tests para prepare_recent_data()
    - Test con ticker válido
    - Test cuando sentimiento no está disponible
    - Test con datos insuficientes

  - [ ] 11.5 Implementar predict_ensemble() para predicción completa
    - Cargar modelos usando load_models()
    - Preparar datos recientes usando prepare_recent_data()
    - Ejecutar predicción con cada modelo BiGRU (usando su window_size específico)
    - Calcular retorno ponderado del ensemble BiGRU
    - Ejecutar predicción con XGBoost
    - Combinar predicciones en meta-ensemble usando combine_predictions()
    - Clasificar tendencia final usando classify_trend()
    - Calcular bandas de incertidumbre: mean ± std de predicciones individuales
    - _Requisitos: 5.4, 5.5, 5.6_

  - [ ]* 11.6 Escribir property test para bandas de incertidumbre
    - **Property 19: Uncertainty Bands Calculation**
    - **Valida: Requisitos 9.5**

  - [ ] 11.7 Implementar format_prediction_response() para respuesta estructurada
    - Incluir todos los campos requeridos: ticker, trend, meta_trend, meta_score, confidence, current_price, predicted_price, price_upper, price_lower, predicted_return, predicted_return_pct
    - Incluir sentiment_available, sentiment_score
    - Incluir xgboost_direction, xgboost_probability
    - Incluir individual_predictions con model_id y predicted_return
    - Incluir timestamp en formato ISO 8601
    - _Requisitos: 5.6, 5.7, 9.2, 9.3, 9.4, 9.5_

  - [ ]* 11.8 Escribir property test para estructura de respuesta
    - **Property 14: Prediction Response Structure**
    - **Valida: Requisitos 5.6, 5.7, 9.2, 9.3, 9.4**

  - [ ] 11.9 Implementar manejo de errores en predict_ensemble()
    - Capturar todas las excepciones durante predicción
    - Registrar error completo en logs
    - Retornar objeto con campo "error" y "detail"
    - _Requisitos: 5.8, 7.7_

  - [ ]* 11.10 Escribir property test para respuesta de error
    - **Property 15: Error Response Structure**
    - **Property 17: Exception Handling for Missing Data**
    - **Valida: Requisitos 5.8, 7.4, 7.5, 7.6, 7.7**

  - [ ]* 11.11 Escribir unit tests para predict_ensemble()
    - Test con modelos pre-entrenados
    - Test cuando modelo no existe
    - Test con ticker inválido
    - Test con datos insuficientes
    - Test cuando todas las predicciones son iguales (std = 0)

- [ ] 12. Checkpoint - Verificar servicio de predicción
  - Asegurar que todos los tests pasen, preguntar al usuario si surgen dudas.

- [ ] 13. Implementar endpoint REST API
  - [ ] 13.1 Crear api/predictions.py con endpoint POST /api/predictions/predict
    - Definir PredictionRequest con campos: ticker (requerido), user_id (opcional)
    - Validar request usando Pydantic
    - Llamar a predict_ensemble() con ticker
    - Retornar respuesta formateada o error
    - Agregar logging de requests y respuestas
    - _Requisitos: 5.6, 5.8_

  - [ ]* 13.2 Escribir integration tests para endpoint
    - Test con ticker válido y modelos entrenados
    - Test con ticker sin modelos entrenados
    - Test con ticker inválido
    - Test de formato de respuesta
    - Test de manejo de errores

- [ ] 14. Implementar tests de integración end-to-end
  - [ ]* 14.1 Escribir test de flujo completo de entrenamiento
    - Descargar datos para ticker de prueba
    - Ejecutar train_ensemble()
    - Verificar que todos los artefactos se guardan correctamente
    - Cargar modelos y verificar que funcionan
    - Validar estructura del informe JSON

  - [ ]* 14.2 Escribir test de flujo completo de predicción
    - Usar modelos pre-entrenados de ticker de prueba
    - Ejecutar predict_ensemble()
    - Validar estructura de respuesta
    - Verificar que todos los campos están en rangos válidos

  - [ ]* 14.3 Escribir tests de escenarios de fallo
    - Test de fallo de API Finnhub durante entrenamiento (debe continuar)
    - Test de fallo de API Finnhub durante predicción (debe continuar)
    - Test de fallo de Yahoo Finance (debe lanzar ValueError)
    - Test de modelos faltantes (debe lanzar FileNotFoundError)

- [ ] 15. Implementar documentación y utilidades
  - [ ] 15.1 Crear script de entrenamiento CLI (train_cli.py)
    - Aceptar ticker como argumento
    - Ejecutar train_ensemble()
    - Mostrar resumen de métricas al finalizar
    - Manejar errores con mensajes descriptivos

  - [ ] 15.2 Crear script de predicción CLI (predict_cli.py)
    - Aceptar ticker como argumento
    - Ejecutar predict_ensemble()
    - Mostrar predicción formateada en consola
    - Manejar errores con mensajes descriptivos

  - [ ] 15.3 Documentar configuración en README.md
    - Instrucciones de instalación de dependencias
    - Configuración de FINNHUB_API_KEY
    - Ejemplos de uso de scripts CLI
    - Descripción de hiperparámetros del meta-ensemble
    - Ejemplos numéricos del impacto de cada hiperparámetro
    - _Requisitos: 10.7_

  - [ ] 15.4 Agregar logging comprehensivo
    - Configurar logging con niveles apropiados (INFO, WARNING, ERROR, DEBUG)
    - Agregar logs informativos durante entrenamiento (inicio, progreso, finalización)
    - Agregar logs informativos durante inferencia (carga de modelos, predicción)
    - Agregar logs de warning para degradación de funcionalidad (API failures)
    - Agregar logs de error para fallos críticos
    - _Requisitos: 9.7_

- [ ] 16. Checkpoint final - Validación completa del sistema
  - Ejecutar todos los tests (unit, property, integration)
  - Verificar cobertura de tests >80% en módulos core
  - Entrenar modelo con ticker de prueba y verificar métricas
  - Ejecutar predicción y validar respuesta
  - Asegurar que todos los tests pasen, preguntar al usuario si surgen dudas.

## Notas

- Las tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido
- Cada tarea referencia los requisitos específicos que implementa para trazabilidad
- Los property tests validan propiedades universales con 100+ iteraciones usando hypothesis
- Los unit tests validan ejemplos específicos y casos edge conocidos
- Los checkpoints aseguran validación incremental del sistema
- Todos los tests deben pasar antes de considerar la implementación completa
- El sistema debe ser robusto ante fallos de APIs externas (continuar con valores neutros)
- La documentación debe incluir ejemplos numéricos del impacto de hiperparámetros del meta-ensemble
