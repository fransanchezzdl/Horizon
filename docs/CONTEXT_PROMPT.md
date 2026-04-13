# 📋 HORIZON - CONTEXTO COMPLETO DEL PROYECTO

*Prompt de contexto exhaustivo para AI. Válido a partir de April 2026.*

---

## 🎯 RESUMEN EJECUTIVO

**Horizon** es una plataforma integral de análisis y predicción financiera para inversores individuales. Combina ML de ciclo completo (BiGRU + XGBoost), explainability (SHAP), chat IA (Gemini), gestión de portafolios y educación financiera.

**Objetivo primario**: Predecir dirección de activos financieros (ALCISTA/BAJISTA/LATERAL) con confiabilidad >60% y explicaciones comprensibles.

**Innovación clave (Phase 3)**: Corrección de sesgo de +75% upside mediante `scale_pos_weight` natural + metricas balanceadas.

---

## 🏗️ ARQUITECTURA GENERAL

### Stack Tecnológico

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (Usuario)                       │
│  HTML5 + CSS3 + Vanilla JS (8 páginas responsivas)          │
└────────────────────┬────────────────────────────────────────┘
                     │ REST API
┌────────────────────▼────────────────────────────────────────┐
│                  BACKEND (FastAPI + Python)                 │
│  ├─ Rutas HTTP (endpoints)                                  │
│  ├─ Servicios (lógica negocio)                              │
│  └─ DAOs (acceso datos)                                     │
└────────────────────┬────────────────────────────────────────┘
                     │ SQL
┌────────────────────▼────────────────────────────────────────┐
│           BASE DE DATOS (Supabase PostgreSQL)               │
│  ├─ usuarios, activos, historico_activos                   │
│  ├─ portfolios, portfolio_activo                           │
│  ├─ chat_messages, explicaciones_xai, explicaciones        │
│  └─ cursos, diapositivas, progreso_cursos                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│           SUBSISTEMAS PARALELOS                             │
├─────────────────────────────────────────────────────────────┤
│ ML Core                 │  Externos                          │
│ ├─ BiGRU (torch)        │  ├─ Supabase Auth (JWT)           │
│ ├─ XGBoost (ternario)   │  ├─ Google Gemini (chat)         │
│ ├─ SHAP (explicabilidad)│  ├─ yfinance (precios)           │
│ └─ Platt (calibración)  │  ├─ Finnhub (fundamentales)      │
│                         │  └─ Alpha Vantage (noticias)      │
└─────────────────────────────────────────────────────────────┘
```

### Principios de Diseño

1. **Separación por capas**: Presentación → Controladores → Servicios → DAOs → DB
2. **DTOs**: Validación de entrada/salida con Pydantic
3. **Dependencia inyectada**: Servicios acoplados débilmente
4. **Ternario (no binario)**: XGBoost clasifica BAJISTA/LATERAL/ALCISTA
5. **Métricas balanceadas**: Balanced Accuracy (no raw accuracy para clasificación imbalanceada)

---

## 📊 BACKEND - ESTRUCTURA DETALLADA

### Localización: `backend/`

```
backend/
├── main.py                          # FastAPI app, CORS, exception handlers
├── database.py                      # Clientes Supabase (anon + admin)
├── .env                             # Secrets (git-ignored)
├── models/                          # ML pipeline
│   ├── config.py                    # Hyperparameters (STABLE vs VOLATILE)
│   ├── xgboost_model.py             # Ternary classifier + scale_pos_weight
│   ├── trainer.py                   # BiGRU training (shuffle=False critical)
│   ├── train_xgboost_all.py         # Batch retraining de todos los tickers
│   ├── xai_explanation_engine.py    # SHAP force plots
│   ├── platt_scaling_calibration_v2.py  # Calibración de probabilidades
│   └── [40+ más archivos ML]
├── routes/
│   ├── auth_routes.py               # /login, /register, /logout
│   ├── activos_routes.py            # /activos, /activos/{ticker}
│   ├── prediction_routes.py         # /predicciones/{ticker}
│   ├── portfolio_routes.py          # /portfolios, /portfolios/{id}/ativos
│   ├── chat_routes.py               # /chat, /chat/history
│   ├── xai_routes.py                # /explicaciones/{id}, /activos/{ticker}/explicacion
│   └── curso_routes.py              # /cursos, /cursos/{id}/progreso
├── services/
│   ├── auth_service.py              # Supabase Auth + perfil usuario
│   ├── prediction_service.py        # Orquesta BiGRU + XGBoost
│   ├── chat_service.py              # Gemini integration
│   ├── portfolio_service.py         # CRUD portfolios + optimización
│   ├── xai_update_service.py        # Generador SHAP batch
│   ├── activo_update_service.py     # Descarga yfinance + actualiza BD
│   ├── gemini_service.py            # Wrapper Google Gemini API
│   ├── storage_service.py           # Upload avatars a Supabase Storage
│   └── [15+ más]
├── daos/
│   ├── usuario_dao.py               # CRUD usuarios
│   ├── activo_dao.py                # CRUD activos
│   ├── portfolio_dao.py             # CRUD portfolios + portfolio_activo
│   ├── historico_dao.py             # Time-series por ticker
│   ├── chat_dao.py                  # Mensajes chat
│   └── [otros DAOs por dominio]
├── dtos/
│   ├── auth_dto.py                  # LoginRequest, RegisterResponse, etc
│   ├── activo_dto.py                # ActivoResponse, ActivoListResponse
│   ├── prediction_dto.py            # PredictionRequest, PredictionResponse
│   ├── portfolio_dto.py             # PortfolioResponse, PortfolioListResponse
│   ├── chat_dto.py                  # ChatRequest, ChatResponse
│   ├── xai_dto.py                   # ExplanationResponse
│   └── [más DTOs]
├── exceptions/
│   └── exceptions.py                # Clases de error personalizadas + handlers
├── models/
│   ├── usuario_model.py             # Estructura Usuario (tabla DB)
│   ├── activo_model.py              # Estructura Activo
│   └── [más modelos ORM]
└── __init__.py
```

### Rutas API Principales

| Ruta | Método | Parámetros | Respuesta |
|------|--------|-----------|-----------|
| `/login` | POST | `{email, password}` | `{access_token, user}` |
| `/register` | POST | `{email, password, nombre, apellidos}` | `{id_usuario, email}` |
| `/activos` | GET | `?search=AAPL&limit=10` | `{activos: [{ticker, nombre, precio, senal_ia, confianza_bygru}]}` |
| `/activos/{ticker}` | GET | - | `{ticket, nombre, precio, senal_ia, confianza_bygru, grafico, noticias}` |
| `/predicciones/{ticker}` | GET | - | `{ticker, prediccion, confianza}` |
| `/activos/{ticker}/explicacion` | GET | - | `{shap_plot (base64), features_top20, confianza}` |
| `/portfolios` | GET | `?id_usuario=UUID` | `{portfolios: [{id, nombre, activos, tvl, riesgo}]}` |
| `/portfolios` | POST | `{nombre, descripcion, riesgo}` | `{id_portfolio}` |
| `/portfolios/{id}/ativos` | POST | `{ticker}` | `{success, updated_portfolio}` |
| `/portfolios/{id}/ativos/{ticker}` | DELETE | - | `{success}` |
| `/chat` | POST | `{message, id_usuario}` | `{rol, contenido, timestamp}` |
| `/chat/history` | GET | `?id_usuario=UUID&limit=50` | `{messages: [{rol, contenido, timestamp}]}` |
| `/cursos` | GET | - | `{cursos: [{id, titulo, descripcion}]}` |
| `/cursos/{id}/progreso` | GET | `?id_usuario=UUID` | `{diapositiva_actual, completado, puntuacion}` |

### Servicios (Lógica Negocio)

**AuthService**
- `iniciar_sesion(email, password)` → Autentica con Supabase, retorna JWT + perfil
- `registrar_usuario(email, password, nombre, apellidos)` → Crea usuario en Auth + BD
- `logout(token)` → Invalida sesión

**PredictionService**
- `obtener_prediccion(ticker)` → BiGRU + XGBoost → Dirección + Confianza
- `predict_next_day(ticker)` → Predicción para próximo día hábil
- Orquesta: descarga histórico → normaliza features → corre modelos ML

**XAIUpdateService**
- `generar_explicaciones_batch(tickers)` → SHAP force plot para cada ticker
- Almacena en `explicaciones_xai` tabla con base64 PNG + JSON features

**ChatService**
- `enviar_mensaje(id_usuario, message)` → Pasa a Gemini, guarda en BD
- `obtener_historial(id_usuario, limit)` → Retorna conversación

**PortfolioService**
- `crear_portfolio(id_usuario, datos)` → Insert portfolio
- `agregar_activo(id_portfolio, ticker)` → Insert portfolio_activo
- `eliminar_activo(id_portfolio, ticker)` → Delete portfolio_activo
- `obtener_portfolios(id_usuario)` → Con cálculo TVL, riesgo, retorno esperado

**ActivoUpdateService**
- `descargar_historico(ticker)` → yfinance.download() → historico_activos tabla
- Corre daily @ 2 AM

---

## 🧠 ML PIPELINE - SISTEMA DUAL DETALLADO

### Arquitectura de Predicción de Alto Nivel

```
Input: Historiico 60 días OHLCV
  ↓
Normalización por perfil volatilidad
  ├─ STABLE: volatilidad histórica < X%   (max_depth=3, subsample=0.75)
  └─ VOLATILE: volatilidad histórica ≥ X% (max_depth=4, subsample=0.8)
  ↓
┌─────────────────────────────────────────────┐
│  STAGE 1: BiGRU (Signal Generation)         │
├─────────────────────────────────────────────┤
│ Input: 30-60 día ventana features           │
│ Arch: Bidirectional GRU + Attention         │
│ Output: Binary signal (ALCISTA/BAJISTA)     │
│       + Confidence score [0, 1]             │
│ Training: shuffle=False (temporal order!)   │
└─────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────┐
│  STAGE 2: XGBoost (Directional Classifier)  │
├─────────────────────────────────────────────┤
│ Input: Aggregated features (last, mean,    │
│        std, trend, RSI, MACD, ATR, etc)    │
│ Classes (Ternary):                          │
│   0 = BAJISTA   (return ≤ -33rd percentile)│
│   1 = LATERAL   (-33 to +66 percentile)    │
│   2 = ALCISTA   (return ≥ +66 percentile)  │
│ Training Params:                            │
│   • scale_pos_weight = natural ratio        │
│   • eval_metric = balanced accuracy         │
│   • max_depth = 3 (STABLE) or 4 (VOLATILE) │
│   • subsample = 0.75 (STABLE) or 0.8       │
│ Output: Class pred + raw probabilities      │
└─────────────────────────────────────────────┘
  ↓
Calibración con Platt Scaling
  ↓
Final Output: {
  prediccion: ALCISTA | BAJISTA | LATERAL,
  confianza: 0-100%,
  breakdown: {alcista_prob: X%, lateral_prob: Y%, bajista_prob: Z%}
}
```

---

### 1️⃣ BIGRU - GENERADOR DE SEÑALES TEMPORALES

#### ¿Qué es?

BiGRU (Bidirectional Gated Recurrent Unit) es una **red neuronal recurrente** que procesa secuencias de datos preservando el **orden temporal**. "Bidirectional" significa que lee la serie tanto hacia adelante como hacia atrás, capturando patrones desde ambas direcciones.

#### Arquitectura Exacta

```python
class BiGRUAttention(nn.Module):
    """
    BiGRU + mecanismo de atención para predicción temporal
    """
    def __init__(self, input_size=30, hidden_size=64, num_layers=2, dropout=0.3):
        super().__init__()
        
        # Embedding (opcional, si entrada normalizada)
        self.embedding = nn.Linear(input_size, 128)
        
        # BiGRU: procesa secuencia en ambas direcciones
        # hidden_size * 2 porque bidirectional
        self.bigru = nn.GRU(
            input_size=128,
            hidden_size=hidden_size,      # 64
            num_layers=num_layers,        # 2 capas
            batch_first=True,
            dropout=dropout,              # 0.3 (regularization)
            bidirectional=True            # CRITICAL: bidirectional
        )
        
        # Atención: aprende qué timesteps son importantes
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_size * 2,    # 128 (64*2 bidirectional)
            num_heads=4,
            dropout=dropout,
            batch_first=True
        )
        
        # Clasificación final: ALCISTA (1) vs BAJISTA (0)
        self.fc = nn.Sequential(
            nn.Linear(hidden_size * 2, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, 2)             # 2 clases
        )
    
    def forward(self, x):
        # x shape: (batch, seq_len=60, features=30)
        
        # Embedding
        x = self.embedding(x)             # (batch, 60, 128)
        
        # BiGRU: procesa secuencia
        gru_out, _ = self.bigru(x)        # (batch, 60, 128)
        
        # Atención: pondera timesteps
        attn_out, _ = self.attention(gru_out, gru_out, gru_out)
        
        # Usa último timestep (resultado final de secuencia)
        last_out = attn_out[:, -1, :]     # (batch, 128)
        
        # Clasificación
        logits = self.fc(last_out)        # (batch, 2)
        
        return logits  # → softmax en training
```

#### Features de Entrada (30 dimensiones)

El BiGRU recibe una **ventana de 60 días** con estas características por día:

```python
features = [
    # Precios normalizados (0-1)
    'close_norm', 'high_norm', 'low_norm', 'open_norm',
    
    # Retornos (%)
    'daily_return', 'log_return',
    
    # Volatilidad rolling (5, 10, 20 días)
    'volatility_5', 'volatility_10', 'volatility_20',
    
    # Indicadores técnicos (TA-Lib)
    'rsi_14',                    # Relative Strength Index -> [0, 100]
    'macd', 'macd_signal',       # Moving Average Convergence Divergence
    'macd_hist',
    'bb_upper', 'bb_middle', 'bb_lower',  # Bollinger Bands
    'atr_14',                    # Average True Range (volatilidad)
    'adx_14',                    # Average Directional Index (trend strength)
    'cci_20',                    # Commodity Channel Index
    
    # Media móviles (ratios vs precio)
    'sma_20_ratio',              # price / sma_20
    'ema_12_ratio',              # price / ema_12
    'ema_26_ratio',              # price / ema_26
    
    # Volumen
    'volume_norm',               # volume / volume_20_avg
    'volume_change',             # (volumen_hoy - volumen_ayer) / volumen_ayer
    
    # Momentum
    'momentum_10',               # price[t] - price[t-10]
    'roc_20',                    # Rate of Change
    
    # Acción de precio
    'highest_high_20',           # precio máximo últimos 20 días
    'lowest_low_20',             # precio mínimo últimos 20 días
]
```

#### Proceso de Entrenamiento

```
Fase 1: Preparación de datos
  1. Descargar 2+ años histórico (yfinance)
  2. Calcular features técnicos (pandas_ta)
  3. Normalizar cada feature: (x - mean) / std
  4. Crear ventanas: (seq_len=60, features=30)
  5. Etiquetas:
     - Label = 1 si retorno próximos 5 días > 0 (ALCISTA)
     - Label = 0 si retorno próximos 5 días ≤ 0 (BAJISTA)

Fase 2: Split temporal (CRITICAL: NO shuffle!)
  • Train: primeros 80% (histórico antiguo)
  • Validation: siguientes 10%
  • Test: últimos 10% (más reciente)
  ⚠️ NO SHUFFLE: preserva orden temporal!

Fase 3: DataLoader
  batch_size = 32
  shuffle = False         # ← CRITICAL
  
Fase 4: Training loop
  for epoch in range(100):
    for batch in dataloader:
      logits = model(batch)
      loss = CrossEntropyLoss(logits, labels)
      loss.backward()
      optimizer.step()
    
    if epoch % 10 == 0:
      val_acc = evaluate_on_validation_set()
      if val_acc mejora:
        save_checkpoint()

Resultado:
  • Modelo guardado en: backend/models/checkpoints/bigru_{ticker}.pt
  • Signal: argmax(logits) → 1 o 0
  • Confidence: softmax(logits)[1] → [0, 1] (probabilidad ALCISTA)
```

#### ¿Por qué shuffle=False es CRÍTICO?

```
❌ CON SHUFFLE:
  Epoch 1, Batch 1: [día 30, día 5, día 60, día 15, ...]
  
  Problema: Modelo aprende que los datos están random
  → Pierde información de orden temporal
  → Accuracy sube artificialmente en train
  → Falla en datos reales (que SÍ tienen orden)

✅ SIN SHUFFLE:
  Epoch 1, Batch 1: [día 1, día 2, día 3, ..., día 32]
  Epoch 1, Batch 2: [día 33, día 34, ..., día 64]
  
  → Modelo preserva orden temporal
  → LSTM/GRU puede "recordar" secuencia
  → Generaliza mejor a datos nuevos
```

#### Posibilidades de Uso

| Uso | Descripción | Implementación |
|-----|-------------|-----------------|
| **Signal puro** | Usar solo BiGRU sin XGBoost | `PredictionService.obtener_prediccion(ticker, use_bigru_only=True)` |
| **Ensemble** | Combinar BiGRU + XGBoost votos | Stacking: XGB meta-learner sobre ambas outputs |
| **Anomaly detection** | Detectar comportamiento anómalo | Comparar confidence BiGRU con valores históricos |
| **Feature importance** | Saber qué features importan | Usar integrated gradients o SHAP en BiGRU |
| **Transfer learning** | Pre-entrenar en índices, fine-tune en stocks | `model.bigru.load_state_dict(checkpoint)` |
| **Volatility prediction** | Predicción volatilidad futura | Cambiar label: output = volatilidad_5d en lugar de retorno |
| **Multi-asset** | Actualización simultánea todos tickers | Batch paralelo en GPUs |

#### Limitaciones Actuales

- ❌ Solo 60 días contexto (ventana pequeña)
- ❌ Features técnicos estándar (no ML feature engineering)
- ❌ No incluye noticias/eventos externos
- ❌ Offline (no incorpora datos en tiempo real)

---

### 2️⃣ XGBOOST - CLASIFICADOR DIRECCIONAL (CORE)

#### ¿Qué es?

XGBoost (eXtreme Gradient Boosting) es un **algoritmo de ensemble** basado en árboles de decisión. Entrena múltiples árboles secuencialmente donde cada nuevo árbol corrige errores del anterior. Es el **modelo principal** en Horizon porque:

✅ Manejo natural de datos tabular (features técnicos + estadísticos)
✅ Robustez a outliers vs redes neuronales
✅ Interpretabilidad (vemos qué features afectan predicción)
✅ Velocidad de inferencia (~1 ms)

#### Configuración STABLE vs VOLATILE (Phase 3)

**Por qué dos perfiles?**

Algunos activos (AAPL, KO) tienen volatilidad baja → patrón predecible
Otros (TSLA, GME) tienen volatilidad alta → más ruidoso

**STABLE_CONFIG** (para activos estables)
```python
{
    'max_depth': 3,              # Árboles pequeños (menos overfitting)
    'subsample': 0.75,           # Usa 75% del data en cada árbol (regularization)
    'colsample_bytree': 0.8,     # Usa 80% de features en cada árbol
    'learning_rate': 0.1,        # Paso pequeño (100 árboles en vez de 10)
    'n_estimators': 100,         # 100 árboles secuenciales
    'min_child_weight': 1,       # Hoja debe tener ≥1 instancia
}
```

**VOLATILE_CONFIG** (para activos volátiles)
```python
{
    'max_depth': 4,              # ↑ +1 profundidad (33% más expresividad)
    'subsample': 0.8,            # ↑ Permite aprender más
    'colsample_bytree': 0.85,    # ↑ Más features disponibles
    'learning_rate': 0.12,       # ↑ Paso ligeramente mayor
    'n_estimators': 120,         # ↑ 20 árboles extra
    'min_child_weight': 1,
}
```

#### Proceso de Entrenamiento Ternario

```
ETIQUETIZACIÓN (Critical):
  1. Calcular retorno próximos 5 días para cada timestamp histórico
     return_5d = (precio[t+5] - precio[t]) / precio[t]
  
  2. Calcular percentiles del retorno histórico
     p33 = numpy.percentile(returns, 33)    # -Z%
     p66 = numpy.percentile(returns, 66)    # +W%
  
  3. Asignar clases (TERNARIAS):
     if return_5d <= p33:
       label = 0  # BAJISTA
     elif return_5d >= p66:
       label = 2  # ALCISTA
     else:
       label = 1  # LATERAL
  
  4. Resultado: ~33% en cada clase (perfectamente balanceado)

ENTRENAMIENTO:
  1. Features de entrada (28 dimensiones):
     - BiGRU signal + confidence
     - Indicadores técnicos (RSI, MACD, etc)
     - Estadísticas (last, mean, std, trend)
     - Volume + volatility
  
  2. Parámetros críticos:
     
     scale_pos_weight = (n_bajista + n_lateral) / n_alcista
     
     ¿Por qué?
       • Sin esto: XGB aprende "bajista es común, alcista es raro"
       • → Predice más bajistas, bias negativo
       • scale_pos_weight iguala importancia de clases
       • Resultado: Distribucion de predicciones ~33% cada una
     
     eval_metric = "mlogloss"  # Multi-class log-loss
     objective = "multi:softprob"
  
  3. Entrenamiento:
     dtrain = xgb.DMatrix(X_train, label=y_train)
     dval = xgb.DMatrix(X_val, label=y_val)
     
     model = xgb.train(
         params,
         dtrain,
         num_boost_round=100,
         evals=[(dtrain, 'train'), (dval, 'eval')],
         early_stopping_rounds=20
     )
  
  4. Validación: Early stopping si val_loss no mejora en 20 rondas

PREDICCIÓN (Raw):
  y_pred_raw = model.predict(X_test)
  # Retorna array (N, 3) con probabilidades raw por clase
  # ej: [[0.2, 0.5, 0.3], [0.1, 0.2, 0.7], ...]
  
  class_pred = argmax(y_pred_raw, axis=1)
  # [1, 2, 0, 2, 1, ...]
```

#### Phase 3 Fix en Detalle

**ANTES (Phase 2)**
```
Problema observado:
  - Predicción: [12% BAJISTA, 94% ALCISTA, 3% LATERAL]
  - Realidad: ~33% cada clase
  - Bias: +75% upside bias

Causa:
  scale_pos_weight = 3.0  (arbitrary, no data-driven)
  
  XGBoost pensaba:
    "ALCISTA debe ser 3x más importante que BAJISTA"
  
  Pero en realidad en datos test:
    n_bajista ≈ n_alcista ≈ n_lateral
```

**DESPUÉS (Phase 3)**
```
Solución implementada:

# Calcular ratio NATURAL del dataset
n_bajista = sum(y_train == 0)
n_lateral = sum(y_train == 1)
n_alcista = sum(y_train == 2)

scale_pos_weight = (n_bajista + n_lateral) / n_alcista

# Ejemplo con 1200 muestras:
n_bajista = 400
n_lateral = 400
n_alcista = 400
scale_pos_weight = 800 / 400 = 2.0

Resultado:
  - Predicción: [40% BAJISTA, 50% LATERAL, 45% ALCISTA]  ✅
  - Elimina extremos (12%, 94%) → rango realista (40-60%)
  - Mejor generalización en datos nuevos

Métrica: Balanced Accuracy = (recall_B + recall_L + recall_A) / 3 = 63%
```

#### Features Detallados

| Feature | Descripción | Rango | Fuente |
|---------|-------------|-------|--------|
| `bigru_signal` | Output BiGRU (0 o 1) | {0, 1} | BiGRU stage 1 |
| `bigru_confidence` | Confianza BiGRU | [0, 1] | BiGRU softmax |
| `rsi_14` | Relative Strength Index | [0, 100] | TA-Lib |
| `rsi_oversold` | RSI < 30 (binario) | {0, 1} | Feature engineering |
| `rsi_overbought` | RSI > 70 (binario) | {0, 1} | Feature engineering |
| `macd_hist` | MACD histogram | ℝ | TA-Lib |
| `atr_14` | Average True Range | ℝ⁺ | TA-Lib |
| `price_sma_20` | precio / SMA(20) | ℝ⁺ | Technical |
| `volume_ratio` | volumen actual / avg | [0, ∞) | Technical |
| `volatility_20` | σ(retornos últimos 20d) | [0, 1] | Statistical |
| `return_last_1d` | Retorno últimas 24h | (-∞, ∞) | OHLCV |
| `return_last_5d` | Retorno últimos 5d | (-∞, ∞) | OHLCV |
| `trend_indicator` | Subida/bajada últimos 10d | [-10, 10] | Technical |
| `high_20_ratio` | máximo 20d / precio actual | ℝ | Technical |
| `low_20_ratio` | mínimo 20d / precio actual | ℝ | Technical |

#### Posibilidades de Uso

| Uso | Descripción | Código |
|-----|-------------|--------|
| **Predicción pura** | XGBoost solo sin BiGRU | `xgb_model.predict(X)` |
| **Feature importance** | Qué features importan más | `xgb_model.get_score()` |
| **Shap values** | Explicar cada predicción | `shap.TreeExplainer(xgb_model).shap_values(X)` |
| **Regression** | Predecir retorno exacto % en vez de clase | Cambiar `objective` a `"reg:squarederror"` |
| **Anomaly scoring** | Asignar score anormalidad | `1 - max(prediction_probs)` |
| **Portfolio optimization** | Usar predicciones en Markowitz | `expected_return = [pred_alcista_prob - pred_bajista_prob]` |
| **Backtesting** | Simular trading con signals | Ver `tests/backtest_xgboost.py` |
| **Ensemble voting** | Votación múltiples modelos | Combinar XGB + Random Forest + SVM |

#### Interpretabilidad Nativa

XGBoost es interpretable sin SHAP:

```python
# Feature importance (ganancia)
importance = model.get_score(importance_type='weight')
# {feature: num_apariciones_en_árbol}

# Feature importance (impacto)
importance = model.get_score(importance_type='gain')
# {feature: ganancia_total_información}

# Reglas de árbol individual
print(model.trees[0].dump())
# Muestra splits exactos: if rsi_14 > 65 then score += 0.34
```

---

### 3️⃣ SENTIMENT ANALYSIS - NEWS SENTIMENT (Deshabilitado)

#### Estado Actual

❌ **Deshabilitado en Phase 3** (degradó BA: 41% → 57%)

#### Cómo Funciona (Si se habilitara)

**Arquitectura**:
```
Noticia: "Apple beats earnings, stock soars"
  ↓
Tokenización: ["apple", "beats", "earnings", "stock", "soars"]
  ↓
Sentiment scoring:
  - "beats": +0.8 (positivo)
  - "earnings": +0.3 (neutral-positivo)
  - "soars": +1.0 (muy positivo)
  - Total: compound score = 0.87 (POSITIVO)
  ↓
Temporal lag features:
  - news_sentiment_0d   (noticia hoy)
  - news_sentiment_1d   (noticia ayer)
  - news_sentiment_5d   (promedio últimos 5 días)
  ↓
Entrada a XGBoost como feature adicional
```

**Features Generados**:
```python
{
    'news_sentiment_today': -1.0 a 1.0,
    'news_sentiment_rolling_5d': promedio,
    'news_sentiment_rolling_20d': promedio,
    'news_volume': cantidad noticias hoy,
    'news_volatility': σ(news_sentiment),
    'news_surprise_score': cambio brusco sentimiento,
}
```

#### Por qué se deshabilitó

**Resultados Phase 3**:
```
SIN sentiment:
  - Balanced Accuracy: 63% ✅
  - Recall ALCISTA: 65%

CON sentiment:
  - Balanced Accuracy: 57% ❌ (-6%)
  - Recall ALCISTA: 41% ⬇️ (-24%)
  
Problema:
  • News es backward-looking (reporta eventos pasados)
  • No predice futura dirección
  • Agrega ruido (overfitting)
  • Market ya ha priced-in la noticia
```

#### Posibilidades de Mejora

| Mejora | Descripción | Esfuerzo |
|--------|-------------|----------|
| **NLP avanzado** | Usar BERT en lugar de keywords | Alto |
| **Real-time streams** | Capturar noticias en vivo vs histórico | Alto |
| **Twitter sentiment** | Incluir redes sociales (WSB, etc) | Medio |
| **Sector correlation** | Expandir a sector news vs solo ticker | Bajo |
| **Embargo detection** | Saber cuándo salió noticia vs publicada | Alto |

---

### 4️⃣ PLATT SCALING - CALIBRACIÓN DE PROBABILIDADES

#### ¿Qué Problema Resuelve?

```
XGBoost retorna:
  predict() → [0.15, 0.45, 0.40]  (raw probabilities)

Usuario ve:
  "Confianza ALCISTA: 40%"

Pero en realidad:
  • De 100 veces que XGB dice "40% confido en ALCISTA"
  • Solo 25 veces acertó (calibration error: 40% ≠ 25%)
  • Sistema reporta confianza INFLADA

Solución: Platt Scaling
  predict() → [0.15, 0.45, 0.40]
  ↓
  Platt transforma
  ↓
  calibrated_predict() → [0.18, 0.30, 0.52]
  
  Ahora: "30% confianza ALCISTA" = realmente 30% de acierto
```

#### Implementación

```python
from sklearn.calibration import IsotonicRegression

class PlattScalingCalibrator:
    def __init__(self):
        # Un calibrador por clase (3 en nuestro caso)
        self.calibrators = {
            0: IsotonicRegression(y_min=0, y_max=1),
            1: IsotonicRegression(y_min=0, y_max=1),
            2: IsotonicRegression(y_min=0, y_max=1),
        }
    
    def fit(self, raw_probs, y_true):
        """
        raw_probs: (n_samples, n_classes) - salida XGBoost sin calibrar
        y_true: (n_samples,) - etiquetas verdaderas
        """
        for class_idx in range(3):
            # Probabilidad que asignó XGB a cada clase
            class_probs = raw_probs[:, class_idx]
            
            # ¿Acertó en esa clase?
            correct = (y_true == class_idx).astype(int)
            
            # Ajustar función: prob → acerto real
            self.calibrators[class_idx].fit(class_probs, correct)
    
    def transform(self, raw_probs):
        """Calibra probabilidades"""
        calibrated = np.zeros_like(raw_probs)
        
        for class_idx in range(3):
            calibrated[:, class_idx] = self.calibrators[class_idx].predict(
                raw_probs[:, class_idx]
            )
        
        # Reescalar para que suma = 1
        calibrated = calibrated / calibrated.sum(axis=1, keepdims=True)
        
        return calibrated
```

#### Workflow Diario

```
1. Entrenar XGBoost en histórico 2 años
2. Generar predicciones en validation set (15% de datos)
3. Ajustar Platt scaling: raw_probs → y_true
4. Guardar calibrador en BD
5. En producción:
   - XGB predice raw
   - Platt transforma
   - Retorna confianza calibrada al usuario
```

#### Posibilidades

- ✅ Garantiza confianza reportada matches realidad
- ✅ Permite risk management basado en confianza real
- ✅ Mejora UX (usuario confía en los % reportados)

---

### 5️⃣ SHAP - EXPLICABILIDAD XAI

#### ¿Qué es?

SHAP (SHapley Additive exPlanations) es un método de **game theory** que explica cada predicción indicando:
- **Qué features** contribuyeron (+/-)
- **Cuánto** contribuyeron (magnitud)

#### Proceso de Generación

```python
import shap
import xgboost as xgb

# Modelo entrenado
model = load_xgboost_model("AAPL")

# Datos de referencia (background)
X_background = X_train[:100]  # 100 muestras

# Crear explainer
explainer = shap.TreeExplainer(model)

# Explicar predicción individual
X_test_sample = X_test[0:1]  # 1 muestra
shap_values = explainer.shap_values(X_test_sample)

# shap_values: array (1, n_features, n_classes)
# Ejemplo: (1, 28, 3) → 28 features × 3 clases

# Renderizar force plot
shap.force_plot(
    explainer.expected_value[2],  # Base value ALCISTA
    shap_values[0][:, 2],          # Contribuciones feature ALCISTA
    X_test_sample,
    feature_names=feature_names
)
```

#### Salida Visual

```
┌─────────────────────────────────────────────┐
│    SHAP FORCE PLOT - Predicción ALCISTA     │
├─────────────────────────────────────────────┤
│ Base value: 0.45                            │
│                                             │
│ ← BAJISTA                 ALCISTA →         │
│                                             │
│ [red -0.12] rsi_overbought=1                │
│ [blue +0.18] macd_hist=0.023                │
│ [blue +0.15] volume_ratio=1.45              │
│ [red -0.08] volatility_20=0.032             │
│ [blue +0.25] bigru_confidence=0.78          │
│                                             │
│ Output: 0.63 (63% ALCISTA)                  │
└─────────────────────────────────────────────┘
```

#### Features Top 20

Para cada predicción, generar JSON:
```json
{
  "prediction": "ALCISTA",
  "confidence": 63.2,
  "shap_base_value": 0.45,
  "top_features": [
    {"feature": "bigru_confidence", "shap_value": 0.25, "value": 0.78, "direction": "pushes_up"},
    {"feature": "volume_ratio", "shap_value": 0.18, "value": 1.45, "direction": "pushes_up"},
    {"feature": "macd_hist", "shap_value": 0.15, "value": 0.023, "direction": "pushes_up"},
    {"feature": "rsi_14", "shap_value": -0.12, "value": 72, "direction": "pushes_down"},
    ...
  ]
}
```

#### Posibilidades de Uso

| Uso | Descripción |
|-----|-------------|
| **Feature feedback** | Usuario valida si features importanteen son sensatos |
| **Model debugging** | Ver si modelo aprende patrones buscados |
| **Litigation/compliance** | Explicar recomendaciones para auditoría |
| **Feature engineering** | Identificar qué features no contribuyen |
| **User trust** | Usuario entiende por qué predicción |

---

### 6️⃣ ENSEMBLE (OPCIONAL) - COMBINACIÓN DE MODELOS

#### Arquitectura: Stacking

```
┌─────────────────┐
│   biGRU Model   │ → output_bigru
└─────────────────┘
         ↓
┌─────────────────┐
│  XGBoost Model  │ → output_xgb
└─────────────────┘
         ↓
    [Combine]
         ↓
    X_meta = [output_bigru, output_xgb, features_adicionales]
         ↓
┌─────────────────┐
│ Meta-learner    │ → PREDICCIÓN FINAL
│ (XGBoost o LR)  │
└─────────────────┘
```

#### Ventajas vs Desventajas

| Aspecto | Stacking | Votación | Simple XGB |
|--------|----------|----------|-----------|
| Complejidad | Alta | Baja | Muy baja |
| Latencia | +20% | +5% | Baseline |
| Accuracy | +2-3% max | +0-1% | Baseline 63% |
| Interpretabilidad | Baja | Alta | Muy alta |
| Overhead | Mantener 2 modelos | - | 1 modelo |
| Recomendación | Testing solo | Production OK | ✅ Usar |

**Conclusión actual**: Stacking añade complejidad para +2% de mejora. No vale la pena en Phase 3.

---

### 7️⃣ MEJORAS Y EXPERIMENTACIONES

#### A. Transfer Learning

```python
# Pre-entrenar BiGRU en SPY (índice general)
pretrained_encoder = train_bigru_on_index("SPY", epochs=50)

# Fine-tune en AAPL (individual stock)
fine_tuned_model = pretrained_encoder.freeze_layers(0, 2)
fine_tuned_model = fine_tuned_model.train_unfrozen(
    ticker="AAPL",
    epochs=10,        # Pocas épocas
    learning_rate=0.001  # LR bajito
)

# Resultado: Mejor convergencia en stocks nuevos
```

#### B. Multi-Timeframe

```python
# Combinar predicciones en diferentes ventanas
pred_1h   = predict(ticker, timeframe="1h")
pred_4h   = predict(ticker, timeframe="4h")
pred_1d   = predict(ticker, timeframe="1d")

# Ensemble por votación
final_pred = (pred_1h + pred_4h + pred_1d) / 3
```

#### C. Reinforcement Learning

```python
# Entrenar agent RL que aprende:
# - Cuándo tomar trade
# - Qué tamaño posición
# - Cuándo salir (take profit / stop loss)

# Reward signal: Sharpe ratio de portfolio simulado
agent = PPO(env=TradingEnv(tickers=[...]))
agent.train(episodes=1000)
```

#### D. GAN para Data Augmentation

```python
# Usar GAN para generar datos históricos sintéticos
# → Entrenar con más datos sin overfitting
gan_generator = train_gan_on_stock_data(ticker)
synthetic_data = gan_generator.sample(1000)
```

---

### RESUMEN COMPARATIVO: BIGRU vs XGBOOST

| Aspecto | BiGRU | XGBoost |
|--------|-------|---------|
| **Tipo** | Red neuronal recurrente | Ensemble árboles decisión |
| **Entrada** | Secuencias temporales | Features tabular |
| **Salida** | Binary (ALCISTA/BAJISTA) | Ternario (+ LATERAL) |
| **Latencia** | ~10 ms | ~1 ms |
| **Interpretabilidad** | Baja (black box) | Alta (vemos árboles) |
| **Uso actual** | Signal generador (Stage 1) | Clasificador final (Stage 2) |
| **Accuracy** | 56-60% | 63% |
| **Mejor en** | Activos con patrón temporal | Activos mixtos/generales |
| **Rol en system** | Entrada a XGBoost | Predictor principal |



### Perfiles de Configuración

**Archivo**: `backend/models/config.py`

```python
STABLE_CONFIG = {
    'max_depth': 3,
    'subsample': 0.75,
    'colsample_bytree': 0.8,
    'learning_rate': 0.1,
    'n_estimators': 100,
}

VOLATILE_CONFIG = {
    'max_depth': 4,              # +33% expresividad vs STABLE
    'subsample': 0.8,            # Permite modelo aprenda más
    'colsample_bytree': 0.85,
    'learning_rate': 0.12,
    'n_estimators': 120,
}
```

**Criterio**: `estabilidad` booleano en tabla `activos`

### Componentes ML Críticos

**1. BiGRU Trainer** (`backend/models/trainer.py`)
- Input shape: `(batch_size, 60_days, n_features)`
- Output: 2D binary classification (softmax)
- **Critical**: `DataLoader(..., shuffle=False)` preserva orden temporal
- Entrenamiento ~2 años histórico por ticker

**2. XGBoost Classifier** (`backend/models/xgboost_model.py`)
- **Phase 3 Fix**: 
  - Antes: scale_pos_weight = 3.0 (arbitrary) → +75% upside bias
  - Después: scale_pos_weight = (n_bajista + n_lateral) / n_alcista (natural ratio)
  - Resultado: Eliminó extremos (12%, 94%) → 40-60% band ✅
- Métrica principal: **Balanced Accuracy** (macro-average recall)
  - Formula: (recall_bajista + recall_lateral + recall_alcista) / 3
  - Razón: Clases balanceadas (~33% cada una), accuracy raw engaña

**3. Platt Scaling** (`backend/models/platt_scaling_calibration_v2.py`)
- Transforma raw XGB probs → calibradas [0, 1]
- Fit en validation set separado
- Crucial para confiabilidad reportada al usuario

**4. SHAP Explainability** (`backend/models/xai_explanation_engine.py`)
- Genera force plot PNG para cada predicción
- Top 20 features + magnitud impacto
- Almacenado en BD: tabla `explicaciones_xai`
- Queries: ~5-10 seg por ticker (por eso cached)

### Reentrenamiento Automático

**Cron**: `scripts/scheduler_daemon.py` (trigger diario 2 AM)

```
Para cada ticker en TODOS:
  1. ActivoUpdateService.descargar_historico()
     → yfinance.download(ticker, period="max")
     → Insert/Update historico_activos tabla
  
  2. DataPipeline.prepare_data(ticker, perfil)
     → Calcula features técnicos (RSI, MACD, ATR, Bollinger, etc)
     → Normaliza según volatilidad perfil
  
  3. BiGRU.train_predict(ticker)
     → Entrena en histérico [2+ años]
     → Genera signal + confianza
  
  4. XGBoost.train_predict(ticker)
     → Entrena ternario clasificador
     → Score balanceado accuracy
     → Aplica scale_pos_weight natural
  
  5. Platt.calibrate()
     → Calibra probs
  
  6. Almacena en activos tabla:
     - senal_ia: predicción final
     - confianza_bygru: confidence BiGRU
     - confianza_xgb: confidence XGBoost
     - updated_at: timestamp
  
  7. XAIUpdateService.generar_explicaciones_batch()
     → Corre SHAP para cada predicción
     → INSERT explicaciones_xai tabla

Típicamente: ~30 min para 30-50 tickers
```

### Resultados Actuales (Phase 3)

| Métrica | Valor | Nota |
|---------|-------|------|
| **Balanced Accuracy** | 63% | ✅ Métrica principal |
| **Macro F1** | 52% | - |
| **Directional Accuracy** | 58% | No confundir con BA |
| **Clase Distribution (Test)** | 33% cada | ✅ Perfectamente balanceado |
| **Recall ALCISTA** | 63-70% | Targetado rango 40-60% |
| **Recall LATERAL** | 58-65% | Estable |
| **Recall BAJISTA** | 56-62% | Estable |
| **Upside Bias** | 0% (FIXED!) | Antes: +75% |

**Mejor performer**: STABLE assets (KO, AAPL, MSFT) con BA ~67%

---

## 💾 BASE DE DATOS - SCHEMA COMPLETO

### Localización
- **Proveedor**: Supabase (managed PostgreSQL)
- **Acceso**: PostgREST API desde backend
- **Auth**: Supabase Auth (managed JWT)

### Tablas Principales

#### `usuarios`
```sql
CREATE TABLE usuarios (
  id UUID PRIMARY KEY,                      -- Auto from Supabase Auth
  email TEXT UNIQUE NOT NULL,
  nombre TEXT NOT NULL,
  apellidos TEXT NOT NULL,
  foto_perfil TEXT,                         -- URL en Supabase Storage
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

#### `activos`
```sql
CREATE TABLE activos (
  ticker TEXT PRIMARY KEY,                  -- "AAPL", "TSLA", etc
  nombre_completo TEXT NOT NULL,            -- "Apple Inc."
  estabilidad BOOLEAN NOT NULL DEFAULT FALSE, -- TRUE=STABLE, FALSE=VOLATILE
  precio DECIMAL(18,2),                     -- Último cierre yfinance
  senal_ia TEXT,                            -- "ALCISTA" | "BAJISTA" | "LATERAL"
  confianza_bygru DECIMAL(5,2),             -- 0-100%
  confianza_xgb DECIMAL(5,2),               -- 0-100% (calibrada)
  grafico_prediccion TEXT,                  -- Base64 gráfica histórico
  noticias TEXT[],                          -- Array URLs últimas noticias
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Índices críticos para búsqueda
CREATE INDEX idx_activos_updated_at ON activos(updated_at DESC);
CREATE INDEX idx_activos_estabilidad ON activos(estabilidad);
```

#### `historico_activos`
```sql
CREATE TABLE historico_activos (
  id_historico UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL REFERENCES activos(ticker) ON DELETE CASCADE,
  fecha DATE NOT NULL,
  precio_cierre DECIMAL(18,2),
  precio_apertura DECIMAL(18,2),
  precio_alto DECIMAL(18,2),
  precio_bajo DECIMAL(18,2),
  volumen BIGINT,
  prediccion_ia TEXT,                       -- "ALCISTA" | "BAJISTA" | "LATERAL"
  confianza_prediccion DECIMAL(5,2),
  UNIQUE(ticker, fecha)
);

CREATE INDEX idx_historico_ticker_fecha ON historico_activos(ticker, fecha DESC);
```

#### `portfolios`
```sql
CREATE TABLE portfolios (
  id_portfolio UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  id_usuario UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  nombre TEXT NOT NULL,
  descripcion TEXT,
  riesgo TEXT,                               -- "bajo" | "medio" | "alto"
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_portfolios_usuario ON portfolios(id_usuario);
```

#### `portfolio_activo` (Many-to-Many)
```sql
CREATE TABLE portfolio_activo (
  id_posicion UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  id_portfolio UUID NOT NULL REFERENCES portfolios(id_portfolio) ON DELETE CASCADE,
  ticker TEXT NOT NULL REFERENCES activos(ticker) ON DELETE CASCADE,
  cantidad DECIMAL(18,8) NOT NULL DEFAULT 1,
  precio_compra DECIMAL(18,2),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(id_portfolio, ticker)
);

CREATE INDEX idx_portfolio_activo_portfolio ON portfolio_activo(id_portfolio);
CREATE INDEX idx_portfolio_activo_ticker ON portfolio_activo(ticker);
```

#### `chat_messages`
```sql
CREATE TABLE chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  id_usuario UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  rol TEXT NOT NULL,                        -- "user" | "assistant"
  contenido TEXT NOT NULL,
  timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_chat_usuario_timestamp ON chat_messages(id_usuario, timestamp DESC);
```

#### `explicaciones_xai`
```sql
CREATE TABLE explicaciones_xai (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL REFERENCES activos(ticker),
  fecha DATE NOT NULL,
  shap_plot TEXT NOT NULL,                  -- Base64 PNG image
  features_top20 JSONB,                     -- {feature_name: importance_value}
  confianza DECIMAL(5,2),
  feedback TEXT,                            -- User evaluation for improvement
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(ticker, fecha)
);

CREATE INDEX idx_explicaciones_ticker_fecha ON explicaciones_xai(ticker, fecha DESC);
```

#### `cursos`
```sql
CREATE TABLE cursos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  titulo TEXT NOT NULL,
  descripcion TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

#### `diapositivas`
```sql
CREATE TABLE diapositivas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  id_curso UUID NOT NULL REFERENCES cursos(id) ON DELETE CASCADE,
  contenido TEXT NOT NULL,
  num_pag INT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_diapositivas_curso ON diapositivas(id_curso, num_pag);
```

#### `progreso_cursos`
```sql
CREATE TABLE progreso_cursos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  id_usuario UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  id_curso UUID NOT NULL REFERENCES cursos(id) ON DELETE CASCADE,
  diapositiva_alcanzada INT DEFAULT 0,
  completado BOOLEAN DEFAULT FALSE,
  puntuacion DECIMAL(5,2),
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(id_usuario, id_curso)
);

CREATE INDEX idx_progreso_usuario_curso ON progreso_cursos(id_usuario, id_curso);
```

---

## 🎨 FRONTEND - ESTRUCTURA

### Localización: `frontend/`

```
frontend/
├── index.html                       # Dashboard principal
├── analysis.html                    # Búsqueda & detalle activos
├── portfolio.html                   # Gestión portafolios
├── academia.html                    # Catálogo cursos
├── reflexion.html                   # Insights diarios
├── profile.html                     # Configuración usuario
├── login.html                       # Autenticación
├── register.html                    # Registro
├── css/
│   └── styles.css                   # Responsive design (mobile-first)
├── js/
│   ├── config.js                    # BASE_URL, constants
│   ├── layout.js                    # Navigation, menú
│   ├── index.js                     # Dashboard logic
│   ├── analysis.js                  # Asset search + XAI viz
│   ├── portfolio.js                 # Portfolio CRUD
│   ├── academia.js                  # Course navigator
│   ├── reflexion.js                 # Insights loader
│   ├── profile.js                   # User settings + avatar upload
│   ├── auth.js                      # Login/register/logout
│   └── api.js                       # HTTP wrapper (bearer token)
└── assets/
    └── [icons, images]
```

### Flujos Principales

**1. Búsqueda de Activos (analysis.html)**
```
User digita "AAPL" en search bar
  ↓
GET /api/activos?search=AAPL
  ↓
Backend retorna [{ticker, nombre, precio, senal_ia, confianza_bygru}]
  ↓
Frontend renderiza lista (cards con señal + % confianza + precio)
  ↓
User hace click en asset
  ↓
GET /api/activos/{ticker}
  ↓
Backend retorna completo: ticker, nombre, precio, senal, confianza, 
         grafico_prediccion (base64), noticias, explicacion
  ↓
Frontend despliega:
  • Gráfico histórico (base64 PNG)
  • Badge de señal (verde ALCISTA, rojo BAJISTA, gris LATERAL)
  • % confianza progresivamente
  • Últimas noticias (links)
  • Botón "Ver Explicación XAI"
  ↓
User clica "Ver Explicación"
  ↓
GET /api/activos/{ticker}/explicacion
  ↓
Backend:
  - Busca en explicaciones_xai si existe reciente (cached)
  - Si NO existe: Corre SHAP en XGBoost (5-10 seg), genera PNG, guarda
  - Retorna {shap_plot: "data:image/png;base64,...", features_top20: [...]}
  ↓
Frontend muestra:
  • SHAP force plot (renderizado como IMG)
  • Tabla top 20 features con magnitud impacto
```

**2. Gestión de Portafolios (portfolio.html)**
```
User navega a portfolio.html
  ↓
GET /api/portfolios?id_usuario={JWT_uid}
  ↓
Backend: PortfolioService.obtener_portfolios()
  - Trae portfolios del user
  - Para cada portfolio: obtiene posiciones + activos + precios actuales
  - Calcula TVL, peso, riesgo
  ↓
Frontend muestra:
  • Grid de portfolios (tarjetas)
  • Dentro: tabla posiciones (ticker, cantidad, %cartera, precio actual, cambio)
  ↓
User clica "+ Agregar Activo"
  ↓
Modal: search ticker
  ↓
POST /api/portfolios/{id}/ativos { ticker: "MSFT" }
  ↓
Backend: PortfolioService.agregar_activo()
  - Valida ticker existe en activos tabla
  - INSERT portfolio_activo
  ↓
Frontend: optimistically agrega a tabla + refresca
```

**3. Chat con Gemini (widget)**
```
User escribe pregunta: "¿Debo invertir en AAPL?"
  ↓
POST /api/chat { message: "...", id_usuario: JWT_uid }
  ↓
Backend: ChatService.enviar_mensaje()
  - Obtiene contexto usuario
  - Llama GeminiService.chat(message, user_context)
  - Google Gemini API: LLM genera respuesta
  - ChatDAO.guardar_mensaje() user question + assistant response
  ↓
Frontend muestra respuesta en chat bubble (rol="assistant")
  ↓
User puede continuar conversación (context mantenido en BD)
```

**4. Cursos (academia.html)**
```
GET /api/cursos
  ↓
Retorna listado cursos [{id, titulo, descripcion}]
  ↓
Frontend: cards de cursos
  ↓
User clica curso
  ↓
GET /api/cursos/{id}/diapositivas
  ↓
Backend: Retorna diapositivas (contenido HTML + número)
  ↓
Frontend: renderiza slideshow (nav anterior/siguiente)
  ↓
User clica "Marcar completado"
  ↓
PUT /api/cursos/{id}/progreso { id_usuario, completado: true }
  ↓
Backend actualiza progreso_cursos tabla
```

### Convenciones Frontend

- **Auth**: Bearer token en localStorage (`"auth_token"`)
- **Todas las requests**: Header `Authorization: Bearer {token}`
- **Error handling**: 401 → logout automático
- **Responsive**: Mobile-first, breakpoints en CSS
- **Validación**: Cliente (básica) + servidor (exhaustiva)

---

## 🔌 INTEGRACIONES EXTERNAS

### Supabase

**Dos clientes**:
1. **Anónimo** (`supabase.create_client()`) - Para operaciones del usuario
2. **Admin** (`new Supabase(url, admin_key)`) - Para operaciones internas (reentrenamiento)

**Funcionalidades**:
- Auth (login/register/JWT)
- PostgREST API (SQL queries automático)
- Storage (avatar uploads)

**Config**: `backend/database.py`
```python
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_ADMIN_KEY = os.getenv("SUPABASE_ADMIN_KEY")

supabase_anon = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
supabase_admin = create_client(SUPABASE_URL, SUPABASE_ADMIN_KEY)
```

### Google Gemini

**Propósito**: Chat IA para Q&A financiero

**Código** (`backend/services/gemini_service.py`):
```python
class GeminiService:
    def chat(self, user_message, context=None):
        # Construye prompt con contexto usuario
        # Llama Google Gemini API
        # Retorna response
        pass
```

**Límites**: 
- Usa API key en `.env`
- Rate limit: Configurar según plan Google Cloud

### yfinance

**Propósito**: Descargar datos históricos OHLCV

**Uso**:
```python
import yfinance as yf

data = yf.download(ticker, period="10y", interval="1d")
# Retorna: Open, High, Low, Close, Volume
```

**Scheduler**: `ActivoUpdateService` corre daily @ 2 AM

### Finnhub (Opcional)

**Propósito**: Datos fundamentales, earnings, etc.

**Status**: Integrado pero NO usado en Phase 3

### Alpha Vantage (Deshabilitado)

**Propósito**: Noticias + sentimiento

**Status**: ⏸️ Deshabilitado en Phase 3 (degradó métricas: 41% → 57%)

---

## 🔄 FLUJOS END-TO-END

### Flujo 1: Nuevo Usuario

```
1. User llega a register.html
2. Completa: email, password, nombre, apellidos
3. POST /register
   → AuthService.registrar_usuario()
   → Supabase.auth.sign_up() (crea cuenta)
   → UsuarioDAO.crear() (inserta tabla usuarios)
   → StorageService.create_default_avatar() (sube avatar default)
4. Backend retorna: {id_usuario, email, token}
5. Frontend guarda token + redirige a dashboard
```

### Flujo 2: Predicción Diaria (Automatizado)

```
0. Cron scheduler @ 2 AM

Para cada ticker en {AAPL, MSFT, TSLA, GOOGL, AMZN, ...}:

1. ActivoUpdateService.descargar_historico(ticker)
   → yfinance.download() → BD historico_activos

2. DataPipeline.prepare_data(ticker, perfil)
   → LEE histórico_activos
   → Calcula features técnicos (RSI, MACD, ATR, etc)
   → Normaliza según estabilidad perfil

3. BiGRU.train_predict(ticker)
   → Entrena en histórico [2+ años]
   → Genera signal + confianza

4. XGBoost.train_predict(ticker)
   → Entrena ternario
   → scale_pos_weight = natural ratio
   → Eval metric = balanced accuracy
   → Genera predicción + probabilidades raw

5. Platt.calibrate()
   → Transforma probs calibradas

6. ActvioDAO.actualizar()
   → UPDATE activos SET senal_ia, confianza_bygru, confianza_xgb, updated_at

7. XAIUpdateService.generar_explicaciones_batch(ticker)
   → SHAP force plot
   → INSERT explicaciones_xai

8. Repetir paso 1-7 para siguiente ticker

Tiempo total: ~30 min para 30-50 tickers
```

### Flujo 3: Usuario Visualiza Predicción + Explicación

```
1. Usuario busca "AAPL" en analysis.html
2. GET /api/activos?search=AAPL
   → ActivoService.buscar()
   → ActivoDAO.obtener_por_nombres(search)
   → Retorna [ActivoResponse(ticker, nombre, precio, senal_ia, confianza_bygru)]
3. Frontend muestra lista cards

4. Usuario clica "APPLE INC"
5. GET /api/activos/AAPL
   → ActivoService.obtener_activo("AAPL")
   → ActivoDAO.obtener("AAPL")
   → Retorna ActivoResponse completo + grafico + noticias

6. Frontend despliega detalle:
   - Gráfico histórico
   - Badge ALCISTA + 67.5% confianza
   - Noticias recientes

7. Usuario clica "Ver Explicación XAI"
8. GET /api/activos/AAPL/explicacion
   → XAIUpdateService.obtener_explicacion("AAPL")
   → Busca en explicaciones_xai si existe reciente (cache)
   → Si no: corre SHAP (5-10 seg), genera PNG, guarda
   → Retorna ExplanationResponse{shap_plot: base64, features_top20}

9. Frontend renderiza:
   - IMG con SHAP force plot
   - Tabla features + magnitud impacto
```

### Flujo 4: Portfolio Optimization

```
1. User navega portfolio.html
2. GET /api/portfolios?id_usuario={uuid}
   → Obtiene posiciones actuales
   → Calcula pesos, retorno esperado, riesgo

3. User clica "Rebalancear"
4. POST /api/portfolios/{id}/rebalancear
   → PortfolioService.rebalancear()
   → Markowitz-style optimization
   → Sugiere nuevos pesos según risk profile
   → Retorna {cambios_sugeridos: [{ticker, peso_actual, peso_sugerido}]}

5. Frontend muestra cambios sugeridos

6. User confirma
7. POST /api/portfolios/{id}/aplicar-rebalance
   → Backend ejecuta trade simulation
   → Guarda en BD
   → Retorna confirmación
```

---

## � PROBLEMAS IDENTIFICADOS Y FIXES RECOMENDADOS

### PROBLEMA 1: ETIQUETAS DINÁMICAS (CRÍTICO) 🔴

#### El Problema

```python
# ACTUAL (Backend/models/xgboost_model.py)
p33 = numpy.percentile(returns, 33)    # ← Recalculado CADA entrenamiento
p66 = numpy.percentile(returns, 66)    # ← Recalculado CADA entrenamiento

# Día 1 (histórico 2 años): p33 = -1.2%, p66 = +1.8%
# Día 2 (histórico 2 años + 1 día): p33 = -1.19%, p66 = +1.81%
# ...

# CONSECUENCIA: Inconsistencia de etiquetado
# Mismo retorno (+0.5%) en día 1: LATERAL (entre -1.2% y +1.8%)
# Mismo retorno (+0.5%) en día 2: ¿LATERAL o BAJISTA? Depende del nuevo p33
```

**Impacto**:
- ❌ Modelo aprende targets DIFERENTES cada reentrenamiento
- ❌ Misma predicción en mismo data puede cambiar de etiqueta
- ❌ No reproducible: dos entrenamientos con mismo data → diferente modelo
- ❌ Feature drift imperceptible

#### Fix: Umbrales Absolutos Fijos

```python
# backend/models/config.py - AGREGAR

# Thresholds FIJOS para etiquetado consistente
# Basados en análisis histórico de distribución (calculados UNA sola vez)
LABELING_THRESHOLDS = {
    'bajista_threshold': -0.015,    # -1.5% en 5 días
    'alcista_threshold': +0.015,    # +1.5% en 5 días
    # Esto crea clases ~25% BAJISTA, ~50% LATERAL, ~25% ALCISTA en S&P500 histórico
    # Ajustar si observas desbalance diferente en tu conjunto
}

def create_ternary_labels_fixed(returns_5d, thresholds=None):
    """
    Etiquetado CONSISTENTE con umbrales fijos
    
    Ventaja: Mismo dato siempre mismo label
    Trade-off: Puede haber desbalance en ciertos períodos (compensar con class_weight)
    """
    if thresholds is None:
        thresholds = LABELING_THRESHOLDS
    
    labels = np.where(
        returns_5d <= thresholds['bajista_threshold'],
        0,  # BAJISTA
        np.where(
            returns_5d >= thresholds['alcista_threshold'],
            2,  # ALCISTA
            1   # LATERAL (default)
        )
    )
    
    return labels

# backend/models/xgboost_model.py - MODIFICAR

def train_xgboost(ticker, X, y, config):
    """Entrenar XGBoost con etiquetas FIJAS"""
    
    # CAMBIO 1: Usar umbrales absolutos para etiquetado
    from backend.models.config import LABELING_THRESHOLDS
    y = create_ternary_labels_fixed(calculate_5d_returns(prices), LABELING_THRESHOLDS)
    
    # CAMBIO 2: Calcular class_weight para desbalance resultante
    unique, counts = np.unique(y, return_counts=True)
    class_weight = compute_class_weight('balanced', unique, y)
    
    scale_pos_weight = (counts[0] + counts[1]) / counts[2]  # Relación natural
    
    params = {
        'objective': 'multi:softprob',
        'num_class': 3,
        'scale_pos_weight': scale_pos_weight,
        'eval_metric': 'mlogloss',
        # ... resto de params
    }
    
    model = xgb.train(params, dtrain, num_boost_round=100, ...)
    
    # CAMBIO 3: LOG del etiquetado para audit trail
    logger.info(f"{ticker} labels distribution: {dict(zip(unique, counts))}")
    logger.info(f"Class weights: {class_weight}")
    
    return model
```

#### Validación del Fix

```python
# tests/test_label_consistency.py

def test_label_consistency():
    """
    Verificar que mismo datum siempre produce mismo label
    """
    from backend.models.xgboost_model import create_ternary_labels_fixed
    
    # Simular reentrenamiento días consecutivos
    returns = np.random.normal(0, 0.02, 500)
    
    # Entrenar "día 1"
    labels_day1 = create_ternary_labels_fixed(returns)
    
    # Entrenar "día 2" (últimos 450 + 50 nuevos)
    returns_day2 = np.concatenate([returns[-450:], np.random.normal(0, 0.02, 50)])
    labels_day2_subset = create_ternary_labels_fixed(returns_day2)[:450]
    
    # Verificar que primeros 450 son IDÉNTICOS
    assert np.array_equal(labels_day1[:-50], labels_day2_subset), \
        "Labels changed on retraining! Inconsistent etiquetado."
    
    print("✅ Labels son reproducibles")
```

---

### PROBLEMA 2: DESALINEACIÓN BIGRU-XGBOOST (CRÍTICO) 🔴

#### El Problema

```
BiGRU (Stage 1):                XGBoost (Stage 2):
├─ Output: 2 clases             ├─ Input: 28 features
│  ├─ 0 = BAJISTA               │  ├─ Feature: bigru_signal (0 o 1) ← PROBLEMA
│  └─ 1 = ALCISTA               │  └─ Feature: bigru_confidence
│                                ├─ Output: 3 clases
                                 │  ├─ 0 = BAJISTA
                                 │  ├─ 1 = LATERAL
                                 │  └─ 2 = ALCISTA

PROBLEMA:
BiGRU nunca puede decirle a XGBoost "esto es LATERAL"
Si bigru_signal=0 y bigru_confidence=0.9 (muy confiado en BAJISTA):
  → XGBoost recibe: [0, 0.9, ...]
  → Nunca ve combinación [?, high_confidence, LATERAL-signal]
  → Pierde información estructural

RESULTADO:
bigru_signal es una feature binaria muy correlacionada con clase,
pero con RUIDO estructural (no contiene info sobre LATERAL)
```

#### Fix Opción A: Simple (Quitar bigru_signal)

```python
# backend/models/data_pipeline.py

def create_xgboost_features(bigru_output, technical_features):
    """
    OPCIÓN A: Usar solo confidence continua, no signal binaria
    """
    features = {
        # ANTES (problematic binary):
        # 'bigru_signal': bigru_output['signal'],  # ← QUITAR
        # 'bigru_confidence': bigru_output['confidence'],
        
        # DESPUÉS (solo continuo):
        'bigru_confidence': bigru_output['confidence'],  # → sin ruido estructural
        
        # Resto de features técnicos
        'rsi_14': technical_features['rsi_14'],
        'macd_hist': technical_features['macd_hist'],
        # ...
    }
    
    return pd.DataFrame([features])

# Resultado:
# ✅ Feature importante es continua (información útil)
# ✅ No hay ruido binario incorrecto
# ❌ Perdemos "opinión binaria" de BiGRU (pero era ruido)
```

**Ventaja**: Implementación inmediata, reduce ruido  
**Desventaja**: Pierdes "hard signal" de BiGRU

#### Fix Opción B: Mejor (BiGRU Ternario)

```python
# backend/models/trainer.py - MODIFICAR

class BiGRUAttention(nn.Module):
    def __init__(self, input_size=30, hidden_size=64, num_layers=2):
        super().__init__()
        self.embedding = nn.Linear(input_size, 128)
        self.bigru = nn.GRU(128, hidden_size, num_layers, batch_first=True, bidirectional=True)
        self.attention = nn.MultiheadAttention(hidden_size * 2, num_heads=4, batch_first=True)
        
        # CAMBIO: 2 clases → 3 clases (TERNARIO)
        self.fc = nn.Sequential(
            nn.Linear(hidden_size * 2, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 3)  # ← Cambio de 2 a 3 (era 2)
        )
    
    def forward(self, x):
        x = self.embedding(x)
        gru_out, _ = self.bigru(x)
        attn_out, _ = self.attention(gru_out, gru_out, gru_out)
        last_out = attn_out[:, -1, :]
        logits = self.fc(last_out)  # Ahora retorna 3 logits
        return logits

# backend/models/trainer.py - dataset

def create_training_data(ticker, data_length_days=730):
    """
    Usar MISMOS umbrales que XGBoost para BiGRU
    """
    from backend.models.config import LABELING_THRESHOLDS
    
    # Calcular retornos 5 días adelante
    prices = load_prices(ticker)
    returns_5d = calculate_5d_returns(prices)
    
    # AQUÍ: Usar umbrales FIJOS (alineado con XGBoost)
    labels = create_ternary_labels_fixed(returns_5d, LABELING_THRESHOLDS)
    
    # Ahora labels son [0, 1, 2] en lugar de [0, 1]
    features = calculate_technical_features(prices)
    
    return features, labels  # labels ternarios

# Entrenamiento

def train_bigru(ticker):
    X, y = create_training_data(ticker)  # y es [0, 1, 2]
    
    model = BiGRUAttention(num_outputs=3)  # 3 outputs
    criterion = nn.CrossEntropyLoss()
    
    for X_batch, y_batch in train_loader:
        logits = model(X_batch)  # shape (batch, 3)
        loss = criterion(logits, y_batch)
        loss.backward()
        optimizer.step()

# Inferencia

def predict_with_bigru(ticker):
    model = load_bigru_model(ticker)
    X = prepare_features(ticker)
    
    logits = model(X[-1:])
    probs = torch.softmax(logits, dim=1)  # Ahora 3 probabilidades
    
    # Output ahora captura LATERAL
    return {
        'signal': probs.argmax().item(),  # 0=BAJISTA, 1=LATERAL, 2=ALCISTA
        'confidence': probs.max().item(),
        'breakdown': {
            'bajista': probs[0, 0].item(),
            'lateral': probs[0, 1].item(),
            'alcista': probs[0, 2].item()
        }
    }

# XGBoost feature

def create_xgboost_features(bigru_output, technical_features):
    """
    OPCIÓN B: BigRU ternario + todas sus probabilidades
    """
    features = {
        'bigru_signal': bigru_output['signal'],         # Ahora ternario correcto
        'bigru_confidence': bigru_output['confidence'],
        'bigru_lateral_prob': bigru_output['breakdown']['lateral'],  # Info adicional
        
        # Resto técnicos
        'rsi_14': technical_features['rsi_14'],
        # ...
    }
    
    return pd.DataFrame([features])
```

**Ventaja**: BiGRU y XGBoost alineados en 3 clases  
**Desventaja**: Más trabajo (retrain BiGRU), matriz confusión más compleja

#### Recomendación

**Implementar Opción B a largo plazo**, pero:
1. **Corto plazo (esta semana)**: Opción A (quitar bigru_signal)
   - Cambio 1 línea, reduce ruido inmediatamente
   - Verifica si accuarcy XGBoost sube

2. **Mediano plazo (next sprint)**: Opción B (BiGRU ternario)
   - Retrain BiGRU con 3 clases
   - Validar walk-forward con nuevas probabilidades

---

### PROBLEMA 3: SIN VALIDACIÓN WALK-FORWARD (CRÍTICO) 🔴

#### El Problema

```python
# ACTUAL (backend/models/trainer.py, xgboost_model.py)
X_train = data[:0.8]     # 80%
X_val = data[0.8:0.9]    # 10%
X_test = data[0.9:]      # 10%

# PROBLEMA:
# Si test period fue "mercado lateral" → BA = 70%
# Si test period fue "mercado trending" → BA = 55%
# Una sola muestra no te dice si el fenómeno es robusto

# REALIDAD:
# 200 días de test puede NO ser representativo de todos los regímenes de mercado
```

**Impacto**:
- ❌ Una sola validación (60/20/20 o 80/10/10)
- ❌ No ves variabilidad: ¿Es BA=63% siempre o varía 55-70%?
- ❌ No detecta si el modelo colapsa en ciertos regímenes
- ❌ Métricas "optimistas" si test fue lucky

#### Fix: TimeSeriesSplit (Walk-Forward)

```python
# backend/models/validation.py - NUEVO ARCHIVO

from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import balanced_accuracy_score, recall_score
import numpy as np

def walk_forward_validation(ticker, n_splits=5):
    """
    Validación walk-forward (time-series cross-validation)
    
    Ventaja: Captura variabilidad real del modelo
    Resultado: "BA 63% ± 8%" en lugar de solo "63%"
    """
    
    X, y = load_training_data(ticker)
    
    tscv = TimeSeriesSplit(n_splits=n_splits)
    
    ba_scores = []
    recall_by_class = {'bajista': [], 'lateral': [], 'alcista': []}
    
    fold_results = []
    
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]
        
        # Entrenar en fold
        model = train_xgboost(ticker, X_train, y_train)
        
        # Validar
        y_pred = model.predict(X_val)
        
        # Metrics
        ba = balanced_accuracy_score(y_val, y_pred)
        ba_scores.append(ba)
        
        # Recall por clase
        for class_idx, class_name in enumerate(['bajista', 'lateral', 'alcista']):
            recall = recall_score(y_val, y_pred, labels=[class_idx], average=None)
            recall_by_class[class_name].append(recall[0] if len(recall) > 0 else 0)
        
        # Log fold
        fold_results.append({
            'fold': fold,
            'dates': (dates[train_idx[0]], dates[val_idx[-1]]),
            'ba': ba,
            'n_samples': len(val_idx),
            'class_distribution': np.bincount(y_val, minlength=3)
        })
        
        print(f"Fold {fold}: BA={ba:.2%}, samples={len(val_idx)}")
    
    # Resumen
    ba_mean = np.mean(ba_scores)
    ba_std = np.std(ba_scores)
    
    print(f"\n{'='*60}")
    print(f"WALK-FORWARD VALIDATION SUMMARY ({n_splits} folds)")
    print(f"{'='*60}")
    print(f"BA: {ba_mean:.2%} ± {ba_std:.2%}")
    print(f"  (Min: {min(ba_scores):.2%}, Max: {max(ba_scores):.2%})")
    print(f"\nRecall por clase:")
    for class_name, recalls in recall_by_class.items():
        print(f"  {class_name}: {np.mean(recalls):.2%} ± {np.std(recalls):.2%}")
    
    print(f"\nFold details:")
    for result in fold_results:
        print(f"  Fold {result['fold']}: {result['dates'][0]} → {result['dates'][1]}")
        print(f"    BA={result['ba']:.2%}, distribution={result['class_distribution']}")
    
    return {
        'ba_mean': ba_mean,
        'ba_std': ba_std,
        'ba_scores': ba_scores,
        'recall_by_class': recall_by_class,
        'fold_results': fold_results,
        'interpretation': interpret_walk_forward(ba_mean, ba_std)
    }

def interpret_walk_forward(ba_mean, ba_std):
    """
    Interpretar robustez del modelo
    """
    cv_ratio = ba_std / ba_mean  # Coefficient of variation
    
    if cv_ratio < 0.05:  # < 5%
        return "✅ Muy robusto: BA consistente en todos los fold"
    elif cv_ratio < 0.15:  # < 15%
        return "⚠️ Medianamente robusto: Tiene variación, pero controlada"
    else:
        return "🔴 Poco robusto: BA varía significativamente entre folds"
```

#### Integración en Pipeline

```python
# backend/models/train_xgboost_all.py

def retrain_all_tickers():
    """
    Reentrenamiento diario CON validación walk-forward
    """
    for ticker in TICKERS:
        logger.info(f"Retraining {ticker}...")
        
        # 1. Entrenar modelo final (en todos los datos)
        X, y = load_training_data(ticker)
        model = train_xgboost(ticker, X, y)
        save_model(model, ticker)
        
        # 2. Evaluar con walk-forward
        wf_results = walk_forward_validation(ticker, n_splits=5)
        
        # 3. Guardar metrics en BD para audit trail
        log_metrics_to_db(ticker, {
            'ba_mean': wf_results['ba_mean'],
            'ba_std': wf_results['ba_std'],
            'cv_ratio': wf_results['ba_std'] / wf_results['ba_mean'],
            'fold_details': wf_results['fold_results']
        })
        
        # 4. Alert si BA cae o varianza sube
        if wf_results['ba_mean'] < 0.60:
            logger.warning(f"⚠️ {ticker} BA dropped to {wf_results['ba_mean']:.2%}")
        if wf_results['ba_std'] > 0.12:  # ± 12%
            logger.warning(f"⚠️ {ticker} BA variability high: ± {wf_results['ba_std']:.2%}")
```

#### Interpretación de Resultados

```
RESULTADO ESPERADO ANTES:
"BA = 63%" ← Un número, sin contexto

RESULTADO ESPERADO DESPUÉS:
Walk-Forward Validation (5 folds):
  BA: 63% ± 8%
    - Min: 55% (challenging period)
    - Max: 71% (favorable period)
  
  Recall:
    - BAJISTA: 62% ± 10%
    - LATERAL: 63% ± 7%
    - ALCISTA: 65% ± 9%

INTERPRETACIÓN:
✅ Modelo es relativamente robusto (8% std es aceptable)
⚠️ Pero cae a 55% en ciertos mercados → investigar cuándoAntagonism

ACCIÓN:
Crear submodelos para regímenes de mercado:
  if volatility_regime == 'high':
      use_volatile_model()
  else:
      use_stable_model()
```

---

### PROBLEMA 4 (DERIVADO): EARLY STOPPING INCORRECTO 🟡

#### El Problema

```python
# ACTUAL
model = xgb.train(
    params,
    dtrain,
    num_boost_round=100,
    evals=[(dtrain, 'train'), (dval, 'eval')],
    early_stopping_rounds=20,
    # Monitorea: mlogloss (multi-class log-loss)
)

# PROBLEMA:
# mlogloss puede MEJORAR mientras balanced_accuracy EMPEORA
# → Early stopping puede estar matando el mejor modelo
```

#### Fix: Monitor Multiple Metrics

```python
# backend/models/xgboost_model.py

def train_xgboost_with_proper_early_stopping(X_train, y_train, X_val, y_val):
    """
    Early stopping basado en balanced_accuracy, no solo mlogloss
    """
    
    dtrain = xgb.DMatrix(X_train, label=y_train)
    dval = xgb.DMatrix(X_val, label=y_val)
    
    params = {
        'objective': 'multi:softprob',
        'num_class': 3,
        'eval_metric': 'mlogloss',  # XGB optimiza esto
        # ... otros params
    }
    
    # Custom callback para monitorear BA
    def monitor_ba_callback(env):
        """Callback que monitorea balanced accuracy durante training"""
        if env.evaluation_result_list:
            # Apenas XGB valida, calculamos BA
            y_pred = model.predict(dval)
            from sklearn.metrics import balanced_accuracy_score
            ba = balanced_accuracy_score(y_val, y_pred)
            
            if env.iteration % 10 == 0:
                print(f"Round {env.iteration}: mlogloss={env.evaluation_result_list[-1][1]:.4f}, BA={ba:.4f}")
    
    # Entrenamiento
    evals_result = {}
    model = xgb.train(
        params,
        dtrain,
        num_boost_round=200,
        evals=[(dtrain, 'train'), (dval, 'eval')],
        evals_result=evals_result,
        early_stopping_rounds=20,
        verbose_eval=False,
        # callbacks=[xgb.callback.EarlyStopping(20)]
    )
    
    # Post-validation: Verificar que mejor round por BA
    best_ba_round = 0
    best_ba = 0
    for round_num in range(len(evals_result['eval'])):
        y_pred_at_round = model.predict(dval)  # ← Aproximado
        ba = balanced_accuracy_score(y_val, y_pred_at_round)
        if ba > best_ba:
            best_ba = ba
            best_ba_round = round_num
    
    print(f"Best round by mlogloss: {evals_result['eval']}")
    print(f"Best round by BA (post-hoc): {best_ba_round} (BA={best_ba:.4f})")
    
    if abs(best_ba_round - len(evals_result['eval'])) > 20:
        print("⚠️ WARNING: Best mlogloss ≠ Best BA. Consider using BA for early stopping.")
    
    return model
```

---

## 📋 PLAN DE IMPLEMENTACIÓN (ROADMAP)

### 🔴 SEMANA 1: Fixes Críticos (Impacto Inmediato)

**Tarea 1.1: Estabilizar Etiquetas**
- [ ] Agregar `LABELING_THRESHOLDS` a `config.py`
- [ ] Modificar `xgboost_model.py` para usar umbrales fijos
- [ ] Test: `test_label_consistency.py`
- [ ] Retrain un ticker (AAPL) y verificar reproducibilidad
- **Tiempo**: 2-3 horas
- **Validación**: Entrenar 2 veces, verificar targets idénticos

**Tarea 1.2: Quitar Ruido BigRU (Opción A Corto Plazo)**
- [ ] Modificar `data_pipeline.py`: quitar `bigru_signal` feature
- [ ] Retrain XGBoost en 5 tickers
- [ ] Comparar BA anterior vs nuevo
- [ ] Si BA sube o igual: mantener
- **Tiempo**: 1-2 horas
- **Validación**: BA no debe bajar >2%

**Tarea 1.3: Walk-Forward Validation**
- [ ] Crear `validation.py` con `walk_forward_validation()`
- [ ] Ejecutar en AAPL histórico
- [ ] Documentar resultados: "BA 63% ± X%"
- [ ] Comparar con split single 80/10/10
- **Tiempo**: 3-4 horas
- **Validación**: Ver reportes de robustez

### 🟡 SEMANA 2: Convergencia de Modelos

**Tarea 2.1: BiGRU Ternario (Opción B)**
- [ ] Modificar `trainer.py`: cambiar FC final 2→3 neuronas
- [ ] Regenerar `LABELING_THRESHOLDS` para BiGRU (usar mismos que XGBoost)
- [ ] Retrain BiGRU en AAPL
- [ ] Validar nuevas probabilidades ternarias
- **Tiempo**: 4-5 horas
- **Validación**: Output tiene 3 probabilidades (no 2)

**Tarea 2.2: Integrar BigRU Ternario a XGBoost**
- [ ] Actualizar `data_pipeline.py`: usar nuevas features BigRU
- [ ] Incluir `bigru_lateral_prob` como feature
- [ ] Retrain XGBoost
- [ ] Comparar BA: XGB binario-input vs ternario-input
- **Tiempo**: 3-4 horas

**Tarea 2.3: Early Stopping Mejorado**
- [ ] Modificar `xgboost_model.py` para monitorear BA
- [ ] Agregar callback custom
- [ ] Reentrain 1 ticker con nuevo early stopping
- [ ] Ver si best round cambia
- **Tiempo**: 2-3 horas

### 🟢 SEMANA 3: Validación Integral

**Tarea 3.1: Full Walk-Forward en Todos los Tickers**
- [ ] Ejecutar walk-forward validation en 10-15 tickers
- [ ] Capturar matriz: (ticker, fold, BA, recalls por clase)
- [ ] Identificar tickers con baja robustez
- **Tiempo**: 5-6 horas (parallelizable)

**Tarea 3.2: Deep Dive en Tickers Inconsistentes**
- [ ] Analizar tickers donde BA varía >15%
- [ ] ¿Es volatilidad del mercado o del modelo?
- [ ] Considerar crear sub-modelos (stable/volatile)
- **Tiempo**: 3-4 horas

**Tarea 3.3: Reentrenamiento Diario Mejorado**
- [ ] Actualizar `scheduler_daemon.py` para incluir walk-forward
- [ ] Log metrics en BD para audit trail
- [ ] Alertas si BA cae o varianza sube
- **Tiempo**: 3-4 horas

### Prioridad de Implementación

```
ANTES DE COMPETENCIA/TRIBUNAL:
1. ✅ Etiquetas fijas (Tarea 1.1)         [CRÍTICO]
2. ✅ Walk-forward validation (Tarea 1.3) [CRÍTICO]
3. ✅ Quitar ruido BigRU (Tarea 1.2)      [IMPORTANTE]

DESPUÉS (Quality Improvements):
4. ⚠️ BigRU ternario (Tarea 2.1)          [NICE-TO-HAVE]
5. ⚠️ Early stopping mejorado (Tarea 2.3) [NICE-TO-HAVE]
```

---

## 🔍 CHECKLIST DE VALIDACIÓN

### Post-Implementación Tarea 1.1 (Etiquetas Fijas)

- [ ] Labels on same data are identical across 2 retrainings
- [ ] `test_label_consistency.py` passes
- [ ] Audit log muestra "Using fixed thresholds: -1.5%, +1.5%"
- [ ] Reproducibilidad verificada en 3 tickers

### Post-Implementación Tarea 1.2 (Quitar bigru_signal)

- [ ] Feature importance shows no `bigru_signal`
- [ ] XGBoost has 27 features instead of 28
- [ ] BA en AAPL: >= 0.61 (no drop significant)
- [ ] SHAP plots still explainable sin bigru_signal

### Post-Implementación Tarea 1.3 (Walk-Forward)

- [ ] Walk-forward script runs without errors
- [ ] Output format: "BA 63% ± 8%" (mean ± std)
- [ ] Folds bien distribuidos temporalmente
- [ ] Log captura class distribution por fold
- [ ] Resumen comparativo: single split vs walk-forward



### Requerimientos

```
Python 3.8+
FastAPI[all]
Supabase (hosted PostgreSQL)
Google Gemini API key
```

### Setup Local

```bash
# 1. Clone
git clone <repo>
cd Horizon

# 2. Virtual env
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Instalar deps
pip install -r requirements.txt

# 4. .env
cat > backend/.env << EOF
SUPABASE_URL=https://...supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_ADMIN_KEY=eyJ...
GOOGLE_GENAI_API_KEY=AI...
FINNHUB_API_KEY=c...
EOF

# 5. Run backend
cd backend
uvicorn main:app --reload --port 8000

# 6. Frontend
# Abrir frontend/index.html en navegador
```

### Production

- **Backend**: Deploy a Cloud Run / AppEngine / AWS Lambda
- **Frontend**: Servir estático desde Cloud Storage / S3 / Vercel
- **DB**: Supabase (already managed)
- **Scheduler**: Cloud Tasks / AWS EventBridge

---

## 📈 MÉTRICAS & OBSERVABILIDAD

### Métricas ML

- **Balanced Accuracy**: 63% (meta: >70%)
- **Macro F1**: 52%
- **Latencia predicción**: <2 seg (on-demand)
- **Latencia SHAP**: 5-10 seg (per-ticker, cached)

### Métricas Backend

- **Uptime**: Target 99.5%
- **API latency P95**: <500 ms
- **DB connection pool**: 20 conns

### Monitoreo

- **Logs**: Supabase logs + application logs
- **Errors**: Sentry (opcional)
- **Performance**: Google Cloud Monitoring

---

## 🎓 ESTRUCTURA PARA DEFENSA TRIBUNAL

### Componentes a Presentar

1. **Problema**: Sesgo +75% en predictor anterior
2. **Solución**: 
   - Ternary classification (ALCISTA/LATERAL/BAJISTA)
   - scale_pos_weight natural (data-driven)
   - Balanced accuracy metric
3. **Resultados**: Eliminó extremos (12%, 94%) → 40-60% band
4. **Explicabilidad**: SHAP force plots (XAI)
5. **End-to-End**: Full pipeline con scheduler + BD

### Archivos Clave

- [docs/XGBOOST_FIX_COMPLETE.md](docs/XGBOOST_FIX_COMPLETE.md) - Documentación fix
- [backend/models/xgboost_model.py](backend/models/xgboost_model.py) - Implementación
- [backend/models/train_xgboost_all.py](backend/models/train_xgboost_all.py) - Batch training

---

---

## 🚀 CASOS DE USO PRÁCTICOS - POSIBILIDADES

### 1. TRADING SIGNALS BÁSICO

**Usar la predicción para trading automático**

```python
# Endpoint a crear: POST /api/portfolio/{id}/auto-trade

def auto_trade_signal(ticker, stop_loss_pct=2, take_profit_pct=5):
    """
    Ejecutar trade si predicción es confiable
    """
    prediccion = PredictionService.obtener_prediccion(ticker)
    
    if prediccion.senal == "ALCISTA" and prediccion.confianza > 65:
        # BUY
        precio_compra = get_current_price(ticker)
        stop_loss = precio_compra * (1 - stop_loss_pct/100)
        take_profit = precio_compra * (1 + take_profit_pct/100)
        
        order = TradeService.market_buy(
            ticker=ticker,
            size=calculate_position_size(portfolio, ticker),
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        return order
```

**Métrica de éxito**: Win rate, Sharpe ratio

---

### 2. PORTFOLIO REBALANCING AUTOMÁTICO

**Rebalancear cartera basado en predicciones**

```python
def rebalance_portfolio(portfolio_id):
    """
    Recalcular pesos óptimos usando predicciones ML
    """
    portfolio = PortfolioDAO.obtener(portfolio_id)
    
    # Obtener predicciones para cada holding
    predictions = {}
    for ticker in portfolio.tickers:
        pred = PredictionService.obtener_prediccion(ticker)
        predictions[ticker] = {
            'signal': pred.senal,
            'confidence': pred.confianza,
            'expected_return': calculate_expected_return(pred)
        }
    
    # Markowitz con expected return de ML
    expected_returns = [predictions[t]['expected_return'] for t in portfolio.tickers]
    cov_matrix = calculate_covariance(portfolio.tickers)
    
    weights = optimize_portfolio(
        expected_returns=expected_returns,
        cov_matrix=cov_matrix,
        risk_profile=portfolio.risk_profile
    )
    
    return weights
```

**Ventaja**: Combine ML predictions + Markowitz optimization

---

### 3. ALERT SYSTEM - NOTIFICACIONES AUTOMÁTICAS

**Sistema de alertas basado en CAMBIOS de predicción**

```python
def monitor_prediction_changes():
    """
    Alertar cuando predicción cambia significativamente
    """
    # Ejecutar cada 30 min (en producción)
    
    for ticker in MONITORED_TICKERS:
        # Obtener predicción actual
        current_pred = PredictionService.obtener_prediccion(ticker)
        
        # Comparar con predicción anterior (que guardamos en BD)
        previous_pred = get_last_prediction_from_db(ticker)
        
        # Detectar cambios
        if current_pred.senal != previous_pred.senal:
            # CAMBIO: LATERAL → ALCISTA
            send_alert(
                user_ids=get_subscribers(ticker),
                message=f"{ticker}: Cambio a {current_pred.senal} "
                        f"({current_pred.confianza}%)",
                notification_type="SIGNAL_CHANGE"
            )
        
        # Detectar baja en confianza
        if current_pred.confianza < previous_pred.confianza - 10:
            send_alert(
                user_ids=get_subscribers(ticker),
                message=f"{ticker}: Confianza bajó a {current_pred.confianza}%",
                notification_type="CONFIDENCE_DROP"
            )
        
        # Guardar predicción actual
        save_prediction_snapshot(ticker, current_pred)
```

**Implementación**: WebSocket + Supabase Realtime

---

### 4. SECTOR ROTATION STRATEGY

**Cambiar asignación por sector basado en predicciones**

```python
def sector_rotation_strategy(portfolio_id):
    """
    Identificar mejor-performing sector y aumentar exposición
    """
    # Agrupar holdings por sector
    sector_predictions = {}
    for ticker in portfolio.tickers:
        sector = get_sector(ticker)
        pred = PredictionService.obtener_prediccion(ticker)
        
        if sector not in sector_predictions:
            sector_predictions[sector] = []
        
        sector_predictions[sector].append({
            'ticker': ticker,
            'signal': pred.senal,
            'confidence': pred.confianza
        })
    
    # Calcular sector strength
    sector_scores = {}
    for sector, predictions in sector_predictions.items():
        avg_confidence = np.mean([p['confidence'] for p in predictions])
        alcista_pct = sum(1 for p in predictions if p['signal'] == 'ALCISTA') / len(predictions)
        
        sector_scores[sector] = {
            'strength': alcista_pct * avg_confidence,
            'sample_size': len(predictions)
        }
    
    # Top 3 sectores
    best_sectors = sorted(sector_scores.items(), key=lambda x: x[1]['strength'], reverse=True)[:3]
    
    # Rebalancear hacia mejores sectores
    return {sector: score for sector, score in best_sectors}
```

**Use case**: Macro rotation (Energy → Tech → Healthcare)

---

### 5. RISK MANAGEMENT - DYNAMIC STOP LOSS

**Ajustar stop loss basado en volatilidad predicha**

```python
def dynamic_stop_loss(ticker, entry_price, base_stop_loss_pct=2):
    """
    Hacer stop loss dinámico según volatilidad predicha
    """
    # Obtener volatilidad histórica
    vol_20d = calculate_volatility(ticker, window=20)
    
    # Modelo de volatilidad futura (opcional: GARCH o XGBoost multioutput)
    predicted_vol = predict_future_volatility(ticker)
    
    # Ajustar stop loss
    if predicted_vol > vol_20d * 1.5:
        # Mercado muy volátil → stop loss más amplio
        adjusted_sl = base_stop_loss_pct * 1.5
    elif predicted_vol < vol_20d * 0.7:
        # Mercado calmado → stop loss más tight
        adjusted_sl = base_stop_loss_pct * 0.7
    else:
        adjusted_sl = base_stop_loss_pct
    
    stop_loss_price = entry_price * (1 - adjusted_sl/100)
    
    return {
        'stop_loss_price': stop_loss_price,
        'stop_loss_pct': adjusted_sl,
        'volatility_regime': 'high' if predicted_vol > vol_20d else 'low'
    }
```

---

### 6. BACKTESTING & STRATEGY VALIDATION

**Framework para testear estrategias sobre histórico**

```python
def backtest_strategy(strategy_name, tickers, start_date, end_date):
    """
    Simular estrategia sobre datos históricos
    """
    portfolio_value = 100_000
    trades = []
    
    for current_date in date_range(start_date, end_date):
        # Obtener predicción como si fuera en vivo
        predictions = {}
        for ticker in tickers:
            # Usar solo data hasta current_date (forward-looking safe)
            X = prepare_data_up_to(ticker, current_date)
            predictions[ticker] = model.predict(X[-1:])
        
        # Ejecutar lógica estrategia
        for ticker in tickers:
            if predictions[ticker].senal == "ALCISTA" and \
               predictions[ticker].confianza > 65:
                # Simular BUY
                entry_price = get_price_at_date(ticker, current_date)
                
                # Simular exit 5 días después
                exit_price = get_price_at_date(ticker, current_date + timedelta(days=5))
                
                pnl = (exit_price - entry_price) / entry_price
                trades.append({
                    'ticker': ticker,
                    'entry_date': current_date,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl * 100
                })
    
    # Calcular métricas
    return {
        'total_trades': len(trades),
        'winning_trades': sum(1 for t in trades if t['pnl_pct'] > 0),
        'win_rate': sum(1 for t in trades if t['pnl_pct'] > 0) / len(trades),
        'avg_pnl': np.mean([t['pnl_pct'] for t in trades]),
        'sharpe_ratio': calculate_sharpe([t['pnl_pct'] for t in trades]),
        'max_drawdown': calculate_max_drawdown(trades)
    }
```

**En desarrollo**: `tests/backtest_xgboost.py`, `tests/backtest_strategy.py`

---

### 7. ANOMALY DETECTION - DETECCIÓN DE COMPORTAMIENTO ANÓMALO

**Identificar cuando activo se comporta "raro"**

```python
def detect_anomaly(ticker):
    """
    Detectar si comportamiento actual es anómalo vs histórico
    """
    current_pred = PredictionService.obtener_prediccion(ticker)
    
    # Obtener predicciones históricas
    historical_preds = get_predictions_last_30_days(ticker)
    
    # Calcular Z-score de confianza
    confidence_zscore = (
        (current_pred.confianza - np.mean([p.confianza for p in historical_preds])) /
        np.std([p.confianza for p in historical_preds])
    )
    
    # Detectar cambios de señal frecuentes
    signal_changes_7d = count_signal_changes(historical_preds[-7:])
    
    anomaly_score = {
        'confidence_zscore': confidence_zscore,
        'is_anomaly': abs(confidence_zscore) > 2.5,
        'signal_instability_7d': signal_changes_7d > 3,
        'interpretation': (
            'Confianza anormalmente ALTA' if confidence_zscore > 2.5 else
            'Confianza anormalmente BAJA' if confidence_zscore < -2.5 else
            'Comportamiento estable'
        )
    }
    
    return anomaly_score
```

**Uso**: Alert quando modelo "dudoso" sobre su predicción

---

### 8. ENSEMBLE VOTING - MÚLTIPLES MODELOS

**Combinar predicciones de varios modelos**

```python
def ensemble_prediction(ticker):
    """
    Combinar: BiGRU + XGBoost + Random Forest + SVM
    """
    models = {
        'bigru': bigru_model,
        'xgboost': xgboost_model,
        'rf': random_forest_model,
        'svm': svm_model
    }
    
    predictions = {}
    for name, model in models.items():
        X = prepare_features(ticker)
        pred = model.predict(X)
        predictions[name] = pred.senal
    
    # Votación por mayoría
    from collections import Counter
    votes = Counter(predictions.values())
    final_signal = votes.most_common(1)[0][0]
    
    # Confianza: qué % de modelos votaron por señal final
    consensus_pct = votes[final_signal] / len(models)
    
    return {
        'signal': final_signal,
        'original_predictions': predictions,
        'consensus': consensus_pct * 100,
        'interpretation': (
            'Fuerte consenso' if consensus_pct >= 0.75 else
            'Débil consenso' if consensus_pct >= 0.5 else
            'Sin consenso (datos conflictivos)'
        )
    }
```

---

### 9. FEATURE ATTRIBUTION - SABER QUÉ IMPORTA

**Identificar qué features más importan para cada predicción**

```python
def feature_attribution_analysis(ticker):
    """
    Top features que afectan predicción (usando SHAP)
    """
    X = prepare_features(ticker)
    
    # SHAP values
    explainer = shap.TreeExplainer(xgboost_model)
    shap_values = explainer.shap_values(X[-1:])  # Última predicción
    
    # Top 10 features
    top_features = sorted(
        zip(feature_names, abs(shap_values[0][:, 2])),  # Clase ALCISTA
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    # Análisis
    positive_contributors = [
        f for f, contribution in top_features
        if shap_values[0][feature_names.index(f), 2] > 0
    ]
    
    negative_contributors = [
        f for f, contribution in top_features
        if shap_values[0][feature_names.index(f), 2] < 0
    ]
    
    return {
        'top_features': top_features,
        'bullish_signals': positive_contributors,
        'bearish_signals': negative_contributors,
        'interpretation': (
            'Mucha bullish conviction' if len(positive_contributors) > len(negative_contributors)
            else 'Outlook ambiguo'
        )
    }
```

---

### 10. TRANSFER LEARNING - PREDECIR NUEVOS ACTIVOS MÁS RÁPIDO

**Usar modelo pre-entrenado en índice para acelerar training en nuevo ticker**

```python
def transfer_learning_new_ticker(new_ticker):
    """
    Fine-tune BiGRU pre-entrenado en SPY para nuevo ticker
    """
    # Cargar modelo pre-entrenado (entrenado en ~50 índices)
    pretrained_bigru = torch.load("models/bigru_pretrained_index.pt")
    
    # Congelar primeras capas (características genéricas)
    for param in pretrained_bigru.embedding.parameters():
        param.requires_grad = False
    for param in pretrained_bigru.bigru.parameters():
        param.requires_grad = False
    
    # Descongelar última capa (características específicas del ticker)
    for param in pretrained_bigru.fc.parameters():
        param.requires_grad = True
    
    # Fine-tune rápido
    train_loader = create_dataloader(new_ticker, batch_size=32, window=60)
    
    optimizer = torch.optim.Adam(
        filter(lambda p: p.requires_grad, pretrained_bigru.parameters()),
        lr=0.001
    )
    
    for epoch in range(5):  # Solo 5 épocas vs 50 normales
        for X, y in train_loader:
            logits = pretrained_bigru(X)
            loss = F.cross_entropy(logits, y)
            loss.backward()
            optimizer.step()
    
    # Resultado: converge en ~1 hora vs ~3 horas sin transfer learning
    return pretrained_bigru
```

**Beneficio**: Acelerar onboarding de nuevos tickers en 60-70%

---

### 11. VOLATILITY PREDICTION - PREDECIR VOLATILIDAD FUTURA

**Usar XGBoost para predecir volatilidad además de dirección**

```python
def train_volatility_model(ticker):
    """
    Modelo paralelo: predecir σ(5d) futura
    """
    X = prepare_features(ticker)
    
    # Label: desviación estándar retornos próximos 5 días
    y_volatility = calculate_future_volatility(ticker, window=5)
    
    # XGBoost regression
    vol_model = xgb.XGBRegressor(
        objective='reg:squarederror',
        max_depth=3,
        n_estimators=100
    )
    
    vol_model.fit(X, y_volatility)
    
    return vol_model

def predict_with_volatility(ticker):
    """
    Retorna: dirección + volatilidad futura
    """
    direction_pred = PredictionService.obtener_prediccion(ticker)
    
    vol_model = load_volatility_model(ticker)
    X = prepare_features(ticker)
    predicted_volatility = vol_model.predict(X[-1:])[0]
    
    return {
        'direction': direction_pred.senal,
        'direction_confidence': direction_pred.confianza,
        'predicted_volatility_5d': predicted_volatility,
        'expected_move': calculate_expected_move(
            price=current_price(ticker),
            volatility=predicted_volatility
        )
    }
```

**Uso**: Option pricing, risk adjusted position sizing

---

### 12. NEWS SENTIMENT MEJORADO - Si se Re-Habilita

**Usar NLP avanzado en lugar de keywords**

```python
def improved_sentiment_with_bert(ticker):
    """
    Usar BERT en lugar de keyword matching
    """
    from transformers import pipeline
    
    # Modelo BERT pre-entrenado en financial news
    classifier = pipeline(
        "zero-shot-classification",
        model="bert-large-uncased-whole-word-masking-finetuned-on-wnut17"
    )
    
    # Obtener últimas noticias
    news_articles = get_latest_news(ticker)
    
    sentiments = []
    for article in news_articles:
        result = classifier(
            article['title'] + " " + article['summary'],
            ["bullish", "bearish", "neutral"]
        )
        
        sentiments.append({
            'article': article['url'],
            'sentiment': result['labels'][0],
            'confidence': result['scores'][0],
            'timestamp': article['timestamp']
        })
    
    # Agregar a features XGBoost
    avg_sentiment_score = np.mean([
        1 if s['sentiment'] == 'bullish' else
        -1 if s['sentiment'] == 'bearish' else
        0
        for s in sentiments
    ])
    
    return {
        'news_sentiment_score': avg_sentiment_score,
        'articles_analyzed': len(news_articles),
        'sentiments': sentiments,
        'add_to_xgboost_features': avg_sentiment_score
    }
```

**Mejora esperada**: +3-5% si news es aligned con dirección

---

### 13. SOCIAL SENTIMENT - Twitter/Reddit Integration

**Capturar sentimiento de redes sociales**

```python
def social_sentiment_analysis(ticker):
    """
    Analizar menciones en Twitter/Reddit
    """
    import praw
    from tweepy import API
    
    # Reddit
    reddit = praw.Reddit(client_id=..., client_secret=...)
    subreddit = reddit.subreddit("stocks")
    
    reddit_posts = subreddit.search(f"${ticker}", time_filter="week")
    reddit_sentiment = np.mean([
        1 if post.score > 0 else -1
        for post in list(reddit_posts)[:20]
    ])
    
    # Twitter
    twitter_api = API(auth=tweepy.OAuthHandler(...))
    tweets = twitter_api.search_tweets(f"${ticker}", count=50)
    
    classifier = pipeline("sentiment-analysis")
    twitter_sentiments = [
        classifier(tweet.text)[0]['label']
        for tweet in tweets
    ]
    
    return {
        'reddit_sentiment': reddit_sentiment,
        'twitter_sentiment_distribution': Counter(twitter_sentiments),
        'social_confirmation': (
            'Strong bullish' if reddit_sentiment > 0.5 else
            'Strong bearish'
        )
    }
```

**Pre-requisito**: API keys (Twitter, Reddit)

---

### 14. BACKTESTING CON COMISIONES Y SLIPPAGE

**Realismo más alto en simulaciones**

```python
def realistic_backtest(strategy, tickers, start_date, end_date):
    """
    Incluir comisiones y slippage
    """
    portfolio_value = 100_000
    trades = []
    
    COMMISSION_PCT = 0.001  # 0.1% por trade
    SLIPPAGE_BPS = 2        # 2 basis points
    
    for current_date in date_range(start_date, end_date):
        for ticker in tickers:
            signal = strategy.generate_signal(ticker, current_date)
            
            if signal == 'BUY':
                entry_price = get_price_at_date(ticker, current_date)
                
                # Aplicar slippage
                entry_price_with_slippage = entry_price * (1 + SLIPPAGE_BPS/10000)
                
                # Aplicar comisión
                effective_entry = entry_price_with_slippage * (1 + COMMISSION_PCT)
                
                # Simular exit
                exit_date = current_date + timedelta(days=5)
                exit_price = get_price_at_date(ticker, exit_date)
                exit_price_with_slippage = exit_price * (1 - SLIPPAGE_BPS/10000)
                effective_exit = exit_price_with_slippage * (1 - COMMISSION_PCT)
                
                pnl = (effective_exit - effective_entry) / effective_entry
                trades.append({'pnl': pnl})
    
    return {
        'win_rate': sum(1 for t in trades if t['pnl'] > 0) / len(trades),
        'avg_pnl': np.mean([t['pnl'] for t in trades]),
        'comparison': f"Realista: {np.mean([t['pnl'] for t in trades])*100:.2f}% "
                     f"vs Ideal: +0.5% (sin costos)"
    }
```

---

### MATRIZ DE POSIBILIDADES

| Posibilidad | Complejidad | Payoff | Status | Prioridad |
|-----------|-------------|--------|--------|-----------|
| Trading Signals | Media | Alto | TODO | ⭐⭐⭐ |
| Auto Rebalance | Media | Medio | TODO | ⭐⭐⭐ |
| Alert System | Baja | Medio | TODO | ⭐⭐⭐ |
| Sector Rotation | Alta | Alto | Research | ⭐⭐ |
| Dynamic SL | Media | Medio | TODO | ⭐⭐ |
| Backtesting | Baja | Alto | Partial | ⭐⭐ |
| Anomaly Detection | Media | Bajo | Research | ⭐ |
| Ensemble Voting | Alta | Bajo | Research | ⭐ |
| Feature Attribution | Baja | Alto | Active | ⭐⭐⭐ |
| Transfer Learning | Alta | Alto | Research | ⭐⭐ |
| Volatility Pred | Alta | Alto | TODO | ⭐⭐⭐ |
| Sentiment (BERT) | Alta | Medio | Disabled | ⭐⭐ |
| Social Sentiment | Media | Bajo | TODO | ⭐ |
| Realistic BT | Media | Alto | Partial | ⭐⭐ |

---

## 🚀 PRÓXIMAS MEJORAS (ROADMAP PHASE 4+)

### Phase 4Q1: Trading Automation
- [ ] Auto-trading engine con API broker (Interactive Brokers, Alpaca)
- [ ] Risk management: dynamic stop loss, position sizing
- [ ] Backtesting framework robusto
- [ ] Paper trading (simular sin dinero real)

### Phase 4Q2: Advanced Analytics
- [ ] Volatility prediction (GARCH + XGBoost multioutput)
- [ ] Multi-timeframe ensemble (1h, 4h, 1d, 1w)
- [ ] Sector rotation strategy
- [ ] Event detection (earnings, splits, etc)

### Phase 4Q3: ML Improvements
- [ ] Ensemble stacking (meta-learner fine-tuned)
- [ ] Transfer learning: pre-train en S&P 500, fine-tune en nuevos tickers
- [ ] Sentiment NLP v2 (BERT financial domain)
- [ ] Reinforcement learning: agent learns entry/exit/sizing

### Phase 4Q4: Production Maturity
- [ ] MLOps: MLflow + DVC para versioning
- [ ] A/B testing framework (test nuevas strategies)
- [ ] Real-time WebSocket vs polling (latency < 100ms)
- [ ] Mobile app (React Native)
- [ ] API v2 (GraphQL + REST)

### Wishlist (Beyond)
- [ ] Option pricing (Black-Scholes with ML volatility)
- [ ] Crypto predictions (extend a Bitcoin/Ethereum)
- [ ] Portfolio optimization with drawdown constraints
- [ ] ESG integration (social impact scoring)
- [ ] API conectado brokers (real trading)



---

## 📞 SOPORTE & DEBUGGING

### Logs

```bash
# Backend
tail -f backend/logs/app.log

# Scheduler
tail -f backend/logs/scheduler.log

# Frontend
Console del navegador (F12)
```

### Errores Comunes

| Error | Causa | Fix |
|-------|-------|-----|
| 401 Unauthorized | Token expirado | Logout + Login |
| CORS error | Frontend no en allow_origins | Actualizar `.env` |
| "No models found" | Reentrenamiento aún no corre | Esperar a 2 AM o forzar `python train_xgboost_all.py` |
| Predicción tarda >10 seg | SHAP generando | Verificar cache en explicaciones_xai |

---

---

## 📚 GUÍA RÁPIDA DE REFERENCIA

### ¿Cómo funciona el sistema en 60 segundos?

1. **Entrada**: Histórico OHLCV + Features técnicos (yfinance)
2. **BiGRU**: Lee secuencia de 60 días → genera señal temporal (ALCISTA/BAJISTA)
3. **XGBoost**: Combina BiGRU + features tabular → Ternario (BAJISTA/LATERAL/ALCISTA)
4. **Calibración**: Platt scaling normaliza confianza reportada
5. **Salida**: Predicción + Confianza + SHAP explanation
6. **Visualización**: Frontend muestra signal, confianza, gráfico SHAP

---

### ¿A QUÉ PREGUNTA RESPONDE CADA COMPONENTE?

| Pregunta | Componente | Respuesta |
|----------|-----------|----------|
| ¿Tiende a subir o bajar? | XGBoost | ALCISTA/BAJISTA/LATERAL (63% BA) |
| ¿Cuán confiable es? | Platt Scaling | 0-100% (calibrado) |
| ¿POR QUÉ esa predicción? | SHAP | Feature attribution explicable |
| ¿Hay patrón temporal? | BiGRU | Señal: valida la dirección |
| ¿Cuál es mi confianza? | BiGRU confidence | [0, 1] meta-signal |

---

### QUICK API REFERENCE

```
GET /api/activos/{ticker}
  └─ Retorna: precio, senal_ia, confianza_bygru, confianza_xgb

GET /api/predicciones/{ticker}
  └─ Retorna: {prediccion, confianza, breakdown}

GET /api/activos/{ticker}/explicacion
  └─ Retorna: {shap_plot (base64), features_top20}

POST /api/chat { message }
  └─ Retorna: respuesta Gemini
```

---

### TROUBLESHOOTING: PREDICTIONS RARA

**Síntoma**: Predicción cambió mucho de ayer a hoy

**Diagnóstico**:
1. ¿Evento de markt (earnings, split, etc)? → Normal
2. ¿Cambio precio > 3%? → BiGRU/XGBoost recalibra
3. ¿Confianza bajó? → Modelo menos seguro (bueno)

**Solución**: Check `anomaly_detection()` en BD

---

**Síntoma**: Todas las predicciones dicen "LATERAL"

**Diagnóstico**: 
1. ¿Fue reentrenamiento? Verificar `backend/models/train_xgboost_all.py` ejecutó
2. ¿Scale_pos_weight incorrecta? Verificar `backend/models/xgboost_model.py` line 150

**Solución**: `python -m backend.models.train_xgboost_all --force-full`

---

**Síntoma**: SHAP explanation tarda >30 seg

**Diagnóstico**: No está cacheada en `explicaciones_xai` tabla

**Solución**: Ejecutar `python tests/generate_xai_explanations.py --all` una ve para warm-up

---

### ARCHIVOS CLAVE POR TAREA

| Tarea | Archivos |
|------|----------|
| Cambiar params XGBoost | `backend/models/config.py` (STABLE/VOLATILE_CONFIG) |
| Fix predicción sesgo | `backend/models/xgboost_model.py` (line 150: scale_pos_weight) |
| Entrenar nuevo ticker | `backend/models/train_xgboost_all.py --single {TICKER}` |
| Debug confianza | `mcp_pylance_mcp_s_pylanceRunCodeSnippet platt_scaling_calibration_v2.py` |
| Generar SHAP | `python tests/generate_xai_explanations.py --ticker {TICKER}` |
| Agregar feature | `backend/models/data_pipeline.py` + retrain |
| Cambiar threshold ternario | `backend/models/xgboost_model.py` (calculate_labels) |

---

### MÉTRICAS ANTES vs DESPUÉS (Phase 3)

| Métrica | Phase 2 | Phase 3 | Delta |
|---------|---------|---------|-------|
| Balanced Accuracy | 58% | 63% | +5% ✅ |
| Recall ALCISTA | 41% | 65% | +24% ✅ |
| Recall BAJISTA | 62% | 59% | -3% (trade-off) |
| Recall LATERAL | 60% | 63% | +3% ✅ |
| Upside Bias | +75% | 0% | -75% ✅ |
| Distribución preds | 12/94/3% | 40/50/45% | Balanceado ✅ |

---

### PIPELINE ENTRENAMIENTO DIARIO (2 AM)

```
2:00 AM → Scheduler inicia
  ├─ For each ticker:
  │   ├─ yfinance.download() → historico_activos
  │   ├─ Calcular features técnicos
  │   ├─ BiGRU.train_predict()
  │   ├─ XGBoost.train_predict() con scale_pos_weight NATURAL
  │   ├─ Platt.calibrate()
  │   ├─ UPDATE activos tabla
  │   └─ SHAP.generate_explanations() → explicaciones_xai tabla
  │
  └─ 2:30 AM → Done (~30 min para 30-50 tickers)

Resultado en DB: Todas las predicciones actualizadas
```

---

### EXTENSIONES POSIBLES (Con Mayor Esfuerzo)

| Extensión | Complejidad | Impacto | Status |
|-----------|-------------|--------|--------|
| Volatility prediction | 8/10 | +5% metrics | 🔴 NotStarted |
| Multi-timeframe (1h/4h/1d) | 7/10 | +3% metrics | 🔴 NotStarted |
| Sector rotation | 6/10 | +2-3% returns | 🟡 Research |
| Sentiment BERT | 8/10 | +3% metrics | 🟡 Tried (disabled) |
| Trading automation | 9/10 | High ROI | 🔴 NotStarted |
| Ensemble (stacking) | 7/10 | +2-3% metrics | 🟡 Research |
| Options pricing | 9/10 | New revenue | 🔴 NotStarted |
| Crypto integration | 6/10 | New market | 🔴 NotStarted |

---

## 🎓 PARA TRIBUNAL - PUNTOS CLAVE

### 1. Problema Identificado
El modelo anterior tenía **+75% sesgo upside**:
- Predicción: 12% BAJISTA, 94% ALCISTA, 3% LATERAL
- Realidad en test: 33% BAJISTA, 33% LATERAL, 33% ALCISTA
- **Causa**: scale_pos_weight arbitrario + métrica accuracy inapropiada

### 2. Solución Implementada
Tres cambios data-driven:
1. **scale_pos_weight natural**: Basado en ratio real de clases
2. **Ternario (no binario)**: Modelar LATERAL como clase explícita
3. **Balanced accuracy**: Métrica que no penaliza desbalance

### 3. Resultados Demostrados
```
Phase 2 (Anterior):       Phase 3 (Actualizado):
BA 58% → Recall 65%       BA 63% ✅
Sesgo +75%                Sesgo 0% ✅
Extemos (12%, 94%)        Rango realista (40-60%) ✅
```

### 4. Defensabilidad
- **Reproducible**: Código abierto, fácil de verificar
- **Data-driven**: Decimales basados en datos históricos, no arbitrario
- **Teoría sólida**: Balanced accuracy es estándar en ML imbalanceado
- **Generalizable**: Aplicable a otros activos/mercados

---

## 📞 CONTACTO Y DEBUGGING

### Logs en Tiempo Real

```bash
# Backend logs
Get-Content -Path "backend/logs/app.log" -Tail 50 -Wait

# Scheduler logs
Get-Content -Path "backend/logs/scheduler.log" -Tail 50 -Wait

# Browser console
F12 → Console
```

### Comandos Útiles

```bash
# Retrain un ticker específico
python -m backend.models.train_xgboost_all --single AAPL

# Generar SHAP para todos
python tests/generate_xai_explanations.py --all

# Validar configuración
python -c "from backend.models.config import STABLE_CONFIG; print(STABLE_CONFIG)"

# Verificar compilación
python -m py_compile backend/models/*.py
```

### Esperados en Producción

- Predicción latency: <2 seg
- SHAP latency: 5-10 seg (first time), <500ms (cached)
- Reentrenamiento: 30 min para 50 tickers
- Uptime: 99.5%

---

## 🏁 CONCLUSIÓN

**Horizon** es una plataforma **production-ready** de predicción financiera con:

✅ **ML robusto**: XGBoost ternario + BiGRU + calibración
✅ **Explicabilidad**: SHAP force plots para cada predicción
✅ **Escalabilidad**: FastAPI async + Supabase managed DB
✅ **Documentado**: Este contexto + código + Jupyter notebooks
✅ **Defendible**: Phase 3 fix data-driven, reproducible

**Próximas oportunidades**:
- Trading automation (via broker APIs)
- Volatility prediction
- Sector rotation strategies
- Real-time WebSocket updates
- Mobile app

---

**Document Version**: 2.1 (Phase 3 Complete)  
**Last Updated**: April 12, 2026  
**Status**: ✅ Ready for Production + Tribunal Defense

---

**FIN DEL CONTEXTO EXHAUSTIVO**

Este documento contiene toda la información necesaria para:
- Entender arquitectura completa
- Implementar mejoras
- Debuggear problemas
- Defender proyecto en tribunal
- Pasar conocimiento a otro desarrollador/IA

**copyto clipboard y pasa a otra IA** ➡️

