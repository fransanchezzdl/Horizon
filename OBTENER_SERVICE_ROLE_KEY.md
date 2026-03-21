# 🔑 Cómo Obtener SUPABASE_SERVICE_ROLE_KEY

## El Problema
La tabla `activos` tiene **RLS (Row Level Security)** habilitado. Esto significa:
- ✅ Las **lecturas** funcionan con la clave anónima
- ❌ Los **UPDATEs** se rechazan silenciosamente

## La Solución: SERVICE_ROLE_KEY

`SUPABASE_SERVICE_ROLE_KEY` es una clave administrativa que **bypasea RLS** para operaciones de backend.

### Paso 1: Obtener la SERVICE_ROLE_KEY

1. Ve a tu proyecto Supabase: https://app.supabase.com/
2. Selecciona proyecto `fzxtliowdmhumnxfskvy`
3. Ve a **Settings** → **API**
4. En el panel derecho encontrarás:
   - **Project URL** ← Ya la tienes (SUPABASE_URL)
   - **Project API keys:**
     - `anon public` ← La que ya tienes (SUPABASE_KEY)
     - **`Service role secret`** ← **ESTA ES LA QUE NECESITAS** 👈

5. Haz click en el ícono de "copiar" junto a **Service role secret**

### Paso 2: Añadir a backend/.env

Abre `backend/.env` y añade al final:

```env
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

(Pega el valor que copiaste)

### Paso 3: Verificar

Ejecuta el test:
```bash
python test_update_activos.py
```

Deberías ver:
```
✅ Response count: 1
✅ Precio en BD ahora: 99.99
```

### Paso 4: Entrenar nuevamente

```bash
python train_single_ticker.py KO
```

Ahora debería funcionar y ver:
```
✅ Activo KO actualizado correctamente (1 fila(s) afectada(s))
```

---

## 🔐 Seguridad

⚠️ **IMPORTANTE:**
- `SUPABASE_SERVICE_ROLE_KEY` es sensible - **NO** la compartas en commits
- Esté en `.env` que está en `.gitignore` ✅
- Solo úsala en el backend, nunca en el frontend ✅
- Supabase recomienda rotarla regularmente

---

## 📝 Archivos Modificados

Estos archivos ahora usan el cliente admin para UPDATEs:
- ✅ `backend/database.py` - Crea cliente admin
- ✅ `backend/daos/activo_dao.py` - Usa cliente admin en UPDATE

