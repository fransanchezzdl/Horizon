/**
 * Lógica de la página de artículo de reflexión (reflexion.html)
 * Extrae el ?id= de la URL, carga el artículo desde el backend y puebla la página.
 */

const API_BASE = window.API_BASE;

function initReflexionPage() {
    const params = new URLSearchParams(window.location.search);
    const idReflexion = params.get('id');

    if (!idReflexion) {
        window.location.replace('index.html');
        return;
    }

    cargarArticulo(idReflexion);
}

// VALIDAR AUTENTICACIÓN CENTRALIZADA
(async () => {
    const result = await window.validateAuthToken();
    if (!result.valid) {
        window.clearAuthSession();
        window.location.replace('login.html');
        return;
    }

    window.setCurrentUserData(result.user);

    // Evita perder DOMContentLoaded si /auth/me responde después de que el DOM ya está listo.
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initReflexionPage, { once: true });
    } else {
        initReflexionPage();
    }
})();

async function cargarArticulo(id) {
    try {
        const response = await window.fetchWithAuth(`${API_BASE}/reflexion/${id}`);

        if (response.status === 404 || response.status === 401) {
            window.location.replace('index.html');
            return;
        }

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        poblarPagina(data);

    } catch (err) {
        console.error('Error cargando el artículo:', err);
        window.location.replace('index.html');
    }
}

function poblarPagina(data) {
    document.title = `${data.titulo_articulo} | Horizon`;

    setTexto('articulo-tema',         data.tema || '');
    setTexto('articulo-titulo',       data.titulo_articulo || '');
    setTexto('articulo-autor-texto',  data.autor || '');
    setTexto('articulo-cita',         `\u201c${data.cita}\u201d`);

    if (data.tiempo_lectura) {
        setTexto('articulo-tiempo-texto', `${data.tiempo_lectura} min de lectura`);
    } else {
        const tiempoEl = document.getElementById('articulo-tiempo');
        if (tiempoEl) tiempoEl.style.display = 'none';
    }

    // Contenido — cada párrafo separado por doble salto de línea
    const contenidoEl = document.getElementById('articulo-contenido');
    if (contenidoEl && data.contenido) {
        contenidoEl.innerHTML = data.contenido
            .split('\n\n')
            .filter(p => p.trim())
            .map(p => `<p>${p.trim()}</p>`)
            .join('');
    }

    // Tags
    const tagsEl = document.getElementById('articulo-tags');
    if (tagsEl && data.tags && data.tags.length > 0) {
        tagsEl.innerHTML = data.tags
            .map(tag => `<span class="tag-badge">${tag}</span>`)
            .join('');
    }
}

function setTexto(id, texto) {
    const el = document.getElementById(id);
    if (el) el.textContent = texto;
}
