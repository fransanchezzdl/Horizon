// Búsqueda de activos contra la API del backend
const API_BASE = window.API_BASE;

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

function normalizeActivoPayload(rawActivo) {
    if (!rawActivo || typeof rawActivo !== 'object') {
        return {};
    }

    return {
        ...rawActivo,
        confianza_bygru: rawActivo.confianza_bygru,
        senal_ia: rawActivo.senal_ia,
        grafico_prediccion: rawActivo.grafico_prediccion
    };
}

function parseGraficoData(graficoPrediccion) {
    if (!graficoPrediccion) return null;
    if (typeof graficoPrediccion === 'object') return graficoPrediccion;

    if (typeof graficoPrediccion === 'string') {
        try {
            return JSON.parse(graficoPrediccion);
        } catch {
            return null;
        }
    }

    return null;
}

function renderGraficoPrediccion(graficoPrediccion) {
    const chartContainer = document.getElementById('predictionChartContainer');
    if (!chartContainer) return;

    const data = parseGraficoData(graficoPrediccion);
    if (!data) {
        chartContainer.style.display = 'flex';
        chartContainer.style.alignItems = 'center';
        chartContainer.style.justifyContent = 'center';
        chartContainer.style.color = '#9ca3af';
        chartContainer.innerHTML = 'Sin datos de predicción';
        return;
    }

    const metrics = [
        { label: 'Precio actual', value: data.current_price },
        { label: 'Precio predicho', value: data.predicted_price },
        { label: 'Rango superior', value: data.price_upper },
        { label: 'Rango inferior', value: data.price_lower },
        { label: 'Retorno %', value: data.predicted_return_pct },
        { label: 'Meta tendencia', value: data.meta_trend }
    ].filter((item) => item.value !== undefined && item.value !== null);

    if (metrics.length === 0) {
        chartContainer.style.display = 'flex';
        chartContainer.style.alignItems = 'center';
        chartContainer.style.justifyContent = 'center';
        chartContainer.style.color = '#9ca3af';
        chartContainer.innerHTML = 'Sin datos de predicción';
        return;
    }

    chartContainer.style.display = 'grid';
    chartContainer.style.alignItems = 'stretch';
    chartContainer.style.justifyContent = 'stretch';
    chartContainer.style.gridTemplateColumns = 'repeat(2, minmax(0, 1fr))';
    chartContainer.style.gap = '10px';
    chartContainer.style.padding = '12px';
    chartContainer.style.color = '#111827';

    chartContainer.innerHTML = metrics
        .map((metric) => {
            const numeric = typeof metric.value === 'number'
                ? (metric.label.includes('%') ? `${metric.value.toFixed(2)}%` : metric.value.toFixed(2))
                : String(metric.value);

            return `
                <div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:10px;display:flex;flex-direction:column;gap:4px;">
                    <span style="font-size:12px;color:#6b7280;">${metric.label}</span>
                    <strong style="font-size:16px;color:#111827;">${numeric}</strong>
                </div>
            `;
        })
        .join('');
}

function initSearch() {
    const input = document.getElementById('tickerSearch');
    const suggestions = document.getElementById('suggestions');
    const searchBtn = document.getElementById('searchBtn');
    let activeIndex = -1;
    let debounceTimer = null;

    if (!input) return;

    // ── Renderizar sugerencias ──────────────────────────────────
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

    // ── Buscar activos en la API ────────────────────────────────
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

    // ── Seleccionar un activo y mostrar sus datos ───────────────
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

    // ── Actualizar la vista con los datos del activo ────────────
    function actualizarVista(activo) {
        // Nombre y ticker en la cabecera del resultado
        const resultCard = document.querySelector('.result-card');
        if (resultCard) {
            const h2 = resultCard.querySelector('h2');
            if (h2) h2.textContent = `${activo.nombre_completo} (${activo.ticker})`;
        }

        // Confianza LSTM
        const confianzaValue = document.getElementById('confianzaValue');
        const confianzaSub = document.getElementById('confianzaSub');
        const confidence = formatConfidence(activo.confianza_bygru);
        if (confianzaValue) confianzaValue.textContent = confidence.value;
        if (confianzaSub) confianzaSub.textContent = confidence.label;

        // Señal de IA
        const senalValue = document.getElementById('senalValue');
        if (senalValue) senalValue.textContent = formatSignal(activo.senal_ia);

        // Gráfico de predicción (render de datos JSON)
        renderGraficoPrediccion(activo.grafico_prediccion);
    }

    // ── Evento de escritura con debounce ────────────────────────
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

    // ── Navegación con teclado ──────────────────────────────────
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

    // ── Cerrar sugerencias al hacer click fuera ─────────────────
    document.addEventListener('click', (ev) => {
        if (!ev.target.closest('.input-wrap')) suggestions.hidden = true;
    });

    // ── Botón de búsqueda ───────────────────────────────────────
    searchBtn && searchBtn.addEventListener('click', () => {
        const val = input.value.trim();
        if (!val) return;
        suggestions.hidden = true;
        seleccionarActivo(val.toUpperCase());
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSearch);
} else {
    initSearch();
}
