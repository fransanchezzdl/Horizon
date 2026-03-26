(function () {
    let currentOptions = null;

    function showCreatePortfolioModal(options = {}) {
        if (document.getElementById('portfolioModal')) {
            return;
        }

        currentOptions = options;

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
        const input = document.getElementById('portfolioNameInput');
        if (input) {
            input.focus();
        }
    }

    function closeCreatePortfolioModal() {
        const modal = document.getElementById('portfolioModal');
        if (modal) modal.remove();
    }

    async function createPortfolio() {
        const apiBase = window.API_BASE;
        const nombre = document.getElementById('portfolioNameInput')?.value?.trim();
        const descripcion = document.getElementById('portfolioDescInput')?.value?.trim();
        const riesgo = parseFloat(document.getElementById('portfolioRiskInput')?.value);

        if (!nombre) {
            if (typeof window.showAlert === 'function') {
                window.showAlert('Por favor ingresa un nombre', 'error');
            } else {
                alert('Por favor ingresa un nombre');
            }
            return;
        }

        try {
            const response = await window.fetchWithAuth(`${apiBase}/portfolios`, {
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

            if (!response.ok) {
                if (typeof window.showAlert === 'function') {
                    window.showAlert('Error al crear el portfolio', 'error');
                } else {
                    alert('Error al crear el portfolio');
                }
                return;
            }

            const createdPortfolio = await response.json();

            if (typeof currentOptions?.onCreated === 'function') {
                await currentOptions.onCreated(createdPortfolio);
            } else {
                if (typeof window.showAlert === 'function') {
                    window.showAlert('Portfolio creado correctamente', 'success');
                }
                if (typeof window.loadPortfolios === 'function') {
                    await window.loadPortfolios();
                }
            }

            closeCreatePortfolioModal();
        } catch (error) {
            console.error('Error:', error);
            if (typeof window.showAlert === 'function') {
                window.showAlert('Error de conexión', 'error');
            } else {
                alert('Error de conexión');
            }
        }
    }

    window.showCreatePortfolioModal = showCreatePortfolioModal;
    window.closeCreatePortfolioModal = closeCreatePortfolioModal;
    window.createPortfolio = createPortfolio;
})();
