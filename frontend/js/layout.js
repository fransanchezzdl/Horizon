// Inyectar el HTML del sidebar
function initSidebar() {
    const sidebarHTML = `
    <aside id="sidebar" class="sidebar">
        <div class="sidebar-header">
            <div class="logo">
                <div class="logo-icon">H</div>
                <span class="logo-text">Horizon</span>
            </div>
            <button class="sidebar-toggle" id="sidebarToggle">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="3" y1="6" x2="21" y2="6"></line>
                    <line x1="3" y1="12" x2="21" y2="12"></line>
                    <line x1="3" y1="18" x2="21" y2="18"></line>
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
                    <svg class="nav-icon" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/>
                    </svg>
                    <span class="nav-label">Análisis de Ticker</span>
                </a>
                <a href="portfolio.html" class="nav-item">
                    <svg class="nav-icon" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                    </svg>
                    <span class="nav-label">Portafolio</span>
                </a>
                <a href="academy.html" class="nav-item">
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
                <div class="user-avatar">A</div>
                <div class="user-info">
                    <p class="user-name">_USUARIO_</p>
                    <p class="user-plan"> P R O </p>
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
    `;

    // Inyectar el HTML al inicio del body
    document.body.insertAdjacentHTML('afterbegin', sidebarHTML);

    // Inicializar event listeners
    initSidebarEvents();
}

// Inicializar event listeners
function initSidebarEvents() {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebarOverlay = document.getElementById('sidebarOverlay');

    // Toggle sidebar en desktop
    sidebarToggle.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
    });

    // Toggle sidebar en mobile
    if (window.innerWidth <= 768) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            sidebarOverlay.classList.toggle('visible');
        });

        sidebarOverlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            sidebarOverlay.classList.remove('visible');
        });
    }

    // Marcar el item activo según la página actual
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav-item').forEach(item => {
        if (item.getAttribute('href') === currentPage) {
            item.classList.add('active');
        }
    });

    // Cerrar sidebar al hacer click en un link en mobile
    if (window.innerWidth <= 768) {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                sidebar.classList.remove('open');
                sidebarOverlay.classList.remove('visible');
            });
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
