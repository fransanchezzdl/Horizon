/**
 * logout.js - Manejo de la lógica de cierre de sesión
 * Similar a login.js, centraliza toda la lógica de logout
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
 * Cierra la sesión en Supabase y redirige al login
 */
async function handleLogout() {
    try {
        console.log('[LOGOUT] Iniciando logout...');
        
        // Esperar a que authAPI esté disponible
        if (typeof window.authAPI === 'undefined') {
            console.error('[LOGOUT] authAPI no disponible');
            window.location.href = 'login.html';
            return;
        }

        // Deshabilitar botón durante el proceso
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.disabled = true;
            logoutBtn.textContent = 'Cerrando...';
        }

        // Llamar a logout en Supabase
        const success = await window.authAPI.logout();
        
        if (success) {
            console.log('[LOGOUT] Sesión cerrada exitosamente');
        } else {
            console.warn('[LOGOUT] Error al cerrar sesión, redirigiendo a login');
        }

        // Redirigir a login.html
        window.location.href = 'login.html';
    } catch (err) {
        console.error('[LOGOUT] Error inesperado:', err);
        
        // Re-habilitar botón en caso de error
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.disabled = false;
            logoutBtn.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                    <polyline points="16 17 21 12 16 7"></polyline>
                    <line x1="21" y1="12" x2="9" y2="12"></line>
                </svg>
                <span>Cerrar Sesión</span>
            `;
        }
        
        // Forzar redirección a login incluso si hay error
        setTimeout(() => {
            window.location.href = 'login.html';
        }, 1000);
    }
}

// Inicializar cuando el DOM esté listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeLogout);
} else {
    initializeLogout();
}
