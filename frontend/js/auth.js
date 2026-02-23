// Configuración de Supabase
const SUPABASE_URL = 'https://fzxtliowdmhumnxfskvy.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ6eHRsaW93ZG1odW1ueGZza3Z5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg5MjQ0ODQsImV4cCI6MjA4NDUwMDQ4NH0.tHP8U_za0N49Bu54fu7wDh-tWfZN43IUeBbcE72TSFU';

// Inicializar Supabase
const supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

/**
 * Obtener la sesión actual del usuario
 * @returns {Promise<Object|null>} Session object o null
 */
async function getCurrentSession() {
    try {
        const { data, error } = await supabaseClient.auth.getSession();
        if (error) {
            console.error('Error obteniendo sesión:', error);
            return null;
        }
        return data.session;
    } catch (err) {
        console.error('Error en getCurrentSession:', err);
        return null;
    }
}

/**
 * Obtener el usuario autenticado actual
 * @returns {Promise<Object|null>} User object o null
 */
async function getCurrentUser() {
    try {
        const { data, error } = await supabaseClient.auth.getUser();
        if (error) {
            console.error('Error obteniendo usuario:', error);
            return null;
        }
        return data.user;
    } catch (err) {
        console.error('Error en getCurrentUser:', err);
        return null;
    }
}

/**
 * Cerrar sesión
 * @returns {Promise<boolean>} true si fue exitoso
 */
async function logout() {
    try {
        const { error } = await supabaseClient.auth.signOut();
        if (error) {
            console.error('Error al cerrar sesión:', error);
            return false;
        }
        return true;
    } catch (err) {
        console.error('Error en logout:', err);
        return false;
    }
}

/**
 * Verificar si el usuario está autenticado
 * @returns {Promise<boolean>} true si hay sesión
 */
async function checkAuth() {
    try {
        const session = await getCurrentSession();
        if (!session) {
            return false;
        }
        return true;
    } catch (err) {
        console.error('Error en checkAuth:', err);
        return false;
    }
}

/**
 * Obtener información del usuario desde la tabla usuarios
 * @param {string} userId - ID del usuario
 * @returns {Promise<Object|null>} User profile object o null
 * @throws {Object} Error object con propiedades: code, message, type
 */
async function getUserProfile(userId) {
    try {
        const { data, error } = await supabaseClient
            .from('usuarios')
            .select('nombre, apellidos, email, membresia')
            .eq('id_usuario', userId)
            .single();

        if (error) {
            // Diferencias errores específicos
            const errorType = error.code === 'PGRST116' ? 'NOT_FOUND' : 'RLS_DENIED';
            throw {
                code: error.code,
                message: error.message,
                type: errorType,
                originalError: error
            };
        }
        return data;
    } catch (err) {
        console.error('Error en getUserProfile:', err);
        throw err;
    }
}

/**
 * Realizar login con email y contraseña
 * @param {string} email
 * @param {string} password
 * @returns {Promise<Object>} { user, error }
 */
async function signInWithPassword(email, password) {
    try {
        const { data, error } = await supabaseClient.auth.signInWithPassword({
            email,
            password
        });

        if (error) {
            throw {
                code: error.code,
                message: error.message,
                type: 'AUTH_ERROR'
            };
        }

        return { user: data.user, error: null };
    } catch (err) {
        console.error('Error en signInWithPassword:', err);
        return {
            user: null,
            error: err
        };
    }
}

// Exportar para uso global
window.authAPI = {
    supabaseClient,
    getCurrentSession,
    getCurrentUser,
    logout,
    checkAuth,
    getUserProfile,
    signInWithPassword
};
