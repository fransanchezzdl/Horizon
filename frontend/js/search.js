// ============================================================
// CONFIGURACION Y ESTADO
// ============================================================

// Base URL de la API usada para busquedas y operaciones de portfolio.
const API_BASE = window.API_BASE;

// Ticker actualmente seleccionado en la vista de analisis.
let selectedTicker = '';

// Lista de portfolios del usuario disponible para el modal.
let availablePortfolios = [];

function setAnalysisMode(mode) {
    const dashboard = document.getElementById('dashboard-contenido');
    if (!dashboard) {
        return;
    }

    if (mode === 'active') {
        dashboard.classList.remove('analysis-home');
        dashboard.classList.add('analysis-active');
        return;
    }

    dashboard.classList.remove('analysis-active');
    dashboard.classList.add('analysis-home');
}

// ============================================================
// UTILIDADES DE PRESENTACION (ANALISIS)
// ============================================================

// Renderiza el logo del activo en analisis con fallback SVG comun.
function renderTickerLogo(activoOrTicker, explicitLogoUrl = '') {
    const logoContainer = document.getElementById('tickerLogoContainer');
    if (!logoContainer) {
        return;
    }

    const logoRef = typeof activoOrTicker === 'object'
        ? activoOrTicker
        : explicitLogoUrl;

    window.renderAssetIcon(logoContainer, logoRef);
}

// Muestra mensaje de estado/errores dentro del modal de analisis.
function showAnalysisMessage(message, isError = true) {
    const errorDiv = document.getElementById('analysisPortfolioError');
    if (!errorDiv) return;
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    errorDiv.style.color = isError ? '#dc2626' : '#059669';
}

// Oculta y limpia el mensaje de estado del modal de analisis.
function hideAnalysisMessage() {
    const errorDiv = document.getElementById('analysisPortfolioError');
    if (!errorDiv) return;
    errorDiv.textContent = '';
    errorDiv.style.display = 'none';
}

// ============================================================
// FLUJO DE MODAL: ANADIR A PORTFOLIO
// ============================================================

// Abre el modal, fija el ticker seleccionado y carga portfolios del usuario.
function openAddPortfolioModal() {
    const modal = document.getElementById('addPortfolioModal');
    const selectedTickerInput = document.getElementById('selectedTickerInput');
    if (!modal || !selectedTickerInput || !selectedTicker) return;

    selectedTickerInput.value = selectedTicker || '';
    hideAnalysisMessage();
    modal.style.display = 'flex';
    loadUserPortfoliosForModal();
}

// Cierra el modal de anadir activo a portfolio.
function closeAddPortfolioModal() {
    const modal = document.getElementById('addPortfolioModal');
    if (!modal) return;
    modal.style.display = 'none';
}

// Renderiza el selector de portfolios o el bloque vacio si no hay portfolios.
function renderPortfolioOptionsInModal() {
    const select = document.getElementById('analysisPortfolioSelect');
    const selectionBlock = document.getElementById('portfolioSelectionBlock');
    const noPortfoliosBlock = document.getElementById('noPortfoliosBlock');
    const confirmBtn = document.getElementById('confirmAddPortfolioBtn');

    if (!select || !selectionBlock || !noPortfoliosBlock || !confirmBtn) return;

    if (!availablePortfolios.length) {
        selectionBlock.style.display = 'none';
        noPortfoliosBlock.style.display = 'block';
        confirmBtn.disabled = true;
        return;
    }

    selectionBlock.style.display = 'block';
    noPortfoliosBlock.style.display = 'none';
    confirmBtn.disabled = false;

    select.innerHTML = '';
    availablePortfolios.forEach((portfolio) => {
        const option = document.createElement('option');
        option.value = String(portfolio.id_portfolio);
        option.textContent = portfolio.nombre_portfolio;
        select.appendChild(option);
    });
}

// Consulta portfolios del usuario y actualiza el contenido del modal.
async function loadUserPortfoliosForModal() {
    try {
        const response = await window.fetchWithAuth(`${API_BASE}/portfolios`);
        if (!response.ok) {
            showAnalysisMessage('No se pudieron cargar los portfolios');
            return;
        }

        availablePortfolios = await response.json();
        renderPortfolioOptionsInModal();
    } catch (error) {
        console.error('Error cargando portfolios:', error);
        showAnalysisMessage('Error de conexion cargando portfolios');
    }
}

// Anade el ticker actual al portfolio seleccionado en el select del modal.
async function addTickerToSelectedPortfolio() {
    const select = document.getElementById('analysisPortfolioSelect');
    if (!select) return;

    const selectedPortfolioId = Number(select.value);
    if (!selectedPortfolioId || !selectedTicker) {
        showAnalysisMessage('Selecciona un portfolio y un ticker valido');
        return;
    }

    try {
        const response = await window.fetchWithAuth(`${API_BASE}/portfolios/${selectedPortfolioId}/activos`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ ticker: selectedTicker })
        });

        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            showAnalysisMessage(data.detail || 'No se pudo anadir el activo al portfolio');
            return;
        }

        showAnalysisMessage(`Activo ${selectedTicker} anadido correctamente`, false);
        setTimeout(() => closeAddPortfolioModal(), 900);
    } catch (error) {
        console.error('Error anadiendo activo:', error);
        showAnalysisMessage('Error de conexion al anadir el activo');
    }
}

// Anade el ticker actual a un portfolio por ID (usado tras crear uno nuevo).
async function addTickerToPortfolioById(portfolioId) {
    if (!portfolioId || !selectedTicker) {
        showAnalysisMessage('Portfolio o ticker invalido');
        return false;
    }

    try {
        const response = await window.fetchWithAuth(`${API_BASE}/portfolios/${portfolioId}/activos`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ ticker: selectedTicker })
        });

        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            showAnalysisMessage(data.detail || 'No se pudo anadir el activo al portfolio');
            return false;
        }

        return true;
    } catch (error) {
        console.error('Error anadiendo activo al nuevo portfolio:', error);
        showAnalysisMessage('Error de conexion al anadir el activo');
        return false;
    }
}

// Abre el modal compartido de creacion y, al crear, anade el ticker actual.
function openExistingCreatePortfolioFlow() {
    if (typeof window.showCreatePortfolioModal !== 'function') {
        showAnalysisMessage('No se pudo abrir el modal de creacion de portfolio');
        return;
    }

    window.showCreatePortfolioModal({
        onCreated: async (createdPortfolio) => {
            const newPortfolioId = createdPortfolio?.id_portfolio;
            if (!newPortfolioId) {
                showAnalysisMessage('Portfolio creado, pero no se pudo recuperar su ID');
                return;
            }

            const added = await addTickerToPortfolioById(newPortfolioId);
            await loadUserPortfoliosForModal();

            if (added) {
                showAnalysisMessage(`Portfolio creado y activo ${selectedTicker} anadido correctamente`, false);
                setTimeout(() => closeAddPortfolioModal(), 1200);
            }
        }
    });
}

// ============================================================
// FORMATEO Y NORMALIZACION DE DATOS
// ============================================================

// Convierte la confianza a porcentaje visible y etiqueta cualitativa.
function formatConfidence(confianza) {
    const numericConfidence = typeof confianza === 'string'
        ? Number(confianza)
        : confianza;

    if (typeof numericConfidence !== 'number' || Number.isNaN(numericConfidence)) {
        return { value: '--', label: 'Sin datos' };
    }

    const percentage = numericConfidence <= 1 ? numericConfidence * 100 : numericConfidence;
    const rounded = Math.round(percentage);

    let label = 'Media';
    if (rounded >= 75) label = 'Alta';
    else if (rounded < 45) label = 'Baja';

    return { value: `${rounded}%`, label };
}

// Normaliza el texto de senal para mostrarlo de forma consistente.
function formatSignal(senal) {
    if (!senal || typeof senal !== 'string') {
        return '--';
    }

    const normalized = senal.trim().toUpperCase();
    const map = {
        ALCISTA: 'ALCISTA',
        BAJISTA: 'BAJISTA',
        LATERAL: 'LATERAL'
    };

    return map[normalized] || normalized;
}

// Devuelve un payload de activo estandarizado para la vista de analisis.
function normalizeActivoPayload(rawActivo) {
    if (!rawActivo || typeof rawActivo !== 'object') {
        return {};
    }

    return {
        ...rawActivo,
        confianza_bygru: rawActivo.confianza_bygru,
        senal_ia: rawActivo.senal_ia
    };
}

function escapeHtml(value) {
    if (typeof value !== 'string') return '';
    return value
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

function formatNewsDate(dateValue) {
    if (!dateValue) return 'Fecha no disponible';

    const parsed = new Date(dateValue);
    if (Number.isNaN(parsed.getTime())) return 'Fecha no disponible';

    return parsed.toLocaleDateString('es-ES', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
    });
}

function formatNewsRelativeTime(dateValue) {
    if (!dateValue) return 'Sin busqueda reciente';

    const parsed = new Date(dateValue);
    if (Number.isNaN(parsed.getTime())) return 'Sin fecha de actualizacion';

    const diffMs = Date.now() - parsed.getTime();
    const diffMinutes = Math.floor(diffMs / 60000);

    if (diffMinutes < 1) return 'Actualizado hace unos segundos';
    if (diffMinutes < 60) return `Actualizado hace ${diffMinutes} min`;

    // No debería tardar más de 1 hora en actualizar nuevas noticias, pero se programa
    // por si acaso surge un error de actualización.
    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `Actualizado hace ${diffHours} h`;

    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `Actualizado hace ${diffDays} d`;

    return `Actualizado ${formatNewsDate(parsed.toISOString())}`;
}

function updateNewsUpdateBadge(metadata = {}) {
    const badge = document.getElementById('newsUpdateBadge');
    if (!badge) return;

    const relativeLabel = formatNewsRelativeTime(metadata.cachedAt);
    const exactDate = metadata.cachedAt ? formatNewsDate(metadata.cachedAt) : '';

    badge.textContent = relativeLabel;
    badge.classList.toggle('is-stale', Boolean(metadata.stale));
    badge.title = exactDate ? `Ultima actualizacion: ${exactDate}` : '';
}

function renderNewsCards(ticker, noticias, metadata = {}) {
    const newsList = document.getElementById('newsList');
    if (!newsList) return;

    updateNewsUpdateBadge(metadata);

    if (!Array.isArray(noticias) || noticias.length === 0) {
        newsList.innerHTML = `
            <div class="news-item-card news-item-card-status">
                <strong>No hay noticias recientes para ${escapeHtml((ticker || '').toUpperCase())}</strong>
                <p class="opt-info" style="margin-top:6px;">Prueba de nuevo en unos minutos.</p>
            </div>
        `;
        return;
    }

    newsList.innerHTML = noticias.map((noticia) => {
        const titulo = escapeHtml(noticia.titulo || 'Sin titulo');
        const resumen = escapeHtml(noticia.resumen || 'Sin resumen disponible.');
        const href = escapeHtml(noticia.url || '#');

        return `
            <article class="news-item-card">
                <a class="news-item-title" href="${href}" target="_blank" rel="noopener noreferrer">${titulo}</a>
                <p class="opt-info">${resumen}</p>
            </article>
        `;
    }).join('');
}

async function loadTickerNews(ticker) {
    const newsList = document.getElementById('newsList');
    updateNewsUpdateBadge();
    if (newsList) {
        newsList.innerHTML = `
            <div class="news-item-card news-item-card-status">
                <strong>Cargando noticias...</strong>
            </div>
        `;
    }

    try {
        const url = `${API_BASE}/activos/${encodeURIComponent(ticker)}/noticias?limit=3&_ts=${Date.now()}`;
        const response = await fetch(url, { cache: 'no-store' });

        if (!response.ok) {
            renderNewsCards(ticker, []);
            return;
        }

        const payload = await response.json();
        renderNewsCards(ticker, payload?.noticias || [], {
            cachedAt: payload?.cached_at,
            stale: payload?.stale === true,
        });
    } catch (error) {
        console.error('Error cargando noticias del ticker:', error);
        renderNewsCards(ticker, []);
    }
}

// ============================================================
// INICIALIZACION Y BUSQUEDA DE ACTIVOS
// ============================================================

// Inicializa la pagina de analisis: eventos UI, busqueda y render inicial.
function initSearch() {
    const input = document.getElementById('tickerSearch');
    const suggestions = document.getElementById('suggestions');
    const searchBtn = document.getElementById('searchBtn');
    const addToPortfolioBtn = document.getElementById('addToPortfolioBtn');
    const closeAddPortfolioModalBtn = document.getElementById('closeAddPortfolioModalBtn');
    const cancelAddPortfolioModalBtn = document.getElementById('cancelAddPortfolioBtn');
    const confirmAddPortfolioBtn = document.getElementById('confirmAddPortfolioBtn');
    const createPortfolioFromAnalysisBtn = document.getElementById('createPortfolioFromAnalysisBtn');
    let activeIndex = -1;
    let suggestionResults = [];
    let recommendedIndex = -1;
    let debounceTimer = null;

    if (!input) return;

    const queryTicker = new URLSearchParams(window.location.search).get('ticker');
    const normalizedQueryTicker = queryTicker?.trim().toUpperCase();

    setAnalysisMode('home');

    const resultCard = document.querySelector('.result-card');
    const h2 = resultCard?.querySelector('h2');
    if (h2) {
        h2.textContent = 'Selecciona un activo';
    }

    const newsTitle = document.getElementById('newsTitle');
    if (newsTitle) {
        newsTitle.textContent = 'Noticias';
    }

    renderNewsCards('', [], { cachedAt: null, stale: false });

    addToPortfolioBtn && addToPortfolioBtn.addEventListener('click', openAddPortfolioModal);
    closeAddPortfolioModalBtn && closeAddPortfolioModalBtn.addEventListener('click', closeAddPortfolioModal);
    cancelAddPortfolioModalBtn && cancelAddPortfolioModalBtn.addEventListener('click', closeAddPortfolioModal);
    confirmAddPortfolioBtn && confirmAddPortfolioBtn.addEventListener('click', addTickerToSelectedPortfolio);
    createPortfolioFromAnalysisBtn && createPortfolioFromAnalysisBtn.addEventListener('click', openExistingCreatePortfolioFlow);

    function updateSuggestionVisualState() {
        const items = suggestions.querySelectorAll('.suggestion-item');

        items.forEach((item, idx) => {
            const isActive = idx === activeIndex;
            const isRecommended = idx === recommendedIndex && activeIndex === -1;

            item.classList.toggle('active', isActive);

            // Reutiliza tokens existentes para sugerencia recomendada en gris.
            if (isRecommended) {
                item.classList.add('text-muted');
                item.style.background = 'var(--color-bg-lighter)';
            } else {
                item.classList.remove('text-muted');
                item.style.background = '';
            }
        });
    }

    // Renderiza la lista de sugerencias de ticker en el dropdown.
    function renderSuggestions(list) {
        suggestionResults = Array.isArray(list) ? list : [];
        suggestions.innerHTML = '';
        if (suggestionResults.length === 0) {
            recommendedIndex = -1;
            activeIndex = -1;
            suggestions.hidden = true;
            return;
        }

        recommendedIndex = 0;
        activeIndex = -1;
        suggestions.hidden = false;
        suggestionResults.forEach((t, idx) => {
            const li = document.createElement('li');
            li.className = 'suggestion-item';
            li.tabIndex = 0;
            li.innerHTML = `<span><span class="suggestion-symbol">${t.ticker}</span> <span class="suggestion-name">${t.nombre_completo}</span></span>`;
            li.addEventListener('click', () => {
                input.value = t.ticker;
                suggestions.hidden = true;
                seleccionarActivo(t.ticker);
            });
            li.addEventListener('mouseenter', () => {
                activeIndex = idx;
                updateSuggestionVisualState();
            });
            suggestions.appendChild(li);
        });

        updateSuggestionVisualState();
    }

    // Busca activos por texto libre en la API.
    async function buscarActivos(query) {
        try {
            const resp = await fetch(`${API_BASE}/activos?q=${encodeURIComponent(query)}`);
            if (!resp.ok) return [];
            return await resp.json();
        } catch (err) {
            console.error('Error buscando activos:', err);
            return [];
        }
    }

    // Carga un ticker concreto y actualiza la vista con su payload.
    async function seleccionarActivo(ticker) {
        try {
            const url = `${API_BASE}/activos/${encodeURIComponent(ticker)}?_ts=${Date.now()}`;
            const resp = await fetch(url, { cache: 'no-store' });
            if (!resp.ok) {
                return false;
            }
            const rawActivo = await resp.json();
            const activo = normalizeActivoPayload(rawActivo);
            actualizarVista(activo);
            return true;
        } catch (err) {
            console.error('Error obteniendo activo:', err);
            return false;
        }
    }

    // Refresca el bloque de resultados/metricas con el activo seleccionado.
    function actualizarVista(activo) {
        const titleElement = document.querySelector('.result-card h2');
        if (titleElement) {
            titleElement.textContent = `${activo.nombre_completo} (${activo.ticker})`;
        }

        const currentNewsTitle = document.getElementById('newsTitle');
        if (currentNewsTitle) {
            currentNewsTitle.textContent = `Noticias de ${activo.ticker}`;
        }

        renderTickerLogo(activo);
        selectedTicker = (activo.ticker || '').toUpperCase();
        setAnalysisMode('active');

        const senalValue = document.getElementById('senalValue');
        if (senalValue) senalValue.textContent = formatSignal(activo.senal_ia);

        if (typeof window.renderProbChart === 'function') {
            window.renderProbChart(activo.probabilidades_xgb || null, activo.senal_ia || '');
        }

        loadTickerNews(selectedTicker);
        loadReliabilityStats(selectedTicker);
        loadPrecioStats(selectedTicker, activo.precio);
        if (typeof window.initPriceSignalChart === 'function') {
            window.initPriceSignalChart(selectedTicker);
        }
        if (typeof window.initShapWaterfall === 'function') {
            window.initShapWaterfall(selectedTicker);
        }
    }

    // Carga y muestra las métricas de fiabilidad del modelo para el ticker.
    async function loadReliabilityStats(ticker) {
        const valueEl = document.getElementById('reliabilityValue');
        const subEl   = document.getElementById('reliabilitySub');
        if (!valueEl || !subEl) return;

        valueEl.textContent = '--';
        subEl.textContent   = 'Cargando...';

        try {
            const response = await fetch(`${API_BASE}/activos/${encodeURIComponent(ticker)}/reliability`);
            if (!response.ok) {
                subEl.textContent = 'Sin datos';
                return;
            }

            const data = await response.json();
            const wf   = data.walk_forward;
            const live = data.live;

            // Valor principal: walk-forward > live > base azar
            valueEl.style.color = '';
            if (wf && wf.ba_mean != null) {
                valueEl.textContent = `${wf.ba_mean.toFixed(1)}%`;
            } else if (live && live.resueltas > 0) {
                valueEl.textContent = `${live.accuracy}%`;
                valueEl.style.color = live.accuracy > data.baseline
                    //? 'var(--color-success)'
                    //: 'var(--color-danger)';
            } else {
                valueEl.textContent = `${data.baseline}%`;
                valueEl.style.color = 'var(--color-tertiary)';
            }

            // Subtexto: señal + conteo live
            const señalLabel = {
                FUERTE:    'Señal fuerte',
                MODERADA:  'Señal moderada',
                DÉBIL:     'Señal débil',
                SIN_SEÑAL: 'Sin señal clara',
                SIN_DATOS: 'Sin historial',
            }[data.señal] || data.señal;

            let subParts = [`${señalLabel} · ref. ${parseFloat(data.baseline).toFixed(1)}%`];

            if (live.resueltas > 0) {
                subParts.push(`${live.correctas}/${live.resueltas} aciertos`);
            } else if (live.total > 0) {
                subParts.push(`${live.total} pred. en seguimiento`);
            }

            subEl.textContent = subParts.join(' | ');

        } catch (err) {
            console.error('Error cargando fiabilidad:', err);
            subEl.textContent = 'No disponible';
        }
    }

    // Carga y muestra el precio actual y la variación diaria del ticker.
    async function loadPrecioStats(ticker, precioActual) {
        const valueEl = document.getElementById('precioValue');
        const subEl   = document.getElementById('precioSub');
        if (!valueEl || !subEl) return;

        // Mostrar precio actual mientras se calcula la variación
        if (precioActual != null) {
            valueEl.textContent = precioActual >= 1000
                ? `$${precioActual.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                : `$${precioActual.toFixed(2)}`;
        } else {
            valueEl.textContent = '--';
        }
        subEl.textContent = 'Cargando...';
        subEl.style.color = '';

        try {
            const response = await fetch(`${API_BASE}/activos/${encodeURIComponent(ticker)}/price-history?days=7`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();
            const candles = data.candles;

            if (!candles || candles.length < 2) {
                subEl.textContent = 'Sin datos de variación';
                return;
            }

            const prevClose = candles[candles.length - 2].close;
            const lastClose = candles[candles.length - 1].close;
            const variacion = ((lastClose - prevClose) / prevClose) * 100;
            const signo = variacion >= 0 ? '+' : '';

            subEl.textContent = `${signo}${variacion.toFixed(2)}% hoy`;
            subEl.style.color = variacion >= 0
                ? 'var(--color-success)'
                : 'var(--color-danger)';

        } catch (err) {
            console.error('Error cargando precio:', err);
            subEl.textContent = 'Variación no disponible';
            subEl.style.color = '';
        }
    }

    // Gestiona la escritura en el input con debounce para autocompletado.
    input.addEventListener('input', () => {
        const q = input.value.trim();
        if (q.length === 0) {
            suggestionResults = [];
            recommendedIndex = -1;
            activeIndex = -1;
            suggestions.hidden = true;
            return;
        }

        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(async () => {
            const results = await buscarActivos(q);
            renderSuggestions(results);
        }, 250);
    });

    // Permite navegar y seleccionar sugerencias con teclado.
    input.addEventListener('keydown', (e) => {
        const items = suggestions.querySelectorAll('.suggestion-item');
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            activeIndex = Math.min(activeIndex + 1, items.length - 1);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            activeIndex = Math.max(activeIndex - 1, 0);
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (activeIndex >= 0 && items[activeIndex]) {
                items[activeIndex].click();
            } else {
                searchBtn && searchBtn.click();
            }
        }
        updateSuggestionVisualState();
    });

    // Cierra sugerencias cuando el usuario hace click fuera del buscador.
    document.addEventListener('click', (ev) => {
        if (!ev.target.closest('.input-wrap')) suggestions.hidden = true;
    });

    // Ejecuta busqueda manual al pulsar el boton principal.
    searchBtn && searchBtn.addEventListener('click', () => {
        const val = input.value.trim();

        let tickerToSearch = '';
        if (activeIndex >= 0 && suggestionResults[activeIndex]) {
            tickerToSearch = suggestionResults[activeIndex].ticker;
        } else if (recommendedIndex >= 0 && suggestionResults[recommendedIndex]) {
            tickerToSearch = suggestionResults[recommendedIndex].ticker;
        } else if (val) {
            tickerToSearch = val.toUpperCase();
        }

        if (!tickerToSearch) return;

        input.value = tickerToSearch;
        suggestions.hidden = true;
        seleccionarActivo(tickerToSearch);
    });

    // Si llega ticker por query param (desde portfolio), lo carga al iniciar.
    if (normalizedQueryTicker) {
        input.value = normalizedQueryTicker;
        seleccionarActivo(normalizedQueryTicker);
    }

    // Selector de rango para la gráfica de precio
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.range-btn');
        if (!btn) return;
        const days = parseInt(btn.dataset.days, 10);
        if (!days) return;
        document.querySelectorAll('.range-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        if (typeof window.updatePriceSignalChart === 'function') {
            window.updatePriceSignalChart(days);
        }
    });
}

// Inicializa inmediatamente o al cargar DOM, segun estado del documento.
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSearch);
} else {
    initSearch();
}
