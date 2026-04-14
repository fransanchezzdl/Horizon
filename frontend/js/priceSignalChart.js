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
  let _resizeHandler = null;

  // ── Colores por tema ─────────────────────────────────────────────────────────
  const COLORS_DARK = {
    ALCISTA_OK:  '#22c55e',
    BAJISTA_OK:  '#ef4444',
    LATERAL_OK:  '#f59e0b',
    PENDING:     '#6b7280',
    BG:          '#111827',
    GRID:        '#1e293b',
    TEXT:        '#94a3b8',
    UP_CANDLE:   '#22c55e',
    DOWN_CANDLE: '#ef4444',
    BORDER:      '#1e293b',
  };

  const COLORS_LIGHT = {
    ALCISTA_OK:  '#16a34a',
    BAJISTA_OK:  '#dc2626',
    LATERAL_OK:  '#d97706',
    PENDING:     '#9ca3af',
    BG:          '#ffffff',
    GRID:        '#f1f5f9',
    TEXT:        '#64748b',
    UP_CANDLE:   '#16a34a',
    DOWN_CANDLE: '#dc2626',
    BORDER:      '#e2e8f0',
  };

  function _getColors() {
    return document.documentElement.getAttribute('data-theme') === 'dark'
      ? COLORS_DARK
      : COLORS_LIGHT;
  }

  // Opacidad hex para señales incorrectas (~40%)
  const INCORRECT_ALPHA = '66';

  // ── Helpers ─────────────────────────────────────────────────────────────────

  function _markerColor(signal, correct) {
    const C = _getColors();
    if (correct === null || correct === undefined) return C.PENDING;
    const base = signal === 'ALCISTA' ? C.ALCISTA_OK
               : signal === 'BAJISTA' ? C.BAJISTA_OK
               : C.LATERAL_OK;
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
    if (_resizeHandler) {
      window.removeEventListener('resize', _resizeHandler);
      _resizeHandler = null;
    }
    if (_chart) {
      _chart.remove();
      _chart = null;
      _candleSeries = null;
    }
  }

  function _createChart(container) {
    const C = _getColors();

    _chart = LightweightCharts.createChart(container, {
      width:  container.clientWidth,
      height: 300,
      layout: {
        background: { color: C.BG },
        textColor:  C.TEXT,
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { color: C.GRID },
      },
      crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
      rightPriceScale: {
        borderVisible: false,
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderVisible:   false,
        timeVisible:     true,
        secondsVisible:  false,
        fixLeftEdge:     true,
        fixRightEdge:    true,
        lockVisibleTimeRangeOnResize: true,
      },
      handleScroll: {
        mouseWheel:    true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: false,
      },
      handleScale: {
        mouseWheel: true,
        pinch:      true,
        axisPressedMouseMove: { time: true, price: false },
      },
    });

    _candleSeries = _chart.addCandlestickSeries({
      upColor:         C.UP_CANDLE,
      downColor:       C.DOWN_CANDLE,
      borderUpColor:   C.UP_CANDLE,
      borderDownColor: C.DOWN_CANDLE,
      wickUpColor:     C.UP_CANDLE,
      wickDownColor:   C.DOWN_CANDLE,
    });

    // Responsivo: reajusta ancho al redimensionar ventana (handler guardado para poder eliminarlo)
    _resizeHandler = () => {
      if (_chart && container) {
        _chart.resize(container.clientWidth, 300);
      }
    };
    window.addEventListener('resize', _resizeHandler);
  }

  function _applyTheme() {
    if (!_chart || !_candleSeries) return;
    const C = _getColors();
    _chart.applyOptions({
      layout: { background: { color: C.BG }, textColor: C.TEXT },
      grid: { vertLines: { visible: false }, horzLines: { color: C.GRID } },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false },
    });
    _candleSeries.applyOptions({
      upColor:         C.UP_CANDLE,
      downColor:       C.DOWN_CANDLE,
      borderUpColor:   C.UP_CANDLE,
      borderDownColor: C.DOWN_CANDLE,
      wickUpColor:     C.UP_CANDLE,
      wickDownColor:   C.DOWN_CANDLE,
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
    // Bloquear scroll fuera del rango de datos
    _chart.timeScale().scrollToPosition(0, false);
  }

  // Escuchar cambios de tema para actualizar colores sin recargar datos
  window.addEventListener('horizon:theme-changed', _applyTheme);

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
