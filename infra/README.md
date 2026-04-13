# Infra portable de Horizon

Esta carpeta separa la infraestructura de despliegue del codigo de aplicacion.

## Que incluye

- `infra/docker/Dockerfile.backend`: imagen base para backend.
- `infra/nginx/default.conf`: proxy inverso y rutas limpias sin `.html`.
- `infra/compose/docker-compose.yml`: stack de Nginx + backend.
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

2. Levantar stack:

```powershell
Set-Location .\infra\compose
docker compose up -d --build
```

3. Abrir en navegador:
- `http://localhost` (o el puerto definido en `PUBLIC_PORT`)

## Scheduler

El scheduler queda solo planificado y no activo en esta fase.

En `docker-compose.yml` esta definido con profile `scheduler` para activarlo despues, cuando termine su implementacion.
