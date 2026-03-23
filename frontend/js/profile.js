const API_BASE = window.API_BASE;

let fotoBase64Temporal = ""; // Guardará el texto de la imagen

function initProfilePage() {
    loadProfileData();
    initProfileEvents();
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

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initProfilePage, { once: true });
    } else {
        initProfilePage();
    }
})();

// Cargar datos del perfil del usuario
function loadProfileData() {
    const user = window.getCurrentUserData();

    if (!user) {
        console.error('No user data found');
        window.location.href = 'login.html';
        return;
    }

    try {
        const nombreMostrar = window.getUserDisplayName(user, 'Usuario');
        const apellidos = (user.apellidos || '').trim();
        const nombreCompleto = user.nombre
            ? `${user.nombre}${apellidos ? ` ${apellidos}` : ''}`
            : nombreMostrar;
        const plan = window.getUserPlan(user, 'Free');

        document.getElementById('profileName').textContent = nombreCompleto;
        document.getElementById('profileEmail').textContent = user.email || 'Sin email';
        document.getElementById('profilePlan').textContent = `Plan ${plan}`;

        const profileAvatar = document.getElementById('profileAvatar');
        window.applyUserAvatar(profileAvatar, user, 'U');

        // Llenar formulario de información general
        document.getElementById('infoNombre').textContent = nombreCompleto;
        document.getElementById('infoEmail').textContent = user.email || 'Sin email';

        // Información de membresía
        document.getElementById('membershipPlan').textContent = plan;
        document.getElementById('membershipDate').textContent = formatDate(user.created_at || new Date().toISOString());

        // Cargar estadísticas (llamar a la API si es necesario)
        const userId = user.id_usuario || user.id;
        if (userId) {
            loadUserStats(userId);
        }

    } catch (e) {
        console.error('Error loading profile:', e);
        console.error('Stack:', e.stack);
        // No redirigir automáticamente, mostrar el error en consola
        // window.location.href = 'login.html';
    }
}

// Cargar estadísticas del usuario desde la API
async function loadUserStats(userId) {
    try {
        // Obtener todos los portfolios del usuario
        console.log('[INFO] Cargando estadisticas del usuario...');
        const portfolioRes = await window.fetchWithAuth(`${API_BASE}/portfolios`);

        if (portfolioRes.ok) {
            const portfolios = await portfolioRes.json();
            console.log('[OK] Portfolios cargados:', portfolios);
            
            // Mostrar total de portfolios
            const totalPortfolios = Array.isArray(portfolios) ? portfolios.length : 0;
            document.getElementById('statPredictions').textContent = totalPortfolios;
            console.log('[OK] Total portfolios:', totalPortfolios);
            
            // Contar total de activos en todos los portfolios
            let totalActivos = 0;
            
            for (const portfolio of portfolios) {
                const portfolioId = portfolio.id_portfolio;
                // Obtener detalles del portfolio con activos
                const detailRes = await window.fetchWithAuth(`${API_BASE}/portfolios/${portfolioId}`);
                if (detailRes.ok) {
                    const detail = await detailRes.json();
                    if (detail.acciones && Array.isArray(detail.acciones)) {
                        totalActivos += detail.acciones.length;
                    }
                }
            }
            
            console.log('[OK] Total activos encontrados:', totalActivos);
            document.getElementById('statPortfolio').textContent = totalActivos;
        } else {
            console.warn('[WARN] Error cargando portfolios:', portfolioRes.status);
            document.getElementById('statPortfolio').textContent = '0';
            document.getElementById('statPredictions').textContent = '0';
        }

    } catch (e) {
        console.warn('[ERROR] No se pudieron cargar las estadisticas:', e);
        document.getElementById('statPortfolio').textContent = '0';
        document.getElementById('statPredictions').textContent = '0';
    }
}

// Formatear fecha
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('es-ES', options);
}

// Event Listeners
function initProfileEvents() {
    // --- 1. NUEVA LÓGICA: EDITAR PERFIL ---
    const btnEditProfile = document.getElementById('btnEditProfile');
    const modalEditProfile = document.getElementById('modalEditProfile');
    const btnCancelEdit = document.getElementById('btnCancelEdit');
    const formEditProfile = document.getElementById('formEditProfile');

    if (btnEditProfile) {
        btnEditProfile.addEventListener('click', () => {
            const user = window.getCurrentUserData();
            
            // Crear preview si no existe
            if (!document.getElementById('previewFoto')) {
                const label = document.createElement('p');
                label.id = 'previewLabel';
                label.textContent = 'Vista Previa:';
                label.style.cssText = 'display:none; margin: 10px 0 5px 0; font-size: 0.9em; color: var(--color-text-secondary);';
                
                const preview = document.createElement('img');
                preview.id = 'previewFoto';
                preview.style.cssText = 'display:none; width:60px; height:60px; border-radius:50%; margin-top:10px;';
                preview.alt = 'Preview de foto';
                
                const fotoPerfilUrl = document.getElementById('fotoPerfilUrl');
                if (fotoPerfilUrl) {
                    fotoPerfilUrl.parentNode.insertBefore(label, fotoPerfilUrl);
                    fotoPerfilUrl.parentNode.insertBefore(preview, fotoPerfilUrl);
                }
            }
            
            // Llenamos los datos
            document.getElementById('editEmail').value = user.email || '';
            document.getElementById('editNombre').value = user.nombre || '';
            document.getElementById('editApellidos').value = user.apellidos || '';
            document.getElementById('editMessage').innerHTML = ''; 
            
            // Resetear selecciones de foto
            const photoOptions = document.querySelectorAll('.profile-photo-option:not(.upload)');
            photoOptions.forEach(opt => opt.classList.remove('selected'));
            document.getElementById('fotoPerfilUrl').value = "";
            fotoBase64Temporal = "";
            const preview = document.getElementById('previewFoto');
            if (preview) {
                preview.style.display = 'none';
            }
            const label = document.getElementById('previewLabel');
            if (label) {
                label.style.display = 'none';
            }

            // Mostrar foto actual si existe
            if (user.foto_perfil) {
                const defaultPhotos = [
                    "https://fzxtliowdmhumnxfskvy.supabase.co/storage/v1/object/public/avatars/default/default-1.png",
                    "https://fzxtliowdmhumnxfskvy.supabase.co/storage/v1/object/public/avatars/default/default-2.png",
                    "https://fzxtliowdmhumnxfskvy.supabase.co/storage/v1/object/public/avatars/default/default-3.png"
                ];
                if (defaultPhotos.includes(user.foto_perfil)) {
                    // Seleccionar la opción predeterminada
                    const option = document.querySelector(`.profile-photo-option[data-photo="${user.foto_perfil}"]`);
                    if (option) {
                        option.classList.add('selected');
                        document.getElementById('fotoPerfilUrl').value = user.foto_perfil;
                        const preview = document.getElementById('previewFoto');
                        if (preview) {
                            preview.src = user.foto_perfil;
                            preview.style.display = 'block';
                        }
                        const label = document.getElementById('previewLabel');
                        if (label) {
                            label.style.display = 'block';
                        }
                    }
                } else {
                    // Foto personalizada
                    const preview = document.getElementById('previewFoto');
                    if (preview) {
                        preview.src = user.foto_perfil;
                        preview.style.display = 'block';
                    }
                    const label = document.getElementById('previewLabel');
                    if (label) {
                        label.style.display = 'block';
                    }
                }
            }
            
            modalEditProfile.style.display = 'flex';
        });
    }

    // --- LEER LA IMAGEN CUANDO EL USUARIO LA SELECCIONA ---
    const inputFoto = document.getElementById('profilePhotoUpload');
    if (inputFoto) {
        inputFoto.addEventListener('change', function(evento) {
            const archivo = evento.target.files[0];
            if (!archivo) return;

            // Usamos FileReader para convertir la imagen a texto (Base64)
            const lector = new FileReader();
            lector.onload = function(e) {
                fotoBase64Temporal = e.target.result; // Guardamos el Base64
                
                // Actualizamos la miniatura para que el usuario vea su nueva foto
                const preview = document.getElementById('previewFoto');
                if (preview) {
                    preview.src = fotoBase64Temporal;
                    preview.style.display = 'block';
                }
                const label = document.getElementById('previewLabel');
                if (label) {
                    label.style.display = 'block';
                }

                // Resetear selección de predeterminadas
                const photoOptions = document.querySelectorAll('.profile-photo-option:not(.upload)');
                photoOptions.forEach(opt => opt.classList.remove('selected'));
                document.getElementById('fotoPerfilUrl').value = "";
            };
            lector.readAsDataURL(archivo);
        });
    }

    // --- SELECCIÓN DE FOTOS PREDETERMINADAS ---
    const photoOptions = document.querySelectorAll('.profile-photo-option:not(.upload)');
    photoOptions.forEach(option => {
        option.addEventListener('click', () => {
            // Remover selected de todas
            photoOptions.forEach(opt => opt.classList.remove('selected'));
            // Agregar selected a esta
            option.classList.add('selected');
            // Setear la URL
            const photoUrl = option.getAttribute('data-photo');
            document.getElementById('fotoPerfilUrl').value = photoUrl;
            fotoBase64Temporal = ""; // Reset upload
            // Mostrar preview
            const preview = document.getElementById('previewFoto');
            if (preview) {
                preview.src = photoUrl;
                preview.style.display = 'block';
            }
            const label = document.getElementById('previewLabel');
            if (label) {
                label.style.display = 'block';
            }
        });
    });

    if (btnCancelEdit) {
        btnCancelEdit.addEventListener('click', () => {
            modalEditProfile.style.display = 'none';
        });
    }

    // --- ENVIAR LOS DATOS ---
    if (formEditProfile) {
        formEditProfile.addEventListener('submit', async (e) => {
            e.preventDefault(); 
            
            const btnSave = document.getElementById('btnSaveEdit');
            const divMessage = document.getElementById('editMessage');
            
            btnSave.disabled = true;
            btnSave.textContent = 'Guardando...';
            divMessage.innerHTML = '';

            // Armamos el Payload incluyendo el Email
            const payload = {
                nombre: document.getElementById('editNombre').value.trim(),
                apellidos: document.getElementById('editApellidos').value.trim(),
                email: document.getElementById('editEmail').value.trim()
            };

            // Incluir foto_perfil si hay una seleccionada o subida
            const selectedPhoto = document.getElementById('fotoPerfilUrl').value;
            if (fotoBase64Temporal !== "") {
                payload.foto_perfil = fotoBase64Temporal;
            } else if (selectedPhoto !== "") {
                payload.foto_perfil = selectedPhoto;
            }

            try {
                const token = window.getAccessToken(); 
                
                const response = await fetch(`${API_BASE}/usuarios/me`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify(payload)
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    divMessage.innerHTML = `<span style="color: green;">${data.mensaje}</span>`;
                    
                    // Actualizamos memoria y pantalla
                    const user = window.getCurrentUserData();
                    const updatedUser = { ...user, ...payload }; 
                    window.setCurrentUserData(updatedUser);
                    loadProfileData(); 
                    
                    setTimeout(() => {
                        modalEditProfile.style.display = 'none';
                        btnSave.disabled = false;
                        btnSave.textContent = 'Guardar Cambios';
                    }, 1500);
                    
                } else {
                    divMessage.innerHTML = `<span style="color: red;">Error: ${data.detail || 'No se pudo actualizar'}</span>`;
                    btnSave.disabled = false;
                    btnSave.textContent = 'Guardar Cambios';
                }
            } catch (error) {
                console.error("Error al actualizar perfil:", error);
                divMessage.innerHTML = `<span style="color: red;">Error de conexión.</span>`;
                btnSave.disabled = false;
                btnSave.textContent = 'Guardar Cambios';
            }
        });
    }

    // --- 2. LÓGICA PENDIENTE (Contraseña, 2FA, Planes) ---
    // Cambiar Contraseña
    const btnChangePassword = document.getElementById('btnChangePassword');
    if (btnChangePassword) {
        btnChangePassword.addEventListener('click', () => {
            alert('Funcionalidad de cambio de contraseña en desarrollo');
        });
    }

    // Autenticación de dos factores
    const btn2FA = document.getElementById('btn2FA');
    if (btn2FA) {
        btn2FA.addEventListener('click', () => {
            alert('Funcionalidad de 2FA en desarrollo');
        });
    }

    // Actualizar plan
    const btnUpgrade = document.getElementById('btnUpgrade');
    if (btnUpgrade) {
        btnUpgrade.addEventListener('click', () => {
            alert('Próximamente podrás mejorar tu plan');
        });
    }
}

function checkLogin() {
    const token = window.getAccessToken();

    if (!token) {
        window.location.replace('login.html');
    }
}