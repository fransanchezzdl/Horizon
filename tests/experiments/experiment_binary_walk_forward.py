"""
Experimento: Walk-Forward Validation con etiquetado BINARIO (sign del retorno).

Cierra la pregunta pendiente del experimento anterior: el lift positivo del
binario en AAPL (single-split) fue real o un artefacto del fold especifico?

Diseno identico a walk_forward_xgb.py (TimeSeriesSplit 5 folds, mismo
build_xgb_features, mismos hiperparametros por tipo de activo) pero con
labels = 1 si retorno > 0 else 0.

Uso:
    python -m tests.experiment_binary_walk_forward
"""

import json
import os
from datetime import datetime

import numpy as np
from sklearn.metrics import balanced_accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from xgboost import XGBClassifier

from backend.models.config import (
    ENSEMBLE_VARIATIONS,
    SAVED_MODELS_DIR,
    XGBOOST_STABLE_CONFIG,
    XGBOOST_VOLATILE_CONFIG,
    get_asset_type,
    get_config,
)
from backend.models.data_pipeline import prepare_data_multi_window

TICKERS_EXPERIMENT = ["AAPL", "TSLA", "NVDA"]
N_SPLITS = 5
SEED = 42
OUT_DIR = os.path.join(SAVED_MODELS_DIR, "experiments", "walk_forward")
TERNARY_WF_PATH = os.path.join(OUT_DIR, "wf_results.json")
BINARY_WF_PATH = os.path.join(OUT_DIR, "wf_binary_results.json")


def _build_xgb_features(X_tensor) -> np.ndarray:
    X = X_tensor.numpy() if hasattr(X_tensor, "numpy") else np.array(X_tensor)
    W = X.shape[1]
    sub_windows = [max(2, W // 6), W // 2, W]
    parts = []
    for sw in sub_windows:
        sl = X[:, -sw:, :]
        parts.extend([sl[:, -1, :], sl.mean(axis=1), sl.std(axis=1), sl[:, -1, :] - sl[:, 0, :]])
    return np.concatenate(parts, axis=1)


def _sample_weights_binary(y: np.ndarray) -> np.ndarray:
    counts = np.bincount(y, minlength=2)
    w = np.ones(len(y), dtype=float)
    for c in range(2):
        if counts[c] > 0:
            w[y == c] = len(y) / (2.0 * counts[c])
    return w


def walk_forward_binary(ticker: str) -> dict:
    config = get_config(ticker)
    asset_type = get_asset_type(ticker)
    ws = max(v["window_size"] for v in ENSEMBLE_VARIATIONS[asset_type])
    data = prepare_data_multi_window(ticker, config, [ws])[ws]

    X_all = np.concatenate([
        _build_xgb_features(data["X_train"]),
        _build_xgb_features(data["X_val"]),
        _build_xgb_features(data["X_test"]),
    ], axis=0)

    def _rets(k):
        v = data.get(f"y_{k}_returns", data[f"y_{k}"])
        return (v.numpy() if hasattr(v, "numpy") else np.array(v)).ravel()

    returns_all = np.concatenate([_rets("train"), _rets("val"), _rets("test")])

    # Descartar retornos exactamente 0 y binarizar por signo
    nonzero = returns_all != 0.0
    X_all = X_all[nonzero]
    y_all = (returns_all[nonzero] > 0).astype(int)

    cfg = XGBOOST_VOLATILE_CONFIG if asset_type == "volatile" else XGBOOST_STABLE_CONFIG
    tscv = TimeSeriesSplit(n_splits=N_SPLITS)

    ba_folds, f1_folds, auc_folds, conf_folds, up_test_pct = [], [], [], [], []
    fold_details = []

    for fold_idx, (train_idx, test_idx) in enumerate(tscv.split(X_all)):
        X_tr, X_te = X_all[train_idx], X_all[test_idx]
        y_tr, y_te = y_all[train_idx], y_all[test_idx]

        if len(np.unique(y_tr)) < 2 or len(np.unique(y_te)) < 2:
            continue

        val_cut = max(1, int(len(X_tr) * 0.15))
        X_tr_fit, X_val_fit = X_tr[:-val_cut], X_tr[-val_cut:]
        y_tr_fit, y_val_fit = y_tr[:-val_cut], y_tr[-val_cut:]

        sw = _sample_weights_binary(y_tr_fit)

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
            X_tr_fit, y_tr_fit,
            sample_weight=sw,
            eval_set=[(X_val_fit, y_val_fit)],
            verbose=False,
        )

        proba = model.predict_proba(X_te)[:, 1]
        y_pred = (proba >= 0.5).astype(int)
        ba = float(balanced_accuracy_score(y_te, y_pred))
        f1 = float(f1_score(y_te, y_pred, average="macro", zero_division=0))
        try:
            auc = float(roc_auc_score(y_te, proba))
        except ValueError:
            auc = float("nan")
        conf = float(np.mean(np.maximum(proba, 1 - proba)))
        up_pct = float(np.mean(y_te == 1))

        ba_folds.append(ba)
        f1_folds.append(f1)
        auc_folds.append(auc)
        conf_folds.append(conf)
        up_test_pct.append(up_pct)
        fold_details.append({
            "fold": fold_idx + 1,
            "train_size": int(len(X_tr_fit)),
            "test_size": int(len(X_te)),
            "ba": round(ba * 100, 2),
            "f1": round(f1 * 100, 2),
            "auc": round(auc, 3),
            "conf": round(conf * 100, 2),
            "test_up_pct": round(up_pct * 100, 2),
        })

    if not ba_folds:
        return {"ticker": ticker, "error": "No folds completed"}

    return {
        "ticker": ticker,
        "asset_type": asset_type,
        "n_splits_done": len(ba_folds),
        "ba_mean": round(float(np.mean(ba_folds)) * 100, 2),
        "ba_std": round(float(np.std(ba_folds)) * 100, 2),
        "f1_mean": round(float(np.mean(f1_folds)) * 100, 2),
        "auc_mean": round(float(np.mean(auc_folds)), 3),
        "auc_std": round(float(np.std(auc_folds)), 3),
        "conf_mean": round(float(np.mean(conf_folds)) * 100, 2),
        "up_test_mean": round(float(np.mean(up_test_pct)) * 100, 2),
        "ba_folds": [round(x * 100, 2) for x in ba_folds],
        "auc_folds": [round(x, 3) for x in auc_folds],
        "fold_details": fold_details,
        "ran_at": datetime.now().isoformat(),
    }


def load_ternary_wf(ticker: str) -> dict:
    if not os.path.exists(TERNARY_WF_PATH):
        return {}
    with open(TERNARY_WF_PATH, "r", encoding="utf-8") as f:
        r = json.load(f)
    t = r.get("tickers", {}).get(ticker, {})
    return {
        "ba_mean": t.get("ba_mean"),
        "ba_folds": t.get("ba_folds"),
        "conf_mean": t.get("conf_mean"),
    }


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    print("=" * 80)
    print("  WALK-FORWARD VALIDATION — XGBoost BINARIO — {} folds".format(N_SPLITS))
    print("  Tickers: {} | Objetivo: cerrar pregunta sobre labeling".format(TICKERS_EXPERIMENT))
    print("=" * 80)
    print()

    results = {}
    for ticker in TICKERS_EXPERIMENT:
        print("-" * 80)
        print("[{}]".format(ticker))
        print("-" * 80)
        try:
            results[ticker] = walk_forward_binary(ticker)
        except Exception as e:
            import traceback
            traceback.print_exc()
            results[ticker] = {"ticker": ticker, "error": str(e)}

    # Guardar
    with open(BINARY_WF_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "_meta": {
                    "ran_at": datetime.now().isoformat(),
                    "n_splits": N_SPLITS,
                    "labeling": "binary_sign",
                    "method": "TimeSeriesSplit (sklearn)",
                    "tickers": TICKERS_EXPERIMENT,
                },
                "tickers": results,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    print("\nResultados binarios guardados en: {}".format(BINARY_WF_PATH))

    # Comparativa
    print()
    print("=" * 80)
    print("COMPARATIVA WALK-FORWARD: binario vs ternario (lift sobre random)")
    print("=" * 80)
    print()
    hdr = "{:<8}{:>10}{:>10}{:>12}{:>10}{:>12}{:>10}".format(
        "Ticker", "BA_bin", "BA_ter", "lift_bin", "lift_ter", "AUC_bin", "Winner"
    )
    print(hdr)
    print("-" * 80)

    rows = []
    for ticker in TICKERS_EXPERIMENT:
        r = results.get(ticker, {})
        if "error" in r:
            print("{:<8} ERROR: {}".format(ticker, r["error"]))
            continue
        ba_bin = r["ba_mean"]
        auc_bin = r["auc_mean"]
        base = load_ternary_wf(ticker)
        ba_ter = base.get("ba_mean", float("nan"))

        lift_bin = ba_bin - 50.0
        lift_ter = (ba_ter - 33.33) if ba_ter is not None else float("nan")
        winner = "BIN" if lift_bin > lift_ter else ("TER" if lift_ter > lift_bin else "tie")

        print("{:<8}{:>10.2f}{:>10.2f}{:>+12.2f}{:>+10.2f}{:>12.3f}{:>10}".format(
            ticker, ba_bin, ba_ter, lift_bin, lift_ter, auc_bin, winner
        ))
        rows.append({"lift_bin": lift_bin, "lift_ter": lift_ter})

    print("-" * 80)
    if rows:
        mean_lift_bin = np.mean([r["lift_bin"] for r in rows])
        mean_lift_ter = np.mean([r["lift_ter"] for r in rows])
        wins = sum(1 for r in rows if r["lift_bin"] > r["lift_ter"])
        print()
        print("Lift medio binario:  {:+.2f}pp sobre random 50.00%".format(mean_lift_bin))
        print("Lift medio ternario: {:+.2f}pp sobre random 33.33%".format(mean_lift_ter))
        print("Binario gana en {}/{} tickers".format(wins, len(rows)))
        print()
        delta = mean_lift_bin - mean_lift_ter
        if delta > 1.0:
            print(">>> VEREDICTO: BINARIO supera claramente al ternario (+{:.1f}pp).".format(delta))
            print("    Recomendacion: migrar labeling a binario y seguir con features de regimen.")
        elif delta < -1.0:
            print(">>> VEREDICTO: TERNARIO supera al binario ({:.1f}pp).".format(delta))
            print("    Recomendacion: mantener ternario y pasar a features de regimen.")
        else:
            print(">>> VEREDICTO: EMPATE estadistico (diff {:+.2f}pp).".format(delta))
            print("    Recomendacion: elegir por criterio secundario (interpretabilidad, UX).")


if __name__ == "__main__":
    main()
