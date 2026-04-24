// frontend/js/shapWaterfall.js
// Módulo para la gráfica SHAP Waterfall usando D3.js v7.
// API pública:
//   initShapWaterfall(ticker)   — carga y renderiza el waterfall para el ticker
//   destroyShapWaterfall()      — limpia la instancia y oculta la sección

(function () {
  'use strict';

  let _currentData   = null;
  let _resizeHandler = null;

  // ── Colores por tema ──────────────────────────────────────────────────────────
  const COLORS_DARK = {
    ALCISTA_OK: '#22c55e', BAJISTA_OK: '#ef4444', LATERAL_OK: '#f59e0b',
    BG: 'transparent', GRID: '#1e293b', TEXT: '#94a3b8', TEXT_MUTED: '#64748b',
  };
  const COLORS_LIGHT = {
    ALCISTA_OK: '#16a34a', BAJISTA_OK: '#dc2626', LATERAL_OK: '#d97706',
    BG: 'transparent', GRID: '#e2e8f0', TEXT: '#374151', TEXT_MUTED: '#9ca3af',
  };

  function _getColors() {
    return document.documentElement.getAttribute('data-theme') === 'dark'
      ? COLORS_DARK : COLORS_LIGHT;
  }

  // ── Etiqueta legible — delega en shapNarrative.js ───────────────────────────
  const CHAR_PX = 6.8;   // ancho aproximado por carácter a 12px Inter
  const MAX_LABEL_LEN = 30;

  function _labelFeature(name) {
    if (!name) return '';
    if (typeof window.parseFeatureName === 'function') {
      return window.parseFeatureName(name).label;
    }
    return name.replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase());
  }

  function _shortLabel(name) {
    const full = _labelFeature(name);
    return full.length > MAX_LABEL_LEN ? full.slice(0, MAX_LABEL_LEN - 1) + '…' : full;
  }

  // ── Panel de descripción de feature ──────────────────────────────────────────
  function _getInfoPanel() { return document.getElementById('shapFeatureInfo'); }

  function _showFeatureInfo(d, C) {
    const panel = _getInfoPanel();
    if (!panel) return;
    const parsed = (typeof window.parseFeatureName === 'function')
      ? window.parseFeatureName(d.feature)
      : { label: _labelFeature(d.feature), desc: '' };
    const dir  = d.shap >= 0 ? 'Impulso al alza' : 'Impulso a la baja';
    const col  = d.shap >= 0 ? C.ALCISTA_OK : C.BAJISTA_OK;
    const val  = (d.value != null && !isNaN(Number(d.value)))
      ? `<span class="shap-info-val">Valor: ${Number(d.value).toFixed(3)}</span>` : '';
    panel.innerHTML = `
      <span class="shap-info-accent" style="background:${col};"></span>
      <div class="shap-info-body">
        <span class="shap-info-name">${parsed.label}</span>
        ${parsed.desc ? `<span class="shap-info-desc">${parsed.desc}</span>` : ''}
      </div>
      <div class="shap-info-meta">
        ${val}
        <span class="shap-info-dir" style="color:${col};">${dir}</span>
      </div>`;
    panel.classList.add('is-active');
  }

  function _hideFeatureInfo() {
    const panel = _getInfoPanel();
    if (panel) panel.classList.remove('is-active');
  }

  // ── Helpers ──────────────────────────────────────────────────────────────────
  function _getChartContainer() { return document.getElementById('shapChart'); }
  function _getSection()        { return document.getElementById('shapSection'); }

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

  // ── Badge de señal ────────────────────────────────────────────────────────────
  const BADGE_CLASS = {
    ALCISTA: 'shap-badge--alcista',
    BAJISTA: 'shap-badge--bajista',
    LATERAL: 'shap-badge--lateral',
  };

  function _renderBadge(data) {
    const badge = document.getElementById('shapSignalBadge');
    if (!badge) return;
    const pct  = Math.round((data.confianza || 0) * 100);
    const cls  = BADGE_CLASS[data.senal] || 'shap-badge--lateral';
    const mark = data.correcta === true ? ' ✓' : data.correcta === false ? ' ✗' : '';
    badge.innerHTML = `<span class="shap-badge ${cls}">${data.senal} ${pct}%${mark}</span>`;
  }

  // ── Renderizado D3 ────────────────────────────────────────────────────────────
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

    // Margen izquierdo dinámico según la etiqueta más larga
    const maxLabelChars = Math.min(
      d3.max(values, d => _shortLabel(d.feature).length) || 20,
      MAX_LABEL_LEN
    );
    const margin     = { top: 8, right: 90, bottom: 16, left: Math.ceil(maxLabelChars * CHAR_PX) + 20 };
    const totalWidth = container.clientWidth || 600;
    const innerWidth = Math.max(totalWidth - margin.left - margin.right, 80);
    const barHeight  = 30;
    const bandPad    = 0.22;
    const innerHeight = values.length * barHeight;

    const svg = d3.select(container)
      .append('svg')
        .attr('width',  totalWidth)
        .attr('height', innerHeight + margin.top + margin.bottom)
        .style('overflow', 'visible')
      .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    const maxAbs = d3.max(values, d => d.abs) || 1;

    const xScale = d3.scaleLinear().domain([-maxAbs, maxAbs]).range([0, innerWidth]);
    const yScale = d3.scaleBand()
      .domain(values.map(d => d.feature))
      .range([0, innerHeight])
      .padding(bandPad);

    // Línea central
    svg.append('line')
      .attr('x1', xScale(0)).attr('x2', xScale(0))
      .attr('y1', 0).attr('y2', innerHeight)
      .attr('stroke', C.GRID).attr('stroke-width', 1);

    // Barras — con eventos hover para el panel de info
    svg.selectAll('.shap-bar')
      .data(values)
      .join('rect')
        .attr('class', 'shap-bar')
        .attr('x',      d => d.shap >= 0 ? xScale(0) : xScale(d.shap))
        .attr('y',      d => yScale(d.feature))
        .attr('width',  d => Math.max(Math.abs(xScale(d.shap) - xScale(0)), 2))
        .attr('height', yScale.bandwidth())
        .attr('fill',   d => d.shap >= 0 ? C.ALCISTA_OK : C.BAJISTA_OK)
        .attr('rx', 3).attr('ry', 3)
        .style('cursor', 'pointer')
        .on('mouseover', (_, d) => _showFeatureInfo(d, C))
        .on('mouseleave', _hideFeatureInfo);

    // Etiquetas de nombre (izquierda) — texto truncado, hover abre el panel
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
        .style('cursor', 'pointer')
        .text(d => _shortLabel(d.feature))
        .on('mouseover', (_, d) => _showFeatureInfo(d, C))
        .on('mouseleave', _hideFeatureInfo);

    // Valores SHAP junto a la barra
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

    // Valores reales de la feature (derecha)
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
          if (d.value == null) return '';
          const n = Number(d.value);
          return isNaN(n) ? String(d.value) : n.toFixed(2);
        });
  }

  // ── Tema ──────────────────────────────────────────────────────────────────────
  function _applyTheme() {
    if (_currentData) { _renderChart(_currentData); _renderBadge(_currentData); }
  }

  // ── Carga de datos ────────────────────────────────────────────────────────────
  async function _loadData(ticker) {
    _showLoading();
    let data;
    try {
      const resp = await fetch(`${window.API_BASE}/activos/${encodeURIComponent(ticker)}/xai/latest-shap`, { cache: 'no-store' });
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
    const section = _getSection();
    if (section) section.style.display = '';

    _renderBadge(data);
    _renderChart(data);
    if (typeof window.renderShapNarrative === 'function') window.renderShapNarrative(data);
  }

  // ── Resize + tema ─────────────────────────────────────────────────────────────
  _resizeHandler = function () { if (_currentData) _renderChart(_currentData); };
  window.addEventListener('resize', _resizeHandler);
  window.addEventListener('horizon:theme-changed', _applyTheme);

  // ── API pública ───────────────────────────────────────────────────────────────
  window.initShapWaterfall = function (ticker) { _loadData(ticker); };

  window.destroyShapWaterfall = function () {
    if (_resizeHandler) { window.removeEventListener('resize', _resizeHandler); _resizeHandler = null; }
    const c = _getChartContainer();
    if (c) c.innerHTML = '';
    const narr = document.getElementById('shapNarrative');
    if (narr) narr.innerHTML = '';
    _hideFeatureInfo();
    _currentData = null;
    const section = _getSection();
    if (section) section.style.display = 'none';
  };
}());
