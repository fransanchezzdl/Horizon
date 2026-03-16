/**
 * Lógica principal del Dashboard (index.html)
 * Se encarga de proteger la ruta y personalizar la vista del usuario
 */
checkLogin();

const API_BASE = 'http://localhost:8000';

document.addEventListener('DOMContentLoaded', () => {
    
    // 2. Si hay token, intentamos mostrar su nombre en la bienvenida
    const userDataString = localStorage.getItem('user_data');
    if (userDataString) {
        try {
            const user = JSON.parse(userDataString);
            
            // Usamos el nombre si existe, si no, la primera parte de su email
            const nombreMostrar = user.nombre || user.email.split('@')[0] || 'Inversor';
            
            // Actualizamos el H1 en el HTML
            const mensajeBienvenida = document.getElementById('mensaje-bienvenida');
            if (mensajeBienvenida) {
                mensajeBienvenida.textContent = `¡Bienvenido ${nombreMostrar}!`;
            }
            
        } catch (e) {
            console.error('Error leyendo los datos del usuario:', e);
        }
    }

    // 3. Cargar reflexión aleatoria desde el backend
    cargarReflexion();
});

async function cargarReflexion() {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    try {
        const response = await fetch(`${API_BASE}/reflexion/aleatoria`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) return; // fallback: mantiene la cita hardcoded

        const data = await response.json();

        const quoteEl  = document.getElementById('reflexion-quote');
        const authorEl = document.getElementById('reflexion-author');
        const btnEl    = document.getElementById('reflexion-btn');

        if (quoteEl)  quoteEl.textContent  = `“${data.cita}”`;
        if (authorEl) authorEl.textContent = `— ${data.autor}`;
        if (btnEl)    btnEl.href           = `reflexion.html?id=${data.id_reflexion}`;

    } catch (err) {
        // Red caída u otro error: la cita hardcoded permanece visible
        console.warn('No se pudo cargar la reflexión del día:', err);
    }
}

function checkLogin(){
    // 1. Verificar si existe el token en el almacenamiento local
    const token = localStorage.getItem('access_token');
    
    // Si no hay token, redirigimos al login inmediatamente
    if (!token) {
        window.location.replace('login.html'); // Usamos replace para que no puedan volver atrás con el botón del navegador
        return; 
    }
}