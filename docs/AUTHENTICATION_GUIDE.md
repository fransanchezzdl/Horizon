# Guía de Seguridad y Autenticación - Horizon

## 📋 Resumen de Cambios

Se ha refactorizado completamente el sistema de autenticación para resolver race conditions y mejorar la seguridad con RLS (Row Level Security).

---

## 🔧 Problemas Resueltos

### 1. Race Condition en Verificación de Sesión
**Problema**: `authAPI.checkAuth()` se ejecutaba antes de que `authAPI` estuviera disponible.

**Solución**: 
- Movemos la verificación a `DOMContentLoaded` en lugar de script inline en `<head>`
- Ahora todas las funciones async esperan a que los scripts carguen completamente

```html
<!-- ANTES (Problematico) -->
<script src="auth.js"></script>
<script>
    authAPI.checkAuth(); // ERROR: authAPI undefined
</script>

<!-- AHORA (Correcto) -->
<script src="auth.js"></script>
<script>
    document.addEventListener('DOMContentLoaded', async () => {
        await authAPI.checkAuth(); // OK: authAPI ya existe
    });
</script>
```

### 2. Manejo de Errores Mejorado

**auth.js** ahora:
- Diferencia entre errores de autenticación y errores de RLS
- Usa `throw` para errores críticos con estructura estándar
- Todas las funciones tienen try-catch

```javascript
// Estructura de error estándar
{
    code: string,           // Código Supabase
    message: string,        // Mensaje legible
    type: 'AUTH_ERROR' | 'RLS_DENIED' | 'NOT_FOUND',
    originalError: object   // Error original de Supabase
}
```

### 3. Estados Visuales en Login

**login.js** ahora muestra:
- "Verificando credenciales..." mientras autentica en Supabase Auth
- "Verificando perfil..." mientras consulta tabla usuarios
- Botón deshabilitado durante el proceso
- Mensajes de error específicos según el tipo

---

## 🔐 Configuración de RLS

### Paso 1: Ejecutar SQL en Supabase

1. Ir a Supabase Dashboard → SQL Editor
2. Crear nueva query
3. Copiar contenido de `docs/RLS_POLICIES.sql`
4. Ejecutar

```sql
-- Esto habilitará RLS y creará todas las políticas necesarias
```

### Paso 2: Verificar Políticas

En Supabase Dashboard:
1. Ir a **Authentication** → **Policies**
2. Verificar que estén habilitadas para todas las tablas

### Políticas Configuradas

| Tabla | Operación | Condición | Quién |
|-------|-----------|-----------|-------|
| usuarios | SELECT | auth.uid() = id_usuario | Usuarios autenticados |
| usuarios | UPDATE | auth.uid() = id_usuario | Usuarios autenticados |
| usuarios | INSERT | Siempre (para triggers) | Sistema |
| activos | SELECT | rol = 'authenticated' | Usuarios autenticados |
| portafolios | SELECT | auth.uid() = id_usuario | Usuarios autenticados |
| portafolios | INSERT/UPDATE/DELETE | auth.uid() = id_usuario | Propietario |
| historico_activos | SELECT | rol = 'authenticated' | Usuarios autenticados |

---

## 🔑 Flujo de Autenticación Completo

```
1. Usuario accede a index.html
   ↓
2. DOMContentLoaded ejecuta authAPI.checkAuth()
   ↓
3. ¿Hay sesión en Supabase Auth?
   ├─ NO → Redirige a login.html
   └─ SÍ → Carga página
   
4. En login.html:
   ├─ Usuario ingresa email/contraseña
   ├─ login.js llama authAPI.signInWithPassword()
   ├─ Supabase Auth verifica credenciales (sin RLS)
   ├─ Si OK: login.js consulta tabla usuarios
   ├─ RLS verifica: auth.uid() = id_usuario
   ├─ Si usuario existe → Redirige a index.html
   └─ Si no existe o error RLS → Muestra error y logout
```

---

## 📁 Archivos Modificados

### Frontend - HTML
- `index.html` - Verificación en DOMContentLoaded
- `analysis.html` - Verificación en DOMContentLoaded
- `portfolio.html` - Verificación en DOMContentLoaded
- `academy.html` - Verificación en DOMContentLoaded

### Frontend - JavaScript
- **`js/auth.js`** (Refactorizado)
  - Mejor manejo de errores
  - Función `signInWithPassword()` agregada
  - Try-catch en todas las funciones
  - Diferenciación de tipos de error

- **`js/login.js`** (Mejorado)
  - Verificación de email válido
  - Estados visuales (botón deshabilitado, texto dinámico)
  - Manejo específico de errores de RLS vs credenciales
  - Logs para debugging

### Backend - SQL
- `docs/RLS_POLICIES.sql` (Nuevo)
  - Políticas de RLS para todas las tablas
  - Comentarios explicativos
  - Instrucciones de verificación

---

## 🧪 Testing - Pasos para Verificar

### 1. Test de Login Exitoso

```
1. Acceder a http://localhost/Horizon/frontend/login.html
2. Ingresar email y contraseña válidos (usuario debe estar en tabla usuarios)
3. Ver "Verificando credenciales..." luego "Verificando perfil..."
4. Redirige a index.html
```

### 2. Test de Usuario No Registrado

```
1. En Supabase Auth crear usuario: test@example.com / password123
2. NO insertar en tabla usuarios
3. Intentar login con esas credenciales
4. Ver error: "Usuario no registrado en el sistema"
5. Botón vuelve a estar habilitado
```

### 3. Test de Error RLS

```
1. Si las políticas RLS están mal configuradas:
   - Intentar login mostrará: "Error de permisos. Contacta a soporte"
2. Verificar logs en consola (F12) para más detalles
```

### 4. Test de Redirección de Sesión

```
1. Loguearse en index.html
2. Abrir login.html
3. Debe redirigir automáticamente a index.html
```

### 5. Test de Protección de Página

```
1. Cerrar sesión de navegador (clear cookies) o usar incógnito
2. Acceder a http://localhost/Horizon/frontend/index.html
3. Debe redirigir a login.html
```

---

## 🐛 Debugging

### Ver logs en consola (F12)

```javascript
// auth.js hace logs de cada paso
[LOGIN] Iniciando login para: user@example.com
[LOGIN] Autenticación exitosa, verificando tabla usuarios...
[LOGIN] Perfil encontrado: { ... }
[LOGIN] Login exitoso, redirigiendo a index...
```

### Errores comunes

| Error | Causa | Solución |
|-------|-------|----------|
| "Email o contraseña incorrectos" | Credenciales inválidas en Supabase Auth | Crear usuario en Supabase Dashboard |
| "Usuario no registrado" | No existe en tabla usuarios | Insertar en tabla usuarios con mismo id_usuario |
| "Error de permisos. RLS" | Políticas RLS no configuradas | Ejecutar RLS_POLICIES.sql |
| "CORS error" | Problema de dominio | Verificar VITE_SUPABASE_URL en auth.js |

---

## 🔒 Seguridad - Buenas Prácticas

✅ **Lo que hacemos bien:**
- RLS previene que usuarios lean datos de otros
- Todas las consultas van a través de políticas de seguridad
- Login valida en dos capas: Auth + Base de Datos
- Errores específicos sin revelar información sensible

❌ **Lo que FALTA (para producción):**
- HTTPS (local está OK)
- Refresh token rotation
- Rate limiting en login
- 2FA/MFA
- Logs de auditoría
- Encriptación de datos en reposo

---

## 📝 Próximos Pasos

1. **Ejecutar RLS_POLICIES.sql** en Supabase
2. **Probar login** con las 5 pruebas listadas arriba
3. **Crear usuarios de prueba** en Supabase Auth + tabla usuarios
4. **Verificar logs** en consola del navegador
5. **Monitorear performance** - verificar que no hay race conditions

---

## 📞 Soporte

Si encuentras problemas:
1. Abre consola (F12)
2. Busca logs con `[LOGIN]`
3. Verifica que RLS_POLICIES.sql fue ejecutado
4. Revisa que el usuario existe en tabla usuarios
