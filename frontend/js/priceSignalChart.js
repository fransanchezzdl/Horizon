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
    BORDER:      '#1e293b',
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

  const INCORRECT_COLOR = '#9ca3af';
  // Pendientes: color de la señal con ~50% de opacidad
  const PENDING_ALPHA = '80';

  // ── Helpers ─────────────────────────────────────────────────────────────────

  function _markerColor(signal, correct) {
    const base = signal === 'ALCISTA' ? SIGNAL_COLORS.ALCISTA_OK
               : signal === 'BAJISTA' ? SIGNAL_COLORS.BAJISTA_OK
               : SIGNAL_COLORS.LATERAL_OK;
    if (correct === false) return INCORRECT_COLOR;
    if (correct === true)  return base;
    // null/undefined → pendiente de evaluar: color de la señal semitransparente
    return base + PENDING_ALPHA;
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
    return correct === false ? '✗' : '';
  }

  // Días máximos de silencio antes de forzar una flecha recordatorio
  const MAX_GAP_DAYS = 7;

  function _daysBetween(dateA, dateB) {
    return Math.abs((new Date(dateA).getTime() - new Date(dateB).getTime()) / 86400000);
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

    const _bestOfGroup = (grp) => {
      const resueltas = grp.filter(s => s.correct !== null && s.correct !== undefined);
      const pool = resueltas.length > 0 ? resueltas : grp;
      return pool.reduce((best, s) =>
        (s.confidence || 0) > (best.confidence || 0) ? s : best
      );
    };

    for (let i = 1; i < sorted.length; i++) {
      const prev = group[group.length - 1]; // Bug 2 fix: comparar con el último del grupo
      const curr = sorted[i];
      if (curr.signal === prev.signal && _daysBetween(curr.time, prev.time) <= 3) {
        group.push(curr);
      } else {
        grouped.push(_bestOfGroup(group));
        group = [curr];
      }
    }
    grouped.push(_bestOfGroup(group));

    return grouped;
  }

  /**
   * Añade flechas recordatorio cuando hay un hueco de más de MAX_GAP_DAYS
   * sin ninguna señal visible, usando la última señal activa como referencia.
   * Las flechas insertadas se marcan con _reminder:true para no tratarlas como incorrectas.
   */
  function _fillGaps(grouped, candleDates) {
    if (!grouped.length || !candleDates.length) return grouped;

    const result = [];
    const dates = [...candleDates].sort();

    for (let i = 0; i < grouped.length; i++) {
      result.push(grouped[i]);
      const nextSignal = grouped[i + 1];
      const nextDate   = nextSignal ? nextSignal.time : dates[dates.length - 1];
      let   lastDate   = grouped[i].time;

      while (_daysBetween(lastDate, nextDate) > MAX_GAP_DAYS) {
        const targetMs = new Date(lastDate).getTime() + MAX_GAP_DAYS * 86400000;
        const candidate = dates.find(d => new Date(d).getTime() >= targetMs);
        // Bug 3 fix: comparar como timestamps, no como strings
        if (!candidate || new Date(candidate).getTime() >= new Date(nextDate).getTime()) break;

        result.push({ ...grouped[i], time: candidate, _reminder: true });
        lastDate = candidate;
      }
    }

    return result;
  }

  // Bug 1 fix: mapear señal a la vela más próxima disponible (fines de semana/festivos)
  function _snapToCandle(signalTime, candleDates) {
    if (candleDates.includes(signalTime)) return signalTime;
    const t = new Date(signalTime).getTime();
    const forward = candleDates.find(d => new Date(d).getTime() >= t);
    return forward || candleDates[candleDates.length - 1];
  }

  function _buildMarkers(signals, candleDates) {
    const filtered = signals
      .filter(s => s.time && s.signal)
      .filter(s => _activeFilters[s.signal] !== false);

    const grouped = _groupSignals(filtered);
    const withReminders = _fillGaps(grouped, candleDates || []);

    return withReminders
      .map(s => ({
        time:     _snapToCandle(s.time, candleDates),
        position: _markerPosition(s.signal),
        color:    _markerColor(s.signal, s._reminder ? true : s.correct),
        shape:    _markerShape(s.signal),
        text:     s._reminder ? '' : _markerText(s.signal, s.confidence, s.correct),
        size:     s.correct === false && !s._reminder ? 0.7 : 1,
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
    const C = _getThemeColors();
    _chart.applyOptions({
      layout: { background: { color: C.BG }, textColor: C.TEXT },
      grid: { vertLines: { color: C.GRID }, horzLines: { color: C.GRID } },
      rightPriceScale: { borderColor: C.GRID },
      timeScale: { borderColor: C.GRID },
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

    // Bug 4 fix: destruir antes de limpiar el DOM
    _destroyChart();
    container.innerHTML = '';
    _createChart(container);

    if (!data.candles || data.candles.length === 0) {
      container.innerHTML = '<div class="chart-error">Sin datos de precio disponibles.</div>';
      return;
    }

    _candleSeries.setData(data.candles);

    if (data.signals && data.signals.length > 0) {
      const candleDates = data.candles.map(c => c.time);
      _candleSeries.setMarkers(_buildMarkers(data.signals, candleDates));
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
    // Respetar el rango activo en el selector del DOM (si el usuario ya había elegido 7/30/90)
    const activeBtn = document.querySelector('.range-btn.active');
    const days = activeBtn ? parseInt(activeBtn.dataset.days, 10) || 30 : 30;
    _currentDays = days;
    _loadData(ticker, days);
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
