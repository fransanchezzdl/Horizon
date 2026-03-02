"""
Módulo de predicción de precios de acciones usando Bi-GRU.

Arquitectura: Bidirectional GRU (Gated Recurrent Unit) con 2 capas.
Entrada: [Close, RSI, MACD, EMA] en ventanas de 60 días.
Salida: Predicción del precio de cierre para el próximo día.

Referencias:
- Cho et al. (2014): Learning Phrase Representations using RNN Encoder-Decoder
- Improved Architecture for LSTM Sequence to Sequence Learning (2015)
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.preprocessing import MinMaxScaler
import yfinance as yf
from typing import Tuple, Dict, Optional
import os
import json
from datetime import datetime, timedelta

# Configuración del dispositivo
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


# ==========================================
# INDICADORES TÉCNICOS
# ==========================================

def calculate_rsi(data: pd.Series, periods: int = 14) -> pd.Series:
    """
    Calcula el Relative Strength Index (RSI).
    
    Args:
        data: Serie de precios (típicamente Close)
        periods: Período de cálculo (défault: 14)
    
    Returns:
        Serie con valores RSI (0-100)
    """
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_ema(data: pd.Series, span: int = 20) -> pd.Series:
    """
    Calcula el Exponential Moving Average (EMA).
    
    Args:
        data: Serie de precios
        span: Período de la media móvil (défault: 20)
    
    Returns:
        Serie con valores EMA
    """
    return data.ewm(span=span, adjust=False).mean()


def calculate_macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    Calcula el Moving Average Convergence Divergence (MACD).
    
    Args:
        data: Serie de precios (típicamente Close)
        fast: Período EMA rápida (défault: 12)
        slow: Período EMA lenta (défault: 26)
        signal: Período de la señal (défault: 9)
    
    Returns:
        DataFrame con columnas: MACD, Signal, Histogram
    """
    ema_fast = calculate_ema(data, span=fast)
    ema_slow = calculate_ema(data, span=slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return pd.DataFrame({
        'MACD': macd_line,
        'Signal': signal_line,
        'Histogram': histogram
    })


# ==========================================
# MODELO BI-GRU
# ==========================================

class BiGRUModel(nn.Module):
    """
    Modelo Bi-GRU para predicción de series temporales.
    
    Parámetros:
    - input_dim: Número de features (défault: 4 → Close, RSI, MACD, EMA)
    - hidden_dim: Dimensión del estado oculto (défault: 64)
    - num_layers: Número de capas recurrentes (défault: 2)
    - output_dim: Dimensión de salida (défault: 1 → precio)
    - dropout: Tasa de dropout para regularización (défault: 0.1)
    """
    
    def __init__(self, input_dim: int, hidden_dim: int = 64, 
                 num_layers: int = 2, output_dim: int = 1, dropout: float = 0.1):
        super(BiGRUModel, self).__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        # GRU bidireccional: procesa secuencia hacia adelante y atrás
        self.gru = nn.GRU(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
            bidirectional=True
        )
        
        # Capa fully connected: de (hidden_dim * 2) a output_dim
        self.fc = nn.Linear(hidden_dim * 2, output_dim)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass del modelo.
        
        Args:
            x: Tensor de entrada [batch_size, seq_length, input_dim]
        
        Returns:
            Predicción [batch_size, output_dim]
        """
        # GRU retorna (output, hidden)
        # output: [batch_size, seq_length, hidden_dim * 2]
        out, _ = self.gru(x)
        
        # Tomamos el último estado temporal ([-1, :])
        last_output = out[:, -1, :]  # [batch_size, hidden_dim * 2]
        
        # Pasamos por la capa fully connected
        prediction = self.fc(last_output)  # [batch_size, output_dim]
        
        return prediction


# ==========================================
# FUNCIONES DE PREDICCIÓN
# ==========================================

def create_sequences(data: np.ndarray, seq_length: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Crea secuencias deslizantes para el entrenamiento.
    
    Args:
        data: Array de datos escalados [n_samples, n_features]
        seq_length: Longitud de la ventana temporal (défault: 60)
    
    Returns:
        (X, y) donde X es [n_sequences, seq_length, n_features]
               y y es [n_sequences] (precio target escalado)
    """
    xs, ys = [], []
    for i in range(len(data) - seq_length):
        x = data[i:(i + seq_length)]
        y = data[i + seq_length, 0]  # Close price (columna 0)
        xs.append(x)
        ys.append(y)
    return np.array(xs), np.array(ys)


def calculate_confidence(
    volatility: float,
    model_mse: float,
    prediction_error: Optional[float] = None
) -> float:
    """
    Calcula la confianza de la predicción.
    
    Argumentos:
        volatility: Volatilidad histórica del ticker
        model_mse: Error cuadrático medio del modelo en test
        prediction_error: Error específico de la predicción (opcional)
    
    Returns:
        float: Confianza entre 0 y 1
    """
    # Fórmula:
    # 1. Stocks volátiles reducen confianza (volatility)
    # 2. Modelos con MSE alto reducen confianza
    # 3. Errors específicos pueden reducir confianza predeterminada
    
    base_confidence = 0.85  # Base optimista
    
    # Penalizar por volatilidad (máx -0.3)
    volatility_penalty = min(volatility / 100 * 0.3, 0.3)
    
    # Penalizar por MSE del modelo (máx -0.2)
    mse_penalty = min(model_mse / 0.1 * 0.2, 0.2)
    
    confidence = base_confidence - volatility_penalty - mse_penalty
    
    return max(min(confidence, 1.0), 0.0)  # Clamp entre 0 y 1


def get_prediction(
    ticker: str,
    model_path: Optional[str] = None,
    window_size: int = 60,
    dias_adelante: int = 1
) -> Dict:
    """
    Obtiene predicción de precio para un ticker.
    
    Args:
        ticker: Símbolo del ticker (ej: "AAPL", "KO")
        model_path: Ruta al archivo .pth del modelo (si None, busca modelo_{TICKER}.pth)
        window_size: Tamaño de la ventana temporal (défault: 60)
        dias_adelante: Días para predecir adelante (défault: 1)
    
    Returns:
        Dict con:
        {
            'ticker': str,
            'precio_actual': float,
            'predicciones': [
                {
                    'fecha': str,
                    'precio_predicho': float,
                    'cambio_esperado': float,
                    'confianza': float
                }
            ],
            'precio_predicho_final': float,
            'cambio_esperado_total': float,
            'confianza_promedio': float,
            'modelo_version': str,
            'indicadores_usados': list[str]
        }
    """
    
    try:
        # Configuración
        feature_cols = ['Close', 'RSI', 'MACD', 'EMA']
        model_name = model_path or f"modelo_{ticker}.pth"
        
        print(f"🧠 Descargando datos de {ticker}...")
        
        # 1. Descargar datos
        df = yf.download(ticker, start='2020-01-01', progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # 2. Calcular indicadores técnicos
        print(f"📊 Calculando indicadores...")
        df['RSI'] = calculate_rsi(df['Close'], periods=14)
        macd_result = calculate_macd(df['Close'], fast=12, slow=26, signal=9)
        df['MACD'] = macd_result['MACD']
        df['EMA'] = calculate_ema(df['Close'], span=20)
        df.dropna(inplace=True)
        
        # Obtener precio actual y volatilidad
        current_price = df['Close'].iloc[-1]
        daily_returns = df['Close'].pct_change().dropna()
        volatility = daily_returns.std() * np.sqrt(252) * 100  # Volatilidad anual %
        
        # 3. Preparar datos para el modelo
        data_raw = df[feature_cols].values
        scaler = MinMaxScaler(feature_range=(0, 1))
        data_scaled = scaler.fit_transform(data_raw)
        
        # 4. Cargar modelo
        print(f"🔌 Cargando modelo: {model_name}...")
        model = BiGRUModel(
            input_dim=len(feature_cols),
            hidden_dim=64,
            num_layers=2,
            output_dim=1,
            dropout=0.1
        )
        
        if not os.path.exists(model_name):
            raise FileNotFoundError(f"Modelo no encontrado: {model_name}")
        
        model.load_state_dict(torch.load(model_name, map_location=device))
        model.to(device)
        model.eval()
        
        # 5. Preparar ventana de entrada (últimos 60 días)
        last_window = data_scaled[-window_size:]
        input_tensor = torch.from_numpy(last_window).float().unsqueeze(0).to(device)
        
        # 6. Predicción recursiva para múltiples días
        print(f"🔮 Generando predicciones para {dias_adelante} día(s)...")
        predictions = []
        current_window = input_tensor.clone()
        
        for day_offset in range(1, dias_adelante + 1):
            with torch.no_grad():
                # Predecir el siguiente precio
                pred_scaled = model(current_window).cpu().numpy()
            
            # Invertir escalado para obtener precio real
            dummy = np.zeros((1, len(feature_cols)))
            dummy[:, 0] = pred_scaled.flatten()
            pred_price = scaler.inverse_transform(dummy)[0, 0]
            
            # Calcular cambio esperado
            if day_offset == 1:
                change_pct = (pred_price - current_price) / current_price * 100
            else:
                previous_pred = predictions[-1]['precio_predicho']
                change_pct = (pred_price - previous_pred) / previous_pred * 100
            
            # Calcular confianza
            confidence = calculate_confidence(volatility, mse=0.001)
            
            # Fecha de predicción
            pred_date = df.index[-1] + timedelta(days=day_offset)
            
            predictions.append({
                'fecha': pred_date.strftime('%Y-%m-%d'),
                'precio_predicho': float(pred_price),
                'cambio_esperado': float(change_pct),
                'confianza': float(confidence)
            })
            
            # Actualizar ventana: quitamos día viejo, añadimos predicción nueva
            new_row = current_window[:, -1, :].clone()
            new_row[:, 0] = torch.from_numpy(np.array([pred_scaled[0, 0]]))
            # Los indicadores se mantienen del último día (simplificación)
            current_window = torch.cat(
                (current_window[:, 1:, :], new_row.unsqueeze(1)), dim=1
            )
        
        # Calcular confianza promedio y cambio total
        confianza_promedio = np.mean([p['confianza'] for p in predictions])
        cambio_total = (predictions[-1]['precio_predicho'] - current_price) / current_price * 100
        
        return {
            'ticker': ticker,
            'precio_actual': float(current_price),
            'predicciones': predictions,
            'precio_predicho_final': float(predictions[-1]['precio_predicho']),
            'cambio_esperado_total': float(cambio_total),
            'confianza_promedio': float(confianza_promedio),
            'modelo_version': '1.0.0',
            'indicadores_usados': feature_cols,
            'volatilidad_historica': float(volatility),
            'fecha_generacion': datetime.now().isoformat()
        }
    
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        return {'error': str(e)}
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return {'error': str(e)}


def predict_multiple_tickers(tickers: list[str], dias_adelante: int = 1) -> Dict[str, Dict]:
    """
    Obtiene predicciones para múltiples tickers simultáneamente.
    
    Args:
        tickers: Lista de símbolos
        dias_adelante: Días para predecir
    
    Returns:
        Dict con predicciones por ticker
    """
    predictions = {}
    for ticker in tickers:
        predictions[ticker] = get_prediction(ticker, dias_adelante=dias_adelante)
    return predictions
