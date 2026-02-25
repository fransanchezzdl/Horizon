checkLogin();

function checkLogin(){
    // 1. Verificar si existe el token en el almacenamiento local
    const token = localStorage.getItem('access_token');
    
    // Si no hay token, redirigimos al login inmediatamente
    if (!token) {
        window.location.replace('login.html'); // Usamos replace para que no puedan volver atrás con el botón del navegador
        return; 
    }
}