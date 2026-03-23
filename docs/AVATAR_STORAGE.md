# Almacenamiento de Avatares — Horizon

Documento que describe cómo se guardan, actualizan y eliminan avatares de usuario.

## Arquitectura

### Buckets de Supabase Storage

| Bucket | Tipo | Contenido |
|--------|------|----------|
| `avatars-default` | Público | Avatares predeterminados (3 opciones) |
| `avatars` | Privado | Avatares personalizados subidos por usuarios |

### Base de datos

Campo `foto_perfil` en tabla `usuarios` almacena:
- URL pública completa para defaults: `https://.../storage/v1/object/public/avatars-default/default/default-{1,2,3}.png`
- Path interno para personalizados: `{user_id}/{uuid}.{ext}` (se convierte a URL firmada al responder)

## Flujo: Subir avatar personalizado

### Endpoint
- `POST /usuarios/me/avatar` — crea nuevo avatar si no existe
- `PUT /usuarios/me/avatar` — reemplaza avatar existente

### Proceso backend

1. `UserService.agregar_avatar()` o `actualizar_avatar()`
2. Valida archivo: tipo MIME, tamaño máximo (5MB), magic bytes
3. `StorageService.upload_avatar()` genera path `{user_id}/{uuid}.{ext}` y sube a bucket privado
4. Actualiza columna `foto_perfil` en BD con path interno
5. `StorageService.hydrate_user_avatar()` convierte path a URL firmada (1h)
6. Frontend recibe URL firmada en respuesta

### Tipos permitidos
JPEG, PNG, WEBP, GIF

### Frontend (profile.js / register.js)

1. Usuario selecciona archivo local
2. Se almacena en `selectedCustomAvatarFile` sin convertir a base64
3. Al enviar formulario:
   - Si es default: enviado en PATCH `/usuarios/me` como JSON
   - Si es personalizado: enviado en POST/PUT `/usuarios/me/avatar` como `FormData`

## Flujo: Actualizar a avatar predeterminado

### Endpoint
`PATCH /usuarios/me` con JSON `{"foto_perfil": "<url_default>"}`

### Proceso backend

1. Detecta cambio de personalizado a default
2. `StorageService.delete_avatar()` elimina archivo anterior (solo si es path privado)
3. Actualiza BD con URL pública
4. No genera URL firmada (es pública)

## Flujo: Eliminar avatar

### Endpoint
`DELETE /usuarios/me/avatar`

### Proceso backend

1. `UserService.eliminar_avatar()`
2. Detecta si es avatar personalizado (path privado)
3. `StorageService.delete_avatar()` elimina de bucket privado
4. Actualiza `foto_perfil` a `NULL` en BD
5. Responde con confirmación

## Flujo: Mostrar avatar

### Proceso backend

Todos los endpoints que devuelven usuario (`GET /auth/me`, etc.) ejecutan:

1. `StorageService.hydrate_user_avatar_safe()` mutatiza el objeto
2. Si `foto_perfil` es URL pública: la devuelve
3. Si `foto_perfil` es path privado: genera signed URL (3600s)
4. Si falla: asigna `None` (no rompe autenticación)

### Frontend

Recibe URL directamente en campo `foto_perfil` del objeto usuario

## Seguridad

- Archivos personalizados protegidos con RLS (bucket privado requiere `SUPABASE_SERVICE_ROLE_KEY`)
- Signed URLs expiran después de 1 hora (`SUPABASE_AVATAR_SIGNED_URL_TTL`)
- Magic bytes validados antes de guardar
- Path privado parseado para evitar acceso a otros usuarios
- Usuario solo puede eliminar/actualizar su propio avatar

## Eliminación de cuenta

Cuando se elimina usuario:
1. Se valida que existe cliente admin (necesario para avatar privado)
2. Se elimina fila en tabla `usuarios`
3. Se elimina en Supabase Auth
4. Se elimina archivo de avatar personalizado (si existe)
5. Si Auth falla, se restaura fila en BD (rollback lógico)

## Variables de entorno

```
SUPABASE_AVATARS_BUCKET=avatars
SUPABASE_AVATAR_SIGNED_URL_TTL=3600
SUPABASE_SERVICE_ROLE_KEY=<jwt_service_role>
```

Sin `SUPABASE_SERVICE_ROLE_KEY`, no se pueden subir ni eliminar avatares personalizados.
