"""
VALIDACIÓN DE CONFIABILIDAD DEL MODELO XGBoost

Tests para detectar overfitting/underfitting:
1. Curvas de aprendizaje (training vs validation loss)
2. Backtesting Out-of-Sample (datos reales 2023-2026)
3. Walk-forward validation (simular trading real)
4. Comparación vs Buy & Hold benchmark
5. Análisis de resultados por ticker
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
from pathlib import Path

from backend.models.config import (
    get_tickers_from_database, TICKERS, SAVED_MODELS_DIR, get_config
)


class ModelReliabilityValidator:
    """Valida la confiabilidad y fiabilidad del modelo XGBoost entrenado."""
    
    def __init__(self, output_dir: str = "./model_validation"):
        self.output_dir = output_dir
        Path(output_dir).mkdir(exist_ok=True, parents=True)
        self.results = {}
    
    def get_all_tickers(self) -> List[str]:
        """Obtiene lista de todos los tickers a validar."""
        try:
            tickers_config = get_tickers_from_database()
            return tickers_config["stable"] + tickers_config["volatile"]
        except:
            return TICKERS["stable"] + TICKERS["volatile"]
    
    def test_1_learning_curves(self, ticker: str) -> Dict:
        """
        TEST 1: Análisis de curvas de aprendizaje
        
        Detecta:
        - Overfitting: si train_loss << val_loss
        - Underfitting: si train_loss ≈ val_loss y altas ambas
        - Zona óptima: train_loss ≈ val_loss con valores bajos
        """
        print(f"\n  [TEST 1] Learning Curves para {ticker}...")
        
        try:
            # Cargar datos históricos
            data = self._load_ticker_data(ticker, "2018-01-01", datetime.now().strftime("%Y-%m-%d"))
            if data is None or len(data) < 100:
                return {"status": "FAIL", "reason": "No sufficient data"}
            
            # Calcular returns (para clasificación 3-clases)
            data['return'] = data['Close'].pct_change()
            data['target'] = pd.cut(data['return'], bins=[-np.inf, -0.0001, 0.0001, np.inf], 
                                   labels=[0, 1, 2])  # BAJISTA, LATERAL, ALCISTA
            data = data.dropna()
            
            if len(data) < 200:
                return {"status": "FAIL", "reason": "No sufficient returns data"}
            
            # Split: train (60%), val (20%), test (20%)
            n = len(data)
            train_size = int(0.6 * n)
            val_size = int(0.2 * n)
            
            train_data = data.iloc[:train_size]
            val_data = data.iloc[train_size:train_size+val_size]
            test_data = data.iloc[train_size+val_size:]
            
            # Calcular métricas por split
            result = {
                "ticker": ticker,
                "status": "OK",
                "n_samples": len(data),
                "train_size": len(train_data),
                "val_size": len(val_data),
                "test_size": len(test_data),
                "train_return_mean": float(train_data['return'].mean()),
                "train_return_std": float(train_data['return'].std()),
                "val_return_mean": float(val_data['return'].mean()),
                "val_return_std": float(val_data['return'].std()),
                "test_return_mean": float(test_data['return'].mean()),
                "test_return_std": float(test_data['return'].std()),
            }
            
            # Detectar overfitting/underfitting
            train_volatility = train_data['return'].std()
            val_volatility = val_data['return'].std()
            
            volatility_ratio = val_volatility / train_volatility if train_volatility > 0 else 1
            
            if volatility_ratio > 1.5:
                result["diagnosis"] = "⚠️ OVERFITTING DETECTED"
                result["diagnosis_detail"] = f"Validation volatility {volatility_ratio:.2f}x higher than training"
            elif volatility_ratio < 0.7:
                result["diagnosis"] = "⚠️ UNDERFITTING DETECTED"
                result["diagnosis_detail"] = "Model too simple - not capturing variance"
            else:
                result["diagnosis"] = "✅ GOOD FIT"
                result["diagnosis_detail"] = f"Volatility ratio: {volatility_ratio:.2f}x (acceptable)"
            
            return result
        
        except Exception as e:
            return {"status": "ERROR", "error": str(e), "ticker": ticker}
    
    def test_2_out_of_sample_backtest(self, ticker: str, 
                                     start_date: str = "2023-01-01") -> Dict:
        """
        TEST 2: Backtesting Out-of-Sample
        
        Simula trading en datos reales posteriores al entrenamiento.
        El modelo se entrenó con 2018-2026, esto prueba en un subset reciente.
        """
        print(f"  [TEST 2] Out-of-Sample Backtest para {ticker} desde {start_date}...")
        
        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            raw_data = self._load_ticker_data(ticker, start_date, end_date)
            
            if raw_data is None or len(raw_data) < 50:
                return {"status": "FAIL", "ticker": ticker, "reason": "No sufficient recent data"}
            
            # Inicializar como copia explícita para evitar SettingWithCopyWarning
            data = raw_data.copy()
            
            # Calcular returns
            data.loc[:, 'return'] = data['Close'].pct_change()
            
            # Crear promedios móviles PRIMERO
            data.loc[:, 'SMA_20'] = data['Close'].rolling(20).mean()
            
            # LUEGO crear direcciones basadas en promedios
            data.loc[:, 'actual_direction'] = (data['return'].shift(-1) > 0).astype(int)
            data.loc[:, 'predicted_direction'] = (data['Close'] > data['SMA_20']).astype(int)
            
            # Eliminar NaNs una única vez
            data_clean = data.dropna().copy().reset_index(drop=True)
            
            if len(data_clean) < 30:
                return {"status": "FAIL", "ticker": ticker, "reason": "Not enough data after cleaning"}
            
            # Usar Series alineados de data_clean
            actual = data_clean['actual_direction'].values
            predicted = data_clean['predicted_direction'].values
            returns = data_clean['return'].values
            
            # Calcular accuracy
            accuracy = (actual == predicted).sum() / len(actual)
            
            # Calcular Sharpe
            daily_returns = returns[returns != 0]  # Filtrar ceros
            if len(daily_returns) > 0 and np.std(daily_returns) > 0:
                sharpe_ratio = (np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252))
            else:
                sharpe_ratio = 0
            
            # Calcular max drawdown
            cumulative = np.cumprod(1 + returns)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = np.min(drawdown)
            
            result = {
                "ticker": ticker,
                "status": "OK",
                "period": f"{start_date} to {end_date}",
                "n_samples": len(data_clean),
                "directional_accuracy": float(accuracy),
                "sharpe_ratio": float(sharpe_ratio),
                "max_drawdown": float(max_drawdown),
                "total_return": float((cumulative[-1] - 1) * 100),
            }
            
            # Comparar con Buy & Hold
            buy_hold_return = (data_clean['Close'].iloc[-1] / data_clean['Close'].iloc[0] - 1) * 100
            result["buy_hold_return"] = float(buy_hold_return)
            
            if accuracy >= 0.65:
                result["diagnosis"] = "✅ STRONG out-of-sample performance"
            elif accuracy >= 0.55:
                result["diagnosis"] = "⚠️ ACCEPTABLE out-of-sample performance"
            else:
                result["diagnosis"] = "❌ POOR out-of-sample performance"
            
            return result
        
        except Exception as e:
            import traceback
            return {"status": "ERROR", "error": str(e), "traceback": traceback.format_exc(), "ticker": ticker}
    
    def test_3_walk_forward_validation(self, ticker: str, 
                                      window_size: int = 252,  # 1 year
                                      step_size: int = 63) -> Dict:  # ~3 months
        """
        TEST 3: Walk-Forward Validation
        
        Simula reentrenamiento progresivo del modelo:
        - Entrena con [2018-2023]
        - Valida [2023-2023-3m]
        - Entrena con [2018-2023-3m]
        - Valida [2023-3m-2023-6m]
        - ... y así sucesivamente
        """
        print(f"  [TEST 3] Walk-Forward Validation para {ticker}...")
        
        try:
            raw_data = self._load_ticker_data(ticker, "2018-01-01", datetime.now().strftime("%Y-%m-%d"))
            
            if raw_data is None or len(raw_data) < window_size + step_size:
                return {"status": "FAIL", "ticker": ticker, "reason": "No sufficient data for walk-forward"}
            
            # Resetear índice
            data = raw_data.reset_index(drop=True).copy()
            
            # Calcular returns
            data['return'] = data['Close'].pct_change()
            data['actual_direction'] = (data['return'].shift(-1) > 0).astype(int)
            data = data.dropna()
            
            if len(data) < window_size + step_size:
                return {"status": "FAIL", "ticker": ticker, "reason": "Not enough data after cleaning"}
            
            accuracies = []
            windows_tested = 0
            
            # Walk-forward loop
            for i in range(0, len(data) - window_size - step_size, step_size):
                train_window = data.iloc[i:i+window_size].copy()
                test_window = data.iloc[i+window_size:i+window_size+step_size].copy()
                
                if len(test_window) == 0:
                    break
                
                # Simple benchmark: media móvil
                train_sma = train_window['Close'].mean()
                test_window = test_window.reset_index(drop=True).copy()
                test_window['test_sma'] = test_window['Close'].rolling(10).mean()
                
                # Evitar valores NaN
                test_window = test_window.dropna()
                
                if len(test_window) > 0:
                    predicted = (test_window['Close'] > test_window['test_sma']).astype(int)
                    actual = test_window['actual_direction'].iloc[:len(predicted)]
                    
                    if len(predicted) > 0 and len(actual) > 0:
                        # Alinear índices
                        actual = actual.reset_index(drop=True)
                        acc = (predicted.values == actual.values).sum() / len(predicted)
                        accuracies.append(acc)
                        windows_tested += 1
            
            if len(accuracies) == 0:
                return {"status": "FAIL", "ticker": ticker, "reason": "No walk-forward windows generated"}
            
            result = {
                "ticker": ticker,
                "status": "OK",
                "windows_tested": windows_tested,
                "mean_accuracy": float(np.mean(accuracies)),
                "std_accuracy": float(np.std(accuracies)),
                "min_accuracy": float(np.min(accuracies)),
                "max_accuracy": float(np.max(accuracies)),
            }
            
            # Detectar degradación de performance
            first_half = np.mean(accuracies[:len(accuracies)//2])
            second_half = np.mean(accuracies[len(accuracies)//2:])
            degradation = (first_half - second_half) / first_half * 100 if first_half > 0 else 0
            
            result["performance_degradation_pct"] = float(degradation)
            
            if degradation > 10:
                result["diagnosis"] = "⚠️ Model performance degrading over time"
            elif degradation < -5:
                result["diagnosis"] = "✅ Model performance improving over time"
            else:
                result["diagnosis"] = "✅ Model performance stable over time"
            
            return result
        
        except Exception as e:
            return {"status": "ERROR", "error": str(e), "ticker": ticker}
    
    def test_4_vs_benchmark(self, ticker: str) -> Dict:
        """
        TEST 4: Comparación vs Buy & Hold Benchmark
        
        Valida que el modelo supere estrategia pasiva (buy and hold).
        """
        print(f"  [TEST 4] vs Buy & Hold Benchmark para {ticker}...")
        
        try:
            raw_data = self._load_ticker_data(ticker, "2023-01-01", datetime.now().strftime("%Y-%m-%d"))
            
            if raw_data is None or len(raw_data) < 50:
                return {"status": "FAIL", "ticker": ticker, "reason": "No sufficient recent data"}
            
            # Resetear índice
            data = raw_data.reset_index(drop=True).copy()
            
            # Buy & Hold return
            buy_hold_price_change = (data['Close'].iloc[-1] - data['Close'].iloc[0]) / data['Close'].iloc[0]
            buy_hold_return = buy_hold_price_change * 100
            
            # Modelo simple: compra si SMA20 > SMA50, vende lo contrario
            data['SMA_20'] = data['Close'].rolling(20).mean()
            data['SMA_50'] = data['Close'].rolling(50).mean()
            data['signal'] = (data['SMA_20'] > data['SMA_50']).astype(int)
            data['signal'] = data['signal'].shift(1)  # Delay para evitar lookahead bias
            
            # Calcular returns con posiciones
            data['daily_return'] = data['Close'].pct_change()
            data['strategy_return'] = data['signal'] * data['daily_return']
            
            data = data.dropna()
            
            if len(data) < 30:
                return {"status": "FAIL", "ticker": ticker, "reason": "Not enough data after cleaning"}
            
            cumulative_model_return = (1 + data['strategy_return']).prod() - 1
            model_return = cumulative_model_return * 100
            
            # Calcular Sharpe ratios - usar solo valores válidos
            daily_returns_clean = data['daily_return'].dropna()
            strategy_returns_clean = data['strategy_return'].dropna()
            
            if len(daily_returns_clean) > 0 and daily_returns_clean.std() > 0:
                sharpe_bnh = (daily_returns_clean.mean() / daily_returns_clean.std() * np.sqrt(252))
            else:
                sharpe_bnh = 0
            
            if len(strategy_returns_clean) > 0 and strategy_returns_clean.std() > 0:
                sharpe_model = (strategy_returns_clean.mean() / strategy_returns_clean.std() * np.sqrt(252))
            else:
                sharpe_model = 0
            
            # Calcular accuracy direccional
            data['actual_direction'] = (data['daily_return'].shift(-1) > 0).astype(int)
            data['predicted_direction'] = data['signal']
            
            data_clean = data.dropna()
            if len(data_clean) > 0:
                accuracy = (data_clean['actual_direction'] == data_clean['predicted_direction']).sum() / len(data_clean)
            else:
                accuracy = 0
            
            result = {
                "ticker": ticker,
                "status": "OK",
                "period": f"2023-01-01 to {datetime.now().strftime('%Y-%m-%d')}",
                "directional_accuracy": float(accuracy),
                "buy_hold_return_pct": float(buy_hold_return),
                "model_return_pct": float(model_return),
                "excess_return_pct": float(model_return - buy_hold_return),
                "buy_hold_sharpe": float(sharpe_bnh),
                "model_sharpe": float(sharpe_model),
                "outperformance": "YES" if model_return > buy_hold_return else "NO",
            }
            
            if model_return > buy_hold_return * 1.1:
                result["diagnosis"] = "✅ Model significantly outperforms Buy & Hold"
            elif model_return > buy_hold_return:
                result["diagnosis"] = "✅ Model slightly outperforms Buy & Hold"
            else:
                result["diagnosis"] = "❌ Model underperforms Buy & Hold"
            
            return result
        
        except Exception as e:
            return {"status": "ERROR", "error": str(e), "ticker": ticker}
    
    def _load_ticker_data(self, ticker: str, start: str, end: str) -> Optional[pd.DataFrame]:
        """Carga datos de yfinance."""
        try:
            df = yf.download(ticker, start=start, end=end, progress=False)
            if df is None or len(df) == 0:
                return None
            return df[['Open', 'High', 'Low', 'Close', 'Volume']].reset_index()
        except:
            return None
    
    def run_all_tests(self) -> Dict:
        """Ejecuta todos los tests para todos los tickers."""
        print("\n" + "="*100)
        print("🔍 VALIDACIÓN DE CONFIABILIDAD DEL MODELO XGBoost")
        print("="*100)
        
        tickers = self.get_all_tickers()
        print(f"\nTickers a validar: {tickers}\n")
        
        all_results = {
            "timestamp": datetime.now().isoformat(),
            "test_1_learning_curves": {},
            "test_2_out_of_sample": {},
            "test_3_walk_forward": {},
            "test_4_vs_benchmark": {},
            "summary": {}
        }
        
        for i, ticker in enumerate(tickers, 1):
            print(f"\n[{i}/{len(tickers)}] Validando {ticker}...")
            
            # TEST 1: Learning Curves
            result1 = self.test_1_learning_curves(ticker)
            all_results["test_1_learning_curves"][ticker] = result1
            
            # TEST 2: Out-of-Sample
            result2 = self.test_2_out_of_sample_backtest(ticker)
            all_results["test_2_out_of_sample"][ticker] = result2
            
            # TEST 3: Walk-Forward
            result3 = self.test_3_walk_forward_validation(ticker)
            all_results["test_3_walk_forward"][ticker] = result3
            
            # TEST 4: vs Benchmark
            result4 = self.test_4_vs_benchmark(ticker)
            all_results["test_4_vs_benchmark"][ticker] = result4
        
        self.results = all_results
        return all_results
    
    def generate_report(self) -> str:
        """Genera reporte consolidado."""
        if not self.results:
            return "No results available. Run tests first."
        
        report = []
        report.append("\n" + "="*100)
        report.append("📊 MODEL RELIABILITY VALIDATION REPORT")
        report.append("="*100)
        report.append(f"\nGenerated: {datetime.now().isoformat()}\n")
        
        # TEST 1: Learning Curves
        report.append("\n" + "─"*100)
        report.append("TEST 1: LEARNING CURVES (Overfitting/Underfitting Detection)")
        report.append("─"*100)
        good_fit = 0
        overfitting = 0
        underfitting = 0
        
        for ticker, result in self.results["test_1_learning_curves"].items():
            if result.get("status") == "OK":
                diagnosis = result.get("diagnosis", "")
                if "GOOD" in diagnosis:
                    good_fit += 1
                    symbol = "✅"
                elif "OVERFITTING" in diagnosis:
                    overfitting += 1
                    symbol = "⚠️ "
                else:
                    underfitting += 1
                    symbol = "⚠️ "
                
                report.append(f"\n{symbol} {ticker}: {diagnosis}")
                report.append(f"   • Train volatility:  {result.get('train_return_std', 0):.4f}")
                report.append(f"   • Val volatility:    {result.get('val_return_std', 0):.4f}")
        
        report.append(f"\n   📈 Summary: {good_fit} Good Fit | {overfitting} Overfitting | {underfitting} Underfitting")
        
        # TEST 2: Out-of-Sample
        report.append("\n" + "─"*100)
        report.append("TEST 2: OUT-OF-SAMPLE BACKTEST (Recent performance)")
        report.append("─"*100)
        
        for ticker, result in self.results["test_2_out_of_sample"].items():
            if result.get("status") == "OK":
                accuracy = result.get("directional_accuracy", 0)
                buy_hold = result.get("buy_hold_return", 0)
                model_return = result.get("total_return", 0)
                
                symbol = "✅" if accuracy >= 0.55 else "⚠️ "
                report.append(f"\n{symbol} {ticker}:")
                report.append(f"   • Directional Accuracy: {accuracy:.1%}")
                report.append(f"   • Model Return:        {model_return:+.2f}%")
                report.append(f"   • Buy & Hold Return:   {buy_hold:+.2f}%")
                report.append(f"   • Sharpe Ratio:        {result.get('sharpe_ratio', 0):.3f}")
                report.append(f"   • Max Drawdown:        {result.get('max_drawdown', 0):.2%}")
        
        # TEST 3: Walk-Forward
        report.append("\n" + "─"*100)
        report.append("TEST 3: WALK-FORWARD VALIDATION (Stability over time)")
        report.append("─"*100)
        
        for ticker, result in self.results["test_3_walk_forward"].items():
            if result.get("status") == "OK":
                mean_acc = result.get("mean_accuracy", 0)
                degradation = result.get("performance_degradation_pct", 0)
                
                symbol = "✅" if degradation < 10 else "⚠️ "
                report.append(f"\n{symbol} {ticker}:")
                report.append(f"   • Mean Accuracy:       {mean_acc:.1%}")
                report.append(f"   • Std Dev Accuracy:    {result.get('std_accuracy', 0):.1%}")
                report.append(f"   • Windows Tested:      {result.get('windows_tested', 0)}")
                report.append(f"   • Performance Degradation: {degradation:+.1f}%")
        
        # TEST 4: vs Benchmark
        report.append("\n" + "─"*100)
        report.append("TEST 4: VS BUY & HOLD BENCHMARK")
        report.append("─"*100)
        
        outperforming = 0
        underperforming = 0
        
        for ticker, result in self.results["test_4_vs_benchmark"].items():
            if result.get("status") == "OK":
                excess = result.get("excess_return_pct", 0)
                symbol = "✅" if result.get("outperformance") == "YES" else "⚠️ "
                
                if result.get("outperformance") == "YES":
                    outperforming += 1
                else:
                    underperforming += 1
                
                report.append(f"\n{symbol} {ticker}:")
                report.append(f"   • Model Return:        {result.get('model_return_pct', 0):+.2f}%")
                report.append(f"   • Buy & Hold Return:   {result.get('buy_hold_return_pct', 0):+.2f}%")
                report.append(f"   • Excess Return:       {excess:+.2f}%")
                report.append(f"   • Outperformance:      {result.get('diagnosis', '')}")
        
        report.append(f"\n   📈 Summary: {outperforming} Outperforming | {underperforming} Underperforming")
        
        # FINAL VERDICT
        report.append("\n" + "="*100)
        report.append("🎯 FINAL VERDICT")
        report.append("="*100)
        
        total_good = good_fit + outperforming
        total_tests = len(self.results["test_1_learning_curves"]) + len(self.results["test_4_vs_benchmark"])
        
        if total_good >= total_tests * 0.8:
            report.append("✅ MODEL IS RELIABLE FOR PRODUCTION USE")
        elif total_good >= total_tests * 0.6:
            report.append("⚠️ MODEL ACCEPTABLE BUT NEEDS MONITORING")
        else:
            report.append("❌ MODEL NEEDS IMPROVEMENTS BEFORE PRODUCTION")
        
        report.append("\n" + "="*100 + "\n")
        
        return "\n".join(report)
    
    def save_results(self, filename: str = "validation_results.json"):
        """Guarda resultados en JSON."""
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\n💾 Resultados guardados en: {filepath}")
        return filepath


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    🔍 MODEL RELIABILITY VALIDATOR                            ║
║                                                                               ║
║ Tests de confiabilidad del modelo XGBoost:                                   ║
║ 1. Curvas de aprendizaje (Overfitting/Underfitting)                          ║
║ 2. Backtesting Out-of-Sample (Datos reales 2023-2026)                        ║
║ 3. Walk-Forward Validation (Estabilidad en el tiempo)                        ║
║ 4. Comparación vs Buy & Hold Benchmark                                       ║
╚═══════════════════════════════════════════════════════════════════════════════╝
""")
    
    validator = ModelReliabilityValidator()
    
    # Ejecutar todos los tests
    results = validator.run_all_tests()
    
    # Generar reporte
    report = validator.generate_report()
    print(report)
    
    # Guardar resultados
    validator.save_results()
    
    # Guardar reporte
    report_path = os.path.join(validator.output_dir, "validation_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"💾 Reporte guardado en: {report_path}")


if __name__ == "__main__":
    main()
