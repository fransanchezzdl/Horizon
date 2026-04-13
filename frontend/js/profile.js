const API_BASE = window.API_BASE;

let selectedCustomAvatarFile = null;
let expectedDeleteAccountName = '';
const DEFAULT_AVATAR_URLS = [
    'https://fzxtliowdmhumnxfskvy.supabase.co/storage/v1/object/public/avatars-default/default/default-1.png',
    'https://fzxtliowdmhumnxfskvy.supabase.co/storage/v1/object/public/avatars-default/default/default-2.png',
    'https://fzxtliowdmhumnxfskvy.supabase.co/storage/v1/object/public/avatars-default/default/default-3.png',
];

function clearDefaultPhotoSelection(photoOptions) {
    photoOptions.forEach(opt => opt.classList.remove('selected'));
}

function resetUploadPreview(uploadOption) {
    if (!uploadOption) return;
    const uploadLabel = uploadOption.querySelector('.upload-label');
    if (!uploadLabel) return;
    uploadLabel.innerHTML = '<span class="plus-icon">+</span>';
}

function applySelectedDefaultPhoto(photoOptions, photoUrl) {
    clearDefaultPhotoSelection(photoOptions);
    const option = document.querySelector(`.profile-photo-option[data-photo="${photoUrl}"]`);
    if (option) {
        option.classList.add('selected');
    }
    document.getElementById('fotoPerfilUrl').value = photoUrl || '';
    selectedCustomAvatarFile = null;

    const uploadOption = document.querySelector('.profile-photo-option.upload');
    resetUploadPreview(uploadOption);
}

function markUploadPhotoSelected(photoOptions, previewUrl) {
    clearDefaultPhotoSelection(photoOptions);
    const uploadOption = document.querySelector('.profile-photo-option.upload');
    if (!uploadOption) return;

    uploadOption.classList.add('selected');
    const uploadLabel = uploadOption.querySelector('.upload-label');
    if (!uploadLabel) return;

    uploadLabel.innerHTML = '';
    const previewImg = document.createElement('img');
    previewImg.src = previewUrl;
    uploadLabel.appendChild(previewImg);
}

function abrirModalAvatar() {
    const modalAvatar = document.getElementById('modalEditAvatar');
    const photoOptions = document.querySelectorAll('#modalEditAvatar .profile-photo-option:not(.upload)');
    const fotoPerfilUrl = document.getElementById('fotoPerfilUrl');
    const uploadInput = document.getElementById('profilePhotoUpload');
    const avatarMessage = document.getElementById('avatarMessage');

    if (!modalAvatar || !fotoPerfilUrl) return;

    selectedCustomAvatarFile = null;
    avatarMessage.innerHTML = '';
    clearDefaultPhotoSelection(photoOptions);
    fotoPerfilUrl.value = '';

    const uploadOption = document.querySelector('#modalEditAvatar .profile-photo-option.upload');
    resetUploadPreview(uploadOption);
    if (uploadInput) uploadInput.value = '';

    const user = window.getCurrentUserData();
    if (user?.foto_perfil) {
        if (DEFAULT_AVATAR_URLS.includes(user.foto_perfil)) {
            applySelectedDefaultPhoto(photoOptions, user.foto_perfil);
        } else {
            markUploadPhotoSelected(photoOptions, user.foto_perfil);
        }
    }

    modalAvatar.style.display = 'flex';
}

function cerrarModalAvatar() {
    const modalAvatar = document.getElementById('modalEditAvatar');
    if (modalAvatar) {
        modalAvatar.style.display = 'none';
    }
}

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
            
            // Llenamos los datos
            document.getElementById('editEmail').value = user.email || '';
            document.getElementById('editNombre').value = user.nombre || '';
            document.getElementById('editApellidos').value = user.apellidos || '';
            document.getElementById('editMessage').innerHTML = ''; 
            
            modalEditProfile.style.display = 'flex';
        });
    }

    const btnAvatarEdit = document.getElementById('btnAvatarEdit');
    if (btnAvatarEdit) {
        btnAvatarEdit.addEventListener('click', abrirModalAvatar);
        btnAvatarEdit.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                abrirModalAvatar();
            }
        });
    }

    // --- LEER LA IMAGEN CUANDO EL USUARIO LA SELECCIONA ---
    const inputFoto = document.getElementById('profilePhotoUpload');
    if (inputFoto) {
        inputFoto.addEventListener('change', function(evento) {
            const archivo = evento.target.files[0];
            if (!archivo) return;

            if (!archivo.type.startsWith('image/')) {
                alert('Por favor selecciona una imagen válida');
                inputFoto.value = '';
                return;
            }

            const maxSize = 5 * 1024 * 1024;
            if (archivo.size > maxSize) {
                alert('La imagen no debe superar 5MB');
                inputFoto.value = '';
                return;
            }

            selectedCustomAvatarFile = archivo;
            const photoOptions = document.querySelectorAll('#modalEditAvatar .profile-photo-option:not(.upload)');
            markUploadPhotoSelected(photoOptions, URL.createObjectURL(archivo));

            // Resetear selección de predeterminadas
            document.getElementById('fotoPerfilUrl').value = "";
        });
    }

    // --- SELECCIÓN DE FOTOS PREDETERMINADAS ---
    const photoOptions = document.querySelectorAll('#modalEditAvatar .profile-photo-option:not(.upload)');
    photoOptions.forEach(option => {
        option.addEventListener('click', () => {
            const photoUrl = option.getAttribute('data-photo');
            applySelectedDefaultPhoto(photoOptions, photoUrl);
        });
    });

    if (btnCancelEdit) {
        btnCancelEdit.addEventListener('click', () => {
            modalEditProfile.style.display = 'none';
        });
    }

    const btnCancelAvatar = document.getElementById('btnCancelAvatar');
    if (btnCancelAvatar) {
        btnCancelAvatar.addEventListener('click', cerrarModalAvatar);
    }

    const btnSaveAvatar = document.getElementById('btnSaveAvatar');
    if (btnSaveAvatar) {
        btnSaveAvatar.addEventListener('click', async () => {
            const avatarMessage = document.getElementById('avatarMessage');
            const selectedPhoto = document.getElementById('fotoPerfilUrl').value;
            const token = window.getAccessToken();

            btnSaveAvatar.disabled = true;
            btnSaveAvatar.textContent = 'Guardando...';
            avatarMessage.innerHTML = '';

            try {
                if (selectedCustomAvatarFile) {
                    const formData = new FormData();
                    formData.append('file', selectedCustomAvatarFile);

                    const avatarRes = await fetch(`${API_BASE}/usuarios/me/avatar`, {
                        method: 'PUT',
                        headers: {
                            'Authorization': `Bearer ${token}`,
                        },
                        body: formData,
                    });

                    const avatarData = await avatarRes.json();
                    if (!avatarRes.ok) {
                        throw new Error(avatarData.detail || 'No se pudo actualizar la foto de perfil');
                    }

                    window.setCurrentUserData(avatarData);
                } else if (selectedPhoto) {
                    const response = await fetch(`${API_BASE}/usuarios/me`, {
                        method: 'PATCH',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify({ foto_perfil: selectedPhoto })
                    });

                    const data = await response.json();
                    if (!response.ok) {
                        throw new Error(data.detail || 'No se pudo actualizar la foto de perfil');
                    }

                    const validacion = await window.validateAuthToken();
                    if (validacion.valid) {
                        window.setCurrentUserData(validacion.user);
                    }
                } else {
                    throw new Error('Selecciona una foto para continuar');
                }

                loadProfileData();
                cerrarModalAvatar();
            } catch (error) {
                console.error('Error actualizando avatar:', error);
                avatarMessage.innerHTML = `<span style="color: red;">${error.message || 'Error de conexión.'}</span>`;
            } finally {
                btnSaveAvatar.disabled = false;
                btnSaveAvatar.textContent = 'Guardar foto';
            }
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

            // Armamos el Payload. El email se envía como el valor actual del usuario (no editable en UI).
            const usuarioActual = window.getCurrentUserData();
            const payload = {
                nombre: document.getElementById('editNombre').value.trim(),
                apellidos: document.getElementById('editApellidos').value.trim(),
                email: usuarioActual?.email || document.getElementById('editEmail').value.trim()
            };

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
    const modalChangePassword = document.getElementById('modalChangePassword');
    const formChangePassword = document.getElementById('formChangePassword');
    const btnCancelPassword = document.getElementById('btnCancelPassword');
    const btnSavePassword = document.getElementById('btnSavePassword');
    const currentPasswordInput = document.getElementById('currentPassword');
    const newPasswordInput = document.getElementById('newPassword');
    const confirmNewPasswordInput = document.getElementById('confirmNewPassword');
    const passwordMessage = document.getElementById('passwordMessage');

    const openChangePasswordModal = () => {
        if (!modalChangePassword) return;
        if (formChangePassword) formChangePassword.reset();
        if (passwordMessage) passwordMessage.innerHTML = '';
        if (btnSavePassword) btnSavePassword.disabled = false;
        modalChangePassword.style.display = 'flex';
    };

    const closeChangePasswordModal = () => {
        if (!modalChangePassword) return;
        modalChangePassword.style.display = 'none';
        if (formChangePassword) formChangePassword.reset();
        if (passwordMessage) passwordMessage.innerHTML = '';
    };

    if (btnChangePassword) {
        btnChangePassword.addEventListener('click', openChangePasswordModal);
    }

    if (btnCancelPassword) {
        btnCancelPassword.addEventListener('click', closeChangePasswordModal);
    }

    if (modalChangePassword) {
        modalChangePassword.addEventListener('click', (event) => {
            if (event.target === modalChangePassword) {
                closeChangePasswordModal();
            }
        });
    }

    if (formChangePassword) {
        formChangePassword.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            if (!btnSavePassword || !passwordMessage) return;
            
            btnSavePassword.disabled = true;
            btnSavePassword.textContent = 'Actualizando...';
            passwordMessage.innerHTML = '';
            
            const password_actual = (currentPasswordInput?.value || '').trim();
            const password_nueva = (newPasswordInput?.value || '').trim();
            const confirmPassword = (confirmNewPasswordInput?.value || '').trim();
            
            // Validar que las contraseñas nuevas coincidan
            if (password_nueva !== confirmPassword) {
                passwordMessage.innerHTML = `<span style="color: red;">Las contraseñas nuevas no coinciden.</span>`;
                btnSavePassword.disabled = false;
                btnSavePassword.textContent = 'Guardar Cambios';
                return;
            }
            
            try {
                const response = await window.fetchWithAuth(`${window.API_BASE}/auth/change-password`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        password_actual,
                        password_nueva
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    passwordMessage.innerHTML = `<span style="color: green;">${data.mensaje || 'Contraseña actualizada correctamente'}</span>`;
                    if (formChangePassword) formChangePassword.reset();
                    
                    setTimeout(() => {
                        closeChangePasswordModal();
                    }, 2000);
                } else {
                    passwordMessage.innerHTML = `<span style="color: red;">Error: ${data.detail || 'No se pudo actualizar la contraseña'}</span>`;
                }
            } catch (error) {
                console.error('Error al cambiar contraseña:', error);
                passwordMessage.innerHTML = `<span style="color: red;">Error de conexión.</span>`;
            } finally {
                btnSavePassword.disabled = false;
                btnSavePassword.textContent = 'Guardar Cambios';
            }
        });
    }

    // Eliminar cuenta
    const btnDeleteAccount = document.getElementById('btnDeleteAccount');
    const deleteAccountModal = document.getElementById('deleteAccountModal');
    const deleteAccountInput = document.getElementById('deleteAccountConfirmInput');
    const deleteAccountExpectedName = document.getElementById('deleteAccountExpectedName');
    const deleteAccountConfirmBtn = document.getElementById('deleteAccountConfirmBtn');
    const deleteAccountCancelBtn = document.getElementById('deleteAccountCancelBtn');

    const notify = (message, type = 'info') => {
        if (typeof window.showAlert === 'function') {
            window.showAlert(message, type);
        } else {
            alert(message);
        }
    };

    const getExpectedDeleteAccountName = () => {
        const user = window.getCurrentUserData() || {};
        if (typeof window.getUserDisplayName === 'function') {
            return window.getUserDisplayName(user, 'Usuario');
        }
        return user.nombre || user.email || 'Usuario';
    };

    const closeDeleteAccountModal = () => {
        if (!deleteAccountModal) return;
        deleteAccountModal.classList.add('is-hidden');
        if (deleteAccountInput) deleteAccountInput.value = '';
        if (deleteAccountConfirmBtn) deleteAccountConfirmBtn.disabled = true;
    };

    const validateDeleteAccountInput = () => {
        if (!deleteAccountInput || !deleteAccountConfirmBtn) return;
        deleteAccountConfirmBtn.disabled = deleteAccountInput.value !== expectedDeleteAccountName;
    };

    const openDeleteAccountModal = () => {
        if (!deleteAccountModal) return;
        expectedDeleteAccountName = getExpectedDeleteAccountName();
        if (deleteAccountExpectedName) {
            deleteAccountExpectedName.textContent = expectedDeleteAccountName;
        }
        if (deleteAccountInput) {
            deleteAccountInput.value = '';
        }
        if (deleteAccountConfirmBtn) {
            deleteAccountConfirmBtn.disabled = true;
        }
        deleteAccountModal.classList.remove('is-hidden');
        deleteAccountInput?.focus();
    };

    const confirmDeleteAccount = async () => {
        if (!deleteAccountInput || deleteAccountInput.value !== expectedDeleteAccountName) {
            return;
        }

        if (deleteAccountConfirmBtn) {
            deleteAccountConfirmBtn.disabled = true;
            deleteAccountConfirmBtn.textContent = 'Eliminando...';
        }

        try {
            const response = await window.fetchWithAuth(`${API_BASE}/usuarios/me`, {
                method: 'DELETE'
            });

            if (response.ok) {
                window.clearAuthSession();
                window.location.replace('login.html');
                return;
            }

            notify('Error al eliminar la cuenta. Inténtalo de nuevo.', 'error');
        } catch (error) {
            console.error('Error eliminando cuenta:', error);
            notify('Error al eliminar la cuenta. Inténtalo de nuevo.', 'error');
        } finally {
            if (deleteAccountConfirmBtn) {
                deleteAccountConfirmBtn.textContent = 'Eliminar cuenta';
            }
            validateDeleteAccountInput();
        }
    };

    if (btnDeleteAccount) {
        btnDeleteAccount.addEventListener('click', openDeleteAccountModal);
    }

    deleteAccountCancelBtn?.addEventListener('click', closeDeleteAccountModal);
    deleteAccountInput?.addEventListener('input', validateDeleteAccountInput);
    deleteAccountConfirmBtn?.addEventListener('click', confirmDeleteAccount);

    if (deleteAccountModal) {
        deleteAccountModal.addEventListener('click', (event) => {
            if (event.target === deleteAccountModal) {
                closeDeleteAccountModal();
            }
        });
    }

    // Actualizar plan
    const btnUpgrade = document.getElementById('btnUpgrade');
    if (btnUpgrade) {
        btnUpgrade.addEventListener('click', () => {
            alert('Próximamente podrás mejorar tu plan');
        });
    }

    const btnSupport = document.getElementById('btnSupport');
    if (btnSupport) {
        btnSupport.addEventListener('click', () => {
            window.location.href = 'ayuda.html';
        });
    }

    const btnOpenSettings = document.getElementById('btnOpenSettings');
    if (btnOpenSettings) {
        btnOpenSettings.addEventListener('click', () => {
            window.location.href = 'ajustes.html';
        });
    }
}

function checkLogin() {
    const token = window.getAccessToken();

    if (!token) {
        window.location.replace('login.html');
    }
}