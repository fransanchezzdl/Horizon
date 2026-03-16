# Guía de Integración Alpha Vantage

## Resumen

Este documento explica cómo funciona la integración de Alpha Vantage en el sistema de predicción Horizon y cómo usar la flag `USE_ALPHA_VANTAGE` para controlar las features adicionales.

## ¿Qué es Alpha Vantage?

Alpha Vantage es una API que proporciona datos financieros completos:
- **Datos fundamentales**: P/E ratio, EPS, dividendos, ratios financieros
- **Indicadores técnicos avanzados**: ADX, CCI, Stochastic, Williams %R
- **Datos macroeconómicos**: GDP, tasas de interés, inflación

## Features Adicionales (18 en total)

### Fundamentales (10 features)
1. **PE_Ratio**: Price-to-Earnings ratio (valoración)
2. **EPS**: Earnings Per Share (beneficio por acción)
3. **Dividend_Yield**: Rendimiento de dividendos
4. **Book_Value**: Valor en libros por acción
5. **ROE**: Return on Equity (rentabilidad sobre capital)
6. **ROA**: Return on Assets (rentabilidad sobre activos)
7. **Debt_to_Equity**: Ratio deuda/capital
8. **Current_Ratio**: Ratio corriente (liquidez)
9. **Quick_Ratio**: Ratio rápido (liquidez inmediata)
10. **Profit_Margin**: Margen de beneficio

### Técnicos Avanzados (5 features)
11. **ADX**: Average Directional Index (fuerza de tendencia)
12. **CCI**: Commodity Channel Index
13. **Stochastic_K**: Oscilador estocástico %K
14. **Stochastic_D**: Oscilador estocástico %D
15. **Williams_R**: Williams %R

### Macroeconómicos (3 features)
16. **GDP_Growth**: Crecimiento del PIB (trimestral)
17. **Interest_Rate**: Tasa de interés de referencia (Federal Funds Rate)
18. **Inflation_Rate**: Tasa de inflación (CPI)

## Configuración

### 1. Obtener API Key

1. Visita: https://www.alphavantage.co/support/#api-key
2. Regístrate (gratis - 500 llamadas/día)
3. Copia tu API key

### 2. Configurar MCP Server

Edita `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "alphavantage": {
      "command": "uvx",
      "args": ["av-mcp", "TU_API_KEY_AQUI"]
    }
  }
}
```

### 3. Configurar Variables de Entorno

Edita `backend/.env`:

```env
# Alpha Vantage API
ALPHA_VANTAGE_API_KEY=TU_API_KEY_AQUI

# Habilitar features de Alpha Vantage
USE_ALPHA_VANTAGE=True
```

## Modos de Operación

### Modo Clásico (USE_ALPHA_VANTAGE=False)
- **Activos estables**: 9 features técnicas base
- **Activos volátiles**: 11 features (9 base + 2 contexto mercado)
- **Accuracy esperado**: ~53%

### Modo Híbrido (USE_ALPHA_VANTAGE=True)
- **Activos estables**: 27 features (9 base + 18 Alpha Vantage)
- **Activos volátiles**: 29 features (11 base + 18 Alpha Vantage)
- **Accuracy esperado**: ~58-63%

### Modo Completo (USE_SENTIMENT=True + USE_ALPHA_VANTAGE=True)
- **Activos estables**: 30 features (9 base + 3 sentimiento + 18 Alpha Vantage)
- **Activos volátiles**: 32 features (11 base + 3 sentimiento + 18 Alpha Vantage)
- **Accuracy esperado**: ~60-70%

## Conteo de Features por Configuración

| Configuración | Estables | Volátiles |
|---------------|----------|-----------|
| Base (sin extras) | 9 | 11 |
| + Sentiment | 12 | 14 |
| + Alpha Vantage | 27 | 29 |
| + Sentiment + AV | 30 | 32 |

## Funcionamiento Interno

### 1. Descarga de Datos

El módulo `alpha_vantage_features.py` se encarga de:
- Obtener datos fundamentales con `COMPANY_OVERVIEW`
- Obtener indicadores técnicos con `ADX`, `CCI`, `STOCH`, `WILLR`
- Obtener datos macro con `REAL_GDP`, `FEDERAL_FUNDS_RATE`, `CPI`

### 2. Integración en Pipeline

En `data_pipeline.py`, la función `compute_features()`:
1. Calcula las 9 features técnicas base
2. Si `USE_ALPHA_VANTAGE=True`, llama a `add_alpha_vantage_features()`
3. Las features de AV se añaden al DataFrame
4. Se aplica forward-fill para fechas sin datos

### 3. Valores por Defecto

Si Alpha Vantage no está disponible o falla:
- **Fundamentales**: Usa valores medios del mercado (P/E=20, ROE=15%, etc.)
- **Técnicos**: Usa valores neutros (ADX=25, CCI=0, Stochastic=50)
- **Macro**: Usa valores históricos medios (GDP=0.5%, Interest=5%, Inflation=2%)

El sistema **siempre funciona**, incluso sin API key.

## Entrenamiento de Modelos

### Importante: Incompatibilidad de Modelos

Los modelos entrenados con diferentes configuraciones de features **NO son compatibles**:

```python
# ❌ INCORRECTO: Entrenar con 9 features, predecir con 27
USE_ALPHA_VANTAGE=False  # Entrenar
# ... entrenar modelo ...
USE_ALPHA_VANTAGE=True   # Predecir
# ... ERROR: dimensiones no coinciden ...

# ✅ CORRECTO: Misma configuración para entrenar y predecir
USE_ALPHA_VANTAGE=True   # Entrenar
# ... entrenar modelo ...
USE_ALPHA_VANTAGE=True   # Predecir
# ... funciona correctamente ...
```

### Reentrenar Modelos

Cuando cambies `USE_ALPHA_VANTAGE`, debes reentrenar:

```bash
# Cambiar flag en backend/.env
USE_ALPHA_VANTAGE=True

# Reentrenar modelo
python train_model.py KO
```

## Verificación

### 1. Verificar Configuración

```python
from backend.models.config import USE_ALPHA_VANTAGE, get_feature_cols

print(f"USE_ALPHA_VANTAGE: {USE_ALPHA_VANTAGE}")
print(f"Features para KO: {len(get_feature_cols('KO'))}")
# Esperado con AV: 27 (estable) o 29 (volátil)
```

### 2. Verificar Features en Datos

```python
from backend.models.data_pipeline import compute_features, download_data
from backend.models.alpha_vantage_features import ALL_AV_FEATURES

df = download_data("KO")
df = compute_features(df, ticker="KO")

av_features_present = [col for col in ALL_AV_FEATURES if col in df.columns]
print(f"Features de AV presentes: {len(av_features_present)}/18")
print(av_features_present)
```

### 3. Verificar Modelo Entrenado

```python
import json

with open("backend/models/saved_models/KO_report.json") as f:
    report = json.load(f)

print(f"Features usadas: {len(report['feature_cols'])}")
print(f"Feature cols: {report['feature_cols']}")
```

## Límites de API

### Plan Gratuito
- **500 llamadas/día** para endpoints estándar
- **25 llamadas/día** para endpoints premium
- **5 llamadas/minuto** de rate limit

### Optimización
El sistema está optimizado para minimizar llamadas:
- Datos fundamentales: 1 llamada por ticker (se cachean)
- Indicadores técnicos: 5 llamadas por ticker (ADX, CCI, STOCH, WILLR)
- Datos macro: 3 llamadas totales (GDP, FFR, CPI) - compartidos entre tickers

**Total por ticker**: ~6-9 llamadas (bien dentro del límite diario)

## Troubleshooting

### Error: "MCP server not connected"
- Verifica que el servidor MCP esté corriendo
- Reinicia Kiro
- Verifica la configuración en `.kiro/settings/mcp.json`

### Error: "API key invalid"
- Verifica que la API key en `.kiro/settings/mcp.json` sea correcta
- Verifica que la API key no haya expirado

### Warning: "Usando valores por defecto"
- El sistema funciona con valores por defecto si Alpha Vantage falla
- Verifica los logs para ver el error específico
- El accuracy será menor pero el sistema sigue funcionando

### Dimensiones no coinciden al predecir
- Verifica que `USE_ALPHA_VANTAGE` sea igual durante entrenamiento y predicción
- Reentrena el modelo con la configuración actual

## Mejora Esperada

### Antes (sin Alpha Vantage)
```
BiGRU Ensemble Accuracy: 53.43%
XGBoost Accuracy: 47.13%
Baseline: 0.37%
```

### Después (con Alpha Vantage)
```
BiGRU Ensemble Accuracy: 58-63% (+5-10%)
XGBoost Accuracy: 52-57% (+5-10%)
Baseline: 0.37%
```

### Factores de Mejora
- **Fundamentales**: Contexto de valoración y salud financiera
- **Técnicos avanzados**: Señales de tendencia y momentum más precisas
- **Macro**: Contexto económico que afecta a todos los activos

## Próximos Pasos

1. **Obtener API key** de Alpha Vantage
2. **Configurar MCP server** en `.kiro/settings/mcp.json`
3. **Habilitar flag** `USE_ALPHA_VANTAGE=True` en `backend/.env`
4. **Reentrenar modelos** con las nuevas features
5. **Comparar accuracy** antes y después

## Referencias

- [Alpha Vantage API Documentation](https://www.alphavantage.co/documentation/)
- [Alpha Vantage MCP Server](https://mcp.alphavantage.co/)
- [Propuesta de Mejoras](PROPUESTA_MCP_MEJORAS.md)
