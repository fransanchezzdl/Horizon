/**
 * Lógica principal del Dashboard (index.html)
 * Se encarga de proteger la ruta y personalizar la vista del usuario
 */
checkLogin();

const API_BASE = window.API_BASE;

document.addEventListener('DOMContentLoaded', () => {
    const user = window.getCurrentUserData();
    const nombreMostrar = window.getUserDisplayName(user, 'Inversor');

    const mensajeBienvenida = document.getElementById('mensaje-bienvenida');
    if (mensajeBienvenida) {
        mensajeBienvenida.textContent = `¡Bienvenido ${nombreMostrar}!`;
    }

    // Cargar reflexión aleatoria desde el backend
    cargarReflexion();
});

async function cargarReflexion() {
    const token = window.getAccessToken();
    if (!token) return;

    try {
        const response = await fetch(`${API_BASE}/reflexion/aleatoria`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) return; // fallback: mantiene la cita hardcoded

        const data = await response.json();

        const quoteEl = document.getElementById('reflexion-quote');
        const authorEl = document.getElementById('reflexion-author');
        const btnEl = document.getElementById('reflexion-btn');

        if (quoteEl) quoteEl.textContent = `“${data.cita}”`;
        if (authorEl) authorEl.textContent = `— ${data.autor}`;
        if (btnEl) btnEl.href = `reflexion.html?id=${data.id_reflexion}`;

    } catch (err) {
        // Red caída u otro error: la cita hardcoded permanece visible
        console.warn('No se pudo cargar la reflexión del día:', err);
    }
}

function checkLogin() {
    const token = window.getAccessToken();

    // Si no hay token, redirigimos al login inmediatamente
    if (!token) {
        window.location.replace('login.html');
    }
}