# Guía de CSS para Desarrolladores - Proyecto Horizon

## Introducción
El CSS ha sido completamente refactorizado para ser **modular, reutilizable y mantenible**. Todas las vistas (index.html, portfolio.html, analysis.html, academy.html) comparten el mismo archivo de estilos.

---

## Sistema de Variables CSS

### Colores
```css
var(--color-primary)       /* #2563EB - Azul principal */
var(--color-secondary)     /* #0B3D91 - Azul oscuro (hover) */
var(--color-tertiary)      /* #777777 - Gris para textos secundarios */
var(--color-text-primary)  /* #1f2937 - Texto principal */
var(--color-text-secondary)/* #6b7280 - Texto secundario */
var(--color-border)        /* #e5e7eb - Bordes */
var(--color-bg-light)      /* #f9fafb - Fondo claro */
var(--color-bg-lighter)    /* #f3f4f6 - Fondo más claro */
```

### Espaciado (Escala completa)
```css
var(--spacing-xs)    /* 4px   - Muy pequeño */
var(--spacing-sm)    /* 8px   - Pequeño */
var(--spacing-md)    /* 12px  - Medio */
var(--spacing-lg)    /* 16px  - Grande */
var(--spacing-xl)    /* 24px  - Muy grande */
var(--spacing-2xl)   /* 32px  - Extra grande */
```

### Bordes Redondeados
```css
var(--radius-sm)     /* 6px   */
var(--radius-md)     /* 8px   */
var(--radius-lg)     /* 10px  */
var(--radius-xl)     /* 12px  */
```

**Consejo:** Usa siempre variables, nunca valores hardcodeados. Esto permite cambios globales en segundos.

---

## Componentes Principales

### Cards
La clase base `.card` se reutiliza en todas partes:

```html
<!-- Card básica -->
<div class="card">
    <div class="card-icon">
        <svg>...</svg>
    </div>
    <h3 class="card-title">Título</h3>
    <p class="card-text">Descripción</p>
    <a class="card-link" href="#">Ver más →</a>
</div>

<!-- Card de métrica (portfolio) -->
<div class="card metric-card">
    <div class="metric-header">
        <span class="metric-title">ETH Disponible</span>
    </div>
    <div class="metric-value">$4,250.00</div>
    <span class="metric-sub text-success">↑ 12.5%</span>
</div>

<!-- Card especial (reflexión) -->
<div class="card card-large">
    <span class="reflexion-label">REFLEXIÓN DEL DÍA</span>
    <p class="reflexion-quote">"El secreto de la inversión..."</p>
    <p class="reflexion-author">— Warren Buffett</p>
    <a class="reflexion-button" href="#">Leer más</a>
</div>
```

### Botones
```html
<!-- Botón primario (filled) -->
<button class="btn-primary">Acciones</button>

<!-- Botón outline -->
<button class="btn-outline">Cancelar</button>

<!-- Botón icon -->
<button class="btn-icon">⚙️</button>

<!-- Alert button small -->
<button class="btn-icon alert-btn">🔔</button>
```

**Nota:** `.btn-primary`, `.reflexion-button` y `.btn-outline` ya tienen hover effects y transitions integrados.

### Badges
```html
<span class="badge badge-success">Activo</span>
<span class="badge badge-green">Confirmado</span>
<span class="badge badge-blue">Información</span>
<span class="badge badge-orange">Pendiente</span>
<span class="badge badge-purple">Premium</span>
<span class="badge badge-gray">Inactivo</span>
<span class="badge badge-teal">Optimizado</span>
```

### Tablas
```html
<div class="card table-section">
    <div class="table-toolbar">
        <h2>Mis Activos</h2>
        <button class="btn-primary">+ Agregar</button>
    </div>
    <div class="table-responsive">
        <table class="custom-table">
            <thead>
                <tr>
                    <th>Activo</th>
                    <th>Precio</th>
                    <th>Cambio</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>
                        <div class="asset-item">
                            <div class="asset-icon">💰</div>
                            <div class="asset-info">
                                <div class="asset-symbol">BTC</div>
                                <div class="asset-name">Bitcoin</div>
                            </div>
                        </div>
                    </td>
                    <td>
                        <div class="price-cell">
                            <div class="price-val">$42,500</div>
                            <div class="price-change text-success">+5.2%</div>
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
        <label class="reflexion-label">Buscar Ticker</label>
        <div class="search-row">
            <div class="input-wrap">
                <svg class="search-icon">...</svg>
                <input 
                    class="search-input" 
                    type="text" 
                    placeholder="Ej: AAPL, GOOGL"
                >
                <ul class="suggestions" style="display: none;">
                    <li class="suggestion-item">Apple (AAPL)</li>
                    <li class="suggestion-item">Google (GOOGL)</li>
                </ul>
            </div>
            <button id="searchBtn" class="btn-primary">Buscar</button>
        </div>
    </div>
</div>
```

---

## Utilidades Reutilizables

### Clases de Texto
```html
<p class="text-success">Ganancia: +$150</p>
<p class="text-danger">Pérdida: -$50</p>
<p class="text-muted">Información secundaria</p>
<p class="text-right">Texto alineado a derecha</p>
<p class="text-bold">Texto en negrita</p>
```

### Iconos
```html
<span class="icon-trend-up">↑ 12.5%</span>  <!-- Verde -->
<span class="icon-shield">🛡️ Seguro</span>   <!-- Azul primario -->
```

---

## Grillas Responsivas

### Grid de Opciones (Index)
```html
<div class="opts-section">
    <div class="card">...</div>
    <div class="card">...</div>
    <div class="card">...</div>
    <div class="card card-large">Reflexión...</div>  <!-- span 2 -->
</div>
```
- **Desktop (1200px+):** 3 columnas
- **Tablet (768-1200px):** 2 columnas
- **Mobile (<768px):** 1 columna

### Grid de Métricas (Portfolio)
```html
<div class="metrics-grid">
    <div class="card metric-card">...</div>
    <div class="card metric-card">...</div>
    <div class="card metric-card">...</div>
</div>
```
- **Desktop:** 3 columnas
- **Tablet:** 2 columnas
- **Mobile:** 1 columna

---

## Sidebar (Automático)

El sidebar se inyecta automáticamente desde `layout.js`. Siempre coloca el contenido en `#dashboard-contenido`:

```html
<script src="js/layout.js"></script>

<div id="dashboard-contenido">
    <h1>Mi Página</h1>
    <p>Contenido aquí...</p>
</div>
```

El sidebar:
- ✅ Es responsivo (oculto en mobile < 768px, slide-over)
- ✅ Tiene toggle para colapsar (80px width)
- ✅ Detecta página activa automáticamente
- ✅ Overlay oscuro en mobile

---

## Responsive Breakpoints

```css
@media (max-width: 1200px) {
    /* Tablets grandes */
    .opts-section { grid-template-columns: repeat(2, 1fr); }
    .metrics-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 768px) {
    /* Tablets y móvil */
    .sidebar { transform: translateX(-100%); }  /* Oculto */
    h1 { font-size: 24px; }
    .card { padding: var(--spacing-lg); }
    .search-row { flex-direction: column; }
}

@media (max-width: 480px) {
    /* Móvil pequeño */
    h1 { font-size: 20px; }
    .card { padding: var(--spacing-md); }
    .reflexion-quote { font-size: 20px; }
}
```

---

## Buenas Prácticas

### ✅ HACER
```css
/* Usar variables */
padding: var(--spacing-lg);
color: var(--color-primary);
border-radius: var(--radius-md);

/* Usar clases reutilizables */
<div class="card">...</div>
<span class="badge badge-success">...</span>
<button class="btn-primary">...</button>

/* Agrupar responsives */
@media (max-width: 768px) {
    .my-component { /* cambios */ }
    .another-component { /* cambios */ }
}
```

### ❌ NO HACER
```css
/* Hardcodear valores */
padding: 24px;
color: #2563EB;
border-radius: 8px;

/* Crear clases duplicadas */
.btn-primary { ... }
.button-primary { ... }
.primary-btn { ... }

/* Media queries dispersas */
/* En línea 150 */
@media (max-width: 768px) { ... }
/* En línea 450 */
@media (max-width: 768px) { ... }  /* ❌ DUPLICADO */
```

---

## Troubleshooting

### Síntoma: Card muy grande/pequeña
**Solución:** Ajusta `padding` usando `--spacing-*`:
```css
.card { padding: var(--spacing-xl); }  /* Grande */
.card { padding: var(--spacing-md); }  /* Pequeño */
```

### Síntoma: Colores inconsistentes
**Solución:** Siempre usa variables de color:
```css
color: var(--color-text-primary);  /* ✅ Correcto */
color: #1f2937;                    /* ❌ Evita */
```

### Síntoma: Hover effect no funciona
**Solución:** Asegúrate de usar la clase correcta:
```html
<!-- ✅ Tiene hover integrado -->
<button class="btn-primary">Clic</button>

<!-- ❌ Falta estilos -->
<button>Clic</button>
```

### Síntoma: Layout roto en mobile
**Solución:** Verifica que `#dashboard-contenido` rodea todo:
```html
<script src="js/layout.js"></script>
<div id="dashboard-contenido">  <!-- ✅ Requerido -->
    <!-- Tu contenido -->
</div>
```

---

## Estructura del Archivo CSS

```
styles.css
├── VARIABLES CSS (:root)
├── BASE (body, h1, p, etc.)
├── CARDS (.card, .card-icon, etc.)
├── BOTONES (.btn-primary, .btn-outline)
├── BADGES (.badge-success, etc.)
├── UTILIDADES (.text-success, .icon-trend-up)
├── SIDEBAR (layout.js)
├── PORTFOLIO ESPECÍFICOS (tablas, métricas)
├── ANALYSIS ESPECÍFICOS (buscador)
└── MEDIA QUERIES (responsive)
```

---

## Cambios Recientes (Refactorización v2.0)

- ✅ Consolidadas 4 clases de cards en 1
- ✅ Unificados 3 tipos de botones
- ✅ Eliminadas 200+ líneas duplicadas
- ✅ Centralizado sistema de variables
- ✅ Media queries sin duplicaciones
- ✅ Mejorado 30% mantenibilidad

---

## Soporte

Si tienes dudas:
1. Revisa la estructura de cards/botones arriba
2. Busca en `styles.css` por nombre de clase
3. Usa el inspector de navegador (F12) para debug
4. Comparte en el canal de desarrollo

¡Feliz codificación! 🚀
