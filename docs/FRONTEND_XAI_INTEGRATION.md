<!-- Frontend XAI Integration Guide -->
<!-- Pasos para mostrar explicaciones SHAP en el frontend -->

# 🎯 Integración XAI con Frontend

## Estado Actual
✅ Backend XAI completamente implementado  
✅ 16 explicaciones SHAP generadas y en BD  
✅ API REST con 7 endpoints listos  
✅ Requirements.txt actualizado con SHAP  

---

## 📋 Siguientes Pasos (Para Frontend)

### **FASE 1: Endpoints API (5-7 min)**
Ya están implementados en `backend/routes/xai_routes.py`:

```
GET  /api/activos/{ticker}/explicacion           → Explicación más reciente
GET  /api/activos/{ticker}/historial-xai?días=30 → Histórico de explicaciones
GET  /api/explicaciones/{id}                      → Detalles completos de 1 explicación
POST /api/explicaciones/{id}/validar              → Guardar feedback del usuario
GET  /api/estadisticas/xai?ticker=AAPL            → Métricas agregadas por ticker
GET  /api/features/top-global                     → Features más importantes globales
GET  /api/health/xai                              → Health check
```

**Acción**: Verificar que estos endpoints están disponibles ejecutando:
```bash
curl http://localhost:8000/api/health/xai
```

---

### **FASE 2: Componentes de Visualización (15-20 min)**

#### **2.1 Nueva página: `explicacion.html`**
Crear vista para mostrar explicación de un ticker:

```html
<!-- frontend/explicacion.html -->
<div id="xai-container">
  <!-- Señal y Confianza -->
  <div class="signal-box">
    <h2 id="senal-prediccion">ALCISTA</h2>
    <div class="confidence-bar">
      <div id="confidence-fill" style="width: 75%"></div>
    </div>
    <p id="confidence-text">Confianza: 75.3%</p>
  </div>

  <!-- SHAP Force Plot (Base64) -->
  <div class="shap-section">
    <h3>🔍 Explicación SHAP (Force Plot)</h3>
    <img id="shap-plot" src="" alt="SHAP Force Plot" />
  </div>

  <!-- Top 20 Features -->
  <div class="features-section">
    <h3>⭐ Top 20 Features Importantes</h3>
    <div id="features-list">
      <!-- Generado dinámicamente -->
    </div>
  </div>

  <!-- Feedback -->
  <div class="feedback-section">
    <h3>💭 ¿Te fue útil esta explicación?</h3>
    <button onclick="guardarFeedback(true)">✓ Sí, útil</button>
    <button onclick="guardarFeedback(false)">✗ No, poco útil</button>
  </div>

  <!-- Histórico -->
  <div class="history-section">
    <h3>📊 Histórico de Explicaciones (últimos 30 días)</h3>
    <table id="history-table">
      <!-- Fecha | Señal | Confianza | Correcta? -->
    </table>
  </div>
</div>
```

#### **2.2 Script JavaScript: `js/xai-viewer.js`** (nuevo archivo)

```javascript
// js/xai-viewer.js
// Maneja las explicaciones XAI

async function cargarExplicacion(ticker) {
    try {
        const response = await fetch(`/api/activos/${ticker}/explicacion`);
        const data = await response.json();
        
        if (!data) {
            console.log("No hay explicación para " + ticker);
            return;
        }
        
        // 1️⃣ Mostrar señal y confianza
        document.getElementById('senal-prediccion').textContent = data.senal_prediccion;
        const confidence = data.confianza_prediccion;
        document.getElementById('confidence-fill').style.width = (confidence * 100) + '%';
        document.getElementById('confidence-text').textContent = 
            `Confianza: ${(confidence * 100).toFixed(1)}%`;
        
        // 2️⃣ Mostrar SHAP Force Plot (es base64 PNG)
        document.getElementById('shap-plot').src = 
            'data:image/png;base64,' + data.shap_grafico;
        
        // 3️⃣ Mostrar Top 20 Features
        mostrarFeatures(data.features_top20);
        
        // 4️⃣ Guardar ID para feedback posterior
        window.currentExplicacionId = data.id;
        
    } catch (error) {
        console.error("Error cargando explicación:", error);
    }
}

function mostrarFeatures(features) {
    const container = document.getElementById('features-list');
    container.innerHTML = '';
    
    features.slice(0, 20).forEach((feature, idx) => {
        const importance = feature.importancia || 0;
        const html = `
            <div class="feature-item">
                <span class="rank">#${idx + 1}</span>
                <span class="name">${feature.feature_name || 'Feature_' + idx}</span>
                <div class="importance-bar">
                    <div class="fill" style="width: ${importance * 100}%"></div>
                </div>
                <span class="value">${(importance * 100).toFixed(1)}%</span>
            </div>
        `;
        container.innerHTML += html;
    });
}

async function guardarFeedback(esUtil) {
    const id = window.currentExplicacionId;
    const response = await fetch(`/api/explicaciones/${id}/validar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            util: esUtil,
            comentario_usuario: prompt('(Opcional) Cuéntanos más...')
        })
    });
    
    if (response.ok) {
        alert('✓ Gracias por tu feedback');
    }
}

async function cargarHistorial(ticker, dias = 30) {
    const response = await fetch(`/api/activos/${ticker}/historial-xai?dias=${dias}`);
    const data = await response.json();
    
    const table = document.getElementById('history-table');
    table.innerHTML = '<tr><th>Fecha</th><th>Señal</th><th>Confianza</th><th>Correcta?</th></tr>';
    
    data.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${new Date(row.fecha_prediccion).toLocaleDateString()}</td>
            <td>${row.senal_prediccion}</td>
            <td>${(row.confianza_prediccion * 100).toFixed(1)}%</td>
            <td>${row.prediccion_correcta === null ? '-' : (row.prediccion_correcta ? '✓' : '✗')}</td>
        `;
        table.appendChild(tr);
    });
}
```

#### **2.3 Estilos CSS: `css/xai.css`** (nuevo archivo)

```css
/* css/xai.css - Estilos para visualización XAI */

#xai-container {
    padding: 20px;
    max-width: 1200px;
    margin: 0 auto;
}

.signal-box {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 30px;
    border-radius: 12px;
    text-align: center;
    margin-bottom: 30px;
}

.signal-box h2 {
    font-size: 2.5em;
    margin: 0;
    font-weight: bold;
}

.confidence-bar {
    background: rgba(255, 255, 255, 0.3);
    height: 20px;
    border-radius: 10px;
    margin: 15px 0;
    overflow: hidden;
}

.confidence-bar .fill {
    background: linear-gradient(90deg, #4caf50, #45a049);
    height: 100%;
    transition: width 0.3s ease;
}

.shap-section {
    background: #f5f5f5;
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 20px;
}

.shap-section img {
    max-width: 100%;
    height: auto;
    border-radius: 6px;
}

.features-section {
    background: white;
    border: 1px solid #e0e0e0;
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 20px;
}

.feature-item {
    display: flex;
    align-items: center;
    gap: 15px;
    padding: 12px 0;
    border-bottom: 1px solid #f0f0f0;
}

.feature-item .rank {
    font-weight: bold;
    color: #667eea;
    min-width: 40px;
}

.feature-item .name {
    min-width: 150px;
    font-family: monospace;
}

.feature-item .importance-bar {
    flex: 1;
    height: 8px;
    background: #e0e0e0;
    border-radius: 4px;
    overflow: hidden;
}

.feature-item .importance-bar .fill {
    background: linear-gradient(90deg, #667eea, #764ba2);
    height: 100%;
}

.feature-item .value {
    min-width: 60px;
    text-align: right;
    font-weight: bold;
}

.feedback-section {
    background: #e3f2fd;
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 20px;
    text-align: center;
}

.feedback-section button {
    margin: 0 10px;
    padding: 10px 20px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-weight: bold;
}

.feedback-section button:first-child {
    background: #4caf50;
    color: white;
}

.feedback-section button:last-child {
    background: #f44336;
    color: white;
}

#history-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
}

#history-table th, #history-table td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #e0e0e0;
}

#history-table th {
    background: #f5f5f5;
    font-weight: bold;
}

#history-table tr:hover {
    background: #f9f9f9;
}
```

---

### **FASE 3: Integración en Página de Análisis (10-15 min)**

#### **3.1 Modificar `frontend/analysis.html`**
Agregar botón para ver explicación:

```html
<!-- En la sección de resultados de predicción -->
<div class="prediction-result">
    <h2 id="signal">ALCISTA</h2>
    <p id="confidence">Confianza: 75.3%</p>
    
    <!-- ✅ NUEVO: Botón para XAI -->
    <button class="btn-xai" onclick="mostrarExplicacion(currentTicker)">
        🔍 Ver Explicación (XAI)
    </button>
</div>

<!-- Modal para mostrar explicación -->
<div id="xai-modal" class="modal">
    <div class="modal-content">
        <span class="close" onclick="cerrarExplicacion()">&times;</span>
        <div id="xai-modal-body">
            <!-- Se carga dinámicamente -->
        </div>
    </div>
</div>
```

#### **3.2 Script JavaScript en `analysis.html`**

```javascript
// Agregar a js/main.js o crear js/analysis.js

let currentTicker = 'AAPL'; // Variable global del ticker seleccionado

function mostrarExplicacion(ticker) {
    currentTicker = ticker;
    document.getElementById('xai-modal').style.display = 'block';
    cargarExplicacion(ticker);  // Función del archivo xai-viewer.js
}

function cerrarExplicacion() {
    document.getElementById('xai-modal').style.display = 'none';
}

// Cerrar modal al hacer click fuera
window.onclick = function(event) {
    const modal = document.getElementById('xai-modal');
    if (event.target == modal) {
        modal.style.display = 'none';
    }
}
```

---

### **FASE 4: Página Dedicada de Explicaciones (20-30 min)**

#### **4.1 Nueva página: `frontend/xai-dashboard.html`**

```html
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard XAI - Explicaciones</title>
    <link rel="stylesheet" href="css/xai.css">
    <link rel="stylesheet" href="css/main.css">
</head>
<body>
    <div class="navbar">
        <h1>🤖 Dashboard XAI - Interpretabilidad</h1>
    </div>

    <div class="container">
        <!-- Selector de Ticker -->
        <div class="control-section">
            <label>Selecciona un ticker:</label>
            <select id="ticker-select" onchange="actualizarExplicacion()">
                <option value="">-- Cargando --</option>
            </select>
            <button onclick="generarNuevaExplicacion()">🔄 Generar Nueva</button>
        </div>

        <!-- Explicación Actual -->
        <div id="xai-container">
            <!-- Se carga dinámicamente -->
        </div>
    </div>

    <script src="js/main.js"></script>
    <script src="js/xai-viewer.js"></script>
    <script>
        // Cargar lista de tickers
        async function cargarTickers() {
            const response = await fetch('/api/activos');
            const data = await response.json();
            
            const select = document.getElementById('ticker-select');
            select.innerHTML = '';
            
            data.forEach(activo => {
                const option = document.createElement('option');
                option.value = activo.ticker;
                option.textContent = activo.ticker + ' - ' + activo.nombre_completo;
                select.appendChild(option);
            });
        }

        async function actualizarExplicacion() {
            const ticker = document.getElementById('ticker-select').value;
            if (ticker) {
                await cargarExplicacion(ticker);
                await cargarHistorial(ticker);
            }
        }

        async function generarNuevaExplicacion() {
            const ticker = document.getElementById('ticker-select').value;
            if (!ticker) {
                alert('Por favor selecciona un ticker');
                return;
            }
            
            alert('Se ejecutará el script de generación...');
            // En real, esto iría a un endpoint POST para re-generar
        }

        // Inicializar
        window.onload = cargarTickers;
    </script>
</body>
</html>
```

---

### **FASE 5: Actualización de Navegación (5 min)**

#### **5.1 Modificar `index.html`** (menú principal)

```html
<!-- Agregar en la barra de navegación -->
<a href="xai-dashboard.html">🔍 XAI Dashboard</a>
```

---

## 🛠️ Checklist de Implementación

### Parte 1: Setup (5 min)
- [ ] ✅ SHAP agregado a requirements.txt
- [ ] Ejecutar: `pip install -r requirements.txt`
- [ ] Verificar endpoints: `curl http://localhost:8000/api/health/xai`

### Parte 2: Archivos (25 min)
- [ ] Crear `frontend/explicacion.html` (o integrar en analysis.html)
- [ ] Crear `frontend/js/xai-viewer.js`
- [ ] Crear `frontend/css/xai.css`
- [ ] Crear `frontend/xai-dashboard.html`
- [ ] Actualizar `index.html` con enlace a XAI

### Parte 3: Testing (10 min)
- [ ] Abrir `xai-dashboard.html` en navegador
- [ ] Seleccionar un ticker (ej: AAPL)
- [ ] Verificar que se carga la explicación
- [ ] Probar feedback (click en "Sí, útil" / "No, útil")
- [ ] Verificar que aparece en historial

### Parte 4: Pulido (15 min)
- [ ] Mejorar estilos CSS
- [ ] Agregar animaciones/transiciones
- [ ] Testing en mobile (responsive)
- [ ] Manejo de errores

---

## 📊 Expected Output

Al completar, los usuarios verán:

1. **Botón "Ver Explicación"** en página de análisis
2. **Modal con SHAP Force Plot** (visualización interactiva)
3. **Top 20 Features** con barras de importancia
4. **Métrica de Confianza** visual
5. **Feedback del usuario** ("¿te fue útil?")
6. **Histórico** de últimas 30 días
7. **Dashboard dedicado** para explorar explicaciones por ticker

---

## 📝 Notas Importantes

### Backend Endpoints Disponibles:
```
GET  /api/activos/{ticker}/explicacion
GET  /api/activos/{ticker}/historial-xai?dias=30
POST /api/explicaciones/{id}/validar  ← Feedback del usuario
```

### Datos que retorna cada endpoint:
```json
{
  "id": 123,
  "ticker": "AAPL",
  "senal_prediccion": "ALCISTA",
  "confianza_prediccion": 0.753,
  "shap_grafico": "iVBORw0KGgoAAAANS...",  // Base64 PNG
  "features_top20": [
    {"feature_name": "Feature_0", "importancia": 0.33},
    {"feature_name": "Feature_28", "importancia": 0.20}
  ],
  "fecha_prediccion": "2026-04-12T11:26:00Z"
}
```

### BD Schema:
- Tabla `xai_explicaciones`: 16 registros actuales
- Tabla `xai_validacion`: Para guardar feedback

---

## 🎯 Próximos Pasos Inmediatos

1. **Ahora**: Implementar FASE 2 (componentes visualización)
2. **Después**: FASE 3 (integración en analysis.html)
3. **Luego**: FASE 4 (dashboard dedicado)
4. **Final**: FASE 5 (menu de navegación)

**Estimación total**: 1-1.5 horas para versión MVP completa

¿Por dónde quieres empezar?
