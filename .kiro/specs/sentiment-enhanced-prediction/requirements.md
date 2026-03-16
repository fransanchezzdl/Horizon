# Requirements Document

## Introduction

El proyecto Horizon es una aplicación web educativa de análisis financiero que actualmente utiliza modelos BiGRU bidireccionales para predecir tendencias de activos financieros a 5 días. El sistema actual alcanza un accuracy del ~50% (prácticamente al azar), utilizando únicamente análisis técnico basado en precios históricos e indicadores técnicos.

Esta especificación define los requisitos para mejorar significativamente el sistema de predicción mediante la integración completa de análisis de sentimiento de noticias financieras y optimización de la arquitectura de modelos híbridos existente (BiGRU + XGBoost). El objetivo es superar sustancialmente el 50% de accuracy actual mediante la combinación de señales técnicas y fundamentales.

## Glossary

- **Prediction_System**: Sistema completo de predicción de tendencias financieras del proyecto Horizon
- **Sentiment_Analyzer**: Módulo de análisis de sentimiento que procesa noticias financieras usando modelos NLP
- **News_Fetcher**: Componente que descarga noticias financieras desde APIs externas (Finnhub, AlphaVantage)
- **Feature_Pipeline**: Pipeline de procesamiento que calcula y combina features técnicas y de sentimiento
- **Hybrid_Model**: Arquitectura de ensemble que combina BiGRU, XGBoost y análisis de sentimiento
- **Meta_Ensemble**: Capa de agregación que combina predicciones de múltiples modelos con pesos adaptativos
- **Training_Pipeline**: Sistema de entrenamiento que gestiona el ciclo completo de preparación de datos, entrenamiento y evaluación
- **Sentiment_Score**: Puntuación numérica [-1.0, +1.0] que representa el sentimiento agregado de noticias
- **Sentiment_Magnitude**: Medida de confianza [0.0, 1.0] del análisis de sentimiento
- **News_Volume**: Cantidad de artículos de noticias disponibles en un período
- **Directional_Accuracy**: Métrica que mide el porcentaje de predicciones correctas de dirección (alcista/bajista/lateral)
- **Trend_Classification**: Clasificación de la tendencia predicha en ALCISTA, BAJISTA o LATERAL
- **Prediction_Confidence**: Nivel de confianza [0.0, 1.0] de la predicción del ensemble

## Requirements

### Requirement 1: Integración Completa de Análisis de Sentimiento

**User Story:** Como desarrollador del sistema, quiero que el análisis de sentimiento esté completamente integrado en el pipeline de predicción, para que las señales fundamentales complementen el análisis técnico.

#### Acceptance Criteria

1. WHEN THE Training_Pipeline prepara datos históricos, THE Sentiment_Analyzer SHALL calcular sentiment_score, sentiment_magnitude y news_volume para cada día de trading
2. WHEN no hay noticias disponibles para una fecha específica, THE Feature_Pipeline SHALL rellenar con valores neutros (0.0, 0.0, 0) con forward-fill limitado a 5 días
3. THE Sentiment_Analyzer SHALL utilizar el modelo FinBERT (ProsusAI/finbert) para clasificar el sentimiento de titulares de noticias
4. WHEN THE News_Fetcher descarga noticias desde Finnhub, THE System SHALL manejar errores de API y límites de rate-limiting sin interrumpir el entrenamiento
5. THE Feature_Pipeline SHALL incluir las 3 features de sentimiento (sentiment_score, sentiment_magnitude, news_volume) en el conjunto de features para todos los activos
6. WHEN USE_SENTIMENT está habilitado en configuración, THE System SHALL usar 12 features para activos estables y 14 features para activos volátiles
7. THE Sentiment_Analyzer SHALL procesar titulares truncados a 512 caracteres para evitar errores de tokenización

### Requirement 2: Optimización del Meta-Ensemble Híbrido

**User Story:** Como científico de datos, quiero que el meta-ensemble combine inteligentemente las predicciones de BiGRU y XGBoost, para maximizar el accuracy direccional del sistema.

#### Acceptance Criteria

1. THE Meta_Ensemble SHALL combinar predicciones de BiGRU y XGBoost usando pesos configurables (META_ENSEMBLE_WEIGHTS)
2. WHEN THE BiGRU predice un retorno logarítmico, THE Meta_Ensemble SHALL convertirlo a probabilidad usando sigmoid escalado (META_ENSEMBLE_SIGMOID_SCALE)
3. WHEN THE XGBoost predice dirección binaria, THE Meta_Ensemble SHALL usar su probabilidad de clase positiva directamente
4. THE Meta_Ensemble SHALL calcular un score final ponderado: w_bigru * prob_bigru + w_xgb * prob_xgb
5. WHEN el score final está en el rango [0.5 - delta, 0.5 + delta], THE Meta_Ensemble SHALL clasificar la tendencia como LATERAL
6. WHEN el score final es mayor que 0.5 + delta, THE Meta_Ensemble SHALL clasificar la tendencia como ALCISTA
7. WHEN el score final es menor que 0.5 - delta, THE Meta_Ensemble SHALL clasificar la tendencia como BAJISTA
8. THE System SHALL permitir ajustar META_ENSEMBLE_TREND_DELTA para controlar la sensibilidad de detección de tendencias laterales

### Requirement 3: Mejora del Pipeline de Entrenamiento

**User Story:** Como desarrollador del sistema, quiero que el pipeline de entrenamiento sea eficiente y robusto, para poder entrenar modelos con datos históricos completos incluyendo sentimiento.

#### Acceptance Criteria

1. THE Training_Pipeline SHALL descargar datos históricos una sola vez por ticker usando prepare_data_multi_window
2. WHEN THE Training_Pipeline procesa múltiples window_sizes, THE System SHALL reutilizar los datos descargados y escalados
3. THE Training_Pipeline SHALL calcular un threshold dinámico basado en el percentil 60 de retornos absolutos del conjunto de entrenamiento
4. THE Training_Pipeline SHALL guardar el threshold dinámico en disco junto con los modelos entrenados
5. WHEN THE Training_Pipeline entrena el ensemble BiGRU, THE System SHALL entrenar también el modelo XGBoost con los mismos datos
6. THE Training_Pipeline SHALL generar un informe JSON completo con métricas de BiGRU, XGBoost y meta-ensemble
7. THE Training_Pipeline SHALL guardar feature importance del XGBoost para análisis de interpretabilidad

### Requirement 4: Validación y Métricas de Rendimiento

**User Story:** Como científico de datos, quiero métricas completas de evaluación del sistema híbrido, para poder comparar el rendimiento con el baseline actual del 50%.

#### Acceptance Criteria

1. THE Training_Pipeline SHALL calcular directional_accuracy para cada modelo individual del ensemble BiGRU
2. THE Training_Pipeline SHALL calcular precision_up y recall_up para la clase ALCISTA en conjunto de test
3. THE Training_Pipeline SHALL calcular MAE y RMSE para evaluar la precisión de los retornos predichos
4. THE Training_Pipeline SHALL calcular xgb_directional_accuracy, xgb_precision_up y xgb_recall_up para el modelo XGBoost
5. THE Training_Pipeline SHALL comparar el accuracy del meta-ensemble contra un baseline naive (predicción de tendencia más frecuente)
6. THE System SHALL guardar todas las métricas en el archivo {ticker}_report.json con timestamp UTC
7. WHEN el entrenamiento finaliza, THE System SHALL mostrar un resumen con accuracy medio del ensemble y comparación con baseline

### Requirement 5: Sistema de Inferencia en Tiempo Real

**User Story:** Como usuario de la aplicación, quiero obtener predicciones actualizadas que incorporen noticias recientes, para tomar decisiones informadas sobre mis inversiones.

#### Acceptance Criteria

1. WHEN THE Prediction_System recibe una solicitud de predicción, THE System SHALL descargar los datos más recientes del ticker
2. THE Sentiment_Analyzer SHALL obtener noticias de los últimos 7 días usando get_daily_sentiment
3. THE Feature_Pipeline SHALL calcular todas las features técnicas y de sentimiento para la ventana más reciente
4. THE Hybrid_Model SHALL ejecutar predicciones con todos los modelos del ensemble BiGRU y el modelo XGBoost
5. THE Meta_Ensemble SHALL combinar las predicciones usando los pesos configurados y generar la tendencia final
6. THE Prediction_System SHALL devolver trend, meta_trend, confidence, predicted_price, price_upper, price_lower y predicted_return_pct
7. THE Prediction_System SHALL incluir en la respuesta sentiment_available, sentiment_score y las predicciones individuales de cada modelo
8. WHEN ocurre un error durante la predicción, THE System SHALL devolver un objeto con el campo "error" y un mensaje descriptivo

### Requirement 6: Configuración Adaptativa por Tipo de Activo

**User Story:** Como desarrollador del sistema, quiero que la configuración se adapte automáticamente al tipo de activo, para optimizar el rendimiento según la volatilidad característica.

#### Acceptance Criteria

1. THE System SHALL clasificar automáticamente cada ticker como "stable" o "volatile" usando get_asset_type
2. WHERE el activo es "stable", THE System SHALL usar STABLE_CONFIG con window_size=30, dropout=0.1 y trend_threshold=0.01
3. WHERE el activo es "volatile", THE System SHALL usar VOLATILE_CONFIG con window_size=60, dropout=0.3 y trend_threshold=0.03
4. WHERE el activo es "volatile", THE Feature_Pipeline SHALL incluir features de contexto de mercado (VIX_Close, NASDAQ_Return)
5. THE System SHALL usar ENSEMBLE_VARIATIONS específicas para cada tipo de activo con diferentes combinaciones de hidden_dim, window_size y dropout
6. THE System SHALL permitir configurar pesos del meta-ensemble (META_ENSEMBLE_WEIGHTS) independientemente por tipo de activo
7. THE System SHALL usar get_feature_cols para determinar automáticamente el conjunto correcto de features según tipo de activo y configuración de sentimiento

### Requirement 7: Robustez y Manejo de Errores

**User Story:** Como usuario del sistema, quiero que el sistema sea robusto ante fallos de APIs externas, para que las predicciones estén disponibles incluso cuando hay problemas de conectividad.

#### Acceptance Criteria

1. WHEN FINNHUB_API_KEY no está configurada, THE Sentiment_Analyzer SHALL usar scores neutros sin interrumpir el entrenamiento
2. WHEN la descarga de noticias desde Finnhub falla, THE News_Fetcher SHALL registrar un warning y continuar con valores neutros
3. WHEN FinBERT no puede cargarse, THE Sentiment_Analyzer SHALL registrar un warning y devolver scores neutros
4. WHEN yfinance no puede descargar datos para un ticker, THE System SHALL lanzar ValueError con mensaje descriptivo
5. WHEN no hay suficientes datos históricos para el window_size requerido, THE System SHALL lanzar ValueError indicando filas disponibles vs requeridas
6. WHEN un modelo guardado no existe en disco, THE System SHALL lanzar FileNotFoundError con instrucciones para entrenar
7. WHEN ocurre un error inesperado durante predicción, THE System SHALL capturar la excepción, registrarla y devolver un objeto de error al cliente

### Requirement 8: Persistencia y Versionado de Modelos

**User Story:** Como desarrollador del sistema, quiero que todos los artefactos de modelos se guarden de forma organizada, para poder reproducir predicciones y auditar el rendimiento histórico.

#### Acceptance Criteria

1. THE Training_Pipeline SHALL guardar cada modelo del ensemble BiGRU como {ticker}_model_{idx}.pth en SAVED_MODELS_DIR
2. THE Training_Pipeline SHALL guardar el scaler ajustado como {ticker}_scaler.pkl
3. THE Training_Pipeline SHALL guardar el threshold dinámico como {ticker}_threshold.pkl
4. THE Training_Pipeline SHALL guardar los pesos del ensemble basados en val_loss como {ticker}_weights.pkl
5. THE Training_Pipeline SHALL guardar el modelo XGBoost como {ticker}_xgboost.pkl
6. THE Training_Pipeline SHALL guardar un informe completo como {ticker}_report.json con configuración, métricas y timestamp
7. THE System SHALL crear el directorio SAVED_MODELS_DIR automáticamente si no existe

### Requirement 9: Interpretabilidad y Transparencia

**User Story:** Como analista financiero, quiero entender qué factores influyen en las predicciones, para poder validar la lógica del modelo y confiar en sus recomendaciones.

#### Acceptance Criteria

1. THE Training_Pipeline SHALL calcular y guardar feature_importance del modelo XGBoost en el informe JSON
2. THE Prediction_System SHALL devolver las predicciones individuales de cada modelo del ensemble con su model_id
3. THE Prediction_System SHALL devolver tanto trend (BiGRU puro) como meta_trend (híbrido) para comparación
4. THE Prediction_System SHALL devolver xgboost_direction y xgboost_probability para análisis individual
5. THE Prediction_System SHALL devolver bandas de incertidumbre (price_upper, price_lower) basadas en la desviación estándar de predicciones individuales
6. THE Training_Pipeline SHALL incluir en el informe JSON la configuración exacta usada para cada modelo individual
7. THE System SHALL registrar logs informativos durante entrenamiento e inferencia para facilitar debugging

### Requirement 10: Optimización de Hiperparámetros del Meta-Ensemble

**User Story:** Como científico de datos, quiero poder ajustar fácilmente los hiperparámetros del meta-ensemble, para optimizar el balance entre BiGRU y XGBoost según el rendimiento observado.

#### Acceptance Criteria

1. THE System SHALL definir META_ENSEMBLE_WEIGHTS como diccionario configurable con claves "bigru" y "xgboost"
2. THE System SHALL validar que los pesos del meta-ensemble sumen 1.0 (w_bigru + w_xgb = 1.0)
3. THE System SHALL permitir configurar META_ENSEMBLE_SIGMOID_SCALE para ajustar la sensibilidad de conversión de retornos a probabilidades
4. THE System SHALL permitir configurar META_ENSEMBLE_TREND_DELTA para ajustar el ancho de la zona neutral
5. WHEN META_ENSEMBLE_SIGMOID_SCALE es 50.0, THE System SHALL mapear un retorno de ±2% a probabilidades cercanas a 0.73/0.27
6. WHEN META_ENSEMBLE_TREND_DELTA es 0.05, THE System SHALL clasificar como LATERAL scores en el rango [0.45, 0.55]
7. THE System SHALL documentar en config.py el impacto de cada hiperparámetro del meta-ensemble con ejemplos numéricos
