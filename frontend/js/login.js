/**
 * Lógica de autenticación para la página de login
 * Maneja el formulario de login, validación de credenciales y sincronización con BD
 */

// Esperar a que el DOM esté cargado Y authAPI esté disponible
document.addEventListener('DOMContentLoaded', async () => {
    // Esperar a que authAPI esté definido
    let attempts = 0;
    while (typeof window.authAPI === 'undefined' && attempts < 50) {
        await new Promise(resolve => setTimeout(resolve, 10));
        attempts++;
    }

    if (typeof window.authAPI === 'undefined') {
        console.error('[LOGIN] Error: authAPI no está disponible');
        return;
    }

    await initializeLogin();
});

/**
 * Inicializar la página de login
 * Si ya está autenticado, redirigir a index
 */
async function initializeLogin() {
    try {
        const session = await window.authAPI.getCurrentSession();
        if (session) {
            window.location.href = 'index.html';
            return;
        }
    } catch (err) {
        console.error('[LOGIN] Error inicializando login:', err);
    }

    // Configurar el formulario de login
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
}

/**
 * Manejar el envío del formulario de login
 * Verifica credenciales en Supabase Auth y luego en tabla usuarios
 */
async function handleLogin(e) {
    e.preventDefault();

    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value.trim();
    const errorMsg = document.getElementById('errorMessage');
    const btn = e.target.querySelector('button');

    // Limpiar mensajes previos
    errorMsg.textContent = '';
    errorMsg.style.display = 'none';

    // Validar campos vacíos
    if (!email || !password) {
        showError(errorMsg, 'Por favor completa todos los campos');
        return;
    }

    // Validar formato email básico
    if (!isValidEmail(email)) {
        showError(errorMsg, 'Por favor ingresa un email válido');
        return;
    }

    // Deshabilitar botón y mostrar estado
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Verificando credenciales...';

    try {
        // 1. Intentar login con Supabase Auth
        console.log('[LOGIN] Iniciando login para:', email);
        const { user, error: authError } = await window.authAPI.signInWithPassword(email, password);

        if (authError) {
            // Error en autenticación (credenciales inválidas)
            console.error('[LOGIN] Error de autenticación:', authError);
            showError(errorMsg, authError.message || 'Email o contraseña incorrectos');
            return;
        }

        if (!user) {
            showError(errorMsg, 'Error inesperado. Por favor intenta de nuevo');
            return;
        }

        // 2. Login exitoso en Supabase Auth, ahora verificar en tabla usuarios
        console.log('[LOGIN] Autenticación exitosa, verificando tabla usuarios...');
        btn.textContent = 'Verificando perfil...';

        try {
            const userProfile = await window.authAPI.getUserProfile(user.id);
            console.log('[LOGIN] Perfil encontrado:', userProfile);
        } catch (profileError) {
            console.error('[LOGIN] Error obteniendo perfil:', profileError);

            // Diferenciar tipos de errores
            if (profileError.type === 'NOT_FOUND') {
                // Usuario no registrado en BD
                console.warn('[LOGIN] Usuario no registrado en tabla usuarios');
                showError(errorMsg, 'Usuario no registrado en el sistema');
                await window.authAPI.logout();
                return;
            } else if (profileError.type === 'RLS_DENIED') {
                // Error de RLS - políticas no configuradas
                console.warn('[LOGIN] Error de permisos RLS');
                showError(errorMsg, 'Error de permisos. Contacta a soporte');
                await window.authAPI.logout();
                return;
            } else {
                // Otro error
                showError(errorMsg, 'Error verificando perfil: ' + (profileError.message || 'Desconocido'));
                await window.authAPI.logout();
                return;
            }
        }

        // 3. Todo OK - redirigir a index
        console.log('[LOGIN] Login exitoso, redirigiendo a index...');
        window.location.href = 'index.html';

    } catch (err) {
        console.error('[LOGIN] Error inesperado:', err);
        showError(errorMsg, 'Ocurrió un error inesperado. Por favor intenta de nuevo');
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

/**
 * Validar formato de email
 */
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Mostrar mensaje de error
 */
function showError(element, message) {
    element.textContent = message;
    element.style.display = 'block';
}
