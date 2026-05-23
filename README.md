# Horizon

Horizon es una aplicacion para consultar informacion de mercados, revisar activos, ver el portfolio, entrar a la academia, leer la reflexion del dia y gestionar opciones basicas de usuario.

## Que puedes hacer en Horizon

La aplicacion esta pensada para que un usuario nuevo pueda entrar, moverse por las pantallas principales y consultar la informacion sin complicaciones.

Las paginas principales son:

- `login.html` y `register.html`: iniciar sesion y registrarse.
- `index.html`: dashboard principal de la aplicacion.
- `portfolio.html`: ver tus portfolios.
- `analysis.html`: explorar activos y consultar un ticker.
- `academia.html`: acceder al contenido de academia y aprendizaje.
- `reflexion.html`: leer la reflexion del dia.
- `profile.html`: ver y editar tu perfil.
- `ajustes.html`: cambiar ajustes de la cuenta o de la interfaz.
- `ayuda.html`: abrir el centro de ayuda.

## Como levantar el proyecto en local

Abre el proyecto Horizon en VS Code y sigue estos pasos.

### 1. Levantar el frontend

Abre una terminal dentro de la carpeta `frontend/` y ejecuta:

```bash
python -m http.server 5000
```

Esto dejara disponible la parte visual del proyecto en el puerto 5000.

### 2. Preparar el backend

Crea el archivo de variables de entorno (.env) en la misma dirección que .env_example. Copia las variables y pega las API keys adjuntas en la entrega.

Desde la raiz del proyecto, crea el entorno virtual del backend e instala las dependencias:

```bash
python -m venv backend/venv
pip install -r requirements.txt
```

### 3. Activar el entorno y arrancar el backend

Abre una terminal Git Bash, activa el entorno virtual y levanta la API:

```bash
. backend/venv/Scripts/activate
uvicorn backend.main:app --reload
```

### 4. Abrir la aplicacion

Cuando ambos servicios esten levantados, entra en el navegador a:

```text
localhost:5000/index.html
```

## Nota importante

Es posible que el servidor casero desplegado no este activo en el momento de la correccion, porque el ordenador de sobremesa de un companero del equipo puede estar inestable. Aun asi, el proyecto se puede levantar y probar completo en local siguiendo este manual.

## Flujo rapido

1. Abrir Horizon en VS Code.
2. Levantar el frontend en `frontend/` con `python -m http.server 5000`.
3. Crear `backend/venv` e instalar los requisitos.
4. Activar el entorno virtual desde Git Bash.
5. Ejecutar `uvicorn backend.main:app --reload`.
6. Abrir `localhost:5000/index.html`.
