const API_BASE = window.API_BASE;

const SETTINGS_KEYS = {
    theme: 'horizon_setting_theme',
};

function loadSettings() {
    const theme = window.getSavedThemePreference();

    const themeSelect = document.getElementById('settingTheme');

    if (themeSelect) {
        themeSelect.value = theme;
    }
}

function saveSettings() {
    const themeSelect = document.getElementById('settingTheme');
    const messageEl = document.getElementById('settingsMessage');

    const theme = themeSelect ? themeSelect.value : 'system';

    window.setThemePreference(theme);

    if (messageEl) {
        messageEl.textContent = 'Ajustes guardados correctamente.';
    }
}

function revealAjustesPage() {
    document.body.classList.remove('page-loading');
}

function initAjustesPage() {
    loadSettings();

    const btnSave = document.getElementById('btnSettingsSave');
    if (btnSave) {
        btnSave.addEventListener('click', saveSettings);
    }

    const btnCancel = document.getElementById('btnSettingsCancel');
    if (btnCancel) {
        btnCancel.addEventListener('click', () => {
            if (window.history.length > 1) {
                window.history.back();
                return;
            }

            window.location.href = 'index.html';
        });
    }

    revealAjustesPage();
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
        document.addEventListener('DOMContentLoaded', initAjustesPage, { once: true });
    } else {
        initAjustesPage();
    }
})();
