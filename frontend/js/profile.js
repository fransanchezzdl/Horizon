// Cargar datos del perfil del usuario
function loadProfileData() {
    const userDataString = localStorage.getItem('user_data');
    
    if (!userDataString) {
        console.error('No user data found');
        window.location.href = 'login.html';
        return;
    }

    try {
        const user = JSON.parse(userDataString);
        
        // Actualizar información general
        const nombre = user.nombre || user.email.split('@')[0] || 'Usuario';
        const inicial = nombre.charAt(0).toUpperCase();
        
        document.getElementById('profileName').textContent = nombre;
        document.getElementById('profileEmail').textContent = user.email;
        document.getElementById('profileAvatar').textContent = inicial;
        document.getElementById('profilePlan').textContent = `Plan ${user.membresia || 'Free'}`;
        
        // Llenar formulario de información general
        document.getElementById('infoNombre').textContent = nombre;
        document.getElementById('infoEmail').textContent = user.email;
        document.getElementById('infoTelefono').textContent = user.telefono || 'No proporcionado';
        document.getElementById('infoPais').textContent = user.pais || 'No especificado';
        
        // Información de membresía
        document.getElementById('membershipPlan').textContent = user.membresia || 'Free';
        document.getElementById('membershipDate').textContent = formatDate(user.fecha_registro || new Date().toISOString());
        
        // Cargar estadísticas (llamar a la API si es necesario)
        loadUserStats(user.id);
        
    } catch (e) {
        console.error('Error loading profile:', e);
        window.location.href = 'login.html';
    }
}

// Cargar estadísticas del usuario desde la API
async function loadUserStats(userId) {
    try {
        const token = localStorage.getItem('token');
        
        // Obtener datos del portfolio
        const portfolioRes = await fetch(`http://localhost:8000/api/portfolio/${userId}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (portfolioRes.ok) {
            const portfolioData = await portfolioRes.json();
            const activosCount = portfolioData.length || 0;
            document.getElementById('statPortfolio').textContent = activosCount;
        }
        
        // Obtener datos de predicciones
        const predictionsRes = await fetch(`http://localhost:8000/api/predictions/${userId}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
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
    // Editar Perfil
    const btnEditProfile = document.getElementById('btnEditProfile');
    if (btnEditProfile) {
        btnEditProfile.addEventListener('click', () => {
            alert('Funcionalidad de edición en desarrollo');
            // TODO: Abrir modal o página de edición
        });
    }

    // Cambiar Contraseña
    const btnChangePassword = document.getElementById('btnChangePassword');
    if (btnChangePassword) {
        btnChangePassword.addEventListener('click', () => {
            alert('Funcionalidad de cambio de contraseña en desarrollo');
            // TODO: Abrir modal para cambiar contraseña
        });
    }

    // Autenticación de dos factores
    const btn2FA = document.getElementById('btn2FA');
    if (btn2FA) {
        btn2FA.addEventListener('click', () => {
            alert('Funcionalidad de 2FA en desarrollo');
            // TODO: Configurar 2FA
        });
    }

    // Actualizar plan
    const btnUpgrade = document.getElementById('btnUpgrade');
    if (btnUpgrade) {
        btnUpgrade.addEventListener('click', () => {
            alert('Próximamente podrás mejorar tu plan');
            // TODO: Mostrar opciones de planes
        });
    }
}

// Inicializar cuando el DOM esté listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        loadProfileData();
        initProfileEvents();
    });
} else {
    loadProfileData();
    initProfileEvents();
}
