# Referencia Rápida CSS - Copiar/Pegar

## Elementos Más Usados

### Cards
```html
<!-- Card simple -->
<div class="card">
    <div class="card-icon">📊</div>
    <h3 class="card-title">Portafolio</h3>
    <p class="card-text">Ver mis inversiones</p>
    <a class="card-link" href="#">Ver más →</a>
</div>

<!-- Card métrica -->
<div class="card metric-card">
    <span class="metric-title">Valor Total</span>
    <div class="metric-value">$12,450</div>
    <span class="metric-sub text-success">+8.5%</span>
</div>

<!-- Card reflexión -->
<div class="card card-large">
    <span class="reflexion-label">REFLEXIÓN</span>
    <p class="reflexion-quote">"El dinero es un sirviente..."</p>
    <p class="reflexion-author">— Warren Buffett</p>
    <a class="reflexion-button" href="#">Leer</a>
</div>
```

### Botones
```html
<button class="btn-primary">Primario</button>
<button class="btn-outline">Secundario</button>
<button class="btn-icon">⚙️</button>
<a href="#" class="btn-primary">Link como botón</a>
```

### Badges
```html
<span class="badge badge-success">Éxito</span>
<span class="badge badge-blue">Información</span>
<span class="badge badge-orange">Advertencia</span>
<span class="badge badge-gray">Neutral</span>
```

### Tablas
```html
<div class="card table-section">
    <div class="table-toolbar">
        <h2>Activos</h2>
        <button class="btn-primary">+ Agregar</button>
    </div>
    <div class="table-responsive">
        <table class="custom-table">
            <thead>
                <tr>
                    <th>Nombre</th>
                    <th>Precio</th>
                    <th>Cambio</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>
                        <div class="asset-item">
                            <div class="asset-icon">💎</div>
                            <div class="asset-info">
                                <div class="asset-symbol">ETH</div>
                                <div class="asset-name">Ethereum</div>
                            </div>
                        </div>
                    </td>
                    <td>
                        <div class="price-cell">
                            <div class="price-val">$2,850</div>
                            <div class="price-change text-success">+3.2%</div>
                        </div>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</div>
```

### Buscador
```html
<div class="card search-section">
    <div class="search-inner">
        <label class="reflexion-label">Buscar</label>
        <div class="search-row">
            <div class="input-wrap">
                <svg class="search-icon">⚙️</svg>
                <input class="search-input" type="text" placeholder="Buscar...">
                <ul class="suggestions"></ul>
            </div>
            <button class="btn-primary">Buscar</button>
        </div>
    </div>
</div>
```

### Grid de Cards
```html
<div class="opts-section">
    <div class="card">Card 1</div>
    <div class="card">Card 2</div>
    <div class="card">Card 3</div>
    <div class="card card-large">Card grande (span 2)</div>
</div>
```

### Grid de Métricas
```html
<div class="metrics-grid">
    <div class="card metric-card">Métrica 1</div>
    <div class="card metric-card">Métrica 2</div>
    <div class="card metric-card">Métrica 3</div>
</div>
```

## Variables de Uso Frecuente

```css
/* Espaciado */
var(--spacing-xs)    /* 4px */
var(--spacing-sm)    /* 8px */
var(--spacing-md)    /* 12px */
var(--spacing-lg)    /* 16px */
var(--spacing-xl)    /* 24px */
var(--spacing-2xl)   /* 32px */

/* Colores */
var(--color-primary)      /* Azul #2563EB */
var(--color-secondary)    /* Azul oscuro #0B3D91 */
var(--color-text-primary) /* Texto #1f2937 */
var(--color-border)       /* Borde #e5e7eb */

/* Redondeo */
var(--radius-md)   /* 8px */
var(--radius-lg)   /* 10px */
var(--radius-xl)   /* 12px */
```

## Clases de Utilidad

```html
<!-- Colores de Texto -->
<p class="text-success">Verde (éxito)</p>
<p class="text-danger">Rojo (error)</p>
<p class="text-muted">Gris (secundario)</p>
<p class="text-bold">Negrita</p>

<!-- Alineación -->
<p class="text-left">Izquierda</p>
<p class="text-right">Derecha</p>

<!-- Iconos con Color -->
<span class="icon-trend-up">↑ Tendencia</span>
<span class="icon-shield">🛡️ Seguridad</span>
```

## Estructura Base de Página

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Horizon</title>
    <link rel="stylesheet" href="../css/styles.css">
</head>
<body>
    <script src="../js/layout.js"></script>
    
    <div id="dashboard-contenido">
        <div class="bienvenida-section">
            <h1>Mi Página</h1>
            <p class="subtitle">Bienvenido a Horizon</p>
        </div>

        <!-- Tu contenido aquí -->
        <div class="opts-section">
            <!-- Cards -->
        </div>
    </div>
</body>
</html>
```

## Grid Responsivo

```html
<!-- 3 columnas en desktop, 2 en tablet, 1 en mobile -->
<div class="opts-section">
    <div class="card">...</div>
    <div class="card">...</div>
    <div class="card">...</div>
</div>

<!-- La card grande ocupa 2 columnas en desktop, 1 en mobile -->
<div class="card card-large">Reflexión</div>
```

## Breakpoints

```
Desktop:  1200px+  (3 columnas)
Tablet:   768-1200px (2 columnas)
Mobile:   < 768px  (1 columna)
```

## Tips Rápidos

✅ **Siempre rodea con `#dashboard-contenido`**
```html
<script src="../js/layout.js"></script>
<div id="dashboard-contenido">
    <!-- AQUÍ va todo -->
</div>
```

✅ **Usa variables CSS, nunca hardcodea valores**
```css
/* ✅ Bien */
padding: var(--spacing-lg);

/* ❌ Evita */
padding: 16px;
```

✅ **Las cards se apilan automáticamente en mobile**
```html
<!-- No necesita media queries -->
<div class="opts-section">
    <div class="card">...</div> <!-- 3 cols desktop, 1 col mobile -->
</div>
```

✅ **Los botones ya tienen hover**
```html
<button class="btn-primary">Click me</button>
<!-- Ya tiene:
   - Transición suave
   - Efecto hover (color + transform)
   - Sombra -->
```

## Atajos de Búsqueda en Styles.css

| Quiero cambiar... | Busca en CSS | Línea aprox |
|------------------|-------------|-----------|
| Color primario | `--color-primary` | 10 |
| Espaciado global | `--spacing-` | 22-27 |
| Tamaño de botón | `.btn-primary` | 197 |
| Padding de card | `.card {` | 91 |
| Hover de card | `.card:hover` | 110 |
| Mobile (768px) | `@media (max-width: 768px)` | 1010 |
| Tablas | `.custom-table` | 765 |
| Sidebar | `.sidebar {` | 505 |

---

**¿Necesitas crear algo nuevo?**

1. ✅ Define clase en `.card`, `.btn-primary` o `.badge`
2. ✅ Usa variables `var(--spacing-*)` y `var(--color-*)`
3. ✅ Agrega media query al final (768px, 1200px)
4. ✅ Prueba en mobile (F12 DevTools)

---

**¡Listo para usar!** Copy-paste los ejemplos arriba. 🚀
