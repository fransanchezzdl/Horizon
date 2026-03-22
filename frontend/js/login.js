/**
 * Lógica de autenticación para la página de login
 * Se comunica exclusivamente con el Backend FastAPI
 */

// URL del Backend (usar localhost en desarrollo)
const API_BASE = window.API_BASE;

document.addEventListener('DOMContentLoaded', () => {
    // 1. Verificación rápida de sesión local
    // Si ya tenemos token, no deberíamos estar en el login
    const token = window.getAccessToken();
    if (token) {
        window.location.href = 'index.html';
        return;
    }

    // 2. Configurar el formulario
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
});

/**
 * Manejar el envío del formulario
 * Envía credenciales al endpoint /login de FastAPI
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

    // Validar formato email básico (ahorra una llamada al servidor)
    if (!isValidEmail(email)) {
        showError(errorMsg, 'Por favor ingresa un email válido');
        return;
    }

    // UX: Deshabilitar botón y mostrar estado
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Autenticando...';

    try {
        //Llamamos a la API en lugar de supabase directamente
        const response = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                email: email, 
                password: password 
            })
        });

        const data = await response.json();

        if (!response.ok) {
            // Si FastAPI devuelve 400, 401 o 500, lanzamos error
            // Asumimos que FastAPI envía el error en el campo "detail"
            throw new Error(data.detail || 'Error al iniciar sesión');
        }

        // --- ÉXITO ---
        console.log('[LOGIN] Login exitoso via API');
        
        // 1. Guardamos el token que nos devolvió FastAPI
        window.setAccessToken(data.access_token);

        // 2. Guardar datos del usuario si el backend los envía
        if (data.user) {
            window.setCurrentUserData(data.user);
        }

        // 3. VALIDAR TOKEN CONTRA BACKEND (CENTRALIZADO)
        console.log('[LOGIN] Validando token contra /auth/me...');
        const validateResult = await window.validateAuthToken();
        
        if (!validateResult.valid) {
            console.error('[LOGIN] Token validation failed');
            throw new Error('Token validation failed');
        }
        
        // Token válido, usar datos validados
        window.setCurrentUserData(validateResult.user);
        console.log('[LOGIN] Token validado correctamente ✓');

        // 4. Redirigir
        window.location.href = 'index.html';

    } catch (err) {
        console.error('[LOGIN] Error:', err);
        showError(errorMsg, err.message || 'Error de conexión con el servidor');
    } finally {
        // Restaurar botón
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

/**
 * Validar formato de email (Helper)
 */
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Mostrar mensaje de error (Helper)
 */
function showError(element, message) {
    element.textContent = message;
    element.style.display = 'block';
    // Opcional: Agregar una clase para animación de shake/temblor
    element.classList.add('shake');
    setTimeout(() => element.classList.remove('shake'), 500);
}