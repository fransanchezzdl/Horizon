# Horizon: Manual del Desarrollador

Bienvenido al repositorio de **Horizon**. Síguelo para evitar conflictos en Git y mantener el código limpio.

---

## 🛠️ 1. Configuración Inicial (Primeros pasos)

Si eres nuevo en el equipo o estás configurando tu ordenador desde cero, sigue **una** de estas dos opciones:

### Opción A: Aún no tienes la carpeta en tu PC (Recomendado)
Abre tu terminal en la carpeta donde guardas tus proyectos y ejecuta:

```bash
git clone [https://github.com/fransanchezzdl/Horizon.git](https://github.com/fransanchezzdl/Horizon.git)
cd Horizon
# Automáticamente estarás en la rama 'developer' o 'master'. 
# Asegúrate de descargar todas las referencias:
git fetch --all
```

### Opción B: Ya tienes el código pero no está conectado a Git
Si ya tienes la carpeta Horizon con archivos en tu disco duro:

```bash
cd "D:\Visual Studio\Proyectos\Horizon"
git init
git branch -M master
git remote add origin [https://github.com/fransanchezzdl/Horizon.git](https://github.com/fransanchezzdl/Horizon.git)

# Bajamos la información del servidor sin borrar tus archivos locales
git fetch --all

# Conectamos tu rama local con la del servidor
git branch --set-upstream-to=origin/master master
```
## 🔄 2. Rutina Diaria (Antes de trabajar)
⚠️ REGLA DE ORO: Nunca empieces a escribir código sin actualizar tu repositorio. Si no lo haces, crearás conflictos difíciles de arreglar.

Actualizar referencias:
```bash
git fetch --all
Descargar cambios en tu rama:
Sitúate en la rama de desarrollo e integra lo nuevo:
```
```bash
git checkout developer
git pull origin developer
```

## 🌊 3. Metodología GitFlow (Nuestras Ramas)
Para mantener el orden, usamos una estructura estricta de ramas. ¡No trabajes directamente en master!

📌 Mapa de Ramas
Rama        Descripción                         Permisos
master      Código de Producción                Estable y probado.,SOLO LECTURA. Nadie hace push aquí.
developer   Rama de Integración.                Aquí se une todo el trabajo.,Se aceptan Pull Requests (PR).
feature/    Ramas temporales para tus tareas.   Aquí es donde tú trabajas.

## 🔨 Flujo de Trabajo (Paso a Paso)
Cada vez que tengas una tarea nueva (ej: "Crear pantalla de Login"), sigue este ciclo:

### 1. Crear la rama (Feature)
Siempre nace desde developer:

```bash
git checkout developer
git pull origin developer  # Asegúrate de estar actualizado
git checkout -b feature/login-pantalla
```

### 2. Programar y Guardar (Commit)
Haz cambios pequeños y frecuentes. Usa mensajes claros:
```bash
git add .
git commit -m "feat: diseño inicial del formulario de login"
Tipos de commit: feat: (nueva función), fix: (corrección), docs: (documentación).
```

### 3. Subir cambios (Push)
Sube tu rama al servidor para guardarla:
```bash
git push -u origin feature/login-pantalla
```
### 4. Integrar (Pull Request)
Ve a GitHub.

Abre un Pull Request (PR) comparando tu rama feature/... contra developer.

Avisa al equipo para que revisen tu código.

Una vez aprobado, se hace el Merge en GitHub.

### 5. Limpieza
Cuando tu código ya esté en developer, borra tu rama local:
```bash
git checkout developer
git pull origin developer
git branch -d feature/login-pantalla
``` 
---
Horizon Project - Guía interna 2026