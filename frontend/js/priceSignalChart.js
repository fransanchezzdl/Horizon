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
