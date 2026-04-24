/**
 * Lógica de registro para la página de register
 * Similar a login.js pero llama a /register
 */

const API_BASE = window.API_BASE;
let selectedCustomAvatarFile = null;

document.addEventListener('DOMContentLoaded', () => {
    const token = window.getAccessToken();
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
            selectedCustomAvatarFile = null;

            const uploadLabel = uploadOption.querySelector('.upload-label');
            uploadLabel.innerHTML = '<span class="plus-icon">+</span>';
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

                // La imagen personalizada se sube después del registro
                // usando el endpoint /usuarios/me/avatar (multipart/form-data)
                fotoPerfilUrl.value = '';
                selectedCustomAvatarFile = file;
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
    const confirmPassword = document.getElementById('confirmPassword').value.trim();
    const fotoPerfil = document.getElementById('fotoPerfilUrl').value.trim();
    const errorMsg = document.getElementById('errorMessage');
    const btn = e.target.querySelector('button');

    errorMsg.textContent = '';
    errorMsg.style.display = 'none';

    if (!email || !password || !confirmPassword) {
        showError(errorMsg, 'Por favor completa email, contraseña y confirmación');
        return;
    }

    if (password !== confirmPassword) {
        showError(errorMsg, 'Las contraseñas no coinciden');
        return;
    }

    if (!isValidEmail(email)) {
        showError(errorMsg, 'Por favor ingresa un email válido');
        return;
    }

    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = selectedCustomAvatarFile ? 'Creando y subiendo foto...' : 'Creando...';

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
                // Solo enviamos URL de default si aplica. La personalizada va por endpoint aparte.
                foto_perfil: selectedCustomAvatarFile ? null : (fotoPerfil || null)
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Error al registrarse');
        }

        // Guardar token y datos de usuario si vienen
        if (data.access_token) {
            window.setAccessToken(data.access_token);
        }
        if (data.user) {
            window.setCurrentUserData(data.user);
        }

        // VALIDAR TOKEN CONTRA BACKEND (CENTRALIZADO)
        console.log('[REGISTER] Validando token contra /auth/me...');
        const validateResult = await window.validateAuthToken();
        
        if (!validateResult.valid) {
            console.error('[REGISTER] Token validation failed');
            throw new Error('Token validation failed');
        }
        
        // Token válido, usar datos validados
        window.setCurrentUserData(validateResult.user);
        console.log('[REGISTER] Token validado correctamente ✓');

        if (selectedCustomAvatarFile) {
            const token = window.getAccessToken();
            const formData = new FormData();
            formData.append('file', selectedCustomAvatarFile);

            const avatarRes = await fetch(`${API_BASE}/usuarios/me/avatar`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
                body: formData,
            });

            const avatarData = await avatarRes.json();
            if (!avatarRes.ok) {
                throw new Error(avatarData.detail || 'No se pudo subir la foto de perfil');
            }

            window.setCurrentUserData(avatarData);
            console.log('[REGISTER] Foto personalizada subida correctamente ✓');
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
