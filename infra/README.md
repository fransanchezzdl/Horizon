# Infra portable de Horizon

Esta carpeta separa la infraestructura de despliegue del codigo de aplicacion.

## Que incluye

- `infra/docker/Dockerfile.backend`: imagen base para backend.
- `infra/nginx/default.conf.template`: proxy inverso con HTTP, HTTPS y challenge de Let's Encrypt.
- `infra/compose/docker-compose.yml`: stack de Nginx + backend + Certbot.
- `infra/compose/.env.template`: variables minimas del host.

## Compatibilidad local (sin romper localhost)

El frontend debe mantener modo dual:
- En desarrollo local, usar `http://localhost:8000`.
- En despliegue con Nginx, usar mismo origen con `/api`.

Esto evita errores donde la app espera JSON y recibe HTML.

## Arranque rapido

1. Copiar plantilla de entorno:

```powershell
Copy-Item .\infra\compose\.env.template .\infra\compose\.env
```

2. Rellenar `SERVER_NAME` y `LETSENCRYPT_EMAIL` en `infra/compose/.env`.

3. Emitir el primer certificado antes de arrancar Nginx:

```powershell
Set-Location .\infra\compose
docker compose --profile bootstrap run --service-ports --rm certbot-init
```

4. Levantar stack:

```powershell
Set-Location .\infra\compose
docker compose up -d --build
```

5. Abrir en navegador:
- `https://tu-dominio.ejemplo.com`
- `http://tu-dominio.ejemplo.com` debe redirigir a HTTPS

## Pasos HTTPS

1. Asigna `SERVER_NAME` al dominio publico real.
2. Abre y redirige en el router los puertos `80/TCP` y `443/TCP` hacia la IP fija del PC anfitrion.
3. Emite el certificado inicial con `docker compose --profile bootstrap run --service-ports --rm certbot-init`.
4. Arranca el stack con `docker compose up -d --build`.
5. Verifica que Nginx sirve `https://<dominio>` sin advertencias.
6. Mantén Certbot activo para renovar automaticamente el certificado.

## Scheduler

El scheduler queda solo planificado y no activo en esta fase.

En `docker-compose.yml` esta definido con profile `scheduler` para activarlo despues, cuando termine su implementacion.
