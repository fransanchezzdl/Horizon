// frontend/js/shapWaterfall.js
// Módulo para la gráfica SHAP Waterfall usando D3.js v7.
// API pública:
//   initShapWaterfall(ticker)   — carga y renderiza el waterfall para el ticker
//   destroyShapWaterfall()      — limpia la instancia y oculta la sección

(function () {
  'use strict';

  // ── Estado interno ──────────────────────────────────────────────────────────
  let _currentTicker = '';
  let _currentData   = null;
  let _resizeHandler = null;

  // ── Colores por tema ─────────────────────────────────────────────────────────
  const COLORS_DARK = {
    ALCISTA_OK: '#22c55e',
    BAJISTA_OK: '#ef4444',
    LATERAL_OK: '#f59e0b',
    BG:         'transparent',
    GRID:       '#1e293b',
    TEXT:       '#94a3b8',
    TEXT_MUTED: '#64748b',
  };

  const COLORS_LIGHT = {
    ALCISTA_OK: '#16a34a',
    BAJISTA_OK: '#dc2626',
    LATERAL_OK: '#d97706',
    BG:         'transparent',
    GRID:       '#e2e8f0',
    TEXT:       '#374151',
    TEXT_MUTED: '#9ca3af',
  };

  function _getColors() {
    return document.documentElement.getAttribute('data-theme') === 'dark'
      ? COLORS_DARK
      : COLORS_LIGHT;
  }

  // ── Helpers ──────────────────────────────────────────────────────────────────

  function _getChartContainer() {
    return document.getElementById('shapChart');
  }

  function _getSection() {
    return document.getElementById('shapSection');
  }

  function _showLoading() {
    const c = _getChartContainer();
    if (c) c.innerHTML = '<div class="shap-loading">Cargando explicación IA...</div>';
  }

  function _showError(msg) {
    const c = _getChartContainer();
    if (c) c.innerHTML = `<div class="shap-error">${msg}</div>`;
    const badge = document.getElementById('shapSignalBadge');
    if (badge) badge.innerHTML = '';
  }

  function _renderBadge(data) {
    const badge = document.getElementById('shapSignalBadge');
    if (!badge) return;

    const pct = Math.round((data.confianza || 0) * 100);
    const cls  = data.senal === 'ALCISTA' ? 'shap-badge--alcista'
               : data.senal === 'BAJISTA' ? 'shap-badge--bajista'
               : 'shap-badge--lateral';
    const correctaIcon = data.correcta === true  ? ' ✓'
                       : data.correcta === false ? ' ✗'
                       : '';

    badge.innerHTML = `<span class="shap-badge ${cls}">${data.senal}&nbsp;${pct}%${correctaIcon}</span>`;
  }

  // ── Renderizado D3 ───────────────────────────────────────────────────────────

  function _renderChart(data) {
    const container = _getChartContainer();
    if (!container) return;
    container.innerHTML = '';

    const values = data.shap_values;
    if (!values || values.length === 0) {
      _showError('Sin datos SHAP disponibles para este activo.');
      return;
    }

    const C = _getColors();

    const margin      = { top: 8, right: 90, bottom: 16, left: 170 };
    const totalWidth  = container.clientWidth || 600;
    const innerWidth  = Math.max(totalWidth - margin.left - margin.right, 80);
    const barHeight   = 30;
    const bandPad     = 0.22;
    const innerHeight = values.length * barHeight;

    const svg = d3.select(container)
      .append('svg')
        .attr('width',  totalWidth)
        .attr('height', innerHeight + margin.top + margin.bottom)
        .style('overflow', 'visible')
      .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    const maxAbs = d3.max(values, d => d.abs) || 1;

    const xScale = d3.scaleLinear()
      .domain([-maxAbs, maxAbs])
      .range([0, innerWidth]);

    const yScale = d3.scaleBand()
      .domain(values.map(d => d.feature))
      .range([0, innerHeight])
      .padding(bandPad);

    // Línea central en x = 0
    svg.append('line')
      .attr('x1', xScale(0)).attr('x2', xScale(0))
      .attr('y1', 0).attr('y2', innerHeight)
      .attr('stroke', C.GRID)
      .attr('stroke-width', 1);

    // Barras
    svg.selectAll('.shap-bar')
      .data(values)
      .join('rect')
        .attr('class', 'shap-bar')
        .attr('x',      d => d.shap >= 0 ? xScale(0) : xScale(d.shap))
        .attr('y',      d => yScale(d.feature))
        .attr('width',  d => Math.max(Math.abs(xScale(d.shap) - xScale(0)), 2))
        .attr('height', yScale.bandwidth())
        .attr('fill',   d => d.shap >= 0 ? C.ALCISTA_OK : C.BAJISTA_OK)
        .attr('rx', 3).attr('ry', 3);

    // Etiquetas de nombre de feature (izquierda)
    svg.selectAll('.shap-label-feat')
      .data(values)
      .join('text')
        .attr('class', 'shap-label-feat')
        .attr('x', -10)
        .attr('y', d => yScale(d.feature) + yScale.bandwidth() / 2)
        .attr('text-anchor',       'end')
        .attr('dominant-baseline', 'middle')
        .attr('fill',        C.TEXT)
        .attr('font-size',   '12px')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text(d => d.feature);

    // Etiquetas de valor SHAP (junto a la barra, mismo color que barra)
    svg.selectAll('.shap-label-shap')
      .data(values)
      .join('text')
        .attr('class', 'shap-label-shap')
        .attr('x', d => d.shap >= 0 ? xScale(d.shap) + 4 : xScale(d.shap) - 4)
        .attr('y', d => yScale(d.feature) + yScale.bandwidth() / 2)
        .attr('text-anchor',       d => d.shap >= 0 ? 'start' : 'end')
        .attr('dominant-baseline', 'middle')
        .attr('fill',        d => d.shap >= 0 ? C.ALCISTA_OK : C.BAJISTA_OK)
        .attr('font-size',   '10px')
        .attr('font-weight', '600')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text(d => (d.shap >= 0 ? '+' : '') + d.shap.toFixed(3));

    // Etiquetas de valor real de la feature (derecha)
    svg.selectAll('.shap-label-val')
      .data(values)
      .join('text')
        .attr('class', 'shap-label-val')
        .attr('x', innerWidth + 8)
        .attr('y', d => yScale(d.feature) + yScale.bandwidth() / 2)
        .attr('text-anchor',       'start')
        .attr('dominant-baseline', 'middle')
        .attr('fill',        C.TEXT_MUTED)
        .attr('font-size',   '11px')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text(d => {
          if (d.value === null || d.value === undefined) return '';
          const n = Number(d.value);
          return isNaN(n) ? String(d.value) : n.toFixed(2);
        });
  }

  // ── Tema ─────────────────────────────────────────────────────────────────────

  function _applyTheme() {
    if (_currentData) {
      _renderChart(_currentData);
      _renderBadge(_currentData);
    }
  }

  // ── Carga de datos ───────────────────────────────────────────────────────────

  async function _loadData(ticker) {
    _showLoading();

    let data;
    try {
      const url  = `${window.API_BASE}/activos/${encodeURIComponent(ticker)}/xai/latest-shap`;
      const resp = await fetch(url, { cache: 'no-store' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      data = await resp.json();
    } catch (err) {
      console.error('[shapWaterfall] Error cargando datos SHAP:', err);
      _showError('No hay datos de explicabilidad disponibles para este activo.');
      const section = _getSection();
      if (section) section.style.display = 'none';
      return;
    }

    _currentData = data;

    // Mostrar sección (estaba oculta por defecto)
    const section = _getSection();
    if (section) section.style.display = '';

    _renderBadge(data);
    _renderChart(data);
  }

  // ── Resize ───────────────────────────────────────────────────────────────────

  _resizeHandler = function () {
    if (_currentData) _renderChart(_currentData);
  };
  window.addEventListener('resize', _resizeHandler);

  // Escuchar cambios de tema para actualizar colores sin recargar datos
  window.addEventListener('horizon:theme-changed', _applyTheme);

  // ── API pública ──────────────────────────────────────────────────────────────

  window.initShapWaterfall = function (ticker) {
    _currentTicker = ticker;
    _loadData(ticker);
  };

  window.destroyShapWaterfall = function () {
    if (_resizeHandler) {
      window.removeEventListener('resize', _resizeHandler);
      _resizeHandler = null;
    }
    const c = _getChartContainer();
    if (c) c.innerHTML = '';
    _currentData   = null;
    _currentTicker = '';
    const section = _getSection();
    if (section) section.style.display = 'none';
  };
}());
