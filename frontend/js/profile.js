const API_BASE = window.API_BASE;

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
        document.getElementById('infoTelefono').textContent = user.telefono || 'No proporcionado';
        document.getElementById('infoPais').textContent = user.pais || 'No especificado';

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
        window.location.href = 'login.html';
    }
}

// Cargar estadísticas del usuario desde la API
async function loadUserStats(userId) {
    try {
        // Obtener datos del portfolio
        const portfolioRes = await window.fetchWithAuth(`${API_BASE}/portfolios/${userId}`);

        if (portfolioRes.ok) {
            const portfolioData = await portfolioRes.json();
            const activosCount = portfolioData.length || 0;
            document.getElementById('statPortfolio').textContent = activosCount;
        }

        // Obtener datos de predicciones
        const predictionsRes = await window.fetchWithAuth(`${API_BASE}/api/predictions/${userId}`);

        if (predictionsRes.ok) {
            const predictionsData = await predictionsRes.json();
            const predictionsCount = predictionsData.length || 0;
            document.getElementById('statPredictions').textContent = predictionsCount;

            // Calcular precisión promedio
            if (predictionsCount > 0) {
                const accuracyPromedio = (predictionsData.reduce((sum, p) => sum + (p.accuracy || 0), 0) / predictionsCount).toFixed(2);
                document.getElementById('statAccuracy').textContent = `${accuracyPromedio}%`;
            }
        }

    } catch (e) {
        console.warn('No se pudieron cargar las estadísticas:', e);
        // Mantener valores por defecto
    }
}

// Formatear fecha
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('es-ES', options);
}

// Event Listeners
function initProfileEvents() {
    // --- 1. NUEVA LÓGICA: EDITAR PERFIL (Modal y API) ---
    const btnEditProfile = document.getElementById('btnEditProfile');
    const modalEditProfile = document.getElementById('modalEditProfile');
    const btnCancelEdit = document.getElementById('btnCancelEdit');
    const formEditProfile = document.getElementById('formEditProfile');

    if (btnEditProfile) {
        // Al hacer clic en "Editar Perfil", abrimos el modal y llenamos los datos
        btnEditProfile.addEventListener('click', () => {
            const user = window.getCurrentUserData();
            
            document.getElementById('editEmail').value = user.email || '';
            document.getElementById('editNombre').value = user.nombre || '';
            document.getElementById('editApellidos').value = user.apellidos || '';
            document.getElementById('editFoto').value = user.foto_perfil || '';
            document.getElementById('editMessage').innerHTML = ''; 
            
            modalEditProfile.style.display = 'flex'; 
        });
    }

    if (btnCancelEdit) {
        // Al hacer clic en "Cancelar", ocultamos el modal
        btnCancelEdit.addEventListener('click', () => {
            modalEditProfile.style.display = 'none';
        });
    }

    if (formEditProfile) {
        // Al enviar el formulario (Guardar Cambios)
        formEditProfile.addEventListener('submit', async (e) => {
            e.preventDefault(); 
            
            const btnSave = document.getElementById('btnSaveEdit');
            const divMessage = document.getElementById('editMessage');
            
            // Estado visual de "Cargando"
            btnSave.disabled = true;
            btnSave.textContent = 'Guardando...';
            divMessage.innerHTML = '';

            // Armamos el Payload
            const payload = {};
            const nombre = document.getElementById('editNombre').value.trim();
            const apellidos = document.getElementById('editApellidos').value.trim();
            const foto = document.getElementById('editFoto').value.trim();
            
            if (nombre) payload.nombre = nombre;
            if (apellidos) payload.apellidos = apellidos;
            if (foto) payload.foto_perfil = foto;

            try {
                // Obtenemos tu token de seguridad
                const token = window.getAccessToken(); 
                
                // Llamamos a nuestro nuevo endpoint del backend
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
                    // Éxito: Mostramos mensaje verde
                    divMessage.innerHTML = `<span style="color: green;">${data.mensaje}</span>`;
                    
                    // Actualizamos la memoria del frontend y la pantalla
                    const user = window.getCurrentUserData();
                    const updatedUser = { ...user, ...payload }; 
                    window.setCurrentUserData(updatedUser);
                    loadProfileData(); 
                    
                    // Cerramos el modal tras un breve retraso
                    setTimeout(() => {
                        modalEditProfile.style.display = 'none';
                        btnSave.disabled = false;
                        btnSave.textContent = 'Guardar Cambios';
                    }, 1500);
                    
                } else {
                    // Error de validación o del servidor
                    divMessage.innerHTML = `<span style="color: red;">Error: ${data.detail || 'No se pudo actualizar'}</span>`;
                    btnSave.disabled = false;
                    btnSave.textContent = 'Guardar Cambios';
                }
            } catch (error) {
                // Error de conexión a internet o backend apagado
                console.error("Error al actualizar perfil:", error);
                divMessage.innerHTML = `<span style="color: red;">Error de conexión con el servidor.</span>`;
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