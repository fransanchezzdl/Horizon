// frontend/js/shapNarrative.js
// Genera un "veredicto en lenguaje natural" a partir de los valores SHAP.
//
// API pública:
//   window.renderShapNarrative(data)        — renderiza la tarjeta narrativa
//   window.parseFeatureName(raw)            — {label, desc} desde nombre técnico crudo
//   window.getFeatureGlossary(raw)          — alias de parseFeatureName (compatibilidad)

(function () {
  'use strict';

  // ── Metadatos de features ───────────────────────────────────────────────────
  // Clave: nombre normalizado (lowercase, sin sufijos ni ventanas).
  // Las claves son las "bases" de los nombres técnicos del backend.

  const META = {
    // Precio y retorno
    close:               { label: 'Precio de cierre',          desc: 'Precio al que cerró la última sesión.' },
    log_return:          { label: 'Retorno reciente',           desc: 'Variación porcentual del precio en la última sesión.',
                           interpret: v => v > 0 ? 'El activo subió en la última sesión' : 'El activo bajó en la última sesión' },
    high_low_ratio:      { label: 'Amplitud del movimiento',   desc: 'Rango entre el máximo y mínimo del día. Alto = sesión volátil.' },
    close_range_pct:     { label: 'Posición del cierre',       desc: 'Indica si el precio cerró cerca del máximo (presión compradora) o del mínimo (presión vendedora) del día.',
                           interpret: v => v >= 0.7 ? 'Cierre cerca del máximo del día — presión compradora' : v <= 0.3 ? 'Cierre cerca del mínimo del día — presión vendedora' : null },
    price_acceleration:  { label: 'Aceleración del precio',    desc: 'Mide si el ritmo de subida/bajada está aumentando o frenando.' },

    // Volumen
    volume:              { label: 'Volumen',                   desc: 'Número de acciones o contratos negociados. Alto volumen = mayor convicción en el movimiento.' },
    volume_ratio:        { label: 'Actividad de volumen',      desc: 'Compara el volumen actual con la media reciente. Más de 1 = actividad inusualmente alta.',
                           interpret: v => v >= 1.5 ? `Volumen ${v.toFixed(1)}× superior a lo habitual — fuerte interés del mercado` : v <= 0.6 ? 'Volumen muy por debajo de la media — poca convicción' : null },
    volume_sma_ratio:    { alias: 'volume_ratio' },

    // Medias móviles y tendencia
    ema:                 { label: 'Media móvil exponencial',   desc: 'Promedio del precio reciente, con más peso en los días más recientes. Marca la dirección de la tendencia.' },
    sma200_dist:         { label: 'Distancia a la media de 200 días', desc: 'Qué tan lejos está el precio de su media de largo plazo. Positivo = por encima (tendencia alcista); negativo = por debajo (bajista).',
                           interpret: v => v > 0.05 ? 'Precio claramente por encima de la tendencia de largo plazo — señal alcista' : v < -0.05 ? 'Precio por debajo de la tendencia de largo plazo — señal bajista' : 'Precio cerca de la media de largo plazo' },
    sma50_slope:         { label: 'Inclinación de la tendencia media', desc: 'Indica si la tendencia de medio plazo (50 días) está subiendo o bajando.',
                           interpret: v => v > 0 ? 'Tendencia de medio plazo al alza' : 'Tendencia de medio plazo a la baja' },
    sma200_regime:       { label: 'Régimen de mercado',        desc: 'Indica si el mercado está en una fase alcista o bajista de largo plazo (basado en la media de 200 días).' },

    // RSI y momentum
    rsi:                 { label: 'RSI — Fuerza relativa',     desc: 'Mide si el activo está sobrecomprado (>70, puede corregir) o sobrevendido (<30, puede rebotar). Oscila entre 0 y 100.',
                           interpret: v => v >= 70 ? `RSI en ${v.toFixed(0)} — sobrecomprado, posible corrección` : v <= 30 ? `RSI en ${v.toFixed(0)} — sobrevendido, posible rebote` : v >= 55 ? `RSI en ${v.toFixed(0)} — impulso comprador` : v <= 45 ? `RSI en ${v.toFixed(0)} — impulso vendedor` : `RSI en ${v.toFixed(0)} — zona neutra` },
    rsi_14:              { alias: 'rsi' },
    momentum_5d:         { label: 'Impulso reciente (5 días)', desc: 'Variación acumulada del precio en los últimos 5 días. Mide la fuerza del movimiento a corto plazo.',
                           interpret: v => v > 0.02 ? 'Fuerte impulso alcista en los últimos días' : v < -0.02 ? 'Fuerte impulso bajista en los últimos días' : null },
    roc_10:              { label: 'Tasa de cambio (10 días)',   desc: 'Variación porcentual del precio en las últimas 10 sesiones.' },
    cci:                 { label: 'Índice de canal (CCI)',      desc: 'Detecta cuándo un activo está en niveles extremos. Por encima de +100 = sobrecompra; por debajo de -100 = sobreventa.',
                           interpret: v => v > 100 ? 'CCI en zona de sobrecompra' : v < -100 ? 'CCI en zona de sobreventa' : null },
    tsi:                 { label: 'Índice de fuerza real (TSI)', desc: 'Oscilador de impulso suavizado. Valores positivos indican presión compradora; negativos, vendedora.' },
    kst:                 { label: 'Indicador KST',             desc: 'Combina múltiples plazos de impulso para detectar cambios de tendencia.' },
    cmo:                 { label: 'Oscilador Chande (CMO)',     desc: 'Mide el impulso puro del precio sin suavizado. Rango -100 a +100.' },
    ultimate_osc:        { label: 'Oscilador múltiple',        desc: 'Combina impulso de corto, medio y largo plazo para reducir falsas señales.' },
    dx:                  { label: 'Fuerza de la tendencia (DX)', desc: 'Mide cuánta fuerza tiene la tendencia actual, sin distinguir si es alcista o bajista. Valores altos = tendencia clara.' },
    macd:                { label: 'MACD — Convergencia/divergencia', desc: 'Diferencia entre dos medias móviles. Positivo = tendencia alcista; negativo = bajista.',
                           interpret: v => v > 0 ? 'MACD positivo — impulso alcista de corto plazo' : 'MACD negativo — impulso bajista de corto plazo' },
    macd_signal:         { label: 'MACD vs su señal',          desc: 'Compara el MACD con su línea de confirmación. Cruces indican posibles cambios de tendencia.' },

    // Volatilidad
    bollinger_pctb:      { label: 'Bandas Bollinger (%B)',     desc: 'Posición del precio dentro de las bandas Bollinger. Valores >1 indican ruptura por arriba; <0, por abajo.',
                           interpret: v => v > 1 ? 'Precio rompiendo la banda superior — posible sobreextensión' : v < 0 ? 'Precio rompiendo la banda inferior — posible sobreextensión bajista' : null },
    bbands_pct:          { alias: 'bollinger_pctb' },
    atr:                 { label: 'Rango medio diario (ATR)',  desc: 'Medida de volatilidad: cuánto suele moverse el precio en una sesión típica.' },
    atr_14:              { alias: 'atr' },
    realized_vol:        { label: 'Volatilidad real reciente', desc: 'Volatilidad efectivamente observada en el periodo reciente. Alta = movimientos bruscos.' },
    volatility_std:      { label: 'Dispersión de los retornos', desc: 'Mide cuánto varían los retornos. Alta dispersión = mercado agitado.' },
    vix_close:           { label: 'VIX — Índice de miedo',    desc: 'Mide la expectativa de volatilidad del S&P 500. Alto (>25) = mercado nervioso; bajo (<15) = calma.',
                           interpret: v => v > 25 ? `VIX en ${v.toFixed(1)} — mercado nervioso, aversión al riesgo` : v < 15 ? `VIX en ${v.toFixed(1)} — mercado tranquilo` : null },

    // Volumen avanzado
    obv:                 { label: 'Volumen en balance (OBV)',  desc: 'Acumula volumen al alza y lo resta cuando el precio baja. Confirma si hay dinero real detrás del movimiento.' },
    obv_momentum:        { label: 'Impulso del volumen',       desc: 'Mide si la entrada de dinero (OBV) está acelerando o desacelerando.' },
    cmf:                 { label: 'Flujo de dinero Chaikin',   desc: 'Indica si hay más compra neta (positivo) o venta neta (negativo) en el periodo reciente.',
                           interpret: v => v > 0.1 ? 'Entrada neta de dinero — interés comprador' : v < -0.1 ? 'Salida neta de dinero — presión vendedora' : null },

    aroon_up:            { label: 'Aroon alcista',             desc: 'Mide cuántos días han pasado desde el último máximo reciente. Valores altos = tendencia alcista reciente.' },
    aroon_down:          { label: 'Aroon bajista',             desc: 'Mide cuántos días han pasado desde el último mínimo reciente. Valores altos = tendencia bajista reciente.' },

    // Macro
    nasdaq_return:       { label: 'Comportamiento del NASDAQ', desc: 'Variación reciente del índice NASDAQ. Refleja el contexto global del mercado tecnológico.',
                           interpret: v => v > 0 ? 'El mercado tecnológico global sube — contexto favorable' : 'El mercado tecnológico global baja — contexto desfavorable' },
    dollar_proxy:        { label: 'Fortaleza del dólar',       desc: 'Un dólar fuerte suele presionar a la baja materias primas y activos de riesgo.' },
    real_rates_proxy:    { label: 'Tipos de interés reales',   desc: 'Tipos ajustados por inflación. Subidas presionan a los activos de riesgo como acciones.' },
    risk_sentiment:      { label: 'Apetito de riesgo global',  desc: 'Mide si los inversores están asumiendo riesgo ("risk-on") o buscando refugio ("risk-off").' },
    industrial_demand:   { label: 'Demanda industrial',        desc: 'Indicador de actividad económica real, relevante para materias primas y sectores cíclicos.' },

    // Sentimiento de noticias
    sentiment_score:     { label: 'Sentimiento de noticias',  desc: 'Puntuación IA sobre el tono de las noticias recientes. +1 = muy positivo, -1 = muy negativo.',
                           interpret: v => v > 0.2 ? 'Noticias recientes con tono claramente positivo' : v < -0.2 ? 'Noticias recientes con tono claramente negativo' : 'Noticias con tono neutro o mixto' },
    sentiment_magnitude: { label: 'Intensidad de las noticias', desc: 'Cuánta carga emocional tienen las noticias, independientemente de si son buenas o malas.' },
    news_volume:         { label: 'Cantidad de noticias',      desc: 'Número de noticias recientes sobre el activo. Picos suelen preceder movimientos de precio.' },
    sentiment_ma_3d:     { label: 'Sentimiento medio (3 días)', desc: 'Promedio del sentimiento de noticias de los últimos 3 días.' },
    sentiment_ma_5d:     { label: 'Sentimiento medio (5 días)', desc: 'Promedio del sentimiento de noticias de los últimos 5 días.' },
    sentiment_momentum_5d: { label: 'Tendencia del sentimiento', desc: 'Indica si el tono de las noticias está mejorando o empeorando en los últimos 5 días.',
                           interpret: v => v > 0 ? 'El tono de las noticias está mejorando' : 'El tono de las noticias se está deteriorando' },
    sentiment_deviation: { label: 'Anomalía en el sentimiento', desc: 'Cuánto se aleja el sentimiento actual de su media histórica. Valores extremos indican noticias inusuales.' },
    sentiment_vol_normalized: { label: 'Sentimiento ponderado', desc: 'Sentimiento ajustado por la cantidad de noticias, para evitar que una sola noticia distorsione la señal.' },
    sentiment_lag_1d:    { label: 'Sentimiento de ayer',       desc: 'Tono de las noticias del día anterior.' },
    sentiment_lag_2d:    { label: 'Sentimiento de hace 2 días', desc: 'Tono de las noticias de hace 2 días.' },
    sentiment_lag_3d:    { label: 'Sentimiento de hace 3 días', desc: 'Tono de las noticias de hace 3 días.' },
    sentiment_lag_4d:    { label: 'Sentimiento de hace 4 días', desc: 'Tono de las noticias de hace 4 días.' },
    sentiment_lag_5d:    { label: 'Sentimiento de hace 5 días', desc: 'Tono de las noticias de hace 5 días.' },
    sentiment_vol_norm_lag_1d: { label: 'Sentimiento ponderado de ayer', desc: 'Sentimiento ponderado del día anterior.' },
    sentiment_vol_norm_lag_2d: { label: 'Sentimiento ponderado (2d)', desc: 'Sentimiento ponderado de hace 2 días.' },
  };

  // ── Parser de nombres técnicos compuestos ───────────────────────────────────
  // Descompone nombres como "SMA50_Slope_sw15_std" en partes legibles.

  // Sufijos de contexto temporal que añaden info a la label
  const SUFFIX_LABELS = {
    last:  null,          // "último valor" — no añade nada, es el comportamiento por defecto
    mean:  'promedio',
    std:   'variabilidad',
    trend: 'tendencia',
  };

  // Fragmentos del nombre base a normalizar antes de buscar en META
  // Permite resolver "SMA50_Slope" → "sma50_slope", "RSI" → "rsi", etc.
  function _normKey(s) {
    return s.toLowerCase().replace(/[^a-z0-9]/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '');
  }

  function _parseFeatureName(raw) {
    if (!raw) return { label: raw || '', desc: '' };
    let name = raw.trim();

    // Extraer _sw{N} (sliding window, ej. "sw15")
    let windowSize = null;
    const swMatch = name.match(/_sw(\d+)/i);
    if (swMatch) { windowSize = parseInt(swMatch[1], 10); name = name.replace(swMatch[0], ''); }

    // Extraer sufijo _last/_mean/_std/_trend
    let suffixLabel = null;
    const suffixMatch = name.match(/_(last|mean|std|trend)$/i);
    if (suffixMatch) {
      suffixLabel = SUFFIX_LABELS[suffixMatch[1].toLowerCase()];
      name = name.slice(0, -suffixMatch[0].length);
    }

    // Buscar la base en META (insensible a mayúsculas y guiones)
    const key = _normKey(name);
    let meta = META[key];
    if (meta && meta.alias) meta = META[_normKey(meta.alias)];

    // Construir etiqueta legible
    let label = meta ? meta.label : name.replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase());

    // Añadir contexto de ventana y sufijo si aplica
    const parts = [];
    if (windowSize)   parts.push(`${windowSize}d`);
    if (suffixLabel)  parts.push(suffixLabel);
    if (parts.length) label += ` (${parts.join(', ')})`;

    const desc = meta ? (meta.desc || '') : '';
    const interpret = meta && typeof meta.interpret === 'function' ? meta.interpret : null;

    return { label, desc, interpret };
  }

  // API pública — usada también por shapWaterfall.js para los tooltips
  window.parseFeatureName = _parseFeatureName;
  window.getFeatureGlossary = function (raw) {
    const p = _parseFeatureName(raw);
    return { label: p.label, desc: p.desc };
  };

  // ── Lógica de narración ─────────────────────────────────────────────────────

  const SIGNAL_INFO = {
    ALCISTA: { label: 'Alcista',  cls: 'alcista' },
    BAJISTA: { label: 'Bajista',  cls: 'bajista' },
    LATERAL: { label: 'Lateral',  cls: 'lateral' },
  };

  function _confidenceCtx(conf) {
    if (conf == null) return '';
    if (conf >= 0.65) return 'Alta confianza — el modelo ve señales claras en esta dirección.';
    if (conf >= 0.50) return 'Confianza moderada — hay algunas señales contradictorias.';
    return 'Baja confianza — señales mixtas; interpreta esta predicción con precaución.';
  }

  function _featurePhrase(item) {
    const parsed = _parseFeatureName(item.feature);
    const v = Number(item.value);
    const hasVal = !isNaN(v);
    const interp = parsed.interpret && hasVal ? parsed.interpret(v) : null;
    if (interp) return interp;
    const dir = item.shap >= 0 ? 'apunta al alza' : 'apunta a la baja';
    return `${parsed.label} — ${dir}`;
  }

  function _buildNarrative(data) {
    const values = (data.shap_values || []).slice().sort((a, b) => Math.abs(b.shap) - Math.abs(a.shap));
    if (!values.length) return null;

    const senal = (data.senal || 'LATERAL').toUpperCase();
    const info  = SIGNAL_INFO[senal] || SIGNAL_INFO.LATERAL;
    const conf  = typeof data.confianza === 'number' ? data.confianza : null;
    const pct   = conf != null ? Math.round(conf * 100) : null;

    let supporting, opposing;
    if (senal === 'ALCISTA')      { supporting = values.filter(d => d.shap > 0); opposing = values.filter(d => d.shap < 0); }
    else if (senal === 'BAJISTA') { supporting = values.filter(d => d.shap < 0); opposing = values.filter(d => d.shap > 0); }
    else                          { supporting = []; opposing = values; }

    return { senal, info, conf, pct, topSupport: supporting.slice(0, 3), topOppose: opposing.slice(0, 2) };
  }

  function _esc(s) {
    return String(s).replace(/[&<>"']/g, ch => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' })[ch]);
  }

  function _renderHTML(n) {
    const { senal, info, pct, conf, topSupport, topOppose } = n;

    const verdictText = senal === 'LATERAL'
      ? `Movimiento lateral esperado${pct != null ? ` — ${pct}% de confianza` : ''}`
      : `Señal ${info.label.toLowerCase()} — ${pct != null ? `${pct}% de confianza` : 'sin confianza calculada'}`;

    const confLine = _confidenceCtx(conf);

    const supportHTML = topSupport.length
      ? `<div class="narr-block">
          <div class="narr-block-title narr-block-title--support">A favor de esta predicción</div>
          <ul class="narr-list">${topSupport.map(d => `<li>${_esc(_featurePhrase(d))}</li>`).join('')}</ul>
        </div>`
      : senal === 'LATERAL'
        ? `<div class="narr-block"><p class="narr-muted">Ningún factor destaca con fuerza en una dirección — de ahí la señal lateral.</p></div>`
        : '';

    const opposeHTML = topOppose.length
      ? `<div class="narr-block">
          <div class="narr-block-title narr-block-title--oppose">Factores que frenan la señal</div>
          <ul class="narr-list">${topOppose.map(d => `<li>${_esc(_featurePhrase(d))}</li>`).join('')}</ul>
        </div>`
      : '';

    return `
<div class="narr-card narr-card--${info.cls}">
  <div class="narr-head">
    <span class="shap-badge shap-badge--${info.cls}" aria-label="Señal ${info.label}">${info.label}</span>
    <div class="narr-head-text">
      <p class="narr-verdict">${_esc(verdictText)}</p>
      ${confLine ? `<p class="narr-conf">${_esc(confLine)}</p>` : ''}
    </div>
  </div>
  <div class="narr-factors">
    ${supportHTML}
    ${opposeHTML}
  </div>
  <p class="narr-disclaimer">
    Predicción estadística basada en datos históricos. No es una recomendación de inversión.
    El modelo puede equivocarse ante eventos imprevistos (resultados, noticias macro, etc.).
  </p>
</div>`;
  }

  window.renderShapNarrative = function (data) {
    const el = document.getElementById('shapNarrative');
    if (!el) return;
    if (!data || !data.shap_values) { el.innerHTML = ''; return; }
    const n = _buildNarrative(data);
    el.innerHTML = n ? _renderHTML(n) : '';
  };
}());
