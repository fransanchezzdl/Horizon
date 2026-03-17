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

    // Configurar selector de fotos de perfil
    setupProfilePhotoSelector();
});

/**
 * Configura el selector de fotos de perfil
 */
function setupProfilePhotoSelector() {
    const photoOptions = document.querySelectorAll('.profile-photo-option:not(.upload)');
    const uploadOption = document.querySelector('.profile-photo-option.upload');
    const uploadInput = document.getElementById('profilePhotoUpload');
    const fotoPerfilUrl = document.getElementById('fotoPerfilUrl');

    // Seleccionar foto predeterminada
    photoOptions.forEach(option => {
        option.addEventListener('click', () => {
            // Remover selección anterior
            photoOptions.forEach(opt => opt.classList.remove('selected'));
            uploadOption.classList.remove('selected');
            // Marcar como seleccionada
            option.classList.add('selected');
            // Guardar URL
            const photoUrl = option.getAttribute('data-photo');
            fotoPerfilUrl.value = photoUrl;
        });
    });

    // Seleccionar por defecto la primera foto predeterminada
    const defaultOption = photoOptions[0];
    if (defaultOption) {
        defaultOption.classList.add('selected');
        const defaultPhotoUrl = defaultOption.getAttribute('data-photo') || '';
        fotoPerfilUrl.value = defaultPhotoUrl;
    }

    // Manejar carga de foto personalizada
    uploadInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        // Validar que sea imagen
        if (!file.type.startsWith('image/')) {
            alert('Por favor selecciona una imagen válida');
            uploadInput.value = '';
            return;
        }

        // Validar tamaño (máx 5MB)
        const maxSize = 5 * 1024 * 1024;
        if (file.size > maxSize) {
            alert('La imagen no debe superar 5MB');
            uploadInput.value = '';
            return;
        }

        try {
            // Mostrar preview mientras se carga
            const reader = new FileReader();
            reader.onload = (event) => {
                // Remover selección anterior
                photoOptions.forEach(opt => opt.classList.remove('selected'));
                // Marcar upload como seleccionado
                uploadOption.classList.add('selected');
                
                // Crear preview temporal
                const uploadLabel = uploadOption.querySelector('.upload-label');
                uploadLabel.innerHTML = '';
                
                const previewImg = document.createElement('img');
                previewImg.src = event.target.result;
                uploadLabel.appendChild(previewImg);

                // Guardar la foto en base64 o URL blob
                // NOTA: Para producción, deberías usar Supabase Storage
                // Por ahora guardaremos la URL blob
                fotoPerfilUrl.value = event.target.result;
            };
            reader.readAsDataURL(file);
        } catch (error) {
            console.error('Error al procesar imagen:', error);
            alert('Error al procesar la imagen');
        }
    });

    // Hacer el label clickeable para el input file
    const uploadLabel = uploadOption.querySelector('.upload-label');
    uploadLabel.style.cursor = 'pointer';
}

/**
 * Maneja el envío del formulario de registro
 */
async function handleRegister(e) {
    e.preventDefault();

    const nombre = document.getElementById('nombre').value.trim();
    const apellidos = document.getElementById('apellidos').value.trim();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value.trim();
    const fotoPerfil = document.getElementById('fotoPerfilUrl').value.trim();
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
                password: password,
                foto_perfil: fotoPerfil || null
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
