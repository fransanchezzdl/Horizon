# Sistema de estilos Horizon

## Objetivo
Este documento define la estructura de frontend/css/styles.css para mantener consistencia visual, reducir duplicados y facilitar cambios sin regresiones.

## Estructura del archivo
styles.css está organizado en bloques funcionales:

1. Variables globales
- Tipografía
- Paleta de colores
- Espaciado
- Radios
- Anchos de layout (sidebar)

2. Base y tipografía
- body
- h1, h2, h3, p
- utilidades de texto

3. Componentes compartidos
- Cards
- Botones
- Badges
- Tablas
- Inputs y buscador
- Modales y alertas

4. Layout global
- Sidebar desktop
- Overlay
- Bottom navbar móvil
- Wrapper principal de contenido

5. Vistas
- Portfolio
- Analysis
- Academia
- Perfil
- Login/Register
- Reflexión

6. Responsive
- Breakpoints de 1200, 1024, 768, 600, 480
- Ajustes centralizados por viewport

## Reglas de escalabilidad

### 1) Mantener contrato de clases
No renombrar clases ya usadas por frontend/js y las vistas HTML sin actualizar ambos lados.

### 2) Reutilizar antes de crear
Antes de crear una clase nueva, validar si existe una equivalente:
- Superficies: card, metric-card, result-card
- Acción: btn-primary, btn-secondary, btn-outline, btn-icon
- Estado: badge-* y text-*

### 3) Evitar hardcode
Usar variables de :root para color, spacing, radios y medidas repetidas.

### 4) Reducir especificidad
Preferir selectores de clase planos. Evitar anidamiento profundo y selectores acoplados a estructura HTML.

### 5) Responsive por bloques
Agregar ajustes responsive junto al bloque global de media queries, no dispersarlos en múltiples secciones.

### 6) Estados visuales explícitos
Definir :hover, :focus, :disabled y variantes de estado cuando aplique (botones, inputs, alertas).

### 7) Compatibilidad con JS
Las clases creadas o eliminadas deben revisarse contra:
- frontend/js/layout.js
- frontend/js/portfolio.js
- frontend/js/search.js
- frontend/js/academia.js
- frontend/js/login.js
- frontend/js/register.js

## Convenciones

### Nombres
- Componentes: nombre corto y semántico (card, badge, modal)
- Variantes: sufijo por intención (btn-primary, badge-success, alert-error)
- Utilidades: prefijo funcional (text-*, icon-*)

### Orden interno sugerido por regla
1. display/position
2. box model
3. tipografía
4. color/fondo/borde
5. interacción/transición

## Flujo recomendado para nuevos estilos
1. Definir el componente base reutilizable.
2. Agregar variantes mínimas necesarias.
3. Probar en desktop, tablet y móvil.
4. Verificar que no se introduzcan duplicados.
5. Revisar impacto en vistas y scripts.

## Mantenimiento
- Evitar duplicar bloques completos de secciones existentes.
- Consolidar reglas comunes con selectores agrupados.
- Si una clase deja de usarse, retirarla en el mismo cambio tras validar referencias.
