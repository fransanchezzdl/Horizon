<!-- 
📋 PROMPT PARA INTEGRACIÓN XAI EN FRONTEND
============================================
Guía completa para desarrollador frontend
Proyecto: Horizon (Trading AI + XAI)
Fecha: Abril 2026
-->

# 🎯 PROMPT: Integración de XAI (Explicabilidad AI) en Frontend

## 📌 Resumen Ejecutivo

El backend está **100% completo** con un sistema de Explicabilidad AI (XAI) usando SHAP. Tu misión es integrar estas explicaciones en el frontend de forma que los usuarios finales puedan **entender por qué el modelo predice ALCISTA/BAJISTA/LATERAL**.

**Tiempo estimado**: 2-3 horas para versión MVP completa

---

## 🔧 Stack Técnico

### Backend (YA HECHO)
- **Framework**: FastAPI
- **Explainability**: SHAP (SHapley Additive exPlanations)
- **BD**: Supabase PostgreSQL
- **Models**: XGBoost (clasificación ternaria)

### Frontend (TU PARTE)
- **HTML5** + **CSS3** + **JavaScript vanilla** (sin frameworks pesados)
- ó **React/Vue** si prefieres (pero no es necesario)
- Llamadas AJAX/Fetch a REST API

---

## 📊 Datos Disponibles en BD

**16 explicaciones XAI ya generadas** en tabla `xai_explicaciones`:

```
Ticker  | Cantidad | Ejemplo Señal | Confianza
--------|----------|---------------|----------
AAPL    | 3        | BAJISTA       | 63.6%
GOOGL   | 2        | ALCISTA       | ~70%
INTC    | 2        | LATERAL       | 51.3%
MSFT    | 2        | ALCISTA       | ~60%
VXX     | 1        | LATERAL       | 50.5%
(otros) | 4        | Variado       | 45-75%
```

---

## 🔌 API Endpoints Disponibles

**Base**: `http://localhost:8000` (en desarrollo)

### 1️⃣ Obtener Explicación Actual de un Ticker
```
GET /api/activos/{ticker}/explicacion

Ejemplo: GET /api/activos/AAPL/explicacion

Response (200 OK):
{
  "id": 123,
  "ticker": "AAPL",
  "fecha_prediccion": "2026-04-12T11:26:00Z",
  "senal_prediccion": "ALCISTA",           ← Señal (3 clases)
  "confianza_prediccion": 0.753,           ← 0-1 (75.3%)
  "shap_grafico": "iVBORw0KGgoAAAANS...", ← Base64 PNG (force plot)
  "features_top20": [
    {
      "feature_name": "Feature_0",
      "importancia": 0.3308,
      "contribucion": 0.15
    },
    {
      "feature_name": "Feature_28",
      "importancia": 0.2012,
      "contribucion": -0.08
    },
    ... (18 más)
  ],
  "shap_valores": [
    {
      "feature_name": "Feature_0",
      "shap_value": 0.25,
      "feature_value": 42.5,
      "shap_abs": 0.25
    },
    ... (87 más)
  ],
  "contribucion_features": {
    "Feature_0": 0.15,
    "Feature_28": -0.08,
    ... (88 total)
  }
}
```

### 2️⃣ Obtener Histórico de Explicaciones
```
GET /api/activos/{ticker}/historial-xai?dias=30

Ejemplo: GET /api/activos/AAPL/historial-xai?dias=30

Response (200 OK):
[
  {
    "id": 125,
    "ticker": "AAPL",
    "fecha_prediccion": "2026-04-12T11:26:00Z",
    "senal_prediccion": "ALCISTA",
    "confianza_prediccion": 0.763,
    "prediccion_correcta": null,  ← null=no validada, true=correcta, false=incorrecta
    "version_modelo": "Phase3"
  },
  {
    "id": 124,
    "ticker": "AAPL",
    "fecha_prediccion": "2026-04-11T15:30:00Z",
    "senal_prediccion": "LATERAL",
    "confianza_prediccion": 0.505,
    "prediccion_correcta": true,
    "version_modelo": "Phase3"
  },
  ... (más historial)
]
```

### 3️⃣ Obtener Explicación por ID
```
GET /api/explicaciones/{id}

Ejemplo: GET /api/explicaciones/123

Response: Mismo formato que endpoint #1
```

### 4️⃣ Guardar Feedback del Usuario (IMPORTANTE)
```
POST /api/explicaciones/{id}/validar

Headers: Content-Type: application/json

Body:
{
  "util": true,              ← El usuario dice: ¿fue útil?
  "comentario_usuario": "Las features seleccionadas tienen sentido"
}

Response (200 OK):
{
  "success": true,
  "message": "Validación guardada"
}
```

### 5️⃣ Obtener Estadísticas Agregadas por Ticker
```
GET /api/estadisticas/xai?ticker=AAPL&dias=30

Response (200 OK):
{
  "ticker": "AAPL",
  "total_explicaciones": 3,
  "explicaciones_validadas": 1,
  "porcentaje_util": 100,
  "features_mas_importantes": [
    {"nombre": "Feature_0", "apariciones": 3, "importancia_promedio": 0.33},
    ... (top 10)
  ]
}
```

### 6️⃣ Health Check
```
GET /api/health/xai

Response (200 OK):
{
  "status": "ok",
  "xai_engine": "active",
  "models_loaded": 12,
  "explicaciones_en_bd": 16
}
```

---

## 🎨 Mockups de UI Recomendada

### Opción A: Integración en Página Existente (Analysis.html)
```
┌────────────────────────────────┐
│ [PREDICCIÓN]                   │
│ Señal: 🔺 ALCISTA              │
│ Confianza: ████████░░ 75.3%    │
└────────────────────────────────┘
        │
        ↓ [Ver Explicación XAI]
        ↓
┌────────────────────────────────┐
│ MODAL/POPUP                    │
├────────────────────────────────┤
│ 🔍 EXPLICACIÓN SHAP            │
│                                │
│ [Gráfico Force Plot PNG]       │
│ (base64 del backend)           │
│                                │
│ ⭐ TOP 20 FEATURES             │
│ #1  Feature_0    ▓▓▓▓░ 33.1%   │
│ #2  Feature_28   ▓▓░░░  20.1%  │
│ #3  Feature_70   ▓▓░░░░ 15.0%  │
│ ... (17 más)                   │
│                                │
│ 💭 ¿Útil? [✓ SÍ] [✗ NO]      │
│                                │
│ [CERRAR]                       │
└────────────────────────────────┘
```

### Opción B: Dashboard Dedicado (xai-dashboard.html)
```
┌──────────────────────────────────────┐
│ 🤖 DASHBOARD XAI                     │
├──────────────────────────────────────┤
│                                      │
│ Selecciona ticker: [AAPL ▼]        │
│                    [Generar Nueva]  │
│                                      │
├──────────────────────────────────────┤
│                                      │
│ 🎯 Predicción Actual                │
│ Signal: ALCISTA │ Confianza: 75.3% │
│                                      │
│ [SHAP Force Plot Image]             │
│                                      │
│ ⭐ Features Importantes             │
│ (tabla con 88 features)             │
│                                      │
│ 💭 Feedback: [✓] [✗]               │
│                                      │
├──────────────────────────────────────┤
│                                      │
│ 📊 Histórico (últimos 30 días)      │
│                                      │
│ Fecha      │ Señal   │ Conf │ OK?  │
│ 12/04/26   │ ALCISTA │ 75%  │ ✓    │
│ 11/04/26   │ LATERAL │ 50%  │ -    │
│ 10/04/26   │ BAJISTA │ 63%  │ ✓    │
│                                      │
└──────────────────────────────────────┘
```

---

## 📁 Estructura de Archivos a Crear

```
frontend/
├── js/
│   ├── xai-api.js                ← ✨ NUEVO: Funciones para llamar API
│   ├── xai-ui.js                 ← ✨ NUEVO: Manejo de UI/DOM
│   └── main.js                   ← EXISTENTE: Incluir scripts XAI
│
├── css/
│   ├── xai-styles.css            ← ✨ NUEVO: Estilos para XAI
│   └── main.css                  ← EXISTENTE: Estilos generales
│
├── analysis.html                 ← MODIFICAR: Agregar botón XAI
├── xai-dashboard.html            ← ✨ NUEVO: Dashboard completo
├── index.html                    ← MODIFICAR: Link a dashboard
│
└── assets/
    └── xai-modal.html            ← ✨ NUEVO: Template de modal
```

---

## 🚀 Implementación Paso a Paso

### PASO 1: Crear `js/xai-api.js` (100 líneas)

Este archivo manejará TODAS las llamadas a la API:

```javascript
// js/xai-api.js
// API client para XAI

const XAI_API = {
  baseURL: 'http://localhost:8000/api',
  
  // Obtener explicación actual
  async getExplicacion(ticker) {
    const url = `${this.baseURL}/activos/${ticker}/explicacion`;
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Error: ${response.status}`);
    return response.json();
  },
  
  // Obtener histórico
  async getHistorial(ticker, dias = 30) {
    const url = `${this.baseURL}/activos/${ticker}/historial-xai?dias=${dias}`;
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Error: ${response.status}`);
    return response.json();
  },
  
  // Guardar feedback
  async guardarFeedback(id, util, comentario = '') {
    const url = `${this.baseURL}/explicaciones/${id}/validar`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        util: util,
        comentario_usuario: comentario
      })
    });
    if (!response.ok) throw new Error(`Error: ${response.status}`);
    return response.json();
  },
  
  // Obtener estadísticas
  async getEstadisticas(ticker, dias = 30) {
    const url = `${this.baseURL}/estadisticas/xai?ticker=${ticker}&dias=${dias}`;
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Error: ${response.status}`);
    return response.json();
  },
  
  // Health check
  async healthCheck() {
    const url = `${this.baseURL}/health/xai`;
    const response = await fetch(url);
    return response.ok;
  }
};
```

### PASO 2: Crear `js/xai-ui.js` (150 líneas)

Maneja toda la lógica de UI:

```javascript
// js/xai-ui.js
// UI component para mostrar explicaciones

class XAIViewer {
  constructor(containerId = 'xai-container') {
    this.container = document.getElementById(containerId);
    this.currentExplicacionId = null;
    this.currentTicker = null;
  }
  
  // Cargar y mostrar explicación
  async mostrar(ticker) {
    try {
      this.currentTicker = ticker;
      console.log(`Cargando explicación para ${ticker}...`);
      
      const data = await XAI_API.getExplicacion(ticker);
      this.currentExplicacionId = data.id;
      
      // Renderizar template
      this.render(data);
      
    } catch (error) {
      console.error('Error:', error);
      this.mostrarError(`No se pudo cargar la explicación: ${error.message}`);
    }
  }
  
  render(data) {
    const html = `
      <!-- Señal y Confianza -->
      <div class="xai-signal-box">
        <h2 class="signal-${data.senal_prediccion.toLowerCase()}">
          ${data.senal_prediccion}
        </h2>
        <div class="confidence-bar">
          <div class="bar-fill" style="width: ${data.confianza_prediccion * 100}%"></div>
        </div>
        <p class="confidence-text">
          Confianza: ${(data.confianza_prediccion * 100).toFixed(1)}%
        </p>
      </div>
      
      <!-- SHAP Force Plot -->
      <div class="xai-shap-section">
        <h3>🔍 Explicación SHAP (Force Plot)</h3>
        <img class="shap-plot" 
             src="data:image/png;base64,${data.shap_grafico}" 
             alt="SHAP Force Plot" />
        <p class="info-text">
          El gráfico muestra cómo cada feature empuja la predicción 
          hacia ALCISTA (derecha) o BAJISTA (izquierda)
        </p>
      </div>
      
      <!-- Top 20 Features -->
      <div class="xai-features-section">
        <h3>⭐ Top 20 Features Importantes</h3>
        <div class="features-list">
          ${data.features_top20.map((f, idx) => `
            <div class="feature-item">
              <span class="rank">#${idx + 1}</span>
              <span class="name">${f.feature_name}</span>
              <div class="importance-bar">
                <div class="fill" style="width: ${f.importancia * 100}%"></div>
              </div>
              <span class="value">${(f.importancia * 100).toFixed(1)}%</span>
            </div>
          `).join('')}
        </div>
      </div>
      
      <!-- Feedback -->
      <div class="xai-feedback-section">
        <h3>💭 ¿Te fue útil esta explicación?</h3>
        <button class="btn-feedback yes" onclick="xaiViewer.feedback(true)">
          ✓ Sí, útil
        </button>
        <button class="btn-feedback no" onclick="xaiViewer.feedback(false)">
          ✗ No, poco útil
        </button>
        <p class="feedback-hint">Tu feedback ayuda a mejorar el modelo</p>
      </div>
    `;
    
    this.container.innerHTML = html;
  }
  
  // Guardar feedback
  async feedback(util) {
    try {
      await XAI_API.guardarFeedback(
        this.currentExplicacionId,
        util,
        prompt('(Opcional) Cuéntanos más...')
      );
      alert('✓ Gracias por tu feedback');
    } catch (error) {
      alert('Error guardando feedback: ' + error.message);
    }
  }
  
  // Cargar histórico
  async mostrarHistorial(ticker) {
    try {
      const data = await XAI_API.getHistorial(ticker);
      this.renderHistorial(data);
    } catch (error) {
      this.mostrarError(`Error cargando histórico: ${error.message}`);
    }
  }
  
  renderHistorial(data) {
    const html = `
      <div class="xai-history">
        <h3>📊 Histórico (últimos 30 días)</h3>
        <table>
          <tr>
            <th>Fecha</th>
            <th>Señal</th>
            <th>Confianza</th>
            <th>Correcta?</th>
          </tr>
          ${data.map(row => `
            <tr>
              <td>${new Date(row.fecha_prediccion).toLocaleDateString()}</td>
              <td>${row.senal_prediccion}</td>
              <td>${(row.confianza_prediccion * 100).toFixed(1)}%</td>
              <td>${row.prediccion_correcta === null ? '-' : (row.prediccion_correcta ? '✓' : '✗')}</td>
            </tr>
          `).join('')}
        </table>
      </div>
    `;
    
    const historyContainer = document.getElementById('xai-history');
    if (historyContainer) historyContainer.innerHTML = html;
  }
  
  mostrarError(mensaje) {
    this.container.innerHTML = `<div class="error">${mensaje}</div>`;
  }
}

// Instancia global
const xaiViewer = new XAIViewer();
```

### PASO 3: Crear `css/xai-styles.css` (200 líneas)

Estilos profesionales:

```css
/* css/xai-styles.css */

#xai-container {
  max-width: 1000px;
  margin: 20px auto;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* Signal Box */
.xai-signal-box {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 40px 30px;
  border-radius: 12px;
  text-align: center;
  margin-bottom: 30px;
  box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
}

.xai-signal-box h2 {
  margin: 0;
  font-size: 3em;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 2px;
}

.xai-signal-box h2.signal-alcista {
  color: #4caf50;
}

.xai-signal-box h2.signal-bajista {
  color: #f44336;
}

.xai-signal-box h2.signal-lateral {
  color: #ff9800;
}

/* Confidence Bar */
.confidence-bar {
  width: 100%;
  height: 24px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 12px;
  margin: 20px 0;
  overflow: hidden;
}

.confidence-bar .bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #4caf50, #45a049);
  transition: width 0.5s ease;
  border-radius: 12px;
}

.confidence-text {
  font-size: 1.3em;
  margin: 15px 0 0 0;
  font-weight: 600;
}

/* SHAP Section */
.xai-shap-section {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 25px;
  margin-bottom: 25px;
}

.xai-shap-section h3 {
  margin-top: 0;
  color: #333;
}

.shap-plot {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  display: block;
  margin: 15px 0;
}

.info-text {
  color: #666;
  font-size: 0.9em;
  font-style: italic;
  margin: 10px 0 0 0;
}

/* Features Section */
.xai-features-section {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 25px;
  margin-bottom: 25px;
}

.features-list {
  max-height: 400px;
  overflow-y: auto;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
  font-size: 0.95em;
}

.feature-item:last-child {
  border-bottom: none;
}

.feature-item .rank {
  min-width: 40px;
  font-weight: bold;
  color: #667eea;
}

.feature-item .name {
  min-width: 120px;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 0.85em;
}

.feature-item .importance-bar {
  flex: 1;
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.feature-item .importance-bar .fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
}

.feature-item .value {
  min-width: 60px;
  text-align: right;
  font-weight: bold;
  color: #333;
}

/* Feedback Section */
.xai-feedback-section {
  background: #e3f2fd;
  border-left: 4px solid #2196f3;
  padding: 25px;
  border-radius: 8px;
  text-align: center;
  margin-bottom: 25px;
}

.xai-feedback-section h3 {
  margin-top: 0;
  color: #1565c0;
}

.btn-feedback {
  margin: 10px 10px;
  padding: 12px 24px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: bold;
  font-size: 1em;
  transition: all 0.3s;
}

.btn-feedback.yes {
  background: #4caf50;
  color: white;
}

.btn-feedback.yes:hover {
  background: #45a049;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
}

.btn-feedback.no {
  background: #f44336;
  color: white;
}

.btn-feedback.no:hover {
  background: #da190b;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(244, 67, 54, 0.3);
}

.feedback-hint {
  color: #666;
  font-size: 0.85em;
  margin-top: 10px;
}

/* History Section */
.xai-history h3 {
  color: #333;
}

.xai-history table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 15px;
}

.xai-history th {
  background: #f5f5f5;
  padding: 12px;
  text-align: left;
  font-weight: bold;
  border-bottom: 2px solid #ddd;
}

.xai-history td {
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.xai-history tr:hover {
  background: #fafafa;
}

/* Error */
.error {
  background: #ffebee;
  border-left: 4px solid #f44336;
  color: #c62828;
  padding: 20px;
  border-radius: 4px;
  font-weight: 500;
}

/* Modal */
.xai-modal {
  display: none;
  position: fixed;
  z-index: 1000;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  animation: fadeIn 0.3s;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.xai-modal-content {
  background-color: #fefefe;
  margin: 5% auto;
  max-height: 90vh;
  overflow-y: auto;
  width: 95%;
  max-width: 1000px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.xai-modal-close {
  position: absolute;
  right: 20px;
  top: 20px;
  font-size: 28px;
  font-weight: bold;
  color: #aaa;
  cursor: pointer;
}

.xai-modal-close:hover {
  color: #000;
}
```

### PASO 4: Modificar `analysis.html`

Agregar esto donde muestres la predicción:

```html
<!-- Después de mostrar la predicción -->
<div class="prediction-result">
  <h2 id="signal-display">ALCISTA</h2>
  <div class="confidence">
    <span>Confianza:</span>
    <div class="bar"><div id="conf-bar"></div></div>
    <span id="conf-percent">75.3%</span>
  </div>
  
  <!-- ✨ NUEVO: Botón XAI -->
  <button class="btn-xai" onclick="mostrarXAI(currentTicker)">
    🔍 Ver Explicación (¿Por qué?)
  </button>
</div>

<!-- Modal para XAI -->
<div id="xai-modal" class="xai-modal">
  <div class="xai-modal-content">
    <span class="xai-modal-close" onclick="cerrarXAI()">&times;</span>
    <div id="xai-container">
      <!-- Se llena dinámicamente -->
    </div>
  </div>
</div>

<script src="js/xai-api.js"></script>
<script src="js/xai-ui.js"></script>
<script>
  function mostrarXAI(ticker) {
    document.getElementById('xai-modal').style.display = 'block';
    xaiViewer.mostrar(ticker);
  }
  
  function cerrarXAI() {
    document.getElementById('xai-modal').style.display = 'none';
  }
  
  // Cerrar modal haciendo click fuera
  window.onclick = function(event) {
    const modal = document.getElementById('xai-modal');
    if (event.target == modal) {
      modal.style.display = 'none';
    }
  }
</script>
```

### PASO 5: Crear `xai-dashboard.html` (Opcional pero recomendado)

```html
<!DOCTYPE html>
<html>
<head>
  <title>🤖 Dashboard XAI</title>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="css/main.css">
  <link rel="stylesheet" href="css/xai-styles.css">
  <style>
    .xai-dashboard {
      padding: 20px;
      max-width: 1200px;
      margin: 0 auto;
    }
    
    .ticker-selector {
      margin-bottom: 30px;
      padding: 20px;
      background: #f5f5f5;
      border-radius: 8px;
      display: flex;
      gap: 15px;
      align-items: center;
    }
    
    .ticker-selector label {
      font-weight: bold;
      color: #333;
    }
    
    .ticker-selector select {
      flex: 1;
      max-width: 300px;
      padding: 10px;
      border: 1px solid #ddd;
      border-radius: 4px;
    }
    
    .ticker-selector button {
      padding: 10px 20px;
      background: #667eea;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    }
  </style>
</head>
<body>
  <div class="xai-dashboard">
    <h1>🤖 Dashboard de Explicabilidad (XAI)</h1>
    
    <div class="ticker-selector">
      <label>Selecciona un ticker:</label>
      <select id="ticker-select" onchange="actualizarExplicacion()">
        <option value="">Cargando tickers...</option>
      </select>
      <button onclick="cargarTickers()">🔄 Recargar</button>
    </div>
    
    <div id="xai-container">
      <p>Selecciona un ticker para ver la explicación</p>
    </div>
    
    <div id="xai-history" style="margin-top: 30px;">
      <!-- Se carga dinámicamente -->
    </div>
  </div>

  <script src="js/xai-api.js"></script>
  <script src="js/xai-ui.js"></script>
  <script>
    async function cargarTickers() {
      // Aquí carga tickers desde el backend u obtén lista hardcodeada
      const tickers = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA', 'META', 'NFLX', 'AMZN', 'INTC', 'KO', 'VXX', 'BTC-USD'];
      const select = document.getElementById('ticker-select');
      select.innerHTML = '';
      
      tickers.forEach(ticker => {
        const option = document.createElement('option');
        option.value = ticker;
        option.textContent = ticker;
        select.appendChild(option);
      });
    }

    async function actualizarExplicacion() {
      const ticker = document.getElementById('ticker-select').value;
      if (ticker) {
        await xaiViewer.mostrar(ticker);
        await xaiViewer.mostrarHistorial(ticker);
      }
    }

    window.onload = cargarTickers;
  </script>
</body>
</html>
```

---

## ✅ Checklist de Implementación

### Parte 1: Backend Setup (5 min)
- [ ] Verificar que backend está corriendo: `python -m backend.models.service` (o tu comando)
- [ ] Verificar endpoint: `curl http://localhost:8000/api/health/xai`
- [ ] Response debe ser: `{"status": "ok", ...}`

### Parte 2: Crear Archivos (30 min)
- [ ] Crear `frontend/js/xai-api.js`
- [ ] Crear `frontend/js/xai-ui.js`
- [ ] Crear `frontend/css/xai-styles.css`
- [ ] Crear `frontend/xai-dashboard.html` (opcional pero recomendado)

### Parte 3: Integrar en Análisis (15 min)
- [ ] Modificar `frontend/analysis.html`:
  - [ ] Agregar botón "Ver Explicación"
  - [ ] Agregar modal
  - [ ] Incluir scripts XAI
- [ ] Probar: Hacer predicción y clickear botón

### Parte 4: Testing (20 min)
- [ ] [✓] GET `/api/activos/AAPL/explicacion`
- [ ] [✓] GET `/api/activos/AAPL/historial-xai`
- [ ] [✓] POST `/api/explicaciones/123/validar`
- [ ] [✓] Feedback guardado en BD

### Parte 5: Pulir (15 min)
- [ ] Mobile responsive (CSS flex/grid)
- [ ] Manejo de errores de red
- [ ] Loading states (spinners)
- [ ] Animaciones suaves

---

## 🐛 Troubleshooting

### Problema: CORS Error
```
Access to XMLHttpRequest blocked by CORS policy
```
**Solución**: Backend ya tiene CORS habilitado. Si falla:
- Verificar que backend corre en `http://localhost:8000`
- En `analysis.html`, cambiar URL a IP correcta si es necesario

### Problema: Imagen SHAP no se muestra
```
Error al cargar imagen Base64
```
**Solución**: 
- Verificar que `shap_grafico` en API no es null
- Comprobar que comienza con `/9j/` (JPEG) o `iVBORw0KGgo` (PNG)

### Problema: Feedback no guarda
```
POST /api/explicaciones/123/validar → 404
```
**Solución**:
- Verificar que `id` es correcto (está en respuesta de `/explicacion`)
- Comprobar método POST (no GET)

---

## 🎨 Ejemplos de Personalización

### Cambiar Colores
En `css/xai-styles.css`, modificar:
```css
/* De: */
.xai-signal-box {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* A: */
.xai-signal-box {
  background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
}
```

### Agregar Gráfico Adicional
El endpoint devuelve `shap_valores` (array de 88 features). Podrías graficar con Chart.js:
```javascript
// Crear gráfico de contribución
const ctx = document.getElementById('contribution-chart').getContext('2d');
new Chart(ctx, {
  type: 'bar',
  data: {
    labels: data.shap_valores.map(f => f.feature_name),
    datasets: [{
      label: 'SHAP Value',
      data: data.shap_valores.map(f => f.shap_value),
      backgroundColor: '#667eea'
    }]
  }
});
```

---

## 📞 Información de Contacto

**Backend (Ya Completo):**
- Archivos: `backend/routes/xai_routes.py`, `backend/daos/explicacion_xai_dao.py`
- BD: Supabase tabla `xai_explicaciones`
- Modelos: 12 tickers con explicaciones listas

**Frontend (Tu Tarea):**
- Crear componentes UI
- Integrar API calls
- Mostrar resultados

---

## 📚 Referencias Técnicas

**SHAP:**
- Documentación: https://shap.readthedocs.io/
- Force plots: Muestran cómo features empujan predicción

**API Testing:**
```bash
# Test todos los endpoints
curl http://localhost:8000/api/health/xai
curl http://localhost:8000/api/activos/AAPL/explicacion
curl "http://localhost:8000/api/activos/AAPL/historial-xai?dias=30"
```

---

## 🎯 Versión MVP (2 horas)

Para entregar rápido, hacer solo:
1. ✅ `js/xai-api.js` (wrapper de API)
2. ✅ Botón en `analysis.html`
3. ✅ Modal simple mostrando:
   - Señal + confianza
   - SHAP Force Plot
   - Top 5 features (no 20)
   - Botón de feedback

Luego extender con:
- [ ] Histórico completo
- [ ] Dashboard dedicado
- [ ] Más visualizaciones
- [ ] Mobile responsive

---

## ✨ Success Criteria

Cuando termines, deberías poder:

1. ✓ Ver predicción en analysis.html
2. ✓ Clickear "Ver Explicación"
3. ✓ Modal aparece con SHAP plot
4. ✓ Ver top 20 features
5. ✓ Hacer click en "Sí, útil" → guardado en BD
6. ✓ Histórico muestra últimas 30 días
7. ✓ Zero console errors

---

**¿Preguntas?** Revisa los endpoints en `backend/routes/xai_routes.py`
**¿Estancado?** Verifica que backend responde con `curl http://localhost:8000/api/health/xai`
