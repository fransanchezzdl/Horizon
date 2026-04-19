// frontend/js/shapTemporal.js
// Gráfico de líneas: evolución temporal de las top-3 features SHAP.
// API pública:
//   initShapTemporal(ticker)   — carga y renderiza
//   destroyShapTemporal()      — limpia y oculta

(function () {
  'use strict';

  let _currentData   = null;
  let _resizeHandler = null;

  const COLORS_LINES = ['#6366f1', '#f59e0b', '#22c55e'];

  const COLORS_DARK = {
    BG:       'transparent',
    GRID:     '#1e293b',
    TEXT:     '#94a3b8',
    TEXT_MUT: '#64748b',
    ZERO:     '#334155',
  };
  const COLORS_LIGHT = {
    BG:       'transparent',
    GRID:     '#e2e8f0',
    TEXT:     '#374151',
    TEXT_MUT: '#9ca3af',
    ZERO:     '#cbd5e1',
  };

  function _getColors() {
    return document.documentElement.getAttribute('data-theme') === 'dark'
      ? COLORS_DARK : COLORS_LIGHT;
  }

  function _getSection()    { return document.getElementById('shapTemporalSection'); }
  function _getContainer()  { return document.getElementById('shapTemporalChart'); }

  function _showLoading() {
    const c = _getContainer();
    if (c) c.innerHTML = '<div class="shap-loading">Cargando evolución SHAP...</div>';
  }

  function _showError(msg) {
    const c = _getContainer();
    if (c) c.innerHTML = `<div class="shap-error">${msg}</div>`;
  }

  // Convierte "RSI_sw5_last" → "RSI (sw5) actual"
  function _labelFeature(name) {
    if (!name) return '';
    return name
      .replace(/_sw(\d+)_/g, ' ($1d) ')
      .replace(/_/g, ' ')
      .replace(/^\w/, c => c.toUpperCase());
  }

  function _renderChart(data) {
    const container = _getContainer();
    if (!container) return;
    container.innerHTML = '';

    const series    = data.series || [];
    const features  = data.top_features || [];

    if (series.length < 2) {
      _showError('Datos insuficientes para mostrar la evolución temporal.');
      return;
    }

    const C      = _getColors();
    const margin = { top: 16, right: 20, bottom: 40, left: 56 };
    const totalW = container.clientWidth || 600;
    const totalH = 220;
    const iW     = Math.max(totalW - margin.left - margin.right, 80);
    const iH     = totalH - margin.top - margin.bottom;

    const svg = d3.select(container)
      .append('svg')
        .attr('width',  totalW)
        .attr('height', totalH)
        .style('overflow', 'visible')
      .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    const parseDate = d3.timeParse('%Y-%m-%d');
    const dates     = series.map(d => parseDate(d.fecha)).filter(Boolean);

    const xScale = d3.scaleTime()
      .domain(d3.extent(dates))
      .range([0, iW]);

    const allVals = features.flatMap(f => series.map(d => d[f] || 0));
    const yMax    = Math.max(Math.abs(d3.min(allVals)), Math.abs(d3.max(allVals)));
    const yScale  = d3.scaleLinear()
      .domain([-yMax * 1.15, yMax * 1.15])
      .range([iH, 0]);

    // Grid horizontal
    svg.append('g')
      .attr('class', 'grid')
      .call(
        d3.axisLeft(yScale)
          .ticks(4)
          .tickSize(-iW)
          .tickFormat('')
      )
      .selectAll('line')
        .attr('stroke', C.GRID)
        .attr('stroke-dasharray', '3,3');
    svg.select('.grid .domain').remove();

    // Línea cero
    svg.append('line')
      .attr('x1', 0).attr('x2', iW)
      .attr('y1', yScale(0)).attr('y2', yScale(0))
      .attr('stroke', C.ZERO)
      .attr('stroke-width', 1);

    // Eje X
    svg.append('g')
      .attr('transform', `translate(0,${iH})`)
      .call(
        d3.axisBottom(xScale)
          .ticks(Math.min(series.length, 6))
          .tickFormat(d3.timeFormat('%d %b'))
      )
      .selectAll('text')
        .attr('fill', C.TEXT)
        .attr('font-size', '10px');
    svg.selectAll('.domain').attr('stroke', C.GRID);
    svg.selectAll('.tick line').attr('stroke', C.GRID);

    // Eje Y
    svg.append('g')
      .call(d3.axisLeft(yScale).ticks(4).tickFormat(d => d.toFixed(3)))
      .selectAll('text')
        .attr('fill', C.TEXT)
        .attr('font-size', '10px');

    // Líneas por feature
    features.forEach((feat, i) => {
      const lineData = series
        .map(d => ({ date: parseDate(d.fecha), val: d[feat] || 0 }))
        .filter(d => d.date);

      const lineGen = d3.line()
        .x(d => xScale(d.date))
        .y(d => yScale(d.val))
        .curve(d3.curveMonotoneX);

      svg.append('path')
        .datum(lineData)
        .attr('fill', 'none')
        .attr('stroke', COLORS_LINES[i])
        .attr('stroke-width', 2)
        .attr('d', lineGen);

      // Puntos
      svg.selectAll(`.dot-${i}`)
        .data(lineData)
        .join('circle')
          .attr('class', `dot-${i}`)
          .attr('cx', d => xScale(d.date))
          .attr('cy', d => yScale(d.val))
          .attr('r', 3)
          .attr('fill', COLORS_LINES[i]);
    });

    // Leyenda
    const legend = svg.append('g')
      .attr('transform', `translate(0,${iH + 28})`);

    features.forEach((feat, i) => {
      const xOff = i * (iW / features.length);
      legend.append('rect')
        .attr('x', xOff).attr('y', -4)
        .attr('width', 12).attr('height', 3)
        .attr('fill', COLORS_LINES[i]);
      legend.append('text')
        .attr('x', xOff + 16).attr('y', 0)
        .attr('fill', C.TEXT)
        .attr('font-size', '10px')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text(_labelFeature(feat));
    });
  }

  function _applyTheme() {
    if (_currentData) _renderChart(_currentData);
  }

  async function _loadData(ticker) {
    _showLoading();

    try {
      const url  = `${window.API_BASE}/activos/${encodeURIComponent(ticker)}/xai/shap-temporal?limit=30`;
      const resp = await fetch(url, { cache: 'no-store' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      _currentData = await resp.json();
    } catch (err) {
      console.error('[shapTemporal] Error:', err);
      _showError('No hay histórico SHAP disponible para este activo.');
      const s = _getSection();
      if (s) s.style.display = 'none';
      return;
    }

    const s = _getSection();
    if (s) s.style.display = '';

    _renderChart(_currentData);
  }

  _resizeHandler = function () {
    if (_currentData) _renderChart(_currentData);
  };
  window.addEventListener('resize', _resizeHandler);
  window.addEventListener('horizon:theme-changed', _applyTheme);

  window.initShapTemporal = function (ticker) { _loadData(ticker); };

  window.destroyShapTemporal = function () {
    if (_resizeHandler) {
      window.removeEventListener('resize', _resizeHandler);
      _resizeHandler = null;
    }
    const c = _getContainer();
    if (c) c.innerHTML = '';
    _currentData = null;
    const s = _getSection();
    if (s) s.style.display = 'none';
  };
}());
