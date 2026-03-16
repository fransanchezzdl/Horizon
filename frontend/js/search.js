// Búsqueda de activos contra la API del backend
const API_BASE = window.API_BASE;

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
            const resp = await fetch(`${API_BASE}/activos/${encodeURIComponent(ticker)}`);
            if (!resp.ok) return;
            const activo = await resp.json();
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

        // Noticias título
        const noticiasTitle = document.querySelector('.opt-title:last-of-type');
        if (noticiasTitle && noticiasTitle.textContent.startsWith('Noticias')) {
            noticiasTitle.textContent = `Noticias de ${activo.ticker}`;
        }
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
