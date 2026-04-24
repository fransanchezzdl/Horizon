// VALIDAR AUTENTICACIÓN CENTRALIZADA
(async () => {
    const result = await window.validateAuthToken();
    if (!result.valid) {
        window.clearAuthSession();
        window.location.replace('login.html');
        return;
    }
})();