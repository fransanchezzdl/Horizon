/**
 * Lógica principal del Dashboard (index.html)
 * Se encarga de validar la autenticación y personalizar la vista del usuario
 */

const API_BASE = window.API_BASE;

document.addEventListener('DOMContentLoaded', async () => {
    // ✅ VALIDAR AUTENTICACIÓN CENTRALIZADA
    const result = await window.validateAuthToken();
    
    if (!result.valid) {
        console.log('[AUTH] Token no válido, redirigiendo a login');
        window.clearAuthSession();
        window.location.replace('login.html');
        return;
    }
    
    // ✅ TOKEN VÁLIDO, usar datos del usuario
    window.setCurrentUserData(result.user);
    
    const nombreMostrar = window.getUserDisplayName(result.user, 'Inversor');

    const mensajeBienvenida = document.getElementById('mensaje-bienvenida');
    if (mensajeBienvenida) {
        mensajeBienvenida.textContent = `¡Bienvenido ${nombreMostrar}!`;
    }

    // Cargar reflexión aleatoria desde el backend
    cargarReflexion();
});

async function cargarReflexion() {
    try {
        // ✅ Usar fetchWithAuth para obtener token y manejar 401
        const response = await window.fetchWithAuth(`${API_BASE}/reflexion/aleatoria`);

        if (!response.ok) return; // fallback: mantiene la cita hardcoded

        const data = await response.json();

        const quoteEl = document.getElementById('reflexion-quote');
        const authorEl = document.getElementById('reflexion-author');
        const btnEl = document.getElementById('reflexion-btn');

        if (quoteEl) quoteEl.textContent = `${data.cita}`;
        if (authorEl) authorEl.textContent = `— ${data.autor}`;
        if (btnEl) btnEl.href = `reflexion.html?id=${data.id_reflexion}`;

    } catch (err) {
        // Red caída u otro error: la cita hardcoded permanece visible
        console.warn('No se pudo cargar la reflexión del día:', err);
    }
}
