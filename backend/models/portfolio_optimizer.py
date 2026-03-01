"""
Módulo de optimización de portfolios usando la teoría de Markowitz.

Teoría: El problema de optimización de cartera de Markowitz busca encontrar la asignación
de activos que maximiza el retorno esperado para un nivel de riesgo dado, o minimiza
el riesgo para un nivel de retorno dado.

Metodología:
1. Obtener retornos esperados de predicciones IA (Bi-GRU)
2. Calcular matriz de covarianza histórica
3. Resolver dos problemas de optimización:
   a) Maximizar Ratio de Sharpe (Max Sharpe)
   b) Minimizar volatilidad (Min Risk)

Referencias:
- Markowitz, H. (1952): Portfolio Selection. Journal of Finance.
- Black-Litterman Model para mezclar opiniones subjetivas con retornos históricos
"""

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.optimize import minimize
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# ==========================================
# UTILIDADES Y CÁLCULOS CORE
# ==========================================

def calculate_blended_return(
    ai_short_term_move: float,
    historical_annual_return: float,
    aversion_riesgo: float,
    projection_days: int = 365
) -> float:
    """
    Calcula retorno "blended" (fusionado) entre IA e historia.
    
    Filosofía Black-Litterman simplificada:
    - Stock conservador (aversion_riesgo=0.8): confía más en historia (80% historia, 20% IA)
    - Stock agresivo (aversion_riesgo=0.2): confía más en IA (60% historia, 40% IA)
    
    Args:
        ai_short_term_move: Cambio predicho para 1 día (ej: 0.02 = +2%)
        historical_annual_return: Retorno histórico anual (ej: 0.10 = +10%)
        aversion_riesgo: 0=Agresivo, 1=Conservador
        projection_days: Horizonte de proyección (défault: 365)
    
    Returns:
        float: Retorno anualizado blended (0.15 = 15% anual)
    """
    
    # Pesos basados en aversión al riesgo
    # Agresivo (0.0) → 60% historia, 40% IA
    # Conservador (1.0) → 80% historia, 20% IA
    peso_ia = 0.2 + (aversion_riesgo * 0.2)  # Rango [0.2, 0.4]
    peso_historia = 1.0 - peso_ia
    
    # Proyectar impacto IA a anual
    # Si IA predice +2% hoy, asumimos tendencia de 12 meses (no se repite 252 veces)
    ai_annual_impact = ai_short_term_move * 12
    
    # Fusión final
    blended = (historical_annual_return * peso_historia) + (ai_annual_impact * peso_ia)
    
    return blended


def download_historical_data(
    tickers: List[str],
    start_date: str = '2020-01-01',
    end_date: Optional[str] = None
) -> pd.DataFrame:
    """
    Descarga datos históricos de precios.
    
    Args:
        tickers: Lista de símbolos
        start_date: Fecha inicio (formato YYYY-MM-DD)
        end_date: Fecha fin (défault: hoy)
    
    Returns:
        DataFrame con precios de cierre
    """
    try:
        print(f"📥 Descargando datos históricos para {len(tickers)} tickers...")
        data = yf.download(tickers, start=start_date, end=end_date, progress=False)['Close']
        return data
    except Exception as e:
        print(f"❌ Error descargando datos: {e}")
        raise


def calculate_covariance_matrix(
    tickers: List[str],
    start_date: str = '2020-01-01'
) -> Tuple[np.ndarray, List[str]]:
    """
    Calcula matriz de covarianza anualizada.
    
    Args:
        tickers: Lista de símbolos
        start_date: Fecha inicio
    
    Returns:
        (cov_matrix, tickers) matriz covarianza anualizada
    """
    data = download_historical_data(tickers, start_date=start_date)
    log_returns = np.log(data / data.shift(1)).dropna()
    cov_matrix = log_returns.cov() * 252  # Anualizada
    return cov_matrix.values, log_returns.columns.tolist()


def calculate_portfolio_performance(
    weights: np.ndarray,
    expected_returns: np.ndarray,
    cov_matrix: np.ndarray,
    risk_free_rate: float = 0.03
) -> Tuple[float, float, float]:
    """
    Calcula performance de un portfolio.
    
    Args:
        weights: Pesos de la cartera [0, 1]
        expected_returns: Retornos esperados por ticker
        cov_matrix: Matriz de covarianza
        risk_free_rate: Tasa libre de riesgo (défault: 3%)
    
    Returns:
        (returns, volatility, sharpe_ratio)
    """
    portfolio_return = np.sum(expected_returns * weights)
    portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
    sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_volatility
    
    return portfolio_return, portfolio_volatility, sharpe_ratio


# ==========================================
# OPTIMIZADORES
# ==========================================

def optimize_max_sharpe(
    tickers: List[str],
    expected_returns: np.ndarray,
    cov_matrix: np.ndarray,
    risk_free_rate: float = 0.03
) -> Dict:
    """
    Optimiza para maximizar Ratio de Sharpe.
    
    Objetivo: Encontrar la cartera más eficiente en términos de riesgo/retorno.
    
    Args:
        tickers: Símbolos
        expected_returns: Retornos esperados
        cov_matrix: Matriz covarianza
        risk_free_rate: Tasa libre de riesgo
    
    Returns:
        Dict con:
        {
            'pesos': {ticker: peso},
            'retorno_esperado': float,
            'volatilidad': float,
            'sharpe_ratio': float
        }
    """
    
    def neg_sharpe(weights):
        ret, vol, _ = calculate_portfolio_performance(
            weights, expected_returns, cov_matrix, risk_free_rate
        )
        return -(ret - risk_free_rate) / vol
    
    num_assets = len(tickers)
    constraints = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
    bounds = tuple((0, 1) for _ in range(num_assets))
    init_guess = np.array([1.0 / num_assets] * num_assets)
    
    result = minimize(
        neg_sharpe,
        init_guess,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints
    )
    
    ret, vol, sharpe = calculate_portfolio_performance(
        result.x, expected_returns, cov_matrix, risk_free_rate
    )
    
    return {
        'pesos': {ticker: float(weight) for ticker, weight in zip(tickers, result.x)},
        'retorno_esperado': float(ret),
        'volatilidad': float(vol),
        'sharpe_ratio': float(sharpe)
    }


def optimize_min_volatility(
    tickers: List[str],
    expected_returns: np.ndarray,
    cov_matrix: np.ndarray,
    risk_free_rate: float = 0.03
) -> Dict:
    """
    Optimiza para minimizar volatilidad.
    
    Objetivo: Encontrar la cartera de menor riesgo independientemente del retorno.
    
    Args:
        tickers: Símbolos
        expected_returns: Retornos esperados
        cov_matrix: Matriz covarianza
        risk_free_rate: Tasa libre de riesgo
    
    Returns:
        Dict con pesos, retorno y volatilidad
    """
    
    def portfolio_volatility(weights):
        _, vol, _ = calculate_portfolio_performance(
            weights, expected_returns, cov_matrix, risk_free_rate
        )
        return vol
    
    num_assets = len(tickers)
    constraints = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
    bounds = tuple((0, 1) for _ in range(num_assets))
    init_guess = np.array([1.0 / num_assets] * num_assets)
    
    result = minimize(
        portfolio_volatility,
        init_guess,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints
    )
    
    ret, vol, sharpe = calculate_portfolio_performance(
        result.x, expected_returns, cov_matrix, risk_free_rate
    )
    
    return {
        'pesos': {ticker: float(weight) for ticker, weight in zip(tickers, result.x)},
        'retorno_esperado': float(ret),
        'volatilidad': float(vol),
        'sharpe_ratio': float(sharpe)
    }


# ==========================================
# API PRINCIPAL
# ==========================================

def optimize_portfolio(
    tickers: List[str],
    ai_predictions: Dict[str, float],
    aversion_riesgo: float,
    risk_free_rate: float = 0.03,
    historical_start_date: str = '2020-01-01'
) -> Dict:
    """
    Optimiza un portfolio completo respetando aversión al riesgo del usuario.
    
    Flujo:
    1. Obtener retornos blended (IA + Historia)
    2. Calcular matriz de covarianza histórica
    3. Resolver dos escenarios de optimización
    4. Devolver recomendaciones personalizadas
    
    Args:
        tickers: Símbolos a considerar
        ai_predictions: {ticker: cambio_predicho_1_dia}
        aversion_riesgo: 0=Agresivo, 1=Conservador
        risk_free_rate: Tasa libre de riesgo
        historical_start_date: Fecha para datos históricos
    
    Returns:
        Dict con:
        {
            'escenario_max_sharpe': {...},
            'escenario_min_riesgo': {...},
            'recomendacion': str
        }
    """
    
    try:
        print(f"📊 Iniciando optimización para {len(tickers)} activos...")
        
        # 1. Calcular retornos blended
        print("🔄 Calculando retornos esperados (IA + Historia)...")
        expected_yields = []
        
        for ticker in tickers:
            # Retorno histórico
            hist_data = download_historical_data([ticker], start_date=historical_start_date)
            daily_returns = hist_data.pct_change().dropna()
            hist_annual_return = daily_returns.mean() * 252
            
            # Predicción IA (cambio predicho para 1 día)
            ai_move = ai_predictions.get(ticker, 0.0)
            
            # Blended
            blended = calculate_blended_return(
                ai_move,
                hist_annual_return,
                aversion_riesgo
            )
            expected_yields.append(blended)
            
            print(f"  {ticker}: IA={ai_move*100:.2f}% + Histórico={hist_annual_return*100:.2f}% = {blended*100:.2f}%")
        
        expected_returns = np.array(expected_yields)
        
        # 2. Matriz de covarianza
        print("📈 Calculando matriz de covarianza histórica...")
        cov_matrix, _ = calculate_covariance_matrix(tickers, start_date=historical_start_date)
        
        # 3. Optimizaciones
        print("⚙️  Ejecutando optimizadores...")
        opt_max_sharpe = optimize_max_sharpe(tickers, expected_returns, cov_matrix, risk_free_rate)
        opt_min_risk = optimize_min_volatility(tickers, expected_returns, cov_matrix, risk_free_rate)
        
        # 4. Determinar recomendación según aversión al riesgo
        if aversion_riesgo < 0.4:
            # Agresivo → Max Sharpe
            recomendacion_escenario = 'max_sharpe'
            recomendacion_texto = (
                f"Perfil AGRESIVO: Maximizar retorno. "
                f"Sharpe={opt_max_sharpe['sharpe_ratio']:.2f}"
            )
        elif aversion_riesgo > 0.7:
            # Conservador → Min Risk
            recomendacion_escenario = 'min_riesgo'
            recomendacion_texto = (
                f"Perfil CONSERVADOR: Minimizar riesgo. "
                f"Volatilidad={opt_min_risk['volatilidad']*100:.2f}%"
            )
        else:
            # Equilibrado → Max Sharpe (balance óptimo)
            recomendacion_escenario = 'max_sharpe'
            recomendacion_texto = (
                f"Perfil EQUILIBRADO: Balance riesgo-retorno. "
                f"Sharpe={opt_max_sharpe['sharpe_ratio']:.2f}"
            )
        
        return {
            'timestamp': datetime.now().isoformat(),
            'aversion_riesgo': aversion_riesgo,
            'tickers': tickers,
            'escenario_max_sharpe': opt_max_sharpe,
            'escenario_min_riesgo': opt_min_risk,
            'recomendacion_escenario': recomendacion_escenario,
            'recomendacion_texto': recomendacion_texto,
            'retornos_esperados': {t: float(r*100) for t, r in zip(tickers, expected_returns)}
        }
    
    except Exception as e:
        print(f"❌ Error en optimización: {e}")
        raise


def generate_efficient_frontier(
    tickers: List[str],
    expected_returns: np.ndarray,
    cov_matrix: np.ndarray,
    num_portfolios: int = 5000,
    risk_free_rate: float = 0.03
) -> Dict:
    """
    Genera frontera eficiente mediante Monte Carlo.
    
    Args:
        tickers: Símbolos
        expected_returns: Retornos esperados
        cov_matrix: Matriz covarianza
        num_portfolios: Número de portfolios aleatorios a simular
        risk_free_rate: Tasa libre de riesgo
    
    Returns:
        Dict con data para graficar
    """
    
    results = np.zeros((3, num_portfolios))
    
    for i in range(num_portfolios):
        weights = np.random.random(len(tickers))
        weights /= np.sum(weights)
        
        ret, vol, sharpe = calculate_portfolio_performance(
            weights, expected_returns, cov_matrix, risk_free_rate
        )
        
        results[0, i] = vol
        results[1, i] = ret
        results[2, i] = sharpe
    
    return {
        'volatilities': results[0],
        'returns': results[1],
        'sharpe_ratios': results[2]
    }
