/**
 * Lógica principal del Dashboard (index.html)
 * Se encarga de proteger la ruta y personalizar la vista del usuario
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Verificar si existe el token en el almacenamiento local
    const token = localStorage.getItem('access_token');
    
    // Si no hay token, redirigimos al login inmediatamente
    if (!token) {
        window.location.replace('login.html'); // Usamos replace para que no puedan volver atrás con el botón del navegador
        return; 
    }

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
});