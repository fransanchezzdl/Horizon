const API_BASE = window.API_BASE;

function initAyudaPage(user) {
    const emailEl = document.getElementById('supportUserEmail');
    if (emailEl) {
        emailEl.textContent = `Email de cuenta: ${user?.email || 'No disponible'}`;
    }

    const btnContactSupport = document.getElementById('btnContactSupport');
    if (btnContactSupport) {
        btnContactSupport.addEventListener('click', () => {
            const subject = encodeURIComponent('Ayuda con mi cuenta Horizon');
            window.location.href = `mailto:soporte@horizon.app?subject=${subject}`;
        });
    }
}

// VALIDAR AUTENTICACION CENTRALIZADA
(async () => {
    const result = await window.validateAuthToken();

    if (!result.valid) {
        window.clearAuthSession();
        window.location.replace('login.html');
        return;
    }

    window.setCurrentUserData(result.user);

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => initAyudaPage(result.user), { once: true });
    } else {
        initAyudaPage(result.user);
    }
})();
