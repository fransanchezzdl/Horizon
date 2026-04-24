"""
Utilidades de evaluación robusta de modelos para problemas desbalanceados.

Incluye:
- Cálculo de métricas especializadas (balanced accuracy, macro F1, etc)
- Generación de reportes de evaluación
- Comparativas sin/con sentimiento (ablation study)
- Trazabilidad de predicciones
"""

import numpy as np
import pandas as pd
from sklearn.metrics import (
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix,
    classification_report,
)
from typing import Dict, Tuple, Optional
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ModelEvaluator:
    """Evaluador de modelos con métricas robustas para desbalance."""
    
    @staticmethod
    def compute_robust_metrics(y_true, y_pred, y_proba=None, dataset_name: str = "test") -> Dict:
        """
        Calcula un conjunto comprehensive de métricas para evaluation.
        
        Args:
            y_true: Labels verdaderos
            y_pred: Predicciones (class predictions)
            y_proba: Probabilidades (opcional, para ROC-AUC)
            dataset_name: Nombre del dataset (train/val/test)
        
        Returns:
            Dict con todas las métricas
        """
        # Métricas básicas
        accuracy = float(np.mean(y_pred == y_true))
        
        # Métricas robustas
        balanced_acc = float(balanced_accuracy_score(y_true, y_pred))
        macro_f1 = float(f1_score(y_true, y_pred, average='macro', zero_division=0))
        weighted_f1 = float(f1_score(y_true, y_pred, average='weighted', zero_division=0))
        
        # Precision y recall por clase
        class_report = classification_report(y_true, y_pred, output_dict=True, zero_division=0)
        
        # Matriz de confusión
        cm = confusion_matrix(y_true, y_pred)
        
        # Para binario
        if len(np.unique(y_true)) == 2:
            tn, fp, fn, tp = cm.ravel()
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
            sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            
            metrics = {
                "accuracy": accuracy,
                "balanced_accuracy": balanced_acc,
                "macro_f1": macro_f1,
                "weighted_f1": weighted_f1,
                "precision": class_report.get("1", {}).get("precision", 0.0),
                "recall": class_report.get("1", {}).get("recall", 0.0),
                "f1_positive": class_report.get("1", {}).get("f1-score", 0.0),
                "sensitivity": sensitivity,
                "specificity": specificity,
                "tp": int(tp),
                "tn": int(tn),
                "fp": int(fp),
                "fn": int(fn),
                "confusion_matrix": {
                    "tp": int(tp),
                    "tn": int(tn),
                    "fp": int(fp),
                    "fn": int(fn),
                },
            }
        else:
            metrics = {
                "accuracy": accuracy,
                "balanced_accuracy": balanced_acc,
                "macro_f1": macro_f1,
                "weighted_f1": weighted_f1,
                "class_report": class_report,
                "confusion_matrix": cm.tolist(),
            }
        
        # Distribución de predicciones
        unique_preds, counts = np.unique(y_pred, return_counts=True)
        pred_dist = {int(label): int(count) for label, count in zip(unique_preds, counts)}
        metrics["prediction_distribution"] = pred_dist
        
        # Distribución de labels verdaderos
        unique_labels, label_counts = np.unique(y_true, return_counts=True)
        label_dist = {int(label): int(count) for label, count in zip(unique_labels, label_counts)}
        metrics["true_label_distribution"] = label_dist
        
        metrics["dataset_name"] = dataset_name
        metrics["n_samples"] = len(y_true)
        
        return metrics
    
    @staticmethod
    def generate_evaluation_report(
        metrics_train: Dict,
        metrics_val: Dict,
        metrics_test: Dict,
        ticker: str,
        model_name: str = "XGBoost",
        comparison_dict: Optional[Dict] = None,
    ) -> str:
        """
        Genera un reporte formateado de evaluación.
        
        Args:
            metrics_train/val/test: Dicts de métricas por dataset
            ticker: Símbolo del activo
            model_name: Nombre del modelo
            comparison_dict: Si viene de ablation, incluir comparación
        
        Returns:
            String formateado con el reporte
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""
{'='*80}
EVALUATION REPORT: {ticker} - {model_name}
{'='*80}
Generated: {now}

📊 METRICS SUMMARY
{'-'*80}

Dataset         | Accuracy | Bal.Acc | Macro F1 | Weighted F1 | Samples
{'-'*80}
TRAIN           | {metrics_train.get('accuracy', 0):.1%}      | {metrics_train.get('balanced_accuracy', 0):.1%}     | {metrics_train.get('macro_f1', 0):.1%}     | {metrics_train.get('weighted_f1', 0):.1%}      | {metrics_train.get('n_samples', 0)}
VALIDATION      | {metrics_val.get('accuracy', 0):.1%}      | {metrics_val.get('balanced_accuracy', 0):.1%}     | {metrics_val.get('macro_f1', 0):.1%}     | {metrics_val.get('weighted_f1', 0):.1%}      | {metrics_val.get('n_samples', 0)}
TEST            | {metrics_test.get('accuracy', 0):.1%}      | {metrics_test.get('balanced_accuracy', 0):.1%}     | {metrics_test.get('macro_f1', 0):.1%}     | {metrics_test.get('weighted_f1', 0):.1%}      | {metrics_test.get('n_samples', 0)}

⚠️  PRIMARY METRIC: Balanced Accuracy (handles class imbalance)

🔍 TEST SET DETAILED ANALYSIS
{'-'*80}
Accuracy (basic):       {metrics_test.get('accuracy', 0):.1%}
Balanced Accuracy:      {metrics_test.get('balanced_accuracy', 0):.1%} ⭐
Macro F1 Score:         {metrics_test.get('macro_f1', 0):.1%}
Weighted F1 Score:      {metrics_test.get('weighted_f1', 0):.1%}

Precision (Positive):   {metrics_test.get('precision', 0):.1%}
Recall (Positive):      {metrics_test.get('recall', 0):.1%}
F1 (Positive):          {metrics_test.get('f1_positive', 0):.1%}

Sensitivity (TPR):      {metrics_test.get('sensitivity', 0):.1%}
Specificity (TNR):      {metrics_test.get('specificity', 0):.1%}

🎯 CONFUSION MATRIX (Test Set)
{'-'*80}
                Predicted Negative | Predicted Positive
Actual Negative | {metrics_test.get('confusion_matrix', {}).get('tn', 0):>5d}              | {metrics_test.get('confusion_matrix', {}).get('fp', 0):>5d}
Actual Positive | {metrics_test.get('confusion_matrix', {}).get('fn', 0):>5d}              | {metrics_test.get('confusion_matrix', {}).get('tp', 0):>5d}

📈 PREDICTION DISTRIBUTION (Test Set)
{'-'*80}
"""
        
        if 'prediction_distribution' in metrics_test:
            pred_dist = metrics_test['prediction_distribution']
            for label, count in sorted(pred_dist.items()):
                report += f"Class {label}: {count:>5d} predictions ({count/metrics_test.get('n_samples', 1)*100:.1f}%)\n"
        
        report += f"\n✓ LABEL DISTRIBUTION (Test Set)\n{'-'*80}\n"
        if 'true_label_distribution' in metrics_test:
            label_dist = metrics_test['true_label_distribution']
            for label, count in sorted(label_dist.items()):
                report += f"Class {label}: {count:>5d} samples  ({count/metrics_test.get('n_samples', 1)*100:.1f}%)\n"
        
        # Comparación (ablation study)
        if comparison_dict:
            report += f"\n🔬 ABLATION STUDY (Sentiment Impact)\n{'-'*80}\n"
            for key, value in comparison_dict.items():
                report += f"{key}:\n"
                if isinstance(value, dict):
                    for subkey, subval in value.items():
                        report += f"  {subkey:15s}: {subval}\n"
                else:
                    report += f"  {value}\n"
        
        report += f"\n{'='*80}\n"
        
        return report
    
    @staticmethod
    def create_ablation_study(
        results_without_sentiment: Dict,
        results_with_sentiment: Dict,
        ticker: str
    ) -> Dict:
        """
        Compara resultados con y sin sentimiento.
        
        Args:
            results_without_sentiment: Métricas sin sentimiento
            results_with_sentiment: Métricas con sentimiento
            ticker: Símbolo
        
        Returns:
            Dict con comparación y recomendaciones
        """
        comparison = {
            "ticker": ticker,
            "timestamp": datetime.now().isoformat(),
            "without_sentiment": results_without_sentiment,
            "with_sentiment": results_with_sentiment,
            "improvement": {
                "balanced_accuracy_delta": (
                    results_with_sentiment.get("balanced_accuracy", 0) -
                    results_without_sentiment.get("balanced_accuracy", 0)
                ),
                "macro_f1_delta": (
                    results_with_sentiment.get("macro_f1", 0) -
                    results_without_sentiment.get("macro_f1", 0)
                ),
            },
            "recommendation": ""
        }
        
        # Recomendación basada en mejora
        ba_improvement = comparison["improvement"]["balanced_accuracy_delta"]
        if ba_improvement > 0.02:  # Más de 2% de mejora
            comparison["recommendation"] = "✅ SENTIMENT HELPS - Use sentiment features"
        elif ba_improvement < -0.02:  # Más de 2% de empeoramiento
            comparison["recommendation"] = "⚠️  SENTIMENT HURTS - Remove sentiment features"
        else:
            comparison["recommendation"] = "➖ NEUTRAL - Sentiment has minimal impact"
        
        return comparison


def create_baseline_always_up() -> Dict:
    """
    Crea baseline trivial: "siempre ALCISTA".
    
    Returns:
        Dict con métricas del baseline
    """
    return {
        "name": "Baseline: Always ALCISTA",
        "description": "Todas las predicciones son 1 (ALCISTA)",
        "accuracy_formula": "% de muestras positivas en test",
        "note": "Sirve para comparar si el modelo realmente aprende"
    }
