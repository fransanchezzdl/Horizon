/**
 * Lógica de registro para la página de register
 * Similar a login.js pero llama a /register
 */

const API_BASE = window.API_BASE;

document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('access_token');
    if (token) {
        window.location.href = 'index.html';
        return;
    }

    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
});

async function handleRegister(e) {
    e.preventDefault();

    const nombre = document.getElementById('nombre').value.trim();
    const apellidos = document.getElementById('apellidos').value.trim();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value.trim();
    const errorMsg = document.getElementById('errorMessage');
    const btn = e.target.querySelector('button');

    errorMsg.textContent = '';
    errorMsg.style.display = 'none';

    if (!email || !password) {
        showError(errorMsg, 'Por favor completa email y contraseña');
        return;
    }

    if (!isValidEmail(email)) {
        showError(errorMsg, 'Por favor ingresa un email válido');
        return;
    }

    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Creando...';

    try {
        const response = await fetch(`${API_BASE}/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                nombre: nombre || null,
                apellidos: apellidos || null,
                email: email, 
                password: password 
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Error al registrarse');
        }

        // Guardar token y datos de usuario si vienen
        if (data.access_token) {
            localStorage.setItem('access_token', data.access_token);
        }
        if (data.user) {
            localStorage.setItem('user_data', JSON.stringify(data.user));
        }

        window.location.href = 'index.html';

    } catch (err) {
        console.error('[REGISTER] Error:', err);
        showError(errorMsg, err.message || 'Error de conexión con el servidor');
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function showError(element, message) {
    element.textContent = message;
    element.style.display = 'block';
    element.classList.add('shake');
    setTimeout(() => element.classList.remove('shake'), 500);
}
