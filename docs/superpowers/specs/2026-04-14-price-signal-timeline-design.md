# Design: Timeline Precio + Señales

**Fecha:** 2026-04-14  
**Feature:** Gráfica candlestick con señales IA superpuestas en la página de Análisis  
**Stack:** JS vanilla, HTML, CSS vanilla, Lightweight Charts (TradingView), FastAPI backend

---

## Objetivo

Mostrar en la página de análisis de un activo una gráfica de velas japonesas (OHLC) con las predicciones históricas del modelo IA marcadas como anotaciones visuales. El usuario puede seleccionar el rango de tiempo (7d / 30d / 90d) y ver qué señales fueron correctas vs incorrectas.

---

## Ubicación en el Frontend

- **Página:** `frontend/analysis.html`
- **Contenedor:** `#predictionChartContainer` (ya existe en el HTML)
- **Posición:** Debajo de los KPIs de predicción actuales

### Estructura interna del contenedor

```html
<div id="predictionChartContainer">
  <!-- Cabecera con selector de rango -->
  <div class="chart-header">
    <span class="chart-title">Histórico de Precio y Señales</span>
    <div class="range-selector">
      <button class="range-btn active" data-days="7">7d</button>
      <button class="range-btn" data-days="30">30d</button>
      <button class="range-btn" data-days="90">90d</button>
    </div>
  </div>

  <!-- Gráfica Lightweight Charts -->
  <div id="priceSignalChart"></div>

  <!-- Leyenda -->
  <div class="chart-legend">
    <span class="legend-item alcista-correct">▲ ALCISTA</span>
    <span class="legend-item bajista-correct">▼ BAJISTA</span>
    <span class="legend-item lateral-correct">— LATERAL</span>
    <span class="legend-item incorrect">⬚ Incorrecta</span>
  </div>
</div>
```

---

## Backend

### Nuevo endpoint

```
GET /activos/{ticker}/price-history?days=30
```

**Respuesta:**

```json
{
  "candles": [
    {"time": "2026-03-01", "open": 170.5, "high": 175.2, "low": 168.1, "close": 173.4}
  ],
  "signals": [
    {
      "time": "2026-03-01",
      "signal": "ALCISTA",
      "confidence": 0.82,
      "correct": true
    }
  ]
}
```

**Implementación:**

- `backend/routers/price_history_router.py` — define la ruta y delega al servicio
- `backend/services/price_history_service.py` — orquesta yfinance + prediction_log
  - Obtiene OHLC de yfinance para el ticker en los últimos N días
  - Consulta `prediction_log` para el mismo período filtrando por ticker y `resuelta = true`
  - Devuelve el JSON combinado
- El endpoint se registra en `main.py`

**Parámetros:**
- `days`: entero, valores permitidos 7 / 30 / 90, default 30
- Predicciones sin resolver (`resuelta = false`) se incluyen en `signals` con `correct: null`

---

## Frontend

### Archivos nuevos

- `frontend/js/priceSignalChart.js` — módulo de la gráfica

### API del módulo

```js
// Inicializa la gráfica para un ticker con rango por defecto (30d)
initPriceSignalChart(ticker)

// Cambia el rango y recarga datos
updatePriceSignalChart(days)
```

### Comportamiento

1. Al cargar la página de análisis con un ticker, se llama `initPriceSignalChart(ticker)`
2. Se hace fetch a `/activos/{ticker}/price-history?days=30`
3. Se monta la serie candlestick con Lightweight Charts
4. Se añaden marcadores de señal encima de las velas
5. Los botones 7d/30d/90d llaman a `updatePriceSignalChart(days)` que hace nuevo fetch y actualiza la serie

### Carga de Lightweight Charts

Via CDN en el `<head>` de `analysis.html`:

```html
<script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
```

---

## Marcadores Visuales de Señales

| Señal    | Correcta | Color               | Forma | Posición    |
|----------|----------|---------------------|-------|-------------|
| ALCISTA  | true     | `#22c55e` sólido    | ▲     | Encima vela |
| ALCISTA  | false    | `#22c55e` 40% opac. | ▲     | Encima vela |
| BAJISTA  | true     | `#ef4444` sólido    | ▼     | Bajo vela   |
| BAJISTA  | false    | `#ef4444` 40% opac. | ▼     | Bajo vela   |
| LATERAL  | true     | `#f59e0b` sólido    | —     | Encima vela |
| LATERAL  | false    | `#f59e0b` 40% opac. | —     | Encima vela |
| Cualq.   | null     | `#6b7280` sólido    | ?     | Encima vela |

Las señales incorrectas usan color con opacidad reducida para que el usuario perciba visualmente el track record del modelo sin perder legibilidad.

---

## Tema visual

- Fondo oscuro (`#0f1117`) coherente con el dark mode del proyecto
- Velas: alcistas `#22c55e`, bajistas `#ef4444`
- Grid y ejes: color sutil `#1e2130`
- Tooltip al hover: muestra OHLC + señal del día si existe + confianza

---

## Archivos a crear/modificar

| Archivo | Acción |
|---------|--------|
| `backend/routers/price_history_router.py` | Crear |
| `backend/services/price_history_service.py` | Crear |
| `backend/main.py` | Modificar — registrar router |
| `frontend/analysis.html` | Modificar — añadir CDN + estructura chart |
| `frontend/js/priceSignalChart.js` | Crear |
| `frontend/css/analysis.css` (o equivalente) | Modificar — estilos del chart |

---

## Fuera de alcance

- Datos en tiempo real / websocket
- Comparativa entre tickers
- Exportar la gráfica como imagen
