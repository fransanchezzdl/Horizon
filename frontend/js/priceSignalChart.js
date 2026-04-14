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

  // ── Colores ─────────────────────────────────────────────────────────────────
  const SIGNAL_COLORS = {
    ALCISTA_OK:  '#22c55e',
    BAJISTA_OK:  '#ef4444',
    LATERAL_OK:  '#f59e0b',
    PENDING:     '#6b7280',
    UP_CANDLE:   '#22c55e',
    DOWN_CANDLE: '#ef4444',
  };

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
  }

  // Opacidad hex para señales incorrectas (~40%)
  const INCORRECT_ALPHA = '66';

  // ── Helpers ─────────────────────────────────────────────────────────────────

  function _markerColor(signal, correct) {
    if (correct === null || correct === undefined) return SIGNAL_COLORS.PENDING;
    const base = signal === 'ALCISTA' ? SIGNAL_COLORS.ALCISTA_OK
               : signal === 'BAJISTA' ? SIGNAL_COLORS.BAJISTA_OK
               : SIGNAL_COLORS.LATERAL_OK;
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
    const C = _getThemeColors();
    _chart = LightweightCharts.createChart(container, {
      width:  container.clientWidth,
      height: 300,
      layout: {
        background: { color: C.BG },
        textColor:  C.TEXT,
      },
      grid: {
        vertLines: { color: C.GRID },
        horzLines: { color: C.GRID },
      },
      crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
      rightPriceScale: { borderColor: C.GRID },
      timeScale: {
        borderColor:     C.GRID,
        timeVisible:     true,
        secondsVisible:  false,
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

  // Recrear el chart con la paleta correcta cuando el usuario cambia de tema
  window.addEventListener('horizon:theme-changed', function () {
    if (_currentTicker) {
      _loadData(_currentTicker, _currentDays);
    }
  });
}());
