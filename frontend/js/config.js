// Configuracion global del frontend
window.API_BASE = 'http://localhost:8000';

window.STORAGE_KEYS = {
    ACCESS_TOKEN: 'access_token',
    USER_DATA: 'user_data',
};

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
        return;
    }

    localStorage.setItem(window.STORAGE_KEYS.USER_DATA, JSON.stringify(user));
    cachedCurrentUser = user;
};

window.clearCurrentUserData = function () {
    localStorage.removeItem(window.STORAGE_KEYS.USER_DATA);
    cachedCurrentUser = null;
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