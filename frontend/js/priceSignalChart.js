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

<<<<<<< HEAD
  // ── Colores por tema ─────────────────────────────────────────────────────────
  const COLORS_DARK = {
=======
  // ── Colores ─────────────────────────────────────────────────────────────────
  const SIGNAL_COLORS = {
>>>>>>> f8102c68ba6735a55a034daab7e3e9ee5ef7e847
    ALCISTA_OK:  '#22c55e',
    BAJISTA_OK:  '#ef4444',
    LATERAL_OK:  '#f59e0b',
    PENDING:     '#6b7280',
<<<<<<< HEAD
    BG:          '#111827',
    GRID:        '#1e293b',
    TEXT:        '#94a3b8',
=======
>>>>>>> f8102c68ba6735a55a034daab7e3e9ee5ef7e847
    UP_CANDLE:   '#22c55e',
    DOWN_CANDLE: '#ef4444',
    BORDER:      '#1e293b',
  };

<<<<<<< HEAD
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
=======
  const THEME_COLORS = {
    dark: {
      BG:   '#111827',
      GRID: '#1e2130',
      TEXT: '#9ca3af',
    },
    light: {
      BG:   '#ffffff',
      GRID: '#e5e7eb',
      TEXT: '#374151',
    },
  };

  function _getThemeColors() {
    const theme = document.documentElement.getAttribute('data-theme') || 'light';
    return { ...SIGNAL_COLORS, ...THEME_COLORS[theme] || THEME_COLORS.light };
>>>>>>> f8102c68ba6735a55a034daab7e3e9ee5ef7e847
  }

  // Opacidad hex para señales incorrectas (~40%)
  const INCORRECT_ALPHA = '66';

  // ── Helpers ─────────────────────────────────────────────────────────────────

  function _markerColor(signal, correct) {
<<<<<<< HEAD
    const C = _getColors();
    if (correct === null || correct === undefined) return C.PENDING;
    const base = signal === 'ALCISTA' ? C.ALCISTA_OK
               : signal === 'BAJISTA' ? C.BAJISTA_OK
               : C.LATERAL_OK;
=======
    if (correct === null || correct === undefined) return SIGNAL_COLORS.PENDING;
    const base = signal === 'ALCISTA' ? SIGNAL_COLORS.ALCISTA_OK
               : signal === 'BAJISTA' ? SIGNAL_COLORS.BAJISTA_OK
               : SIGNAL_COLORS.LATERAL_OK;
>>>>>>> f8102c68ba6735a55a034daab7e3e9ee5ef7e847
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

  // Filtros activos (sincronizados con los checkboxes del HTML)
  const _activeFilters = { ALCISTA: true, BAJISTA: true, LATERAL: false };

  function _markerText(signal, confidence, correct) {
    const pct = confidence != null ? ` ${Math.round(confidence * 100)}%` : '';
    const mark = correct === false ? ' ✗' : correct === true ? '' : ' ?';
    return `${signal}${pct}${mark}`;
  }

  /**
   * Agrupa señales consecutivas del mismo tipo en una ventana de 3 días,
   * conservando solo la de mayor confianza de cada grupo.
   */
  function _groupSignals(signals) {
    if (!signals.length) return [];

    const sorted = [...signals].sort((a, b) => (a.time < b.time ? -1 : 1));
    const grouped = [];
    let group = [sorted[0]];

    for (let i = 1; i < sorted.length; i++) {
      const prev = group[0];
      const curr = sorted[i];
      const daysDiff = Math.abs(
        (new Date(curr.time).getTime() - new Date(prev.time).getTime()) / 86400000
      );
      if (curr.signal === prev.signal && daysDiff <= 3) {
        group.push(curr);
      } else {
        // Conservar la de mayor confianza del grupo
        grouped.push(group.reduce((best, s) =>
          (s.confidence || 0) > (best.confidence || 0) ? s : best
        ));
        group = [curr];
      }
    }
    grouped.push(group.reduce((best, s) =>
      (s.confidence || 0) > (best.confidence || 0) ? s : best
    ));

    return grouped;
  }

  function _buildMarkers(signals) {
    const filtered = signals
      .filter(s => s.time && s.signal)
      .filter(s => _activeFilters[s.signal] !== false);

    return _groupSignals(filtered)
      .map(s => ({
        time:     s.time,
        position: _markerPosition(s.signal),
        color:    _markerColor(s.signal, s.correct),
        shape:    _markerShape(s.signal),
        text:     _markerText(s.signal, s.confidence, s.correct),
        // Señales incorrectas más pequeñas para reducir ruido visual
        size:     s.correct === false ? 0.7 : 1,
      }))
      .sort((a, b) => (a.time < b.time ? -1 : 1));
  }

  /**
   * Actualiza el estado de un filtro y recarga los markers.
   * Llamado desde los checkboxes del HTML.
   */
  window.setPriceSignalFilter = function (type, enabled) {
    if (type in _activeFilters) {
      _activeFilters[type] = enabled;
    }
    // Recargar datos para reflejar el cambio
    if (_currentTicker) {
      _loadData(_currentTicker, _currentDays);
    }
  };

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
<<<<<<< HEAD
    const C = _getColors();

=======
    const C = _getThemeColors();
>>>>>>> f8102c68ba6735a55a034daab7e3e9ee5ef7e847
    _chart = LightweightCharts.createChart(container, {
      width:  container.clientWidth,
      height: 300,
      layout: {
        background: { color: C.BG },
        textColor:  C.TEXT,
      },
      grid: {
<<<<<<< HEAD
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
=======
        vertLines: { color: C.GRID },
        horzLines: { color: C.GRID },
      },
      crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
      rightPriceScale: { borderColor: C.GRID },
      timeScale: {
        borderColor:     C.GRID,
>>>>>>> f8102c68ba6735a55a034daab7e3e9ee5ef7e847
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

  // Recrear el chart con la paleta correcta cuando el usuario cambia de tema
  window.addEventListener('horizon:theme-changed', function () {
    if (_currentTicker) {
      _loadData(_currentTicker, _currentDays);
    }
  });
}());
