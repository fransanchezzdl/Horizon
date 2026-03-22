// ============================================================
// INICIALIZACIÓN Y CONFIGURACIÓN
// ============================================================

const API_BASE = window.API_BASE;
let currentPortfolioId = null;
let currentPortfolios = [];

// Cargar estado y renderizar al abrir la página
async function initPortfolioPage() {
    // VALIDAR AUTENTICACIÓN CENTRALIZADA
    const result = await window.validateAuthToken();
    
    if (!result.valid) {
        window.clearAuthSession();
        window.location.replace('login.html');
        return;
    }
    
    window.setCurrentUserData(result.user);
    await loadPortfolios();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPortfolioPage, { once: true });
} else {
    initPortfolioPage();
}

// ============================================================
// CARGAR PORTFOLIOS Y ACTIVOS
// ============================================================

async function loadPortfolios() {
    try {
        const response = await window.fetchWithAuth(`${API_BASE}/portfolios`);

        if (!response.ok) {
            console.error('Error cargando portfolios:', response.status);
            showAlert('Error al cargar portfolios', 'error');
            return;
        }

        currentPortfolios = await response.json();
        console.log(`📊 Portfolios cargados: ${currentPortfolios.length}`, currentPortfolios);
        
        if (currentPortfolios.length > 0) {
            // Mostrar selector de portfolios
            renderPortfolioSelector();
            
            // Cargar el primer portfolio por defecto
            currentPortfolioId = currentPortfolios[0].id_portfolio;
            await loadPortfolioDetails(currentPortfolioId);
        } else {
            // Si no hay portfolios, mostrar mensaje vacío
            renderEmptyState();
        }
    } catch (error) {
        console.error('Error:', error);
        showAlert('Error de conexión', 'error');
    }
}

async function loadPortfolioDetails(portfolioId) {
    try {
        console.log(`🔐 Cargando portfolio ${portfolioId}`);
        
        const response = await window.fetchWithAuth(`${API_BASE}/portfolios/${portfolioId}`);

        console.log(`   Response status: ${response.status}`);

        if (!response.ok) {
            console.error('❌ Error cargando detalles:', response.status);
            const errorData = await response.json().catch(() => ({}));
            console.error('   Error detail:', errorData);
            showAlert(`Error cargando portfolio: ${response.status}`, 'error');
            return;
        }

        const portfolio = await response.json();
        console.log(`✅ Portfolio cargado:`, portfolio);
        renderPortfolioData(portfolio);
        renderAssetsTable(portfolio.acciones || []);
    } catch (error) {
        console.error('❌ Error:', error);
        showAlert('Error de conexión', 'error');
    }
}

// ============================================================
// RENDERIZAR DATOS EN LA UI
// ============================================================

function renderPortfolioSelector() {
    /**
     * Rellena el selector de portfolios con las opciones disponibles
     * Usa el HTML del archivo portfolio.html (no lo genera)
     */
    const selectorContainer = document.getElementById('portfolioSelectorContainer');
    const portfolioSelector = document.getElementById('portfolioSelector');
    const riskBadge = document.getElementById('portfolioRiskBadge');
    
    if (!selectorContainer || !portfolioSelector) {
        console.warn('⚠️ Elementos del selector no encontrados en HTML');
        return;
    }
    
    // Mostrar/ocultar la sección basada en si hay portfolios
    if (currentPortfolios.length === 0) {
        selectorContainer.style.display = 'none';
        return;
    }
    
    selectorContainer.style.display = 'flex';
    
    // Limpiar opciones previas
    portfolioSelector.innerHTML = '';
    
    // Agregar opciones con datos de portfolios
    currentPortfolios.forEach(portfolio => {
        const option = document.createElement('option');
        option.value = portfolio.id_portfolio;
        option.textContent = portfolio.nombre_portfolio;
        
        if (portfolio.id_portfolio === currentPortfolioId) {
            option.selected = true;
            // Actualizar badge de riesgo
            const riskLevel = portfolio.riesgo < 0.35 ? 'Agresivo' : 
                              portfolio.riesgo < 0.65 ? 'Moderado' : 'Conservador';
            riskBadge.textContent = `${riskLevel} (${(portfolio.riesgo * 100).toFixed(0)}%)`;
        }
        
        portfolioSelector.appendChild(option);
    });
    
    console.log(`📊 Selector rellenado con ${currentPortfolios.length} portfolio(s)`);
    
    // Event listener para cambiar portfolio (agregar solo si no existe)
    if (!portfolioSelector.hasListener) {
        portfolioSelector.addEventListener('change', async (e) => {
            const portfolioId = parseInt(e.target.value);
            console.log(`🔀 Cambiando a portfolio ${portfolioId}`);
            currentPortfolioId = portfolioId;
            
            // Actualizar badge de riesgo
            const portfolio = currentPortfolios.find(p => p.id_portfolio === portfolioId);
            if (portfolio) {
                const riskLevel = portfolio.riesgo < 0.35 ? 'Agresivo' : 
                                  portfolio.riesgo < 0.65 ? 'Moderado' : 'Conservador';
                riskBadge.textContent = `${riskLevel} (${(portfolio.riesgo * 100).toFixed(0)}%)`;
            }
            
            await loadPortfolioDetails(portfolioId);
        });
        portfolioSelector.hasListener = true;
    }
}

function renderPortfolioData(portfolio) {
    // Actualizar nombre del portfolio
    const headerTitle = document.querySelector('.header-titles h1');
    if (headerTitle) {
        headerTitle.innerHTML = `
            <div>
                <div>${portfolio.nombre_portfolio}</div>
                <small style="font-size: 12px; color: #999; margin-top: 3px; display: block;">
                    ${portfolio.descripcion || 'Sin descripción'}
                </small>
            </div>
        `;
    }

    // Actualizar balance
    const balanceAmount = document.querySelector('.balance-amount');
    if (balanceAmount) {
        const activeCount = (portfolio.acciones && portfolio.acciones.length) || 0;
        balanceAmount.textContent = `${activeCount} activos`;
    }
    
    // Actualizar badge de riesgo
    const badge = document.querySelector('#portfolioCountBadge');
    if (badge) {
        const riskLevel = portfolio.riesgo < 0.35 ? 'Agresivo' : 
                          portfolio.riesgo < 0.65 ? 'Moderado' : 'Conservador';
        badge.textContent = `${riskLevel} (${(portfolio.riesgo * 100).toFixed(0)}%)`;
    }
}

function createNewPortfolio() {
    showCreatePortfolioModal();
}

function renderAssetsTable(acciones) {
    const tbody = document.querySelector('.custom-table tbody');
    if (!tbody) return;

    // Limpiar tabla
    tbody.innerHTML = '';

    if (acciones.length === 0) {
        // Mostrar mensaje si no hay activos
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 40px; color: #999;">
                    <p>No hay activos en este portfolio. Haz clic en "Añadir Inversión" para comenzar.</p>
                </td>
            </tr>
        `;
        return;
    }

    acciones.forEach(activo => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <div class="asset-item">
                    <div class="asset-icon">
                        <svg viewBox="0 0 24 24" fill="#000" width="24" height="24">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/>
                        </svg>
                    </div>
                    <div class="asset-info">
                        <span class="asset-symbol">${activo.ticker}</span>
                        <span class="asset-name">${activo.ticker}</span>
                    </div>
                </div>
            </td>
            <td>
                <div class="price-cell">
                    <span class="price-val">$${(Math.random() * 300 + 50).toFixed(2)}</span>
                    <span class="price-change text-success">+${(Math.random() * 3).toFixed(1)}%</span>
                </div>
            </td>
            <td><span class="badge badge-green">Estable</span></td>
            <td class="text-muted">Activo</td>
            <td><span class="badge badge-blue-soft">Monitoreo</span></td>
            <td class="text-right">
                <button class="btn-icon" data-stock-id="${activo.id_posicion}" onclick="deleteAsset(${activo.id_posicion})">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <circle cx="12" cy="5" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="12" cy="19" r="2"/>
                    </svg>
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function renderEmptyState() {
    const pageContent = document.querySelector('#dashboard-contenido');
    if (pageContent) {
        pageContent.innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 60vh; color: #999; text-align: center;">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" style="margin-bottom: 20px; color: #ccc;">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/>
                    <line x1="12" y1="16" x2="12" y2="12"></line>
                    <line x1="12" y1="8" x2="12.01" y2="8"></line>
                </svg>
                <h2 style="color: #333; font-size: 24px; margin-bottom: 10px;">No tienes portfolios aún</h2>
                <p style="margin-bottom: 30px; color: #666; font-size: 15px;">Crea tu primer portfolio para comenzar a invertir y gestionar tus activos</p>
                <button class="btn-primary" onclick="showCreatePortfolioModal()" style="padding: 12px 30px; font-size: 15px;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="12" y1="5" x2="12" y2="19"></line>
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                    </svg>
                    Crear Mi Primer Portfolio
                </button>
            </div>
        `;
    }
}

// ============================================================
// EVENTOS Y ACCIONES
// ============================================================

async function deleteAsset(stockId) {
    if (!confirm('¿Estás seguro de que deseas eliminar este activo del portfolio?')) {
        return;
    }

    try {
        const response = await window.fetchWithAuth(`${API_BASE}/portfolios/${currentPortfolioId}/activos/${stockId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showAlert('Activo eliminado correctamente', 'success');
            await loadPortfolioDetails(currentPortfolioId);
        } else {
            showAlert('Error al eliminar el activo', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showAlert('Error de conexión', 'error');
    }
}

// ============================================================
// MODALES Y FORMULARIOS
// ============================================================

function showAddAssetModal() {
    /**
     * Muestra el modal de agregar activos (ya existe en portfolio.html)
     * Configura la búsqueda dinámica de activos
     */
    const modal = document.getElementById('assetModal');
    const searchInput = document.getElementById('assetSearch');
    const suggestions = document.getElementById('assetSuggestions');
    const errorDiv = document.getElementById('tickerError');
    const selectedInfo = document.getElementById('selectedAssetInfo');
    const addBtn = document.getElementById('addAssetBtn');
    let selectedAsset = null;
    let debounceTimer = null;
    let activeIndex = -1;
    
    // Mostrar modal
    modal.style.display = 'flex';
    searchInput.value = '';
    suggestions.hidden = true;
    errorDiv.style.display = 'none';
    selectedInfo.style.display = 'none';
    addBtn.disabled = true;
    searchInput.focus();
    
    // Buscar activos en la API
    async function buscarActivos(query) {
        try {
            const resp = await window.fetchWithAuth(`${API_BASE}/activos?q=${encodeURIComponent(query)}`);
            if (!resp.ok) return [];
            return await resp.json();
        } catch (err) {
            console.error('Error buscando activos:', err);
            return [];
        }
    }
    
    // Renderizar sugerencias
    function renderSuggestions(list) {
        suggestions.innerHTML = '';
        if (list.length === 0) { 
            suggestions.hidden = true; 
            return; 
        }
        suggestions.hidden = false;
        list.forEach((activo) => {
            const li = document.createElement('li');
            li.className = 'suggestion-item';
            li.tabIndex = 0;
            li.innerHTML = `<span><span class="suggestion-symbol">${activo.ticker}</span> <span class="suggestion-name">${activo.nombre_completo}</span></span>`;
            li.addEventListener('click', () => {
                seleccionarActivo(activo);
            });
            suggestions.appendChild(li);
        });
    }
    
    // Seleccionar un activo
    function seleccionarActivo(activo) {
        selectedAsset = activo;
        searchInput.value = activo.ticker;
        suggestions.hidden = true;
        
        // Mostrar información del activo seleccionado
        document.getElementById('selectedAssetName').textContent = activo.nombre_completo;
        document.getElementById('selectedAssetTicker').textContent = activo.ticker;
        selectedInfo.style.display = 'block';
        
        // Habilitar botón de añadir
        addBtn.disabled = false;
        errorDiv.style.display = 'none';
        
        console.log('[OK] Activo seleccionado:', activo);
    }
    
    // Evento de búsqueda con debounce
    searchInput.addEventListener('input', () => {
        const q = searchInput.value.trim();
        if (q.length === 0) { 
            suggestions.hidden = true; 
            selectedAsset = null;
            addBtn.disabled = true;
            selectedInfo.style.display = 'none';
            return; 
        }
        
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(async () => {
            const results = await buscarActivos(q);
            renderSuggestions(results);
            activeIndex = -1;
        }, 250);
    });
    
    // Navegación con teclado
    searchInput.addEventListener('keydown', (e) => {
        const items = suggestions.querySelectorAll('.suggestion-item');
        if (e.key === 'ArrowDown') { 
            e.preventDefault(); 
            activeIndex = Math.min(activeIndex + 1, items.length - 1); 
        }
        else if (e.key === 'ArrowUp') { 
            e.preventDefault(); 
            activeIndex = Math.max(activeIndex - 1, 0); 
        }
        else if (e.key === 'Enter') {
            e.preventDefault();
            if (activeIndex >= 0 && items[activeIndex]) { 
                items[activeIndex].click(); 
            }
            else if (selectedAsset) {
                addAssetToPortfolio();
            }
        }
        items.forEach((it, idx) => it.classList.toggle('active', idx === activeIndex));
    });
    
    // Cerrar sugerencias al hacer click fuera
    document.addEventListener('click', (ev) => {
        if (!ev.target.closest('.input-wrap')) suggestions.hidden = true;
    });
    
    // Escape para cerrar modal
    const escapeHandler = (e) => {
        if (e.key === 'Escape') {
            closeAddAssetModal();
            document.removeEventListener('keydown', escapeHandler);
        }
    };
    document.addEventListener('keydown', escapeHandler);
}

function closeAddAssetModal() {
    const modal = document.getElementById('assetModal');
    const searchInput = document.getElementById('assetSearch');
    const suggestions = document.getElementById('assetSuggestions');
    
    modal.style.display = 'none';
    suggestions.hidden = true;
    searchInput.value = '';
    
    // Limpiar listeners escondiendo y mostrando modal vacío
    document.getElementById('selectedAssetInfo').style.display = 'none';
    document.getElementById('tickerError').style.display = 'none';
}

async function addAssetToPortfolio() {
    const searchInput = document.getElementById('assetSearch');
    const errorDiv = document.getElementById('tickerError');
    
    let ticker = searchInput.value?.toUpperCase()?.trim();
    
    // Validación básica
    if (!ticker || ticker.length === 0) {
        errorDiv.textContent = 'Por favor selecciona un activo de la lista';
        errorDiv.style.display = 'block';
        return;
    }

    if (ticker.length > 10) {
        errorDiv.textContent = 'El ticker es muy largo (máximo 10 caracteres)';
        errorDiv.style.display = 'block';
        return;
    }

    if (!/^[A-Z0-9]+$/.test(ticker)) {
        errorDiv.textContent = 'El ticker solo debe contener letras y números';
        errorDiv.style.display = 'block';
        return;
    }

    if (!currentPortfolioId) {
        showAlert('Selecciona un portfolio primero', 'error');
        return;
    }

    try {
        console.log(`[INFO] Aniadiendo activo ${ticker} al portfolio ${currentPortfolioId}`);
        
        const response = await window.fetchWithAuth(`${API_BASE}/portfolios/${currentPortfolioId}/activos`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ ticker })
        });

        console.log(`   Response status: ${response.status}`);

        if (response.ok) {
            const data = await response.json();
            console.log(`[OK] Activo aniadido:`, data);
            showAlert(`Activo ${ticker} aniadido correctamente`, 'success');
            closeAddAssetModal();
            await loadPortfolioDetails(currentPortfolioId);
        } else if (response.status === 400) {
            const error = await response.json().catch(() => ({}));
            console.error('[ERROR] Ticker invalido:', error);
            errorDiv.textContent = error.detail || 'Ticker invalido o no existe';
            errorDiv.style.display = 'block';
        } else {
            const error = await response.json().catch(() => ({}));
            console.error('[ERROR]:', error);
            showAlert(`Error al aniadir activo: ${response.status}`, 'error');
        }
    } catch (error) {
        console.error('[ERROR]:', error);
        showAlert('Error de conexion', 'error');
    }
}

function showCreatePortfolioModal() {
    const modal = `
        <div id="portfolioModal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Crear Portfolio</h3>
                    <button class="btn-close" onclick="closeCreatePortfolioModal()">×</button>
                </div>
                <div class="modal-body">
                    <div class="form-group">
                        <label>Nombre del Portfolio</label>
                        <input type="text" id="portfolioNameInput" placeholder="ej: Mi Portfolio Agresivo">
                    </div>
                    <div class="form-group">
                        <label>Descripción</label>
                        <textarea id="portfolioDescInput" placeholder="Describe tu estrategia de inversión" rows="3"></textarea>
                    </div>
                    <div class="form-group">
                        <label>Nivel de Riesgo</label>
                        <select id="portfolioRiskInput">
                            <option value="0.3">Conservador (Bajo riesgo)</option>
                            <option value="0.5" selected>Moderado (Riesgo medio)</option>
                            <option value="0.8">Agresivo (Alto riesgo)</option>
                        </select>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn-secondary" onclick="closeCreatePortfolioModal()">Cancelar</button>
                    <button class="btn-primary" onclick="createPortfolio()">Crear</button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modal);
    document.getElementById('portfolioNameInput').focus();
}

function closeCreatePortfolioModal() {
    const modal = document.getElementById('portfolioModal');
    if (modal) modal.remove();
}

async function createPortfolio() {
    const nombre = document.getElementById('portfolioNameInput')?.value?.trim();
    const descripcion = document.getElementById('portfolioDescInput')?.value?.trim();
    const riesgo = parseFloat(document.getElementById('portfolioRiskInput')?.value);

    if (!nombre) {
        showAlert('Por favor ingresa un nombre', 'error');
        return;
    }

    try {
        const response = await window.fetchWithAuth(`${API_BASE}/portfolios`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                nombre_portfolio: nombre,
                descripcion: descripcion || '',
                riesgo: riesgo
            })
        });

        if (response.ok) {
            showAlert('Portfolio creado correctamente', 'success');
            closeCreatePortfolioModal();
            await loadPortfolios();
        } else {
            showAlert('Error al crear el portfolio', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showAlert('Error de conexión', 'error');
    }
}

// ============================================================
// UTILIDADES
// ============================================================

function showAlert(message, type = 'info') {
    const colors = {
        success: '#10b981',
        error: '#ef4444',
        info: '#3b82f6',
        warning: '#f59e0b'
    };
    
    const icons = {
        success: '✅',
        error: '❌',
        info: 'ℹ️',
        warning: '⚠️'
    };
    
    const bgColor = colors[type] || colors.info;
    const icon = icons[type] || '';
    
    const alertBox = document.createElement('div');
    alertBox.className = `alert alert-${type}`;
    alertBox.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${bgColor};
        color: white;
        border-radius: 6px;
        z-index: 10001;
        animation: slideInAlert 0.3s ease-out;
        font-size: 14px;
        font-weight: 500;
        max-width: 350px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        display: flex;
        align-items: center;
        gap: 10px;
        word-wrap: break-word;
    `;
    
    alertBox.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    document.body.appendChild(alertBox);
    
    setTimeout(() => {
        alertBox.style.animation = 'slideInAlert 0.3s ease-out reverse';
        setTimeout(() => alertBox.remove(), 300);
    }, 3000);
}