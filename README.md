# Horizon - Guía de Trabajo
🚀 Flujo de Trabajo para el Equipo
Para mantener el repositorio limpio, todos debemos seguir estos pasos:

## 1. Al empezar el día (Sincronización)
Antes de escribir una sola línea de código, descarga los cambios de tus compañeros:

git fetch --all: Actualiza la información de las ramas remotas.

git pull origin developer: Trae los últimos cambios a tu local.

## 2. Procedimiento GitFlow
Rama main: Solo para código estable y en producción. No se toca directamente.

Rama developer: Rama principal de desarrollo. Aquí se integran las nuevas funcionalidades.

Ramas feature/: Para cada tarea nueva, crea una rama desde developer:

Ejemplo: git checkout -b feature/nombre-tarea

Pull Requests (PR): Una vez terminada tu tarea, sube tu rama y abre un PR hacia developer para que alguien revise el código.

Ramas release/: Cuando tengamos varias funciones listas para subir a producción, se crea una rama de preparación antes de pasar a main.

Guarda y haz el primer commit:

Bash
git add README.md
git commit -m "Initial commit: Add README with workflow instructions"

## 3. Crear rama developer y sincronizar
Ahora vamos a crear el entorno de desarrollo donde realmente sucederá la magia.

Crea la rama developer a partir de main:

Bash
git checkout -b developer
Mergear main (aunque en este momento son idénticas, este es el comando que usarás en el futuro):

Bash
git merge main

## 4. Empezar a usar developer
¡Ya estás ahí! Para asegurarte de que estás trabajando en el lugar correcto, verifica tu rama actual:

Comprobar rama:

Bash
git branch
(Debería aparecer un asterisco en developer).

A partir de ahora, todo lo que hagas será sobre developer. Cuando quieras subirlo a la nube (GitHub/GitLab), recuerda conectar el remoto:

Bash
git remote add origin https://github.com/tu-usuario/Horizon.git
git push -u origin developer