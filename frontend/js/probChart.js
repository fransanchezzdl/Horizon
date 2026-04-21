// frontend/js/probChart.js
// Distribución de probabilidades XGBoost (3 clases) con detección de abstención.
// API pública:
//   renderProbChart(probabilidades_xgb, senal_ia)

(function () {
  'use strict';

  const COLORS = {
    alcista: '#22c55e',
    lateral: '#f59e0b',
    bajista: '#ef4444',
  };

  const LABELS = { alcista: 'Alcista', lateral: 'Lateral', bajista: 'Bajista' };

  // Umbral de convicción: si la clase ganadora XGBoost no supera esto,
  // la señal LATERAL es por baja convicción general (abstención).
  const ABSTENTION_THRESHOLD = 0.40;

  function _getSection()    { return document.getElementById('probSection'); }
  function _getContainer()  { return document.getElementById('probBarsContainer'); }
  function _getBadge()      { return document.getElementById('probAbstentionBadge'); }

  function _pct(raw) {
    const v = raw <= 1 ? raw * 100 : raw;
    return Math.round(v * 10) / 10;
  }

  function _renderBars(probs) {
    const container = _getContainer();
    if (!container) return;

    const ordered = ['alcista', 'lateral', 'bajista'];
    container.innerHTML = ordered.map(key => {
      const raw = probs[key];
      if (raw == null) return '';
      const pct = _pct(raw);
      const color = COLORS[key];
      return `
        <div class="prob-bar-row">
          <span class="prob-bar-label" style="color:${color};">${LABELS[key]}</span>
          <div class="prob-bar-track">
            <div class="prob-bar-fill" style="width:${pct}%;background:${color};"></div>
          </div>
          <span class="prob-bar-pct">${pct}%</span>
        </div>
      `;
    }).join('');
  }

  function _renderBadge(probs, senal) {
    const badge = _getBadge();
    if (!badge) return;

    const maxProb = Math.max(probs.alcista || 0, probs.lateral || 0, probs.bajista || 0);
    const isAbstention = senal === 'LATERAL' && maxProb < ABSTENTION_THRESHOLD;

    if (isAbstention) {
      badge.innerHTML = `
        <span class="prob-abstention-badge" title="Las tres clases tienen probabilidades similares (~33%). El modelo no encuentra un patrón claro y emite LATERAL como señal por defecto.">
          ⚠️ Baja convicción
        </span>
      `;
    } else if (senal === 'LATERAL' && (probs.lateral || 0) >= ABSTENTION_THRESHOLD) {
      badge.innerHTML = `<span class="prob-neutral-badge">Movimiento lateral predicho</span>`;
    } else {
      badge.innerHTML = '';
    }
  }

  window.renderProbChart = function (probabilidades_xgb, senal_ia) {
    const section = _getSection();

    if (!probabilidades_xgb || typeof probabilidades_xgb !== 'object') {
      if (section) section.style.display = 'none';
      return;
    }

    if (section) section.style.display = '';
    _renderBars(probabilidades_xgb);
    _renderBadge(probabilidades_xgb, senal_ia || '');
  };
}());
