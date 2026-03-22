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
     * Muestra un selector de portfolios del usuario
     * Se muestra siempre para permitir cambiar entre ellos
     */
    const container = document.querySelector('.page-header');
    let selectorContainer = document.getElementById('portfolioSelectorContainer');
    
    if (!selectorContainer && currentPortfolios.length > 0) {
        selectorContainer = document.createElement('div');
        selectorContainer.id = 'portfolioSelectorContainer';
        selectorContainer.style.cssText = `
            margin-top: 15px;
            padding: 15px;
            background: #f9fafb;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
        `;
        
        let selectorHTML = `
            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                <label style="font-weight: 600; color: #333;">Mis Portfolios:</label>
                <select id="portfolioSelector" style="
                    padding: 8px 12px;
                    border: 1px solid #e5e7eb;
                    border-radius: 6px;
                    font-family: inherit;
                    cursor: pointer;
                    min-width: 250px;
                ">
        `;
        
        currentPortfolios.forEach(portfolio => {
            const selected = portfolio.id_portfolio === currentPortfolioId ? 'selected' : '';
            const riskLevel = portfolio.riesgo < 0.35 ? '🔴 Agresivo' : 
                              portfolio.riesgo < 0.65 ? '🟡 Moderado' : '🟢 Conservador';
            selectorHTML += `
                <option value="${portfolio.id_portfolio}" ${selected}>
                    ${portfolio.nombre_portfolio} - ${riskLevel}
                </option>
            `;
        });
        
        selectorHTML += `
                </select>
                <button class="btn-primary" onclick="createNewPortfolio()" style="padding: 8px 16px; font-size: 13px;">
                    + Nuevo Portfolio
                </button>
            </div>
        `;
        
        selectorContainer.innerHTML = selectorHTML;
        container.parentNode.insertBefore(selectorContainer, container.nextSibling);
        
        console.log(`📊 Selector renderizado con ${currentPortfolios.length} portfolio(s)`);
        
        // Event listener para cambiar portfolio
        document.getElementById('portfolioSelector').addEventListener('change', async (e) => {
            const portfolioId = parseInt(e.target.value);
            console.log(`🔀 Cambiando a portfolio ${portfolioId}`);
            currentPortfolioId = portfolioId;
            await loadPortfolioDetails(portfolioId);
        });
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
    const modal = `
        <div id="assetModal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Añadir Activo al Portfolio</h3>
                    <button class="btn-close" onclick="closeAddAssetModal()">×</button>
                </div>
                <div class="modal-body">
                    <div class="form-group">
                        <label>Ticker del Activo</label>
                        <input type="text" id="tickerInput" placeholder="Ingresa el símbolo (ej: AAPL, MSFT, GOOGL, TSLA)" maxlength="10" style="text-transform: uppercase;">
                        <small style="color: #999; margin-top: 5px; display: block;">Ejemplos de tickers válidos: AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META, NFLX</small>
                    </div>
                    <div id="tickerError" style="display: none; color: #dc2626; font-size: 13px; margin-top: 10px;"></div>
                </div>
                <div class="modal-footer">
                    <button class="btn-secondary" onclick="closeAddAssetModal()">Cancelar</button>
                    <button class="btn-primary" onclick="addAssetToPortfolio()">Añadir Activo</button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modal);
    const input = document.getElementById('tickerInput');
    input.focus();
    
    // Enter para enviar
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') addAssetToPortfolio();
    });

    // Escape para cerrar
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeAddAssetModal();
    }, { once: true });
}

function closeAddAssetModal() {
    const modal = document.getElementById('assetModal');
    if (modal) modal.remove();
}

async function addAssetToPortfolio() {
    const ticker = document.getElementById('tickerInput')?.value?.toUpperCase()?.trim();
    const errorDiv = document.getElementById('tickerError');
    
    // Validación básica
    if (!ticker || ticker.length === 0) {
        errorDiv.textContent = '⚠️ Por favor ingresa un ticker';
        errorDiv.style.display = 'block';
        return;
    }

    if (ticker.length > 10) {
        errorDiv.textContent = '⚠️ El ticker es muy largo (máximo 10 caracteres)';
        errorDiv.style.display = 'block';
        return;
    }

    if (!/^[A-Z0-9]+$/.test(ticker)) {
        errorDiv.textContent = '⚠️ El ticker solo debe contener letras y números';
        errorDiv.style.display = 'block';
        return;
    }

    if (!currentPortfolioId) {
        showAlert('Selecciona un portfolio primero', 'error');
        return;
    }

    try {
        console.log(`📝 Añadiendo activo ${ticker} al portfolio ${currentPortfolioId}`);
        
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
            console.log(`✅ Activo añadido:`, data);
            showAlert(`✅ Activo ${ticker} añadido correctamente`, 'success');
            closeAddAssetModal();
            await loadPortfolioDetails(currentPortfolioId);
        } else if (response.status === 400) {
            const error = await response.json().catch(() => ({}));
            console.error('❌ Ticker inválido:', error);
            errorDiv.textContent = `⚠️ ${error.detail || 'Ticker inválido o no existe'}`;
            errorDiv.style.display = 'block';
        } else {
            const error = await response.json().catch(() => ({}));
            console.error('❌ Error:', error);
            showAlert(`Error al añadir activo: ${response.status}`, 'error');
        }
    } catch (error) {
        console.error('❌ Error:', error);
        showAlert('Error de conexión', 'error');
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