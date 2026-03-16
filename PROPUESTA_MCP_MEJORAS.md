# Propuesta: MCPs para Mejorar el Accuracy del Modelo

## Problema Actual

**Accuracy actual: 53.43%** (apenas mejor que el azar del 50%)

**Análisis del problema:**
1. **Sentimiento sin valor**: `sentiment_score` tiene 0.0 de importancia (API con límite)
2. **Features limitadas**: Solo 9 features técnicas básicas
3. **Sin contexto fundamental**: No hay datos de earnings, ratios financieros, volumen institucional
4. **Sin datos macroeconómicos**: No considera tasas de interés, inflación, etc.

## MCPs Recomendados para Mejorar el Modelo

### 1. 🏆 **Alpha Vantage MCP** (ALTA PRIORIDAD)

**Qué aporta:**
- Datos fundamentales: P/E ratio, EPS, dividendos, balance sheets
- Indicadores técnicos adicionales: ADX, CCI, Aroon, Stochastic
- Datos macroeconómicos: GDP, tasas de interés, inflación
- Sentimiento de noticias (alternativa a Finnhub)

**Nuevas features que agregaría:**
- `pe_ratio`: Price-to-Earnings ratio
- `eps`: Earnings Per Share
- `dividend_yield`: Rendimiento de dividendos
- `book_value`: Valor en libros
- `adx`: Average Directional Index (fuerza de tendencia)
- `cci`: Commodity Channel Index
- `stochastic_k`, `stochastic_d`: Osciladores estocásticos
- `gdp_growth`: Crecimiento del PIB
- `interest_rate`: Tasa de interés de referencia
- `inflation_rate`: Tasa de inflación

**Impacto esperado:** +5-10% accuracy

**Instalación:**
```bash
# En .kiro/settings/mcp.json
{
  "mcpServers": {
    "alphavantage": {
      "command": "uvx",
      "args": ["mcp-server-alphavantage"],
      "env": {
        "ALPHAVANTAGE_API_KEY": "tu_api_key_aqui"
      }
    }
  }
}
```

### 2. 📊 **Financial Datasets MCP** (ALTA PRIORIDAD)

**Qué aporta:**
- Datos históricos de alta calidad
- Ratios financieros calculados
- Datos de volumen institucional
- Splits y dividendos ajustados

**Nuevas features:**
- `institutional_ownership`: % de propiedad institucional
- `short_interest`: Interés corto (%)
- `insider_transactions`: Transacciones de insiders
- `analyst_ratings`: Calificaciones de analistas

**Impacto esperado:** +3-5% accuracy

### 3. 🌐 **Yahoo Finance MCP** (MEDIA PRIORIDAD)

**Qué aporta:**
- Datos en tiempo real
- Opciones y derivados
- Datos de mercado global
- Correlaciones entre activos

**Nuevas features:**
- `options_volume`: Volumen de opciones
- `put_call_ratio`: Ratio Put/Call
- `correlation_spy`: Correlación con S&P 500
- `correlation_sector`: Correlación con sector

**Impacto esperado:** +2-4% accuracy

### 4. 📰 **News API MCP** (MEDIA PRIORIDAD)

**Qué aporta:**
- Noticias de múltiples fuentes
- Sin límites estrictos de rate
- Categorización de noticias
- Análisis de sentimiento mejorado

**Nuevas features:**
- `news_sentiment_multi`: Sentimiento de múltiples fuentes
- `news_category`: Categoría de noticias (earnings, M&A, etc.)
- `news_impact_score`: Score de impacto de noticias

**Impacto esperado:** +2-3% accuracy

### 5. 🤖 **OpenAI/Anthropic MCP** (BAJA PRIORIDAD)

**Qué aporta:**
- Análisis de sentimiento avanzado con LLMs
- Resumen de noticias y earnings calls
- Detección de eventos importantes

**Nuevas features:**
- `llm_sentiment`: Sentimiento analizado por LLM
- `event_detection`: Detección de eventos importantes
- `earnings_summary`: Resumen de earnings calls

**Impacto esperado:** +1-2% accuracy (pero costoso)

## Estrategia de Implementación Recomendada

### Fase 1: Quick Wins (1-2 días)

1. **Instalar Alpha Vantage MCP**
   - Obtener API key gratuita
   - Agregar 10 features fundamentales
   - Re-entrenar y medir mejora

2. **Optimizar hiperparámetros actuales**
   - Probar diferentes window_sizes
   - Ajustar dropout y learning_rate
   - Probar más capas en BiGRU

### Fase 2: Mejoras Incrementales (3-5 días)

3. **Instalar Financial Datasets MCP**
   - Agregar datos institucionales
   - Agregar ratios financieros avanzados

4. **Instalar Yahoo Finance MCP**
   - Agregar datos de opciones
   - Agregar correlaciones

### Fase 3: Refinamiento (1 semana)

5. **Feature Engineering Avanzado**
   - Crear features derivadas
   - Interacciones entre features
   - Feature selection con importancia

6. **Ensemble Avanzado**
   - Agregar más modelos (LSTM, Transformer)
   - Stacking de modelos
   - Voting ensemble

## Configuración Propuesta

### Archivo: `.kiro/settings/mcp.json`

```json
{
  "mcpServers": {
    "alphavantage": {
      "command": "uvx",
      "args": ["mcp-server-alphavantage"],
      "env": {
        "ALPHAVANTAGE_API_KEY": "tu_api_key_aqui"
      },
      "disabled": false
    },
    "financial-datasets": {
      "command": "uvx",
      "args": ["mcp-server-financial-datasets"],
      "disabled": false
    },
    "yahoo-finance": {
      "command": "uvx",
      "args": ["mcp-server-yahoo-finance"],
      "disabled": false
    }
  }
}
```

## Nuevas Features Propuestas (Total: ~25-30 features)

### Features Técnicas Actuales (9):
- Close, Volume, RSI, MACD, EMA, Bollinger_PctB, ATR, Log_Return, Volume_Ratio

### Features Fundamentales (Alpha Vantage) (+10):
- PE_Ratio, EPS, Dividend_Yield, Book_Value, ROE, ROA, Debt_to_Equity, Current_Ratio, Quick_Ratio, Profit_Margin

### Features Técnicas Avanzadas (Alpha Vantage) (+5):
- ADX, CCI, Stochastic_K, Stochastic_D, Williams_R

### Features Macroeconómicas (Alpha Vantage) (+3):
- GDP_Growth, Interest_Rate, Inflation_Rate

### Features de Mercado (Yahoo Finance) (+3):
- Options_Volume, Put_Call_Ratio, Correlation_SPY

### Features de Sentimiento Mejoradas (News API) (+2):
- News_Sentiment_Multi, News_Impact_Score

## Accuracy Esperado

**Actual:** 53.43%

**Con Alpha Vantage:** 58-63%

**Con todos los MCPs:** 65-70%

**Con feature engineering:** 70-75%

## Costos

**Alpha Vantage:** Gratuito (500 llamadas/día)

**Financial Datasets:** Gratuito (con límites)

**Yahoo Finance:** Gratuito

**News API:** $29/mes (plan básico)

**Total:** $0-29/mes

## Próximos Pasos Inmediatos

✅ **IMPLEMENTACIÓN COMPLETADA** - Ver `RESUMEN_ALPHA_VANTAGE.md` para detalles

La integración de Alpha Vantage está completa y lista para usar:

1. **Obtén tu API key** de Alpha Vantage (gratis, 500 llamadas/día)
   - Visita: https://www.alphavantage.co/support/#api-key

2. **Configura el MCP server** en `.kiro/settings/mcp.json`
   - Reemplaza `your_api_key_here` con tu API key real

3. **Habilita la flag** en `backend/.env`
   - Cambia `USE_ALPHA_VANTAGE=False` a `USE_ALPHA_VANTAGE=True`

4. **Reinicia Kiro** para conectar el servidor MCP

5. **Reentrena el modelo** con las nuevas features
   ```bash
   python train_model.py KO
   ```

6. **Compara el accuracy** antes y después
   ```bash
   python check_training_results.py
   ```

**Archivos creados:**
- `backend/models/alpha_vantage_features.py` - Módulo de integración
- `ALPHA_VANTAGE_GUIDE.md` - Guía completa de uso
- `test_alpha_vantage.py` - Script de prueba
- `RESUMEN_ALPHA_VANTAGE.md` - Resumen de implementación

**Mejora esperada:** 53% → 58-63% accuracy
