(function () {
    let currentOptions = null;

    function showCreatePortfolioModal(options = {}) {
        currentOptions = options;

        const modal = document.getElementById('portfolioModal');
        if (!modal) {
            console.error('No se encontró #portfolioModal en el HTML');
            return;
        }

        modal.classList.remove('is-hidden');

        const nameInput = document.getElementById('portfolioNameInput');
        const descInput = document.getElementById('portfolioDescInput');
        const riskInput = document.getElementById('portfolioRiskInput');

        if (nameInput) {
            nameInput.value = '';
            nameInput.focus();
        }
        if (descInput) descInput.value = '';
        if (riskInput) riskInput.value = '0.5';
    }

    function closeCreatePortfolioModal() {
        const modal = document.getElementById('portfolioModal');
        if (modal) modal.classList.add('is-hidden');
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
