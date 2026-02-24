/**
 * logout.js - Manejo de la lógica de cierre de sesión
 * Elimina las credenciales locales y redirige al login
 */

/**
 * Inicializa los event listeners para el botón de logout
 */
function initializeLogout() {
    const logoutBtn = document.getElementById('logoutBtn');
    
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
}

/**
 * Manejar logout del usuario
 * Limpia el localStorage y redirige al login
 */
function handleLogout() {
    try {
        console.log('[LOGOUT] Iniciando cierre de sesión...');

        // 1. Opcional: Feedback visual en el botón
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.disabled = true;
            logoutBtn.textContent = 'Cerrando sesión...';
        }

        // 2. LA MAGIA REAL: Destruir los datos de sesión local
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_data');
        
        // Por si acaso tu compañero usó sessionStorage en algún momento, lo limpiamos también
        sessionStorage.clear();

        console.log('[LOGOUT] Sesión cerrada localmente');

        // 3. Redirigir a login.html (usamos replace para que no puedan volver atrás)
        window.location.replace('login.html');
        
    } catch (err) {
        console.error('[LOGOUT] Error inesperado:', err);
        
        // Si algo falla, forzamos la expulsión por seguridad
        window.location.replace('login.html');
    }
}

// Inicializar cuando el DOM esté listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeLogout);
} else {
    initializeLogout();
}