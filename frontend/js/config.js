// Configuracion global del frontend
window.API_BASE = 'http://localhost:8000';

window.STORAGE_KEYS = {
    ACCESS_TOKEN: 'access_token',
    USER_DATA: 'user_data',
    THEME: 'horizon_setting_theme',
};

window.getSavedThemePreference = function () {
    return localStorage.getItem(window.STORAGE_KEYS.THEME) || 'system';
};

window.resolveThemePreference = function (themePreference) {
    const selected = themePreference || 'system';
    if (selected === 'light' || selected === 'dark') {
        return selected;
    }

    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    return prefersDark ? 'dark' : 'light';
};

window.applyThemePreference = function (themePreference = window.getSavedThemePreference()) {
    const resolvedTheme = window.resolveThemePreference(themePreference);
    document.documentElement.setAttribute('data-theme', resolvedTheme);

    window.dispatchEvent(new CustomEvent('horizon:theme-changed', {
        detail: {
            preference: themePreference || 'system',
            resolvedTheme,
        },
    }));

    return resolvedTheme;
};

window.setThemePreference = function (themePreference) {
    const normalized = themePreference || 'system';
    localStorage.setItem(window.STORAGE_KEYS.THEME, normalized);
    return window.applyThemePreference(normalized);
};

window.applyThemePreference();

if (window.matchMedia) {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const syncSystemTheme = () => {
        if (window.getSavedThemePreference() === 'system') {
            window.applyThemePreference('system');
        }
    };

    if (typeof media.addEventListener === 'function') {
        media.addEventListener('change', syncSystemTheme);
    } else if (typeof media.addListener === 'function') {
        media.addListener(syncSystemTheme);
    }
}

let cachedCurrentUser = undefined;

window.getAccessToken = function () {
    return localStorage.getItem(window.STORAGE_KEYS.ACCESS_TOKEN);
};

window.setAccessToken = function (token) {
    if (token) {
        localStorage.setItem(window.STORAGE_KEYS.ACCESS_TOKEN, token);
        return;
    }
    localStorage.removeItem(window.STORAGE_KEYS.ACCESS_TOKEN);
};

window.getCurrentUserData = function () {
    if (cachedCurrentUser !== undefined) {
        return cachedCurrentUser;
    }

    const userDataString = localStorage.getItem(window.STORAGE_KEYS.USER_DATA);
    if (!userDataString) {
        cachedCurrentUser = null;
        return null;
    }

    try {
        cachedCurrentUser = JSON.parse(userDataString);
        return cachedCurrentUser;
    } catch (e) {
        console.error('Error leyendo los datos del usuario:', e);
        cachedCurrentUser = null;
        return null;
    }
};

window.setCurrentUserData = function (user) {
    if (!user) {
        localStorage.removeItem(window.STORAGE_KEYS.USER_DATA);
        cachedCurrentUser = null;

        window.dispatchEvent(new CustomEvent('horizon:user-updated', {
            detail: null,
        }));

        return;
    }

    localStorage.setItem(window.STORAGE_KEYS.USER_DATA, JSON.stringify(user));
    cachedCurrentUser = user;

    window.dispatchEvent(new CustomEvent('horizon:user-updated', {
        detail: user,
    }));
};

window.clearCurrentUserData = function () {
    localStorage.removeItem(window.STORAGE_KEYS.USER_DATA);
    cachedCurrentUser = null;

    window.dispatchEvent(new CustomEvent('horizon:user-updated', {
        detail: null,
    }));
};

window.clearAuthSession = function () {
    window.setAccessToken(null);
    window.clearCurrentUserData();
};

window.getUserDisplayName = function (user = window.getCurrentUserData(), fallback = 'Inversor') {
    if (!user) {
        return fallback;
    }
    return user.nombre || user.email?.split('@')[0] || fallback;
};

window.getUserInitial = function (user = window.getCurrentUserData(), fallback = 'I') {
    const displayName = window.getUserDisplayName(user, fallback);
    const firstChar = displayName.charAt(0) || fallback.charAt(0);
    return firstChar.toUpperCase();
};

window.getUserPlan = function (user = window.getCurrentUserData(), fallback = 'Gratis') {
    if (!user) {
        return fallback;
    }
    return user.membresia || fallback;
};

window.getUserAvatarUrl = function (user = window.getCurrentUserData()) {
    const avatarUrl = (user?.foto_perfil || '').trim();
    if (!avatarUrl || avatarUrl === '-') {
        return '';
    }
    return avatarUrl;
};

window.applyUserAvatar = function (avatarElement, user = window.getCurrentUserData(), fallbackInitial = 'I') {
    if (!avatarElement) {
        return;
    }

    const initial = window.getUserInitial(user, fallbackInitial);
    const avatarUrl = window.getUserAvatarUrl(user);

    const applyInitial = () => {
        avatarElement.textContent = initial;
        avatarElement.style.backgroundImage = '';
        avatarElement.style.backgroundSize = '';
        avatarElement.style.backgroundPosition = '';
        avatarElement.style.backgroundRepeat = '';
    };

    if (!avatarUrl) {
        applyInitial();
        return;
    }

    // Evita el parpadeo mostrando directamente la foto si existe URL.
    avatarElement.textContent = '';
    avatarElement.style.backgroundImage = `url('${avatarUrl}')`;
    avatarElement.style.backgroundSize = 'cover';
    avatarElement.style.backgroundPosition = 'center';
    avatarElement.style.backgroundRepeat = 'no-repeat';

    const testImage = new Image();
    testImage.onerror = () => {
        applyInitial();
    };

    testImage.src = avatarUrl;
};

window.ASSET_ICON_FALLBACK_SVG = [
    '<svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24" aria-hidden="true">',
    '<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/>',
    '</svg>'
].join('');

window.getAssetLogoUrl = function (assetOrLogo) {
    const rawLogo = typeof assetOrLogo === 'string'
        ? assetOrLogo
        : assetOrLogo?.logo_activo;

    const logoUrl = (rawLogo || '').trim();
    if (!logoUrl || logoUrl === '-') {
        return '';
    }

    return logoUrl;
};

window.renderAssetIcon = function (containerElement, assetOrLogo) {
    if (!containerElement) {
        return;
    }

    const drawFallback = () => {
        containerElement.innerHTML = window.ASSET_ICON_FALLBACK_SVG;
    };

    const logoUrl = window.getAssetLogoUrl(assetOrLogo);
    if (!logoUrl) {
        drawFallback();
        return;
    }

    const img = document.createElement('img');
    img.src = logoUrl;
    img.alt = 'Logo del activo';
    img.loading = 'lazy';
    img.style.width = '100%';
    img.style.height = '100%';
    img.style.objectFit = 'contain';
    img.style.objectPosition = 'center';
    img.style.padding = '2px';
    img.style.boxSizing = 'border-box';
    img.style.display = 'block';

    img.onerror = () => {
        drawFallback();
    };

    containerElement.innerHTML = '';
    containerElement.appendChild(img);
};

// ──────────────────────────────────────────────────────────────────
// CENTRALIZACIÓN DE AUTENTICACIÓN
// ──────────────────────────────────────────────────────────────────

/**
 * Valida que el token actual sea auténtico llamando a /auth/me
 * 
 * El backend valida el token contra Supabase Auth:
 * - Firma criptográfica
 * - Expiración
 * - Revocación
 * 
 * Returns:
 *   - { valid: true, user: UsuarioResponse } si token es válido
 *   - { valid: false, user: null } si token es inválido
 */
window.validateAuthToken = async function () {
    const token = window.getAccessToken();
    
    if (!token) {
        console.log('[AUTH] No hay token en localStorage');
        return { valid: false, user: null };
    }
    
    try {
        console.log('[AUTH] Validando token contra /auth/me...');
        
        const response = await fetch(`${window.API_BASE}/auth/me`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            console.error(`[AUTH] Token inválido (${response.status})`);
            return { valid: false, user: null };
        }
        
        const user = await response.json();
        console.log('[AUTH] Token válido ✓');
        return { valid: true, user: user };
        
    } catch (err) {
        console.error('[AUTH] Error validando token:', err);
        return { valid: false, user: null };
    }
};

/**
 * Función helper para fetch con autenticación
 * 
 * Automáticamente:
 * - Agrega header Authorization: Bearer <token>
 * - Maneja errores 401 (token expirado/revocado)
 * - Redirige a login si el token es inválido
 * 
 * Usage:
 *   const response = await window.fetchWithAuth(`${API_BASE}/chat`, {
 *       method: 'POST',
 *       body: JSON.stringify({ message: 'Hola' })
 *   });
 */
window.fetchWithAuth = async function (url, options = {}) {
    const token = window.getAccessToken();
    
    if (!token) {
        console.warn('[AUTH] fetchWithAuth: No hay token');
        throw new Error('Sin autenticación');
    }
    
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                ...options.headers,
                'Authorization': `Bearer ${token}`
            }
        });
        
        // Manejar token inválido/expirado
        if (response.status === 401) {
            console.error('[AUTH] Token inválido/expirado durante API call');
            window.clearAuthSession();
            window.location.replace('login.html');
            throw new Error('Token expirado, sesión cerrada');
        }
        
        return response;
        
    } catch (err) {
        // Si ya fue redirigido, no re-lanzar
        if (err.message === 'Token expirado, sesión cerrada') {
            throw err;
        }
        console.error('[AUTH] Error en fetchWithAuth:', err);
        throw err;
    }
};