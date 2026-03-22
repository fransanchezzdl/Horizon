// Inyectar el HTML del sidebar
function initSidebar() {
    const sidebarHTML = `
    <aside id="sidebar" class="sidebar">
        <div class="sidebar-header">
            <div class="logo">
                <img class="logo-icon" src="assets/icon/logo.png" alt="Logo de Horizon">
                <span class="logo-text">Horizon</span>
            </div>
            <button class="sidebar-toggle" id="sidebarToggle" aria-label="Contraer barra lateral" title="Contraer barra lateral">
                <svg class="sidebar-toggle-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="15 18 9 12 15 6"></polyline>
                </svg>
            </button>
        </div>

        <nav class="sidebar-nav">
            <div class="nav-section">
                <a href="index.html" class="nav-item">
                    <svg class="nav-icon" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/>
                    </svg>
                    <span class="nav-label">Dashboard</span>
                </a>
                <a href="analysis.html" class="nav-item">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill=currentColor stroke=currentColor    stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                    <span class="nav-label">Análisis de Ticker</span>
                </a>
                <a href="portfolio.html" class="nav-item">
                    <svg class="nav-icon" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/>
                    </svg>
                    <span class="nav-label">Portfolio</span>
                </a>
                <a href="academia.html" class="nav-item">
                    <svg class="nav-icon" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2l-5.5 9h11z M17.5 13c1.93 0 3.5 1.57 3.5 3.5S19.43 20 17.5 20 14 18.43 14 16.5s1.57-3.5 3.5-3.5z M3 13.5h8v8H3z"/>
                    </svg>
                    <span class="nav-label">AcademIA</span>
                </a>
            </div>

            <div class="nav-divider"></div>

            <div class="nav-section">
                <span class="nav-section-title">CONFIGURACIÓN</span>
                <a href="#" class="nav-item">
                    <svg class="nav-icon" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.62l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.09-.47 0-.59.22L2.74 8.87c-.12.21-.08.48.1.62l2.03 1.58c-.05.3-.07.62-.07.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.62l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.48-.1-.62l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>
                    </svg>
                    <span class="nav-label">Ajustes</span>
                </a>
                <a href="#" class="nav-item">
                    <svg class="nav-icon" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10zm0-2c-4.418 0-8-3.582-8-8s3.582-8 8-8 8 3.582 8 8-3.582 8-8 8zm0-12.5c.828 0 1.5.672 1.5 1.5S12.828 10.5 12 10.5 10.5 9.828 10.5 9 11.172 7.5 12 7.5zm0 8c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3z"/>
                    </svg>
                    <span class="nav-label">Notificaciones</span>
                </a>
            </div>
        </nav>

        <div class="sidebar-footer">
            <div class="user-profile">
                <div class="user-avatar" id="user-avatar"></div>
                <div class="user-info">
                    <p class="user-name" id="user-name">Cargando...</p>
                    <p class="user-plan" id="user-plan">Cargando...</p>
                </div>
            </div>
            <button id="logoutBtn" class="btn-logout">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                    <polyline points="16 17 21 12 16 7"></polyline>
                    <line x1="21" y1="12" x2="9" y2="12"></line>
                </svg>
                <span>Cerrar Sesión</span>
            </button>
        </div>
    </aside>

    <div id="sidebarOverlay" class="sidebar-overlay"></div>
    
    <!-- Barra inferior para móvil -->
    <nav class="bottom-navbar" id="bottomNavbar">
        <div class="bottom-navbar-items">
            <a href="index.html" class="bottom-navbar-item" title="Dashboard">
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/>
                </svg>
                <span>Dashboard</span>
            </a>
            <a href="analysis.html" class="bottom-navbar-item" title="Análisis">
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/>
                </svg>
                <span>Análisis</span>
            </a>
            <a href="portfolio.html" class="bottom-navbar-item" title="Portfolio">
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
                <span>Portfolio</span>
            </a>
            <a href="academia.html" class="bottom-navbar-item" title="Academia">
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2l-5.5 9h11z M17.5 13c1.93 0 3.5 1.57 3.5 3.5S19.43 20 17.5 20 14 18.43 14 16.5s1.57-3.5 3.5-3.5z M3 13.5h8v8H3z"/>
                </svg>
                <span>AcademIA</span>
            </a>
            <a href="profile.html" class="bottom-navbar-item" title="Perfil">
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                </svg>
                <span>Perfil</span>
            </a>
        </div>
    </nav>
    `;

    // Inyectar el HTML al inicio del body
    document.body.insertAdjacentHTML('afterbegin', sidebarHTML);

    const currentUser = window.getCurrentUserData();
    initNombreUsuario(currentUser);
    initAvatar(currentUser);
    initMembresia(currentUser);

    // Inicializar event listeners
    initSidebarEvents();
}

// Inicializar event listeners
function initSidebarEvents() {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const SIDEBAR_STATE_KEY = 'sidebar_collapsed';
    const isMobile = window.innerWidth <= 768;

    // Restaurar estado de sidebar colapsada solo en desktop
    if (!isMobile && localStorage.getItem(SIDEBAR_STATE_KEY) === 'true') {
        sidebar.classList.add('collapsed');
    }

    // Ajustar dirección de flecha según el estado actual del sidebar.
    const syncSidebarToggleState = () => {
        const isCollapsed = sidebar.classList.contains('collapsed');
        sidebarToggle.classList.toggle('is-collapsed', isCollapsed);

        const actionText = isCollapsed ? 'Expandir barra lateral' : 'Contraer barra lateral';
        sidebarToggle.setAttribute('aria-label', actionText);
        sidebarToggle.setAttribute('title', actionText);
    };

    syncSidebarToggleState();

    // Toggle desde el botón dentro de la sidebar (desktop solo)
    sidebarToggle.addEventListener('click', () => {
        if (isMobile) return;

        const isCollapsed = sidebar.classList.toggle('collapsed');
        localStorage.setItem(SIDEBAR_STATE_KEY, isCollapsed);
        syncSidebarToggleState();
    });

    // Marcar el item activo según la página actual (sidebar)
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav-item').forEach(item => {
        if (item.getAttribute('href') === currentPage) {
            item.classList.add('active');
        }
    });

    // Función para actualizar el indicador del bottom navbar y marcar item activo
    const updateBottomNavbarIndicator = () => {
        const navItems = document.querySelectorAll('.bottom-navbar-item');
        let activeItem = null;

        navItems.forEach(item => {
            item.classList.remove('active');
            if (item.getAttribute('href') === currentPage) {
                item.classList.add('active');
                activeItem = item;
            }
        });

        // Animar el indicador azul
        const indicator = document.querySelector('.bottom-navbar-indicator');
        if (activeItem && indicator) {
            const itemWidth = activeItem.offsetWidth;
            const itemLeft = activeItem.offsetLeft;
            indicator.style.left = itemLeft + 'px';
            indicator.style.width = itemWidth + 'px';
        }
    };

    // Sincronizar indicador al cargar
    updateBottomNavbarIndicator();

    // Actualizar indicador cuando se redimensiona la ventana
    window.addEventListener('resize', updateBottomNavbarIndicator);

    // Abrir perfil del usuario al hacer click
    const userProfile = document.querySelector('.user-profile');
    if (userProfile) {
        userProfile.style.cursor = 'pointer';
        userProfile.addEventListener('click', () => {
            window.location.href = 'profile.html';
        });
    }

    // Nota: La lógica de logout está en logout.js
}

// Inicializar cuando el DOM esté listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSidebar);
} else {
    initSidebar();
}


// Carga la foto de perfil del usuario en el avatar del sidebar.
function initAvatar(user = window.getCurrentUserData()) {
    const avatar = document.getElementById('user-avatar');
    window.applyUserAvatar(avatar, user, 'I');
}

// Muestra el nombre del usuario abajo en la sidebar
function initNombreUsuario(user = window.getCurrentUserData()){
    const nombreMostrar = window.getUserDisplayName(user, 'Inversor');

    // Actualizamos el nombre en el HTML
    const user_name = document.getElementById('user-name');
    if (user_name) {
        user_name.textContent = `${nombreMostrar}`;
    }
}

// Muestra el plan de membresia del usuario logeado
function initMembresia(user = window.getCurrentUserData()){
    const planMostrar = window.getUserPlan(user, 'Gratis');

    // Actualizamos el plan en el HTML
    const user_plan = document.getElementById('user-plan');
    if (user_plan) {
        user_plan.textContent = `Plan ${planMostrar}`;
    }
}
