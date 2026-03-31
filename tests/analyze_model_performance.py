"""
Análisis de Overfitting/Underfitting y áreas de mejora

Evaluará:
1. Train vs Test accuracy (detección de overfitting)
2. Feature importance (qué variables más contribuyen)
3. Propuestas de mejora (adicionar sentimiento, técnicas avanzadas, etc)
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import Dict, List

from backend.models.config import get_tickers_from_database, TICKERS, SAVED_MODELS_DIR
from backend.models.data_pipeline import prepare_data_multi_window, get_feature_cols
from backend.models.config import get_config, get_asset_type, ENSEMBLE_VARIATIONS
import xgboost as xgb
import pickle


def analyze_model_performance(ticker: str) -> Dict:
    """
    Analiza un modelo XGBoost para detectar overfitting/underfitting.
    """
    try:
        config = get_config(ticker)
        asset_type = get_asset_type(ticker)
        variations = ENSEMBLE_VARIATIONS[asset_type]
        feature_cols = get_feature_cols(ticker)
        
        # Preparar datos
        unique_window_sizes = list(set(v["window_size"] for v in variations))
        all_data = prepare_data_multi_window(ticker, config, unique_window_sizes)
        max_ws = max(unique_window_sizes)
        data = all_data[max_ws]
        
        # Construir features XGBoost
        def build_xgb_features(X_tensor):
            X = X_tensor.numpy()
            last = X[:, -1, :]
            mean = X.mean(axis=1)
            std = X.std(axis=1)
            trend = X[:, -1, :] - X[:, 0, :]
            return np.concatenate([last, mean, std, trend], axis=1)
        
        X_train = build_xgb_features(data["X_train"])
        X_val = build_xgb_features(data["X_val"])
        X_test = build_xgb_features(data["X_test"])
        
        y_train = (data["y_train"].numpy().ravel() > 0).astype(int)
        y_val = (data["y_val"].numpy().ravel() > 0).astype(int)
        y_test = (data["y_test"].numpy().ravel() > 0).astype(int)
        
        # Cargar modelo XGBoost
        xgb_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost.pkl")
        with open(xgb_path, "rb") as f:
            model = pickle.load(f)
        
        # Calcular accuracy en train, val, test
        train_pred = model.predict(X_train)
        val_pred = model.predict(X_val)
        test_pred = model.predict(X_test)
        
        train_acc = np.mean(train_pred == y_train)
        val_acc = np.mean(val_pred == y_val)
        test_acc = np.mean(test_pred == y_test)
        
        # Feature importance
        importance_dict = dict(zip(
            feature_cols,
            model.feature_importances_[:len(feature_cols)]
        ))
        
        # Detectar overfitting/underfitting
        overfit_gap = train_acc - test_acc
        
        if overfit_gap > 0.15:
            status = "⚠️  OVERFITTING"
            diagnosis = f"Train {train_acc:.1%} >> Test {test_acc:.1%} (gap: {overfit_gap:.1%})"
        elif train_acc < 0.70:
            status = "⚠️  UNDERFITTING"
            diagnosis = f"Accuracy general baja: Train {train_acc:.1%}"
        elif test_acc > 0.80:
            status = "✅ BIEN"
            diagnosis = f"Buen balance: Train {train_acc:.1%}, Test {test_acc:.1%}"
        else:
            status = "🔶 OK"
            diagnosis = f"Aceptable: Train {train_acc:.1%}, Test {test_acc:.1%}"
        
        return {
            "ticker": ticker,
            "train_acc": float(train_acc),
            "val_acc": float(val_acc),
            "test_acc": float(test_acc),
            "overfit_gap": float(overfit_gap),
            "status": status,
            "diagnosis": diagnosis,
            "top_features": sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)[:10],
            "n_features": len(feature_cols),
            "n_samples": {
                "train": len(X_train),
                "val": len(X_val),
                "test": len(X_test)
            }
        }
    
    except Exception as e:
        return {
            "ticker": ticker,
            "error": str(e)
        }


def generate_improvement_proposals(analysis: Dict) -> List[str]:
    """
    Genera propuestas de mejora basadas en el análisis.
    """
    proposals = []
    
    test_acc = analysis.get("test_acc", 0)
    train_acc = analysis.get("train_acc", 0)
    overfit_gap = analysis.get("overfit_gap", 0)
    
    # Propuestas por accuracy
    if test_acc < 0.70:
        proposals.append("📊 Agregar SENTIMENT ANALYSIS (FinBERT) — muchas variables técnicas pero sin contexto de noticias")
        proposals.append("🔍 Feature Engineering avanzado: volatilidad histórica, correlation matrices, patterns")
        proposals.append("⚙️ Tune hyperparameters: max_depth, learning_rate, subsample")
    
    # Propuestas por overfitting
    if overfit_gap > 0.15:
        proposals.append("🛑 Reducir overfitting: aumentar regularization (gamma, lambda en XGBoost)")
        proposals.append("📈 Recolectar más datos: más historía financiera")
        proposals.append("🎲 Early stopping más agresivo: parar antes")
    
    # Si va bien, propuestas de optimización
    if test_acc > 0.80 and overfit_gap < 0.10:
        proposals.append("🚀 Ensemble con otros modelos: Random Forest, LightGBM, Neural Networks")
        proposals.append("📢 Agregar SENTIMENT: puede capturar eventos no en precio histórico")
        proposals.append("🔄 Meta-features: volatilidad relativa, comportamiento sector, correlación con índices")
    
    return proposals


def generate_report() -> None:
    """
    Genera reporte completo de análisis para todos los tickers.
    """
    
    print("\n" + "="*100)
    print("🔬 ANÁLISIS DE OVERFITTING/UNDERFITTING — XGBoost Models")
    print("="*100)
    
    # Cargar tickers
    tickers_config = get_tickers_from_database()
    all_tickers = tickers_config["stable"] + tickers_config["volatile"]
    
    if not all_tickers:
        all_tickers = TICKERS["stable"] + TICKERS["volatile"]
    
    print(f"\n📍 Analizando {len(all_tickers)} modelos...\n")
    
    results = []
    for ticker in all_tickers:
        result = analyze_model_performance(ticker)
        results.append(result)
    
    # ────────────────────────────────────────────────────────────────────────────
    # TABLA 1: Resumen Train vs Test
    # ────────────────────────────────────────────────────────────────────────────
    
    print("┌" + "─"*98 + "┐")
    print("│" + " TABLA 1: TRAIN vs TEST ACCURACY (Detección de Overfitting)".center(98) + "│")
    print("├" + "─"*98 + "┤")
    print(f"│ {'Ticker':<10} │ {'Train':<10} │ {'Val':<10} │ {'Test':<10} │ {'Gap':<10} │ {'Status':<35} │")
    print("├" + "─"*98 + "┤")
    
    successful = [r for r in results if "error" not in r]
    overfitting_risk = []
    underfitting = []
    
    for r in successful:
        ticker = r["ticker"]
        train = r["train_acc"]
        val = r["val_acc"]
        test = r["test_acc"]
        gap = r["overfit_gap"]
        status = r["status"]
        
        print(f"│ {ticker:<10} │ {train:>8.1%}  │ {val:>8.1%}  │ {test:>8.1%}  │ {gap:>8.1%}  │ {status:<35} │")
        
        if gap > 0.15:
            overfitting_risk.append(ticker)
        if test < 0.70:
            underfitting.append(ticker)
    
    print("└" + "─"*98 + "┘")
    
    # ────────────────────────────────────────────────────────────────────────────
    # TABLA 2: Top Features por Ticker
    # ────────────────────────────────────────────────────────────────────────────
    
    print("\n┌" + "─"*98 + "┐")
    print("│" + " TABLA 2: TOP 5 FEATURES (Feature Importance)".center(98) + "│")
    print("├" + "─"*98 + "┤")
    
    for r in successful:
        ticker = r["ticker"]
        top_features = r["top_features"][:5]
        
        features_str = " | ".join([f"{name[:10]}: {imp:.3f}" for name, imp in top_features])
        print(f"│ {ticker:<10} │ {features_str:<86} │")
    
    print("└" + "─"*98 + "┘")
    
    # ────────────────────────────────────────────────────────────────────────────
    # ANÁLISIS POR GRUPO
    # ────────────────────────────────────────────────────────────────────────────
    
    print("\n" + "="*100)
    print("📊 GRUPPUPS DE RIESGO")
    print("="*100)
    
    if overfitting_risk:
        print(f"\n⚠️  OVERFITTING RISK ({len(overfitting_risk)}):")
        for ticker in overfitting_risk:
            r = next(r for r in successful if r["ticker"] == ticker)
            print(f"   • {ticker}: Train {r['train_acc']:.1%} vs Test {r['test_acc']:.1%} (gap: {r['overfit_gap']:.1%})")
    else:
        print(f"\n✅ Sin riesgo de overfitting significativo")
    
    if underfitting:
        print(f"\n⚠️  UNDERFITTING ({len(underfitting)}):")
        for ticker in underfitting:
            r = next(r for r in successful if r["ticker"] == ticker)
            print(f"   • {ticker}: Test accuracy {r['test_acc']:.1%} (baja)")
    else:
        print(f"\n✅ Accuracy general satisfactoria")
    
    # ────────────────────────────────────────────────────────────────────────────
    # PROPUESTAS DE MEJORA GENERALES
    # ────────────────────────────────────────────────────────────────────────────
    
    print("\n" + "="*100)
    print("💡 PROPUESTAS DE MEJORA POR ÁREA")
    print("="*100)
    
    # Análisis general
    avg_test_acc = np.mean([r["test_acc"] for r in successful])
    avg_overfit = np.mean([r["overfit_gap"] for r in successful])
    
    print(f"\n📈 RESUMEN GENERAL:")
    print(f"   • Accuracy promedio: {avg_test_acc:.1%}")
    print(f"   • Overfitting promedio: {avg_overfit:.1%}")
    print(f"   • Tickers evaluados: {len(successful)}/{len(all_tickers)}")
    
    print(f"\n🎯 PROPUESTAS PRINCIPAL ES:")
    
    general_proposals = [
        ("📢 SENTIMENT ANALYSIS (Priority ++)", 
         [
             "Integrar FinBERT para análisis de sentimiento de noticias",
             "Features: positive_count, negative_count, sentiment_score",
             "Puede capturar eventos que no se ven en precios históricos",
             "Expected improvement: +3-5% accuracy"
         ]),
        ("🔍 FEATURE ENGINEERING AVANZADO",
         [
             "Volatilidad histórica (rolling std por período)",
             "Correlation con índices principales (S&P500, etc)",
             "Relative Strength Index (RSI) + MACD mejorados",
             "Patterns: support/resistance levels, trends",
             "Expected improvement: +2-4% accuracy"
         ]),
        ("⚙️ HYPERPARAMETER TUNING",
         [
             "GridSearch sobre max_depth, learning_rate, subsample",
             "Early stopping: variar patience",
             "Class weights: ajustar según imbalance",
             "Expected improvement: +1-2% accuracy"
         ]),
        ("🚀 ENSEMBLE CON OTROS MODELOS",
         [
             "Combinar XGBoost con Random Forest, LightGBM",
             "Meta-learner (stacking) para combinar predicciones",
             "Votación ponderada por performance",
             "Expected improvement: +2-3% accuracy"
         ]),
        ("🛑 REDUCIR OVERFITTING",
         [
             "Aumentar regularization: gamma, lambda",
             "Validación cruzada más estricta",
             "Feature selection: reducir features ruidosas",
             "Expected improvement: mejor generalización"
         ])
    ]
    
    for i, (title, items) in enumerate(general_proposals, 1):
        print(f"\n   {i}. {title}")
        for item in items:
            print(f"      • {item}")
    
    # ────────────────────────────────────────────────────────────────────────────
    # RECOMENDACIÓN POR TICKER
    # ────────────────────────────────────────────────────────────────────────────
    
    print("\n" + "="*100)
    print("🎯 RECOMENDACIONES POR TICKER")
    print("="*100)
    
    for r in successful:
        proposals = generate_improvement_proposals(r)
        if proposals:
            print(f"\n{r['ticker']} ({r['status']}):")
            for proposal in proposals:
                print(f"   • {proposal}")
    
    # ────────────────────────────────────────────────────────────────────────────
    # RESUMEN FINAL
    # ────────────────────────────────────────────────────────────────────────────
    
    print("\n" + "="*100)
    print("📋 PLAN DE ACCIÓN RECOMENDADO")
    print("="*100)
    
    print("""
FASE 1 (Corto plazo - Semana 1):
   1. Agregar SENTIMENT ANALYSIS (FinBERT)
      - Mayor impacto esperado (+3-5% accuracy)
      - Requiere setup de modelo, pero ya hay cache en BD
   
   2. Mejorar Feature Engineering
      - RSI, MACD, Volatilidad histórica
      - Normalmente +2-4% accuracy

FASE 2 (Medio plazo - Semana 2-3):
   3. Hyperparameter Tuning
      - GridSearch sobre params críticos
      - +1-2% accuracy esperado
   
   4. Ensemble avanzado
      - Combinar XGBoost con otros modelos
      - Stacking meta-learner

FASE 3 (Largo plazo):
   5. Regularización avanzada
      - Feature selection automática
      - Cross-validation más estricta

EXPECTATIVA TOTAL: 83.63% → 88-92% accuracy
    """)
    
    print("="*100 + "\n")


if __name__ == "__main__":
    generate_report()
