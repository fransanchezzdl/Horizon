// ============================================================
// CONFIGURACIÓN Y ESTADO
// ============================================================

// Base URL de la API usada para búsquedas y operaciones de portfolio.
const API_BASE = window.API_BASE;

// Ticker actualmente seleccionado en la vista de análisis.
let selectedTicker = 'AAPL';

// Lista de portfolios del usuario disponible para el modal.
let availablePortfolios = [];

// ============================================================
// UTILIDADES DE PRESENTACIÓN (ANÁLISIS)
// ============================================================

// Renderiza las iniciales del ticker en el avatar/fallback del resultado.
function renderTickerLogo(ticker) {
    const logoFallback = document.getElementById('tickerLogoFallback');

    if (!logoFallback) {
        return;
    }

    const normalizedTicker = (ticker || '').toUpperCase().trim();
    const fallbackText = normalizedTicker.slice(0, 2) || '--';
    logoFallback.textContent = fallbackText;
}

// Obtiene el ticker inicial desde la cabecera y pinta su fallback visual.
function renderInitialTickerLogo() {
    const resultCard = document.querySelector('.result-card');
    const h2 = resultCard?.querySelector('h2');
    const text = h2?.textContent || '';
    const match = text.match(/\(([^)]+)\)/);
    const ticker = match?.[1] || '';
    renderTickerLogo(ticker);
}

// Muestra mensaje de estado/errores dentro del modal de análisis.
function showAnalysisMessage(message, isError = true) {
    const errorDiv = document.getElementById('analysisPortfolioError');
    if (!errorDiv) return;
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    errorDiv.style.color = isError ? '#dc2626' : '#059669';
}

// Oculta y limpia el mensaje de estado del modal de análisis.
function hideAnalysisMessage() {
    const errorDiv = document.getElementById('analysisPortfolioError');
    if (!errorDiv) return;
    errorDiv.textContent = '';
    errorDiv.style.display = 'none';
}

// ============================================================
// FLUJO DE MODAL: AÑADIR A PORTFOLIO
// ============================================================

// Abre el modal, fija el ticker seleccionado y carga portfolios del usuario.
function openAddPortfolioModal() {
    const modal = document.getElementById('addPortfolioModal');
    const selectedTickerInput = document.getElementById('selectedTickerInput');
    if (!modal || !selectedTickerInput) return;

    selectedTickerInput.value = selectedTicker || '';
    hideAnalysisMessage();
    modal.style.display = 'flex';
    loadUserPortfoliosForModal();
}

// Cierra el modal de añadir activo a portfolio.
function closeAddPortfolioModal() {
    const modal = document.getElementById('addPortfolioModal');
    if (!modal) return;
    modal.style.display = 'none';
}

// Renderiza el selector de portfolios o el bloque vacío si no hay portfolios.
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
        showAnalysisMessage('Error de conexión cargando portfolios');
    }
}

// Añade el ticker actual al portfolio seleccionado en el select del modal.
async function addTickerToSelectedPortfolio() {
    const select = document.getElementById('analysisPortfolioSelect');
    if (!select) return;

    const selectedPortfolioId = Number(select.value);
    if (!selectedPortfolioId || !selectedTicker) {
        showAnalysisMessage('Selecciona un portfolio y un ticker válido');
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
            showAnalysisMessage(data.detail || 'No se pudo añadir el activo al portfolio');
            return;
        }

        showAnalysisMessage(`Activo ${selectedTicker} añadido correctamente`, false);
        setTimeout(() => closeAddPortfolioModal(), 900);
    } catch (error) {
        console.error('Error añadiendo activo:', error);
        showAnalysisMessage('Error de conexión al añadir el activo');
    }
}

// Añade el ticker actual a un portfolio por ID (usado tras crear uno nuevo).
async function addTickerToPortfolioById(portfolioId) {
    if (!portfolioId || !selectedTicker) {
        showAnalysisMessage('Portfolio o ticker inválido');
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
            showAnalysisMessage(data.detail || 'No se pudo añadir el activo al portfolio');
            return false;
        }

        return true;
    } catch (error) {
        console.error('Error añadiendo activo al nuevo portfolio:', error);
        showAnalysisMessage('Error de conexión al añadir el activo');
        return false;
    }
}

// Abre el modal compartido de creación y, al crear, añade el ticker actual.
function openExistingCreatePortfolioFlow() {
    if (typeof window.showCreatePortfolioModal !== 'function') {
        showAnalysisMessage('No se pudo abrir el modal de creación de portfolio');
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
                showAnalysisMessage(`Portfolio creado y activo ${selectedTicker} añadido correctamente`, false);
                setTimeout(() => closeAddPortfolioModal(), 1200);
            }
        }
    });
}

// ============================================================
// FORMATEO Y NORMALIZACIÓN DE DATOS
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

// Normaliza el texto de señal para mostrarlo de forma consistente.
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

// Devuelve un payload de activo estandarizado para la vista de análisis.
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
// INICIALIZACIÓN Y BÚSQUEDA DE ACTIVOS
// ============================================================

// Inicializa la página de análisis: eventos UI, búsqueda y render inicial.
function initSearch() {
    const input = document.getElementById('tickerSearch');
    const suggestions = document.getElementById('suggestions');
    const searchBtn = document.getElementById('searchBtn');
    const addToPortfolioBtn = document.getElementById('addToPortfolioBtn');
    const closeAddPortfolioModalBtn = document.getElementById('closeAddPortfolioModalBtn');
    const cancelAddPortfolioBtn = document.getElementById('cancelAddPortfolioBtn');
    const confirmAddPortfolioBtn = document.getElementById('confirmAddPortfolioBtn');
    const createPortfolioFromAnalysisBtn = document.getElementById('createPortfolioFromAnalysisBtn');
    let activeIndex = -1;
    let debounceTimer = null;

    if (!input) return;

    // Render inicial del logo según el ticker que viene en la cabecera
    renderInitialTickerLogo();

    const resultCard = document.querySelector('.result-card');
    const h2 = resultCard?.querySelector('h2');
    const initialMatch = h2?.textContent?.match(/\(([^)]+)\)/);
    if (initialMatch?.[1]) {
        selectedTicker = initialMatch[1].toUpperCase();
    }

    addToPortfolioBtn && addToPortfolioBtn.addEventListener('click', openAddPortfolioModal);
    closeAddPortfolioModalBtn && closeAddPortfolioModalBtn.addEventListener('click', closeAddPortfolioModal);
    cancelAddPortfolioBtn && cancelAddPortfolioBtn.addEventListener('click', closeAddPortfolioModal);
    confirmAddPortfolioBtn && confirmAddPortfolioBtn.addEventListener('click', addTickerToSelectedPortfolio);
    createPortfolioFromAnalysisBtn && createPortfolioFromAnalysisBtn.addEventListener('click', openExistingCreatePortfolioFlow);

    // Renderiza la lista de sugerencias de ticker en el dropdown.
    function renderSuggestions(list) {
        suggestions.innerHTML = '';
        if (list.length === 0) { suggestions.hidden = true; return; }
        suggestions.hidden = false;
        list.forEach((t) => {
            const li = document.createElement('li');
            li.className = 'suggestion-item';
            li.tabIndex = 0;
            li.innerHTML = `<span><span class="suggestion-symbol">${t.ticker}</span> <span class="suggestion-name">${t.nombre_completo}</span></span>`;
            li.addEventListener('click', () => {
                input.value = t.ticker;
                suggestions.hidden = true;
                seleccionarActivo(t.ticker);
            });
            suggestions.appendChild(li);
        });
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
            if (!resp.ok) return;
            const rawActivo = await resp.json();
            const activo = normalizeActivoPayload(rawActivo);
            actualizarVista(activo);
        } catch (err) {
            console.error('Error obteniendo activo:', err);
        }
    }

    // Refresca el bloque de resultados/métricas con el activo seleccionado.
    function actualizarVista(activo) {
        // Nombre y ticker en la cabecera del resultado
        const resultCard = document.querySelector('.result-card');
        if (resultCard) {
            const h2 = resultCard.querySelector('h2');
            if (h2) h2.textContent = `${activo.nombre_completo} (${activo.ticker})`;
        }

        renderTickerLogo(activo.ticker);
        selectedTicker = (activo.ticker || '').toUpperCase();

        // Confianza LSTM
        const confianzaValue = document.getElementById('confianzaValue');
        const confianzaSub = document.getElementById('confianzaSub');
        const confidence = formatConfidence(activo.confianza_bygru);
        if (confianzaValue) confianzaValue.textContent = confidence.value;
        if (confianzaSub) confianzaSub.textContent = confidence.label;

        // Señal de IA
        const senalValue = document.getElementById('senalValue');
        if (senalValue) senalValue.textContent = formatSignal(activo.senal_ia);

        // El bloque de predicción queda estático en HTML en esta fase
    }

    // Gestiona la escritura en el input con debounce para autocompletado.
    input.addEventListener('input', () => {
        const q = input.value.trim();
        if (q.length === 0) { suggestions.hidden = true; return; }
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(async () => {
            const results = await buscarActivos(q);
            renderSuggestions(results);
            activeIndex = -1;
        }, 250);
    });

    // Permite navegar y seleccionar sugerencias con teclado.
    input.addEventListener('keydown', (e) => {
        const items = suggestions.querySelectorAll('.suggestion-item');
        if (e.key === 'ArrowDown') { e.preventDefault(); activeIndex = Math.min(activeIndex + 1, items.length - 1); }
        else if (e.key === 'ArrowUp') { e.preventDefault(); activeIndex = Math.max(activeIndex - 1, 0); }
        else if (e.key === 'Enter') {
            e.preventDefault();
            if (activeIndex >= 0 && items[activeIndex]) { items[activeIndex].click(); }
            else { searchBtn && searchBtn.click(); }
        }
        items.forEach((it, idx) => it.classList.toggle('active', idx === activeIndex));
    });

    // Cierra sugerencias cuando el usuario hace click fuera del buscador.
    document.addEventListener('click', (ev) => {
        if (!ev.target.closest('.input-wrap')) suggestions.hidden = true;
    });

    // Ejecuta búsqueda manual al pulsar el botón principal.
    searchBtn && searchBtn.addEventListener('click', () => {
        const val = input.value.trim();
        if (!val) return;
        suggestions.hidden = true;
        seleccionarActivo(val.toUpperCase());
    });
}

// Inicializa inmediatamente o al cargar DOM, según estado del documento.
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSearch);
} else {
    initSearch();
}
