"""
Análisis de distribución de clases por ticker
Para identificar desbalanceo y optimizar estrategia de entrenamiento en FASE 2
"""

import numpy as np
import pandas as pd
from backend.models.data_pipeline import prepare_data
from backend.models.config import Config, TICKERS
import warnings

warnings.filterwarnings('ignore')

def analyze_class_distribution(ticker):
    """Analiza distribución de clases (BAJISTA/LATERAL/ALCISTA) para un ticker"""
    
    try:
        # Preparar datos
        config = Config(ticker=ticker, asset_type="stable" if ticker in TICKERS["stable"] else "volatile")
        X, y, dates = prepare_data(ticker, config)
        
        if X is None or len(y) == 0:
            return None
        
        # Convertir a clases (0=BAJISTA, 1=LATERAL, 2=ALCISTA)
        # El threshold se determina en data_pipeline, aquí usamos 0.01 como default
        threshold = 0.01
        y_classes = np.zeros(len(y), dtype=int)
        y_classes[y > threshold] = 2  # ALCISTA
        y_classes[y < -threshold] = 0  # BAJISTA
        # El resto son LATERAL (1)
        
        # Contar distribución
        unique, counts = np.unique(y_classes, dtype=int, return_counts=True)
        distribution = dict(zip(unique, counts))
        
        total = len(y_classes)
        percentages = {k: (v / total * 100) for k, v in distribution.items()}
        
        # Relatype de desbalanceo (ratio max/min)
        class_counts = [distribution.get(i, 0) for i in range(3)]
        imbalance_ratio = max(class_counts) / (min([c for c in class_counts if c > 0]) + 1e-6)
        
        return {
            'ticker': ticker,
            'asset_type': 'stable' if ticker in TICKERS["stable"] else 'volatile',
            'total_samples': total,
            'class_0_bajista': class_counts[0],
            'class_1_lateral': class_counts[1],
            'class_2_alcista': class_counts[2],
            'pct_0': percentages.get(0, 0),
            'pct_1': percentages.get(1, 0),
            'pct_2': percentages.get(2, 0),
            'imbalance_ratio': imbalance_ratio,
            'majority_class': np.argmax(class_counts)
        }
    except Exception as e:
        print(f"Error analizando {ticker}: {e}")
        return None

def main():
    print("=" * 100)
    print("ANÁLISIS DE DISTRIBUCIÓN DE CLASES - TODOS LOS TICKERS")
    print("=" * 100)
    
    all_tickers = TICKERS["stable"] + TICKERS["volatile"]
    results = []
    
    for ticker in all_tickers:
        print(f"\nAnalizando {ticker}...", end=' ')
        result = analyze_class_distribution(ticker)
        if result:
            results.append(result)
            print(f"✓ OK")
            print(f"  - Total samples: {result['total_samples']}")
            print(f"  - BAJISTA: {result['class_0_bajista']:4d} ({result['pct_0']:6.2f}%)")
            print(f"  - LATERAL: {result['class_1_lateral']:4d} ({result['pct_1']:6.2f}%)")
            print(f"  - ALCISTA: {result['class_2_alcista']:4d} ({result['pct_2']:6.2f}%)")
            print(f"  - Imbalance Ratio: {result['imbalance_ratio']:.2f}x")
        else:
            print("❌ ERROR")
    
    # Crear dataframe para análisis
    df_results = pd.DataFrame(results)
    
    print("\n" + "=" * 100)
    print("RESUMEN GENERAL")
    print("=" * 100)
    print(df_results.to_string(index=False))
    
    print("\n" + "=" * 100)
    print("PROBLEMAS IDENTIFICADOS")
    print("=" * 100)
    
    # Tickers con severo desbalanceo
    severe = df_results[df_results['imbalance_ratio'] > 4]
    if len(severe) > 0:
        print(f"\n⚠️  SEVERA DESBALANCEO (ratio > 4x):")
        for _, row in severe.iterrows():
            print(f"   {row['ticker']:10s}: {row['imbalance_ratio']:.2f}x (LATERAL es {row['pct_1']:.1f}% del dataset)")
    
    # Tickers con desbalanceo moderado
    moderate = df_results[(df_results['imbalance_ratio'] > 2.5) & (df_results['imbalance_ratio'] <= 4)]
    if len(moderate) > 0:
        print(f"\n⚠️  MODERADA DESBALANCEO (ratio 2.5-4x):")
        for _, row in moderate.iterrows():
            print(f"   {row['ticker']:10s}: {row['imbalance_ratio']:.2f}x")
    
    # Análisis por clase mayoritaria
    print(f"\n📊 DISTRIBUCIÓN DE CLASES MAYORITARIAS:")
    majority_counts = df_results['majority_class'].value_counts()
    class_names = {0: 'BAJISTA', 1: 'LATERAL', 2: 'ALCISTA'}
    for class_id, count in majority_counts.items():
        print(f"   {class_names[class_id]}: {count} tickers (mayoritaria en {count})") 
    
    print(f"\n🎯 RECOMENDACIONES PARA FASE 2:")
    print(f"   1. Aplicar SMOTE (rebalanceo sintético) en tickers con ratio > 3x")
    print(f"   2. Considerar clasificación binaria (ALCISTA vs NO-ALCISTA) si ratio > 4x")
    print(f"   3. Usar class_weight='balanced' en entrenamiento")
    print(f"   4. Investigar commodities (GC=F, SI=F) con features especializadas")
    
    return df_results

if __name__ == "__main__":
    df = main()
    df.to_csv('tests/class_distribution_analysis.csv', index=False)
    print(f"\n✓ Resultados guardados en tests/class_distribution_analysis.csv")
