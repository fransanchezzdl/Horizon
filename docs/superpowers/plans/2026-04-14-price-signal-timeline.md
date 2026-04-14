# Price Signal Timeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir una gráfica candlestick con señales IA históricas en la página de Análisis, con selector de rango 7d/30d/90d.

**Architecture:** Nuevo endpoint FastAPI `GET /activos/{ticker}/price-history?days=N` que combina OHLC de yfinance con señales de `prediction_log`. El frontend carga Lightweight Charts vía CDN y monta la gráfica en el `#predictionChartContainer` ya existente. El módulo `priceSignalChart.js` expone `initPriceSignalChart(ticker)` y `updatePriceSignalChart(days)` que son llamados desde `search.js` al seleccionar un activo.

**Tech Stack:** FastAPI, yfinance (ya instalado), Supabase/prediction_log (ya existe), Lightweight Charts v4 CDN, JS vanilla, CSS vanilla

---

## File Map

| Archivo | Acción | Responsabilidad |
|---------|--------|-----------------|
| `backend/services/price_history_service.py` | Crear | Obtiene OHLC de yfinance + señales de prediction_log |
| `backend/main.py` | Modificar | Registrar endpoint `/activos/{ticker}/price-history` |
| `frontend/js/priceSignalChart.js` | Crear | Módulo Lightweight Charts: montar gráfica, marcadores, selector |
| `frontend/analysis.html` | Modificar | Añadir CDN script + reemplazar contenido de `#predictionChartContainer` |
| `frontend/js/search.js` | Modificar | Llamar a `initPriceSignalChart` y `updatePriceSignalChart` desde `actualizarVista` |
| `frontend/css/styles.css` | Modificar | Estilos de `.chart-header`, `.range-selector`, `.chart-legend` |

---

## Task 1: Backend — Servicio price_history

**Files:**
- Create: `backend/services/price_history_service.py`

- [ ] **Step 1: Crear el servicio**

```python
# backend/services/price_history_service.py
"""
Servicio para obtener OHLC histórico + señales de predicción por ticker.
Combina yfinance (precios) con prediction_log (señales IA).
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import yfinance as yf
import logging

from ..daos.prediction_log_dao import PredictionLogDAO

logger = logging.getLogger(__name__)


class PriceHistoryService:

    @staticmethod
    def get_price_and_signals(ticker: str, days: int = 30) -> Dict:
        """
        Devuelve velas OHLC + señales IA para el rango solicitado.

        Args:
            ticker: Símbolo (ej: "AAPL")
            days:   Rango en días. Valores permitidos: 7, 30, 90.

        Returns:
            {
                "candles": [{"time": "YYYY-MM-DD", "open": float, "high": float,
                              "low": float, "close": float}],
                "signals": [{"time": "YYYY-MM-DD", "signal": str,
                              "confidence": float, "correct": bool|None}]
            }
        """
        if days not in (7, 30, 90):
            days = 30

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        candles = PriceHistoryService._fetch_ohlc(ticker, start_date, end_date)
        signals = PriceHistoryService._fetch_signals(ticker, start_date)

        return {"candles": candles, "signals": signals}

    @staticmethod
    def _fetch_ohlc(ticker: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Descarga OHLC de yfinance y lo convierte al formato esperado por Lightweight Charts."""
        try:
            data = yf.download(
                ticker,
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                progress=False,
                auto_adjust=True
            )

            if data is None or data.empty:
                logger.warning(f"[PriceHistoryService] Sin datos OHLC para {ticker}")
                return []

            # Aplanar MultiIndex si existe
            if hasattr(data.columns, 'get_level_values'):
                data.columns = data.columns.get_level_values(0)

            candles = []
            for date_idx, row in data.iterrows():
                try:
                    candles.append({
                        "time": date_idx.strftime("%Y-%m-%d"),
                        "open": round(float(row["Open"]), 4),
                        "high": round(float(row["High"]), 4),
                        "low": round(float(row["Low"]), 4),
                        "close": round(float(row["Close"]), 4),
                    })
                except (KeyError, ValueError):
                    continue

            logger.info(f"[PriceHistoryService] {len(candles)} velas para {ticker}")
            return candles

        except Exception as e:
            logger.error(f"[PriceHistoryService] Error OHLC {ticker}: {e}")
            return []

    @staticmethod
    def _fetch_signals(ticker: str, start_date: datetime) -> List[Dict]:
        """Obtiene predicciones del prediction_log desde start_date."""
        try:
            all_preds = PredictionLogDAO.obtener_por_ticker(ticker, solo_resueltas=False, limit=200)

            signals = []
            for pred in all_preds:
                fecha_str = pred.get("fecha_prediccion")
                if not fecha_str:
                    continue

                # Filtrar por rango
                try:
                    fecha_dt = datetime.fromisoformat(str(fecha_str))
                except ValueError:
                    continue

                if fecha_dt < start_date:
                    continue

                resuelta = pred.get("resuelta", False)
                correct: Optional[bool] = pred.get("correcta") if resuelta else None

                signals.append({
                    "time": fecha_dt.strftime("%Y-%m-%d"),
                    "signal": pred.get("tendencia_predicha", ""),
                    "confidence": pred.get("confianza_ensemble"),
                    "correct": correct,
                })

            logger.info(f"[PriceHistoryService] {len(signals)} señales para {ticker}")
            return signals

        except Exception as e:
            logger.error(f"[PriceHistoryService] Error señales {ticker}: {e}")
            return []
```

- [ ] **Step 2: Commit**

```bash
git add backend/services/price_history_service.py
git commit -m "feat: PriceHistoryService combina OHLC yfinance + señales prediction_log"
```

---

## Task 2: Backend — Endpoint en main.py

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Añadir import del servicio**

Localizar los imports de servicios al inicio de `main.py` (línea ~8) y añadir:

```python
from .services.price_history_service import PriceHistoryService
```

- [ ] **Step 2: Añadir el endpoint**

Añadir después del endpoint `/activos/{ticker}/reliability` (busca `@app.get("/activos/{ticker}/reliability")`):

```python
@app.get("/activos/{ticker}/price-history")
def obtener_price_history(ticker: str, days: int = 30):
    """
    Devuelve OHLC histórico + señales IA para el ticker en los últimos N días.
    days: 7 | 30 | 90 (default 30)
    """
    activo = activo_service.obtener_activo(ticker)
    if not activo:
        raise HTTPException(status_code=404, detail="Activo no encontrado")

    return PriceHistoryService.get_price_and_signals(ticker=ticker, days=days)
```

- [ ] **Step 3: Verificar que el servidor arranca sin errores**

```bash
cd backend
uvicorn backend.main:app --reload --port 8000
```

Esperado: `Application startup complete.` sin traceback.

- [ ] **Step 4: Commit**

```bash
git add backend/main.py
git commit -m "feat: endpoint GET /activos/{ticker}/price-history"
```

---

## Task 3: Frontend — Módulo priceSignalChart.js

**Files:**
- Create: `frontend/js/priceSignalChart.js`

- [ ] **Step 1: Crear el módulo**

```javascript
// frontend/js/priceSignalChart.js
// Módulo para la gráfica candlestick + señales IA usando Lightweight Charts v4.
// API pública:
//   initPriceSignalChart(ticker)        — monta la gráfica con rango 30d
//   updatePriceSignalChart(days)        — cambia rango y recarga datos
//   destroyPriceSignalChart()           — limpia la instancia (opcional)

(function () {
  'use strict';

  // ── Estado interno ──────────────────────────────────────────────────────────
  let _chart = null;
  let _candleSeries = null;
  let _currentTicker = '';
  let _currentDays = 30;

  // ── Colores ─────────────────────────────────────────────────────────────────
  const COLORS = {
    ALCISTA_OK:  '#22c55e',
    BAJISTA_OK:  '#ef4444',
    LATERAL_OK:  '#f59e0b',
    PENDING:     '#6b7280',
    BG:          '#111827',
    GRID:        '#1e2130',
    TEXT:        '#9ca3af',
    UP_CANDLE:   '#22c55e',
    DOWN_CANDLE: '#ef4444',
  };

  // Opacidad hex para señales incorrectas (~40%)
  const INCORRECT_ALPHA = '66';

  // ── Helpers ─────────────────────────────────────────────────────────────────

  function _markerColor(signal, correct) {
    if (correct === null || correct === undefined) return COLORS.PENDING;
    const base = signal === 'ALCISTA' ? COLORS.ALCISTA_OK
               : signal === 'BAJISTA' ? COLORS.BAJISTA_OK
               : COLORS.LATERAL_OK;
    return correct ? base : base + INCORRECT_ALPHA;
  }

  function _markerPosition(signal) {
    return signal === 'BAJISTA' ? 'belowBar' : 'aboveBar';
  }

  function _markerShape(signal) {
    return signal === 'ALCISTA' ? 'arrowUp'
         : signal === 'BAJISTA' ? 'arrowDown'
         : 'circle';
  }

  function _markerText(signal, confidence, correct) {
    const pct = confidence != null ? ` ${Math.round(confidence * 100)}%` : '';
    const mark = correct === false ? ' ✗' : correct === true ? '' : ' ?';
    return `${signal}${pct}${mark}`;
  }

  function _buildMarkers(signals) {
    return signals
      .filter(s => s.time && s.signal)
      .map(s => ({
        time:     s.time,
        position: _markerPosition(s.signal),
        color:    _markerColor(s.signal, s.correct),
        shape:    _markerShape(s.signal),
        text:     _markerText(s.signal, s.confidence, s.correct),
        size:     1,
      }))
      .sort((a, b) => (a.time < b.time ? -1 : 1));
  }

  // ── Core ────────────────────────────────────────────────────────────────────

  function _getChartContainer() {
    return document.getElementById('priceSignalChart');
  }

  function _destroyChart() {
    if (_chart) {
      _chart.remove();
      _chart = null;
      _candleSeries = null;
    }
  }

  function _createChart(container) {
    _chart = LightweightCharts.createChart(container, {
      width:  container.clientWidth,
      height: 300,
      layout: {
        background: { color: COLORS.BG },
        textColor:  COLORS.TEXT,
      },
      grid: {
        vertLines: { color: COLORS.GRID },
        horzLines: { color: COLORS.GRID },
      },
      crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
      rightPriceScale: { borderColor: COLORS.GRID },
      timeScale: {
        borderColor:     COLORS.GRID,
        timeVisible:     true,
        secondsVisible:  false,
      },
    });

    _candleSeries = _chart.addCandlestickSeries({
      upColor:        COLORS.UP_CANDLE,
      downColor:      COLORS.DOWN_CANDLE,
      borderUpColor:  COLORS.UP_CANDLE,
      borderDownColor: COLORS.DOWN_CANDLE,
      wickUpColor:    COLORS.UP_CANDLE,
      wickDownColor:  COLORS.DOWN_CANDLE,
    });

    // Responsivo: reajusta ancho al redimensionar ventana
    window.addEventListener('resize', () => {
      if (_chart && container) {
        _chart.resize(container.clientWidth, 300);
      }
    });
  }

  async function _loadData(ticker, days) {
    const container = _getChartContainer();
    if (!container) return;

    // Mostrar loading
    container.innerHTML = '<div class="chart-loading">Cargando gráfica...</div>';

    let data;
    try {
      const url = `${window.API_BASE}/activos/${encodeURIComponent(ticker)}/price-history?days=${days}`;
      const resp = await fetch(url, { cache: 'no-store' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      data = await resp.json();
    } catch (err) {
      console.error('[priceSignalChart] Error cargando datos:', err);
      container.innerHTML = '<div class="chart-error">No se pudieron cargar los datos de precio.</div>';
      return;
    }

    // Limpiar container y recrear chart
    container.innerHTML = '';
    _destroyChart();
    _createChart(container);

    if (!data.candles || data.candles.length === 0) {
      container.innerHTML = '<div class="chart-error">Sin datos de precio disponibles.</div>';
      return;
    }

    _candleSeries.setData(data.candles);

    if (data.signals && data.signals.length > 0) {
      _candleSeries.setMarkers(_buildMarkers(data.signals));
    }

    _chart.timeScale().fitContent();
  }

  // ── API pública ─────────────────────────────────────────────────────────────

  window.initPriceSignalChart = function (ticker) {
    _currentTicker = ticker;
    _currentDays   = 30;
    _loadData(ticker, 30);
  };

  window.updatePriceSignalChart = function (days) {
    _currentDays = days;
    if (_currentTicker) {
      _loadData(_currentTicker, days);
    }
  };

  window.destroyPriceSignalChart = function () {
    _destroyChart();
    _currentTicker = '';
  };
}());
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/priceSignalChart.js
git commit -m "feat: módulo priceSignalChart.js con Lightweight Charts"
```

---

## Task 4: Frontend — HTML (analysis.html)

**Files:**
- Modify: `frontend/analysis.html`

- [ ] **Step 1: Añadir CDN de Lightweight Charts en el `<head>`**

Localizar la línea con `<script src="js/config.js">` (línea ~12) y añadir **antes** de ella:

```html
<script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
```

- [ ] **Step 2: Añadir script de priceSignalChart antes del cierre `</body>`**

Localizar los scripts al final del `<body>` (donde están los `<script src="js/...">`) y añadir antes del cierre `</body>`:

```html
<script src="js/priceSignalChart.js"></script>
```

- [ ] **Step 3: Reemplazar el contenido de `#predictionChartContainer`**

Localizar esta línea (línea ~92):

```html
<div class="card">
    <h3 class="opt-title">Predicción de Precios LSTM</h3>
    <p class="opt-info">Histórico + Pronóstico 30 días</p>
    <div id="predictionChartContainer" style="height:260px; border-radius:10px; background:#f8fafc; margin-top:12px; display:flex; align-items:center; justify-content:center; color:#9ca3af;">
        Sin datos de predicción
    </div>
</div>
```

Reemplazar por:

```html
<div class="card">
    <div class="chart-header">
        <div>
            <h3 class="opt-title" style="margin:0;">Precio e Historial de Señales IA</h3>
            <p class="opt-info" style="margin:2px 0 0;">Velas OHLC + predicciones del modelo</p>
        </div>
        <div class="range-selector" id="rangeSelector">
            <button class="range-btn" data-days="7">7d</button>
            <button class="range-btn active" data-days="30">30d</button>
            <button class="range-btn" data-days="90">90d</button>
        </div>
    </div>
    <div id="predictionChartContainer">
        <div id="priceSignalChart"></div>
    </div>
    <div class="chart-legend">
        <span class="legend-item"><span style="color:#22c55e;">▲</span> ALCISTA correcta</span>
        <span class="legend-item"><span style="color:#ef4444;">▼</span> BAJISTA correcta</span>
        <span class="legend-item"><span style="color:#f59e0b;">●</span> LATERAL correcta</span>
        <span class="legend-item legend-incorrect"><span style="opacity:0.4;">▲▼●</span> Incorrecta</span>
        <span class="legend-item"><span style="color:#6b7280;">●</span> Pendiente</span>
    </div>
</div>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/analysis.html
git commit -m "feat: estructura HTML para gráfica precio + señales en analysis.html"
```

---

## Task 5: Frontend — Estilos CSS

**Files:**
- Modify: `frontend/css/styles.css`

- [ ] **Step 1: Añadir estilos al final de styles.css**

```css
/* ── Price Signal Chart ─────────────────────────────────────────────────── */

.chart-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 12px;
    flex-wrap: wrap;
    gap: 8px;
}

.range-selector {
    display: flex;
    gap: 4px;
}

.range-btn {
    padding: 4px 12px;
    border-radius: 20px;
    border: 1px solid var(--color-border, #334155);
    background: transparent;
    color: var(--color-text-muted, #9ca3af);
    font-size: 12px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
}

.range-btn:hover {
    background: var(--color-bg-lighter, #1e293b);
    color: var(--color-text, #f1f5f9);
}

.range-btn.active {
    background: var(--color-primary, #3b82f6);
    color: #fff;
    border-color: var(--color-primary, #3b82f6);
}

#predictionChartContainer {
    min-height: 300px;
    border-radius: 8px;
    overflow: hidden;
}

#priceSignalChart {
    width: 100%;
}

.chart-loading,
.chart-error {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 300px;
    color: var(--color-text-muted, #9ca3af);
    font-size: 14px;
}

.chart-error {
    color: #f87171;
}

.chart-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 10px;
    font-size: 12px;
    color: var(--color-text-muted, #9ca3af);
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 4px;
}

.legend-incorrect {
    opacity: 0.7;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/css/styles.css
git commit -m "feat: estilos chart-header, range-selector y chart-legend"
```

---

## Task 6: Frontend — Integración con search.js

**Files:**
- Modify: `frontend/js/search.js`

- [ ] **Step 1: Llamar a `initPriceSignalChart` desde `actualizarVista`**

En `search.js`, localizar la función `actualizarVista` (busca `function actualizarVista`). Al final de esa función, después de la línea `loadReliabilityStats(selectedTicker);`, añadir:

```javascript
if (typeof window.initPriceSignalChart === 'function') {
    window.initPriceSignalChart(selectedTicker);
}
```

- [ ] **Step 2: Conectar los botones del selector de rango**

Al final de la función `initSearch`, antes del cierre `}`, añadir:

```javascript
// Selector de rango para la gráfica de precio
document.addEventListener('click', (e) => {
    const btn = e.target.closest('.range-btn');
    if (!btn) return;
    const days = parseInt(btn.dataset.days, 10);
    if (!days) return;
    document.querySelectorAll('.range-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    if (typeof window.updatePriceSignalChart === 'function') {
        window.updatePriceSignalChart(days);
    }
});
```

- [ ] **Step 3: Commit**

```bash
git add frontend/js/search.js
git commit -m "feat: integrar initPriceSignalChart y selector de rango en search.js"
```

---

## Task 7: Verificación manual

- [ ] **Step 1: Arrancar backend**

```bash
cd d:/Uni/TFG/Horizon
uvicorn backend.main:app --reload --port 8000
```

- [ ] **Step 2: Abrir analysis.html en el navegador**

Navegar a la página de análisis, buscar cualquier ticker (ej: `AAPL`).

Verificar:
- La gráfica candlestick carga con velas visibles
- Los botones 7d / 30d / 90d cambian el rango correctamente
- Las señales aparecen como marcadores con colores correctos (verde ▲, rojo ▼, naranja ●)
- Las señales incorrectas aparecen más transparentes
- Las señales pendientes aparecen en gris con `?`
- La leyenda es visible debajo de la gráfica
- La gráfica es responsiva al redimensionar la ventana

- [ ] **Step 3: Verificar en DevTools**

Abrir DevTools > Network y confirmar que:
- El endpoint `/activos/AAPL/price-history?days=30` devuelve 200
- El JSON tiene `candles` con datos OHLC y `signals` con las predicciones

- [ ] **Step 4: Commit final**

```bash
git add -A
git commit -m "0.10.6 - Timeline Precio + Señales IA en página de Análisis"
```
