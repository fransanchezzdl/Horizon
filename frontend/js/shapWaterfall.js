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
  const CHAR_PX = 6.5;   // ancho aproximado por carácter a 11.5px Inter
  const MAX_LABEL_LEN = 36;

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

  // Porcentaje sobre la suma total de influencias absolutas (nunca llega a 100%)
  function _shapToInfluenceText(shap, totalAbs, isLateral, barW) {
    if (!totalAbs) return '';
    const pct = Math.round((Math.abs(shap) / totalAbs) * 100);
    if (pct < 1) return '';
    // En LATERAL, suprimir el label si la barra es demasiado estrecha para
    // evitar solapamiento entre filas. El hover muestra el valor exacto.
    if (isLateral && barW != null && barW < 30) return '';
    if (isLateral) return `${pct}%`;
    return shap >= 0 ? `+${pct}%` : `-${pct}%`;
  }

  // ── Panel de descripción de feature ──────────────────────────────────────────
  function _getInfoPanel() { return document.getElementById('shapFeatureInfo'); }

  function _showFeatureInfo(d, C, totalAbs, senal) {
    const panel = _getInfoPanel();
    if (!panel) return;
    const parsed = (typeof window.parseFeatureName === 'function')
      ? window.parseFeatureName(d.feature)
      : { label: _labelFeature(d.feature), desc: '' };

    const isLateral = (senal || '').toUpperCase() === 'LATERAL';
    const col = isLateral ? C.LATERAL_OK : (d.shap >= 0 ? C.ALCISTA_OK : C.BAJISTA_OK);
    const pct = totalAbs ? Math.round((Math.abs(d.shap) / totalAbs) * 100) : null;

    // Texto de dirección contextualizado según la señal activa
    let dirText;
    const s = (senal || '').toUpperCase();
    if (s === 'ALCISTA') {
      dirText = d.shap >= 0 ? 'Apoya la predicción alcista' : 'Frena la predicción alcista';
    } else if (s === 'BAJISTA') {
      dirText = d.shap < 0 ? 'Apoya la predicción bajista' : 'Frena la predicción bajista';
    } else {
      // LATERAL: mostramos peso relativo, no dirección de precio
      const pctStr = pct != null ? ` (${pct}% del peso total)` : '';
      dirText = `Factor influyente en la predicción lateral${pctStr}`;
    }

    const val = (d.value != null && !isNaN(Number(d.value)))
      ? `<span class="shap-info-val">Valor actual: ${Number(d.value).toFixed(2)}</span>` : '';
    const influence = pct != null
      ? `<span class="shap-info-influence" style="color:${col};">${pct}% del peso total</span>` : '';

    panel.innerHTML = `
      <span class="shap-info-accent"></span>
      <div class="shap-info-body">
        <span class="shap-info-name">
          <span class="shap-info-dot" style="background:${col};"></span>${parsed.label}
        </span>
        ${parsed.desc ? `<span class="shap-info-desc">${parsed.desc}</span>` : ''}
      </div>
      <div class="shap-info-meta">
        ${val}
        ${influence}
        <span class="shap-info-dir" style="color:${col};">${dirText}</span>
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
    const senal  = (data.senal || 'LATERAL').toUpperCase();
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
    const HEADER_H   = 20;
    const margin     = { top: HEADER_H + 4, right: 110, bottom: 16, left: Math.ceil(maxLabelChars * CHAR_PX) + 24 };
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

    const maxAbs   = d3.max(values, d => d.abs) || 1;
    const totalAbs = d3.sum(values, d => Math.abs(d.shap)) || 1;

    // Para LATERAL el signo SHAP no indica dirección de precio.
    // Usamos escala bipolar [-maxAbs, maxAbs] pero dibujamos barras simétricas
    // (la mitad hacia cada lado desde el centro) según la magnitud absoluta.
    // Así las etiquetas quedan centradas y el gráfico se ve equilibrado.
    const isLateral = senal === 'LATERAL';
    const xScale = d3.scaleLinear().domain([-maxAbs, maxAbs]).range([0, innerWidth]);

    const yScale = d3.scaleBand()
      .domain(values.map(d => d.feature))
      .range([0, innerHeight])
      .padding(bandPad);

    // Línea central (siempre visible)
    svg.append('line')
      .attr('x1', xScale(0)).attr('x2', xScale(0))
      .attr('y1', 0).attr('y2', innerHeight)
      .attr('stroke', C.GRID).attr('stroke-width', 1);

    // Header
    const headerY = -HEADER_H + 4;
    svg.append('text')
      .attr('x', xScale(0))
      .attr('y', headerY)
      .attr('text-anchor', 'middle')
      .attr('fill', C.TEXT_MUTED)
      .attr('font-size', '10px')
      .attr('font-family', 'Inter, system-ui, sans-serif')
      .attr('letter-spacing', '0.04em')
      .text('INFLUENCIA EN LA PREDICCIÓN');

    svg.append('text')
      .attr('x', innerWidth + 8)
      .attr('y', headerY)
      .attr('text-anchor', 'start')
      .attr('fill', C.TEXT_MUTED)
      .attr('font-size', '10px')
      .attr('font-family', 'Inter, system-ui, sans-serif')
      .attr('letter-spacing', '0.04em')
      .text('VALOR ACTUAL');

    // Barras: LATERAL → simétricas desde el centro según |shap|
    //         ALCISTA/BAJISTA → dirección según signo
    svg.selectAll('.shap-bar')
      .data(values)
      .join('rect')
        .attr('class', 'shap-bar')
        .attr('x',      d => isLateral ? xScale(-d.abs / 2) : (d.shap >= 0 ? xScale(0) : xScale(d.shap)))
        .attr('y',      d => yScale(d.feature))
        .attr('width',  d => isLateral ? Math.max(xScale(d.abs / 2) - xScale(-d.abs / 2), 2) : Math.max(Math.abs(xScale(d.shap) - xScale(0)), 2))
        .attr('height', yScale.bandwidth())
        .attr('fill',   d => isLateral ? C.LATERAL_OK : (d.shap >= 0 ? C.ALCISTA_OK : C.BAJISTA_OK))
        .attr('rx', 3).attr('ry', 3)
        .style('cursor', 'pointer')
        .on('mouseover', (_, d) => _showFeatureInfo(d, C, totalAbs, senal))
        .on('mouseleave', _hideFeatureInfo)
        .on('click', (_, d) => _showFeatureInfo(d, C, totalAbs, senal));

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
        .attr('font-size',   '11.5px')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .style('cursor', 'pointer')
        .text(d => _shortLabel(d.feature))
        .on('mouseover', (_, d) => _showFeatureInfo(d, C, totalAbs, senal))
        .on('mouseleave', _hideFeatureInfo)
        .on('click', (_, d) => _showFeatureInfo(d, C, totalAbs, senal));

    // Porcentaje de influencia junto a la barra
    // Regla de posicionamiento: si la barra es suficientemente ancha, el texto va
    // dentro (blanco), evitando solapamiento con las etiquetas del eje Y.
    const valColX   = innerWidth + 8;
    const MIN_BAR_W = 30; // px mínimos para caber dentro
    svg.selectAll('.shap-label-shap')
      .data(values)
      .join('text')
        .attr('class', 'shap-label-shap')
        .attr('x', d => {
          if (isLateral) return xScale(0);   // siempre centrado
          const barW = Math.abs(xScale(d.shap) - xScale(0));
          if (d.shap >= 0) {
            return barW >= MIN_BAR_W ? xScale(d.shap) - 4 : Math.min(xScale(d.shap) + 4, valColX - 40);
          } else {
            return barW >= MIN_BAR_W ? xScale(d.shap) + 4 : xScale(d.shap) - 4;
          }
        })
        .attr('y',      d => yScale(d.feature) + yScale.bandwidth() / 2)
        .attr('text-anchor', d => {
          if (isLateral) return 'middle';
          const barW = Math.abs(xScale(d.shap) - xScale(0));
          if (d.shap >= 0) return barW >= MIN_BAR_W ? 'end'   : 'start';
          else              return barW >= MIN_BAR_W ? 'start' : 'end';
        })
        .attr('dominant-baseline', 'middle')
        .attr('fill', d => {
          if (isLateral) {
            const barW = xScale(d.abs / 2) - xScale(-d.abs / 2);
            return barW >= MIN_BAR_W ? '#fff' : C.LATERAL_OK;
          }
          const barW = Math.abs(xScale(d.shap) - xScale(0));
          return barW >= MIN_BAR_W ? '#fff' : (d.shap >= 0 ? C.ALCISTA_OK : C.BAJISTA_OK);
        })
        .attr('font-size',   '10px')
        .attr('font-weight', '700')
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .text(d => {
          const barW = isLateral
            ? xScale(d.abs / 2) - xScale(-d.abs / 2)
            : Math.abs(xScale(d.shap) - xScale(0));
          return _shapToInfluenceText(d.shap, totalAbs, isLateral, barW);
        });

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

    // Restablecer panel idle tras re-render
    const panel = _getInfoPanel();
    if (panel && !panel.classList.contains('is-active')) {
      const body = panel.querySelector('.shap-info-body .shap-info-name');
      if (body) {
        body.textContent = 'Selecciona un indicador para ver su explicación';
        body.classList.add('shap-info-idle');
      }
    }
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
