"""
Experimento rapido: etiquetado binario sin clase LATERAL.

Objetivo: determinar si el problema del XGBoost actual (BA ~= 0.338, baseline aleatorio 0.333)
es el etiquetado ternario o algo mas profundo (features/regimen/leakage).

Diseno:
    - Reutiliza el pipeline de features existente (prepare_data_multi_window + build_xgb_features)
    - UNICO cambio: labels = sign(retorno) -> 1 si sube, 0 si baja (sin LATERAL)
    - Mismo split temporal, mismos hiperparametros, mismo seed
    - Compara contra la BA ternaria reportada en saved_models/<ticker>_report.json

Tickers: AAPL (stable, mid), TSLA (volatile, mid), NVDA (volatile, peor).

Salida: backend/models/saved_models/experiments/binary/<ticker>_report.json
(no sobrescribe los modelos baseline).

Interpretacion:
    - Random baseline binario = 0.500
    - Random baseline ternario = 0.333
    - "Gap sobre random": BA - baseline. Mide senal real.
    - Si gap_binario > gap_ternario -> el problema ERA el etiquetado -> seguir con el plan
    - Si gap_binario <= gap_ternario -> problema es features/regimen -> rollback y pivotar

Uso:
    python -m tests.experiment_binary_labels
"""

import json
import os
import time
from datetime import datetime
from typing import Dict

import numpy as np

from backend.models.config import (
    ENSEMBLE_VARIATIONS,
    SAVED_MODELS_DIR,
    XGBOOST_STABLE_CONFIG,
    XGBOOST_VOLATILE_CONFIG,
    get_asset_type,
    get_config,
    get_feature_cols,
)
from backend.models.data_pipeline import prepare_data_multi_window

EXPERIMENT_DIR = os.path.join(SAVED_MODELS_DIR, "experiments", "binary")
TICKERS_EXPERIMENT = ["AAPL", "TSLA", "NVDA"]
SEED = 42


def build_xgb_features(X_tensor) -> np.ndarray:
    """Replica build_xgb_features() de xgboost_model.py para mantener equivalencia."""
    X = X_tensor.numpy() if hasattr(X_tensor, "numpy") else np.array(X_tensor)
    W = X.shape[1]
    sub_windows = [max(2, W // 6), W // 2, W]
    parts = []
    for sw in sub_windows:
        sl = X[:, -sw:, :]
        parts.extend([
            sl[:, -1, :],
            sl.mean(axis=1),
            sl.std(axis=1),
            sl[:, -1, :] - sl[:, 0, :],
        ])
    return np.concatenate(parts, axis=1)


def _get_returns(data: dict, split_key: str) -> np.ndarray:
    val = data.get(f"y_{split_key}_returns", None)
    if val is None:
        val = data[f"y_{split_key}"]
    arr = val.numpy() if hasattr(val, "numpy") else np.array(val)
    return arr.ravel()


def run_binary_experiment(ticker: str) -> Dict:
    """Entrena XGBoost binario para un ticker y devuelve metricas."""
    from sklearn.metrics import (
        balanced_accuracy_score,
        f1_score,
        confusion_matrix,
        roc_auc_score,
    )
    from xgboost import XGBClassifier

    config = get_config(ticker)
    asset_type = get_asset_type(ticker)
    variations = ENSEMBLE_VARIATIONS[asset_type]
    feature_cols = get_feature_cols(ticker)

    unique_window_sizes = list(set(v["window_size"] for v in variations))
    all_data = prepare_data_multi_window(ticker, config, unique_window_sizes)
    max_ws = max(unique_window_sizes)
    data = all_data[max_ws]

    X_train = build_xgb_features(data["X_train"])
    X_val = build_xgb_features(data["X_val"])
    X_test = build_xgb_features(data["X_test"])

    r_train = _get_returns(data, "train")
    r_val = _get_returns(data, "val")
    r_test = _get_returns(data, "test")

    # Etiquetado binario: signo puro del retorno.
    # Descarta muestras con retorno exactamente 0 (muy raras).
    def to_binary(r: np.ndarray):
        mask = r != 0.0
        return (r[mask] > 0).astype(int), mask

    y_train, m_train = to_binary(r_train)
    y_val, m_val = to_binary(r_val)
    y_test, m_test = to_binary(r_test)
    X_train = X_train[m_train]
    X_val = X_val[m_val]
    X_test = X_test[m_test]

    train_pos = float(np.mean(y_train == 1))
    val_pos = float(np.mean(y_val == 1))
    test_pos = float(np.mean(y_test == 1))
    print(f"[{ticker}] Binary class balance  train={train_pos:.2%} UP, val={val_pos:.2%}, test={test_pos:.2%}")

    # Sample weights inversamente proporcional a la frecuencia en train.
    counts = np.bincount(y_train, minlength=2)
    sample_weights = np.ones(len(y_train), dtype=float)
    for cls in range(2):
        if counts[cls] > 0:
            sample_weights[y_train == cls] = len(y_train) / (2.0 * counts[cls])

    cfg = XGBOOST_VOLATILE_CONFIG if asset_type == "volatile" else XGBOOST_STABLE_CONFIG

    model = XGBClassifier(
        n_estimators=cfg["n_estimators"],
        max_depth=cfg["max_depth"],
        learning_rate=cfg["learning_rate"],
        subsample=cfg["subsample"],
        colsample_bytree=cfg["colsample_bytree"],
        min_child_weight=cfg.get("min_child_weight", 1.0),
        gamma=cfg.get("gamma", 0.0),
        early_stopping_rounds=cfg["early_stopping_rounds"],
        objective="binary:logistic",
        eval_metric="logloss",
        verbosity=0,
        random_state=SEED,
    )

    model.fit(
        X_train,
        y_train,
        sample_weight=sample_weights,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    balanced_acc = float(balanced_accuracy_score(y_test, y_pred))
    macro_f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
    dir_acc = float(np.mean(y_pred == y_test))
    try:
        auc = float(roc_auc_score(y_test, y_proba))
    except ValueError:
        auc = float("nan")

    cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
    tn, fp, fn, tp = (int(v) for v in cm.ravel())
    precision_up = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall_up = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    confidence_score = float(np.mean(np.maximum(y_proba, 1 - y_proba)))

    # Top features (sobre el bloque "last" de build_xgb_features, 1er subbloque)
    importances = model.feature_importances_
    n_features = len(feature_cols)
    last_importances = importances[:n_features]
    top_indices = np.argsort(last_importances)[::-1][:10]
    feature_importance = {
        feature_cols[i]: round(float(last_importances[i]), 6) for i in top_indices
    }

    return {
        "ticker": ticker,
        "asset_type": asset_type,
        "seed": SEED,
        "experiment": "binary_sign_labels",
        "trained_at": datetime.utcnow().isoformat() + "Z",
        "n_samples": {
            "train": int(len(y_train)),
            "val": int(len(y_val)),
            "test": int(len(y_test)),
        },
        "class_balance": {
            "train_up_pct": round(train_pos * 100, 2),
            "val_up_pct": round(val_pos * 100, 2),
            "test_up_pct": round(test_pos * 100, 2),
        },
        "metrics": {
            "balanced_accuracy": balanced_acc,
            "macro_f1": macro_f1,
            "directional_accuracy": dir_acc,
            "auc_roc": auc,
            "precision_up": precision_up,
            "recall_up": recall_up,
            "confidence_score": confidence_score,
        },
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "feature_importance_top10": feature_importance,
        "hyperparameters": cfg,
    }


def load_baseline_metric(ticker: str) -> dict:
    """Lee el report ternario baseline para comparar."""
    path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_report.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        r = json.load(f)
    xgb = r.get("xgboost_metrics", {})
    return {
        "balanced_accuracy": xgb.get("xgb_balanced_accuracy"),
        "macro_f1": xgb.get("xgb_macro_f1"),
        "directional_accuracy": xgb.get("xgb_directional_accuracy"),
        "confidence_score": xgb.get("xgb_confidence_score"),
        "recall_up": xgb.get("xgb_recall_up"),
    }


def main() -> None:
    os.makedirs(EXPERIMENT_DIR, exist_ok=True)

    print("=" * 80)
    print("EXPERIMENTO: XGBoost con etiquetado BINARIO (sign del retorno)")
    print("=" * 80)
    print(f"Checkpoint git: checkpoint/pre-binary-experiment")
    print(f"Salida:         {EXPERIMENT_DIR}")
    print(f"Tickers:        {TICKERS_EXPERIMENT}")
    print()

    results = []
    t0 = time.time()

    for ticker in TICKERS_EXPERIMENT:
        print("-" * 80)
        print(f"[{ticker}]")
        print("-" * 80)
        try:
            rep = run_binary_experiment(ticker)
            out_path = os.path.join(EXPERIMENT_DIR, f"{ticker}_report.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(rep, f, indent=2)
            print(f"[OK] Report guardado: {out_path}")
            results.append(rep)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[ERROR] {ticker}: {e}")
            results.append({"ticker": ticker, "error": str(e)})

    # --- Comparativa final -------------------------------------------------
    print()
    print("=" * 80)
    print("COMPARATIVA: binario (este experimento) vs ternario (baseline)")
    print("=" * 80)
    print(
        f"{'Ticker':<8}{'BA_bin':>10}{'BA_ter':>10}{'gap_bin':>10}{'gap_ter':>10}{'AUC':>8}{'Rec_UP_b':>10}{'Rec_UP_t':>10}"
    )
    print("-" * 80)

    summary = []
    for r in results:
        if "error" in r:
            print(f"{r['ticker']:<8} ERROR: {r['error']}")
            continue
        ticker = r["ticker"]
        ba_bin = r["metrics"]["balanced_accuracy"]
        auc = r["metrics"]["auc_roc"]
        recall_bin = r["metrics"]["recall_up"]
        base = load_baseline_metric(ticker)
        ba_ter = base.get("balanced_accuracy", float("nan"))
        recall_ter = base.get("recall_up", float("nan"))

        gap_bin = ba_bin - 0.50
        gap_ter = (ba_ter - 0.333) if ba_ter is not None else float("nan")

        print(
            f"{ticker:<8}{ba_bin:>10.3f}{ba_ter:>10.3f}{gap_bin:>+10.3f}{gap_ter:>+10.3f}"
            f"{auc:>8.3f}{recall_bin:>10.3f}{recall_ter:>10.3f}"
        )
        summary.append({"ticker": ticker, "gap_bin": gap_bin, "gap_ter": gap_ter})

    print("-" * 80)
    if summary:
        wins = sum(1 for s in summary if s["gap_bin"] > s["gap_ter"])
        mean_gap_bin = np.mean([s["gap_bin"] for s in summary])
        mean_gap_ter = np.mean([s["gap_ter"] for s in summary])
        print(f"Tickers donde binario gana en 'gap sobre random': {wins}/{len(summary)}")
        print(f"Gap medio binario:  {mean_gap_bin:+.3f}")
        print(f"Gap medio ternario: {mean_gap_ter:+.3f}")
        print()
        if mean_gap_bin > mean_gap_ter + 0.02:
            print(">>> VEREDICTO: el etiquetado ternario era parte del problema. Merece seguir por aqui.")
        elif mean_gap_bin < mean_gap_ter:
            print(">>> VEREDICTO: binario no mejora. Problema probable: features / regimen / leakage.")
            print("    Rollback: git reset --hard checkpoint/pre-binary-experiment")
        else:
            print(">>> VEREDICTO: mejora marginal. No concluyente; revisar features antes de invertir mas.")

    print()
    print(f"Tiempo total: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
