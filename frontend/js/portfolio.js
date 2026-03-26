// ============================================================
// INICIALIZACIÓN Y CONFIGURACIÓN
// ============================================================

const API_BASE = window.API_BASE;
let currentPortfolioId = null;
let currentPortfolios = [];

// Carga sesión, valida autenticación y arranca la carga de portfolios.
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

// Obtiene la lista de portfolios del usuario y decide el estado inicial de UI.
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
            // Cargar el primer portfolio por defecto
            currentPortfolioId = currentPortfolios[0].id_portfolio;

            // Mostrar selector de portfolios
            renderPortfolioSelector();

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

// Carga el detalle de un portfolio concreto y renderiza cabecera + tabla.
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
        const accionesEnriquecidas = await enrichPortfolioStocks(portfolio.acciones || []);
        renderAssetsTable(accionesEnriquecidas);
        await renderPortfolioMetrics(portfolio);
    } catch (error) {
        console.error('❌ Error:', error);
        showAlert('Error de conexión', 'error');
    }
}

async function enrichPortfolioStocks(acciones) {
    if (!Array.isArray(acciones) || acciones.length === 0) {
        return [];
    }

    const uniqueTickers = Array.from(
        new Set(acciones.map((accion) => (accion.ticker || '').toUpperCase()).filter(Boolean))
    );

    const activosMap = new Map();

    for (const ticker of uniqueTickers) {
        try {
            const response = await window.fetchWithAuth(`${API_BASE}/activos/${encodeURIComponent(ticker)}`);
            if (!response.ok) continue;
            const activo = await response.json();
            activosMap.set(ticker, activo);
        } catch (error) {
            console.error(`Error cargando detalles de ${ticker}:`, error);
        }
    }

    return acciones.map((accion) => {
        const ticker = (accion.ticker || '').toUpperCase();
        const detalles = activosMap.get(ticker) || {};

        return {
            ...accion,
            ticker,
            nombre_completo: detalles.nombre_completo || ticker,
            precio: detalles.precio,
            estabilidad: detalles.estabilidad,
            senal_ia: detalles.senal_ia
        };
    });
}

async function renderPortfolioMetrics(portfolio) {
    const acciones = Array.isArray(portfolio?.acciones) ? portfolio.acciones : [];
    const totalAssets = acciones.length;

    const totalAssetsValue = document.getElementById('totalAssetsValue');
    const totalAssetsSub = document.getElementById('totalAssetsSub');
    if (totalAssetsValue) totalAssetsValue.textContent = String(totalAssets);
    if (totalAssetsSub) totalAssetsSub.textContent = 'tickers en cartera';

    const stableAssets = await countStableAssets(acciones);
    const stablePercent = totalAssets > 0 ? Math.round((stableAssets / totalAssets) * 100) : 0;

    const stableAssetsValue = document.getElementById('stableAssetsValue');
    const stableAssetsSub = document.getElementById('stableAssetsSub');
    const stableAssetsBar = document.getElementById('stableAssetsBar');

    if (stableAssetsValue) stableAssetsValue.textContent = `${stableAssets} de ${totalAssets}`;
    if (stableAssetsSub) stableAssetsSub.textContent = totalAssets > 0 ? `${stablePercent}% del portfolio` : 'Sin datos';
    if (stableAssetsBar) stableAssetsBar.style.width = `${stablePercent}%`;

    const risk = Number(portfolio?.riesgo);
    const riskProfileValue = document.getElementById('riskProfileValue');
    const riskProfileSub = document.getElementById('riskProfileSub');

    if (Number.isNaN(risk)) {
        if (riskProfileValue) riskProfileValue.textContent = '--';
        if (riskProfileSub) riskProfileSub.textContent = 'Sin datos';
        return;
    }

    let riskLabel = 'Moderado';
    let riskText = 'riesgo medio';

    if (risk < 0.35) {
        riskLabel = 'Bajo';
        riskText = 'riesgo bajo';
    } else if (risk >= 0.65) {
        riskLabel = 'Alto';
        riskText = 'riesgo alto';
    }

    const riskPercentage = Math.round(risk * 100);
    if (riskProfileValue) riskProfileValue.textContent = riskLabel;
    if (riskProfileSub) riskProfileSub.textContent = `${riskPercentage}% · ${riskText}`;
}

async function countStableAssets(acciones) {
    if (!acciones.length) {
        return 0;
    }

    const uniqueTickers = Array.from(new Set(acciones.map((accion) => (accion.ticker || '').toUpperCase()).filter(Boolean)));
    let stableCount = 0;

    for (const ticker of uniqueTickers) {
        try {
            const response = await window.fetchWithAuth(`${API_BASE}/activos/${encodeURIComponent(ticker)}`);
            if (!response.ok) {
                continue;
            }
            const activo = await response.json();
            if (activo?.estabilidad === true) {
                stableCount += 1;
            }
        } catch (error) {
            console.error(`Error consultando estabilidad para ${ticker}:`, error);
        }
    }

    return stableCount;
}

// ============================================================
// RENDERIZAR DATOS EN LA UI
// ============================================================

function renderPortfolioSelector() {
    // Renderiza portfolios como tabs tipo píldora y conecta cambio de portfolio activo.
    const selectorContainer = document.getElementById('portfolioSelectorContainer');
    const portfolioTabs = document.getElementById('portfolioTabs');
    
    if (!selectorContainer || !portfolioTabs) {
        console.warn('⚠️ Elementos de tabs no encontrados en HTML');
        return;
    }
    
    // Mostrar/ocultar la sección basada en si hay portfolios
    if (currentPortfolios.length === 0) {
        selectorContainer.style.display = 'none';
        return;
    }
    
    selectorContainer.style.display = 'flex';
    portfolioTabs.innerHTML = '';

    currentPortfolios.forEach((portfolio) => {
        const tabButton = document.createElement('button');
        tabButton.type = 'button';
        tabButton.classList.add('portfolio-tab');
        tabButton.className = portfolio.id_portfolio === currentPortfolioId
            ? 'btn-primary portfolio-tab active'
            : 'btn-outline portfolio-tab';
        tabButton.style.padding = '10px 20px';
        tabButton.style.borderRadius = '999px';
        tabButton.style.fontSize = '15px';
        tabButton.textContent = portfolio.nombre_portfolio;

        tabButton.addEventListener('click', async () => {
            if (portfolio.id_portfolio === currentPortfolioId) return;
            currentPortfolioId = portfolio.id_portfolio;
            renderPortfolioSelector();
            await loadPortfolioDetails(currentPortfolioId);
        });

        portfolioTabs.appendChild(tabButton);
    });

    const newPortfolioTab = document.createElement('button');
    newPortfolioTab.type = 'button';
    newPortfolioTab.className = 'btn-outline portfolio-tab';
    newPortfolioTab.style.padding = '10px 20px';
    newPortfolioTab.style.borderRadius = '999px';
    newPortfolioTab.style.fontSize = '15px';
    newPortfolioTab.textContent = '+ Nuevo';
    newPortfolioTab.addEventListener('click', createNewPortfolio);
    portfolioTabs.appendChild(newPortfolioTab);
    
    console.log(`📊 Tabs renderizadas con ${currentPortfolios.length} portfolio(s)`);
}

// Renderiza datos generales del portfolio (título, conteo de activos y riesgo).
function renderPortfolioData(portfolio) {
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

// Abre el modal compartido para crear un nuevo portfolio.
function createNewPortfolio() {
    showCreatePortfolioModal();
}

// Renderiza la tabla de activos del portfolio o el estado vacío de la tabla.
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

    acciones.forEach((activo) => {
        const precio = typeof activo.precio === 'number'
            ? activo.precio
            : Number(activo.precio);

        const precioTexto = Number.isFinite(precio)
            ? `$${precio.toFixed(2)}`
            : '--';

        const estabilidad = activo.estabilidad === true
            ? { text: 'Estable', badge: 'badge-green' }
            : { text: 'Volátil', badge: 'badge-orange' };

        const senal = (activo.senal_ia || '').toString().toUpperCase();
        const senalTexto = senal || 'SIN DATOS';
        const senalClase = senal === 'ALCISTA'
            ? 'text-success'
            : senal === 'BAJISTA'
                ? 'text-danger'
                : 'text-muted';

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
                        <span class="asset-name">${activo.nombre_completo || activo.ticker}</span>
                    </div>
                </div>
            </td>
            <td>
                <div class="price-cell">
                    <span class="price-val">${precioTexto}</span>
                </div>
            </td>
            <td><span class="badge ${estabilidad.badge}">${estabilidad.text}</span></td>
            <td><span class="text-bold ${senalClase}">${senalTexto}</span></td>
            <td><span class="badge badge-blue-soft">Monitoreo</span></td>
            <td class="text-center">
                <div class="row-action-buttons">
                    <button class="table-action-btn" type="button" title="Ver en análisis" onclick="goToTickerAnalysis('${activo.ticker}')">↗</button>
                    <button class="table-action-btn table-action-btn-delete" type="button" title="Eliminar activo" data-stock-id="${activo.id_posicion}" onclick="deleteAsset(${activo.id_posicion})">✕</button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Renderiza el estado vacío global cuando el usuario no tiene portfolios.
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

function goToTickerAnalysis(ticker) {
    if (!ticker) {
        return;
    }

    window.location.href = `analysis.html?ticker=${encodeURIComponent(ticker)}`;
}

// Elimina una posición del portfolio activo y refresca el detalle tras éxito.
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
    // Abre el modal de añadir activo y prepara sus estados/eventos locales.
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
    
    // Busca activos por texto para el autocompletado del modal.
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
    
    // Dibuja las sugerencias de activos en la lista desplegable.
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
    
    // Marca un activo como seleccionado y habilita el botón de añadir.
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
    
    // Gestiona escritura en input con debounce para evitar llamadas excesivas.
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
    
    // Permite navegar sugerencias con teclado y confirmar selección.
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
    
    // Cierra sugerencias cuando el click ocurre fuera del input-wrap.
    document.addEventListener('click', (ev) => {
        if (!ev.target.closest('.input-wrap')) suggestions.hidden = true;
    });
    
    // Cierra el modal al pulsar Escape.
    const escapeHandler = (e) => {
        if (e.key === 'Escape') {
            closeAddAssetModal();
            document.removeEventListener('keydown', escapeHandler);
        }
    };
    document.addEventListener('keydown', escapeHandler);
}

// Cierra el modal de añadir activo y resetea sus elementos básicos.
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

// Valida y envía el ticker seleccionado al portfolio activo.
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

// ============================================================
// UTILIDADES
// ============================================================

// Muestra una notificación tipo toast para feedback de éxito/error/info.
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