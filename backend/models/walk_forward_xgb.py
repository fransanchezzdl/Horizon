"""
Walk-Forward Validation para XGBoost (Horizon v5).

Metodología:
    TimeSeriesSplit con n_splits=5: en cada fold, el train crece
    acumulativamente y el test es el periodo siguiente, respetando
    el orden temporal. No hay shuffle, no hay leakage.

    Esta es la validación estándar recomendada para series temporales
    financieras (Marcos López de Prado, "Advances in Financial ML", 2018).

Uso:
    # Un ticker:
    python -m backend.models.walk_forward_xgb --tickers AAPL

    # Todos los tickers:
    python -m backend.models.walk_forward_xgb --all

    # Con output JSON:
    python -m backend.models.walk_forward_xgb --all --output docs/walk_forward_results.json
"""

import argparse
import json
import os
import sys
from datetime import datetime

import numpy as np
from sklearn.metrics import balanced_accuracy_score, f1_score
from sklearn.model_selection import TimeSeriesSplit
from xgboost import XGBClassifier

from .config import (
    ENSEMBLE_VARIATIONS,
    TICKERS,
    XGBOOST_STABLE_CONFIG,
    XGBOOST_VOLATILE_CONFIG,
    get_asset_type,
    get_config,
    get_feature_cols,
)
from .data_pipeline import prepare_data_multi_window
from .xgboost_model import _load_frozen_thresholds

N_SPLITS = 5  # folds walk-forward
RANDOM_STATE = 42


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_xgb_features(X_tensor) -> np.ndarray:
    """
    Convierte tensor [n, window, features] en matriz tabular [n, 12*features].

    Agrega [last, mean, std, trend] sobre 3 sub-ventanas temporales:
      - corta  : últimos W//6 pasos  (ej. 5d  para stable, 10d para volatile)
      - media  : últimos W//2 pasos  (ej. 15d para stable, 30d para volatile)
      - completa: ventana entera W   (ej. 30d para stable, 60d para volatile)

    Debe ser idéntico a build_xgb_features en xgboost_model.py
    y a _build_xgb_features en prediction_log_service.py.
    """
    X = X_tensor.numpy() if hasattr(X_tensor, "numpy") else np.array(X_tensor)
    W = X.shape[1]
    sub_windows = [max(2, W // 6), W // 2, W]
    parts = []
    for sw in sub_windows:
        sl = X[:, -sw:, :]
        parts.extend([sl[:, -1, :], sl.mean(axis=1), sl.std(axis=1), sl[:, -1, :] - sl[:, 0, :]])
    return np.concatenate(parts, axis=1)


def _returns_to_classes(returns: np.ndarray, dn: float, up: float) -> np.ndarray:
    cls = np.ones(len(returns), dtype=int)
    cls[returns <= dn] = 0
    cls[returns >= up] = 2
    return cls


def _sample_weights(y: np.ndarray) -> np.ndarray:
    counts = np.bincount(y, minlength=3)
    w = np.ones(len(y), dtype=float)
    for c in range(3):
        if counts[c] > 0:
            w[y == c] = len(y) / (3.0 * counts[c])
    return w


# ── Núcleo: walk-forward para un ticker ───────────────────────────────────────

def walk_forward_ticker(ticker: str, n_splits: int = N_SPLITS) -> dict:
    """
    Ejecuta walk-forward validation sobre un ticker.

    Returns dict con:
        ba_folds, f1_folds, conf_folds  — listas de métricas por fold
        ba_mean, ba_std, f1_mean, f1_std, conf_mean
        n_splits_done   — folds completados (puede ser < n_splits si hay pocos datos)
    """
    # ── Preparar datos completos ───────────────────────────────────────────────
    config = get_config(ticker)
    asset_type = get_asset_type(ticker)
    ws = max(v["window_size"] for v in ENSEMBLE_VARIATIONS[asset_type])
    data = prepare_data_multi_window(ticker, config, [ws])[ws]

    # Concatenar todos los splits en orden temporal: train + val + test
    def _cat(key):
        arr = data[key]
        return arr.numpy() if hasattr(arr, "numpy") else np.array(arr)

    X_all = np.concatenate([
        _build_xgb_features(data["X_train"]),
        _build_xgb_features(data["X_val"]),
        _build_xgb_features(data["X_test"]),
    ], axis=0)

    def _rets(k):
        v = data.get(f"y_{k}_returns", data[f"y_{k}"])
        return (v.numpy() if hasattr(v, "numpy") else np.array(v)).ravel()

    returns_all = np.concatenate([_rets("train"), _rets("val"), _rets("test")])

    # Etiquetas frozen
    dn, up = _load_frozen_thresholds(ticker)
    y_all = _returns_to_classes(returns_all, dn, up)

    # ── TimeSeriesSplit ────────────────────────────────────────────────────────
    cfg = XGBOOST_VOLATILE_CONFIG if asset_type == "volatile" else XGBOOST_STABLE_CONFIG
    tscv = TimeSeriesSplit(n_splits=n_splits)

    ba_folds, f1_folds, conf_folds = [], [], []
    fold_details = []

    for fold_idx, (train_idx, test_idx) in enumerate(tscv.split(X_all)):
        X_tr, X_te = X_all[train_idx], X_all[test_idx]
        y_tr, y_te = y_all[train_idx], y_all[test_idx]

        # Necesitamos al menos 2 clases en train y test
        if len(np.unique(y_tr)) < 2 or len(np.unique(y_te)) < 2:
            continue

        # Val = último 15% del train para early stopping
        val_cut = max(1, int(len(X_tr) * 0.15))
        X_tr_fit, X_val_fit = X_tr[:-val_cut], X_tr[-val_cut:]
        y_tr_fit, y_val_fit = y_tr[:-val_cut], y_tr[-val_cut:]

        sw = _sample_weights(y_tr_fit)

        model = XGBClassifier(
            n_estimators=cfg["n_estimators"],
            max_depth=cfg["max_depth"],
            learning_rate=cfg["learning_rate"],
            subsample=cfg["subsample"],
            colsample_bytree=cfg["colsample_bytree"],
            min_child_weight=cfg.get("min_child_weight", 1.0),
            gamma=cfg.get("gamma", 0.0),
            early_stopping_rounds=cfg["early_stopping_rounds"],
            objective="multi:softprob",
            num_class=3,
            eval_metric="mlogloss",
            verbosity=0,
            random_state=RANDOM_STATE,
        )
        model.fit(
            X_tr_fit, y_tr_fit,
            sample_weight=sw,
            eval_set=[(X_val_fit, y_val_fit)],
            verbose=False,
        )

        proba  = model.predict_proba(X_te)
        y_pred = np.argmax(proba, axis=1)
        conf   = float(np.mean(np.max(proba, axis=1)))

        ba = float(balanced_accuracy_score(y_te, y_pred))
        f1 = float(f1_score(y_te, y_pred, average="macro", zero_division=0))

        ba_folds.append(ba)
        f1_folds.append(f1)
        conf_folds.append(conf)
        fold_details.append({
            "fold": fold_idx + 1,
            "train_size": len(X_tr_fit),
            "test_size": len(X_te),
            "ba": round(ba * 100, 2),
            "f1": round(f1 * 100, 2),
            "conf": round(conf * 100, 2),
        })

    if not ba_folds:
        return {"error": "No se pudieron completar folds", "ticker": ticker}

    return {
        "ticker": ticker,
        "asset_type": asset_type,
        "n_splits_done": len(ba_folds),
        "ba_mean":  round(float(np.mean(ba_folds)) * 100, 2),
        "ba_std":   round(float(np.std(ba_folds))  * 100, 2),
        "f1_mean":  round(float(np.mean(f1_folds)) * 100, 2),
        "f1_std":   round(float(np.std(f1_folds))  * 100, 2),
        "conf_mean":round(float(np.mean(conf_folds))* 100, 2),
        "ba_folds": [round(x * 100, 2) for x in ba_folds],
        "f1_folds": [round(x * 100, 2) for x in f1_folds],
        "fold_details": fold_details,
        "thresholds": {"bajista": round(dn, 6), "alcista": round(up, 6)},
        "ran_at": datetime.now().isoformat(),
    }


# ── Resumen multi-ticker ───────────────────────────────────────────────────────

def run_all(tickers: list, n_splits: int = N_SPLITS, output_path: str = None) -> dict:
    all_results = {}
    print(f"\n{'='*80}")
    print(f"  WALK-FORWARD VALIDATION — XGBoost v5 — {n_splits} folds")
    print(f"  Tickers: {len(tickers)} | Método: TimeSeriesSplit (sklearn)")
    print(f"{'='*80}\n")
    print(f"{'Ticker':<10} {'Tipo':<10} {'BA mean':<10} {'BA std':<10} {'F1 mean':<10} {'Folds':<8}")
    print(f"{'─'*60}")

    ba_all = []
    for ticker in tickers:
        try:
            r = walk_forward_ticker(ticker, n_splits=n_splits)
            all_results[ticker] = r
            if "error" in r:
                print(f"{ticker:<10} ERROR: {r['error']}")
                continue
            ba_all.append(r["ba_mean"])
            signal = "✓" if r["ba_mean"] > 35 else "~" if r["ba_mean"] > 31 else "✗"
            print(f"{ticker:<10} {r['asset_type']:<10} {r['ba_mean']:>6.2f}%   ±{r['ba_std']:>5.2f}%   {r['f1_mean']:>6.2f}%    {r['n_splits_done']}/{n_splits}  {signal}")
        except Exception as e:
            print(f"{ticker:<10} EXCEPTION: {e}")
            all_results[ticker] = {"error": str(e)}

    print(f"{'─'*60}")
    if ba_all:
        print(f"{'MEDIA':<10} {'':10} {np.mean(ba_all):>6.2f}%   ±{np.std(ba_all):>5.2f}%")

    print(f"\n  Leyenda: ✓ señal (BA>35%) | ~ marginal (31-35%) | ✗ sin señal (<31%)")

    summary = {
        "_meta": {
            "ran_at": datetime.now().isoformat(),
            "n_splits": n_splits,
            "method": "TimeSeriesSplit (sklearn)",
            "model": "XGBoost v5 multi:softprob",
            "labeling": "frozen_per_ticker_percentile_33_67",
            "tickers_total": len(tickers),
            "tickers_ok": len(ba_all),
        },
        "aggregate": {
            "ba_mean": round(float(np.mean(ba_all)), 2) if ba_all else None,
            "ba_std":  round(float(np.std(ba_all)), 2) if ba_all else None,
        },
        "tickers": all_results,
    }

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"\n  Resultados guardados en: {output_path}")

    return summary


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Walk-Forward XGBoost")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Todos los tickers")
    group.add_argument("--tickers", nargs="+", help="Lista de tickers")
    parser.add_argument("--splits", type=int, default=N_SPLITS, help=f"Número de folds (default: {N_SPLITS})")
    parser.add_argument("--output", type=str, default="docs/walk_forward_results.json")
    args = parser.parse_args()

    if args.all:
        tickers = TICKERS["stable"] + TICKERS["volatile"]
    else:
        tickers = args.tickers

    run_all(tickers, n_splits=args.splits, output_path=args.output)


if __name__ == "__main__":
    main()
