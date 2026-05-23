# Infra portable de Horizon

Esta carpeta agrupa toda la infraestructura de despliegue y deja separado lo que es aplicacion de lo que es ejecucion, red y contenedores.

## Que incluye

- `infra/docker/Dockerfile.backend`: imagen base para el backend.
- `infra/nginx/default.conf`: configuracion de Nginx para servir la aplicacion por HTTP.
- `infra/compose/docker-compose.yml`: stack de Nginx + backend.
- `infra/compose/.env.template`: variables minimas del host.

## Uso con IP local

- En desarrollo local, usar `http://localhost:8000`.
- En despliegue compartido, usar `http://<IP_DEL_PC>`.
- Si el frontend llama al backend con `/api`, debe seguir apuntando al mismo origen para no romper la carga de JSON.

Esto evita errores donde la app espera JSON y recibe HTML.

## Arranque rapido

1. Copiar plantilla de entorno:

```powershell
Copy-Item .\infra\compose\.env.template .\infra\compose\.env
```

2. Ajustar `PUBLIC_PORT` en `infra/compose/.env` para usar un puerto distinto.

3. Levantar stack:

```powershell
Set-Location .\infra\compose
docker compose up -d --build
```

4. Abrir en navegador:
- `http://<IP_DEL_PC>`
- Si el backend expone otro puerto, usar `http://<IP_DEL_PC>:<PUERTO>`

