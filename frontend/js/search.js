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

        const confianzaValue = document.getElementById('confianzaValue');
        const confianzaSub = document.getElementById('confianzaSub');
        const confidence = formatConfidence(activo.confianza_bygru);
        if (confianzaValue) confianzaValue.textContent = confidence.value;
        if (confianzaSub) confianzaSub.textContent = confidence.label;

        const senalValue = document.getElementById('senalValue');
        if (senalValue) senalValue.textContent = formatSignal(activo.senal_ia);
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
}

// Inicializa inmediatamente o al cargar DOM, segun estado del documento.
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSearch);
} else {
    initSearch();
}
