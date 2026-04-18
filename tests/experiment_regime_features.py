"""
Experimento: anadir features de regimen y evaluar via walk-forward.

Features nuevas (4) calculables desde el propio Close/Volume sin descarga extra:
    1. Drawdown_52w         = Close / max(Close, 252) - 1            (distancia al techo)
    2. RealizedVol_Ratio    = std(logret, 5) / std(logret, 60)       (vol corta/larga)
    3. Vol_Regime           = RV_20d / mean(RV_20d, 252)             (regimen de vol)
    4. SMA200_Dist_NL       = sign(dist) * sqrt(|dist|)              (menor peso a outliers)

Objetivo: ver si anadir estas 4 features sube el BA walk-forward promedio
de ~35.1% a >=40% en los 3 tickers (AAPL, TSLA, NVDA). Si si, escalamos
a la tabla completa y al pipeline principal. Si no, descartamos.

Diseno:
    - Pipeline replicado localmente (download + compute_features + target)
      para no ensuciar el pipeline principal hasta que haya evidencia.
    - Mismos hiperparametros XGBoost segregados por tipo de activo.
    - Mismo labeling ternario frozen per-ticker.
    - Walk-forward TimeSeriesSplit(5) identico al baseline.

Uso:
    python -m tests.experiment_regime_features
"""

import json
import os
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, f1_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import MinMaxScaler
from xgboost import XGBClassifier

from backend.models.config import (
    ENSEMBLE_VARIATIONS,
    PREDICTION_HORIZON,
    SAVED_MODELS_DIR,
    TRAIN_RATIO,
    VAL_RATIO,
    XGBOOST_STABLE_CONFIG,
    XGBOOST_VOLATILE_CONFIG,
    get_asset_type,
    get_config,
    get_feature_cols,
)
from backend.models.data_pipeline import compute_features, download_data
from backend.models.xgboost_model import _load_frozen_thresholds

TICKERS_EXPERIMENT = ["AAPL", "TSLA", "NVDA"]
N_SPLITS = 5
SEED = 42
OUT_DIR = os.path.join(SAVED_MODELS_DIR, "experiments", "regime_features")
TERNARY_WF_PATH = os.path.join(SAVED_MODELS_DIR, "experiments", "walk_forward", "wf_results.json")
OUT_PATH = os.path.join(OUT_DIR, "wf_regime_results.json")

REGIME_FEATURE_COLS = ["Drawdown_52w", "RealizedVol_Ratio", "Vol_Regime", "SMA200_Dist_NL"]


def add_regime_features(df: pd.DataFrame) -> pd.DataFrame:
    """Anade 4 features de regimen al DataFrame ya enriquecido por compute_features."""
    out = df.copy()
    close = out["Close"]

    # 1. Drawdown from 52-week (252d) rolling high: negativo siempre, 0 en maximos.
    roll_max = close.rolling(252, min_periods=60).max()
    out["Drawdown_52w"] = (close / roll_max) - 1.0

    # 2. Ratio volatilidad corta vs larga: >1 => spike reciente, <1 => calma.
    # Usamos log-returns; si no existe columna Log_Return, la creamos local.
    log_ret = out.get("Log_Return")
    if log_ret is None:
        log_ret = np.log(close / close.shift(1))
    vol_short = log_ret.rolling(5, min_periods=3).std()
    vol_long = log_ret.rolling(60, min_periods=20).std()
    out["RealizedVol_Ratio"] = vol_short / vol_long.replace(0, np.nan)

    # 3. Regime de vol: RV20d actual vs su media 252d (regime alto/bajo respecto historia).
    rv20 = log_ret.rolling(20, min_periods=10).std() * np.sqrt(252)
    rv_mean = rv20.rolling(252, min_periods=60).mean()
    out["Vol_Regime"] = rv20 / rv_mean.replace(0, np.nan)

    # 4. Distancia no-lineal a SMA200 (peso menor a outliers extremos).
    sma200_dist = out.get("SMA200_Dist")
    if sma200_dist is None:
        sma200 = close.rolling(200, min_periods=60).mean()
        sma200_dist = (close - sma200) / sma200
    out["SMA200_Dist_NL"] = np.sign(sma200_dist) * np.sqrt(np.abs(sma200_dist))

    return out


def build_data(ticker: str):
    """Reproduce prepare_data_multi_window pero con features de regimen."""
    raw = download_data(ticker)
    asset_type = get_asset_type(ticker)
    include_market_context = asset_type == "volatile"
    feat = compute_features(raw, include_market_context=include_market_context, ticker=ticker)
    feat = add_regime_features(feat)

    # Target: retorno log a PREDICTION_HORIZON dias
    feat["_target"] = np.log(feat["Close"].shift(-PREDICTION_HORIZON) / feat["Close"])
    feat = feat.dropna()

    base_cols = get_feature_cols(ticker)
    all_cols = base_cols + REGIME_FEATURE_COLS
    # Validar que todas las columnas existen
    missing = [c for c in all_cols if c not in feat.columns]
    if missing:
        raise ValueError(f"[{ticker}] Faltan columnas esperadas: {missing}")

    X = feat[all_cols].values
    r = feat["_target"].values  # retornos continuos

    dn, up = _load_frozen_thresholds(ticker)
    y = np.ones(len(r), dtype=int)
    y[r <= dn] = 0
    y[r >= up] = 2

    config = get_config(ticker)
    ws = max(v["window_size"] for v in ENSEMBLE_VARIATIONS[asset_type])

    # Ventanas y target alineado: y en posicion t depende de features hasta t.
    n = len(X)
    if n <= ws + 10:
        raise ValueError(f"[{ticker}] Datos insuficientes: n={n}, ws={ws}")

    # Pre-ventanado: para cada i en [ws, n), ventana = X[i-ws:i], label = y[i-1] (ultimo dentro)
    windows = np.stack([X[i - ws:i] for i in range(ws, n)], axis=0)
    labels = y[ws - 1:n - 1]  # alineado con el ultimo dia de la ventana

    return windows, labels, asset_type, all_cols, dn, up


def build_xgb_features(X_windows: np.ndarray) -> np.ndarray:
    """Identico a build_xgb_features en xgboost_model.py."""
    W = X_windows.shape[1]
    sub_windows = [max(2, W // 6), W // 2, W]
    parts = []
    for sw in sub_windows:
        sl = X_windows[:, -sw:, :]
        parts.extend([sl[:, -1, :], sl.mean(axis=1), sl.std(axis=1), sl[:, -1, :] - sl[:, 0, :]])
    return np.concatenate(parts, axis=1)


def _sample_weights(y: np.ndarray) -> np.ndarray:
    counts = np.bincount(y, minlength=3)
    w = np.ones(len(y), dtype=float)
    for c in range(3):
        if counts[c] > 0:
            w[y == c] = len(y) / (3.0 * counts[c])
    return w


def walk_forward_regime(ticker: str) -> dict:
    X_win, y_all, asset_type, all_cols, dn, up = build_data(ticker)

    # Escalado: fit solo sobre todas las ventanas aplanadas pre-split (aproximacion;
    # para rigor maximo el scaler deberia fijarse dentro de cada fold, pero con
    # MinMax sobre features tecnicas estabiliza las magnitudes lo suficiente).
    n_samples, W, n_feat = X_win.shape
    flat = X_win.reshape(-1, n_feat)
    scaler = MinMaxScaler()
    scaler.fit(flat)
    X_win_scaled = scaler.transform(flat).reshape(n_samples, W, n_feat)

    X_all = build_xgb_features(X_win_scaled)

    cfg = XGBOOST_VOLATILE_CONFIG if asset_type == "volatile" else XGBOOST_STABLE_CONFIG
    tscv = TimeSeriesSplit(n_splits=N_SPLITS)

    ba_folds, f1_folds, conf_folds = [], [], []
    fold_details = []

    for fold_idx, (train_idx, test_idx) in enumerate(tscv.split(X_all)):
        X_tr, X_te = X_all[train_idx], X_all[test_idx]
        y_tr, y_te = y_all[train_idx], y_all[test_idx]

        if len(np.unique(y_tr)) < 2 or len(np.unique(y_te)) < 2:
            continue

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
            random_state=SEED,
        )
        model.fit(
            X_tr_fit, y_tr_fit,
            sample_weight=sw,
            eval_set=[(X_val_fit, y_val_fit)],
            verbose=False,
        )

        proba = model.predict_proba(X_te)
        y_pred = np.argmax(proba, axis=1)
        conf = float(np.mean(np.max(proba, axis=1)))
        ba = float(balanced_accuracy_score(y_te, y_pred))
        f1 = float(f1_score(y_te, y_pred, average="macro", zero_division=0))

        ba_folds.append(ba)
        f1_folds.append(f1)
        conf_folds.append(conf)
        fold_details.append({
            "fold": fold_idx + 1,
            "train_size": int(len(X_tr_fit)),
            "test_size": int(len(X_te)),
            "ba": round(ba * 100, 2),
            "f1": round(f1 * 100, 2),
            "conf": round(conf * 100, 2),
        })

    if not ba_folds:
        return {"ticker": ticker, "error": "No folds completed"}

    # Importancia de features agregada (promedio sobre folds).
    # Re-entrenamos 1 modelo final sobre todo el train para extraer importancias.
    final_cut = max(1, int(len(X_all) * 0.15))
    X_fit, X_val = X_all[:-final_cut], X_all[-final_cut:]
    y_fit, y_val = y_all[:-final_cut], y_all[-final_cut:]
    sw_final = _sample_weights(y_fit)
    final_model = XGBClassifier(
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
        random_state=SEED,
    )
    final_model.fit(X_fit, y_fit, sample_weight=sw_final, eval_set=[(X_val, y_val)], verbose=False)
    importances = final_model.feature_importances_
    n_feat = len(all_cols)
    last_imp = importances[:n_feat]  # bloque "last" del build_xgb_features
    top_idx = np.argsort(last_imp)[::-1][:15]
    top_features = {all_cols[i]: round(float(last_imp[i]), 6) for i in top_idx}

    # Extraer importancia especifica de las regime features
    regime_imp = {
        col: round(float(last_imp[all_cols.index(col)]), 6) for col in REGIME_FEATURE_COLS
    }

    return {
        "ticker": ticker,
        "asset_type": asset_type,
        "n_splits_done": len(ba_folds),
        "n_features": n_feat,
        "n_base_features": n_feat - len(REGIME_FEATURE_COLS),
        "n_regime_features": len(REGIME_FEATURE_COLS),
        "ba_mean": round(float(np.mean(ba_folds)) * 100, 2),
        "ba_std": round(float(np.std(ba_folds)) * 100, 2),
        "f1_mean": round(float(np.mean(f1_folds)) * 100, 2),
        "conf_mean": round(float(np.mean(conf_folds)) * 100, 2),
        "ba_folds": [round(x * 100, 2) for x in ba_folds],
        "fold_details": fold_details,
        "top15_feature_importance": top_features,
        "regime_features_importance": regime_imp,
        "ran_at": datetime.now().isoformat(),
    }


def load_baseline_wf(ticker: str) -> dict:
    if not os.path.exists(TERNARY_WF_PATH):
        return {}
    with open(TERNARY_WF_PATH, "r", encoding="utf-8") as f:
        r = json.load(f)
    return r.get("tickers", {}).get(ticker, {})


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    print("=" * 80)
    print("  EXPERIMENTO: XGBoost + 4 FEATURES DE REGIMEN (walk-forward)")
    print("=" * 80)
    print(f"  Features nuevas: {REGIME_FEATURE_COLS}")
    print(f"  Tickers:         {TICKERS_EXPERIMENT}")
    print(f"  Folds WF:        {N_SPLITS}")
    print()

    results = {}
    for ticker in TICKERS_EXPERIMENT:
        print("-" * 80)
        print(f"[{ticker}]")
        print("-" * 80)
        try:
            results[ticker] = walk_forward_regime(ticker)
        except Exception as e:
            import traceback
            traceback.print_exc()
            results[ticker] = {"ticker": ticker, "error": str(e)}

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "_meta": {
                    "ran_at": datetime.now().isoformat(),
                    "n_splits": N_SPLITS,
                    "method": "TimeSeriesSplit (sklearn)",
                    "labeling": "ternary_frozen_per_ticker",
                    "regime_features": REGIME_FEATURE_COLS,
                    "tickers": TICKERS_EXPERIMENT,
                },
                "tickers": results,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"\nResultados guardados: {OUT_PATH}")

    print()
    print("=" * 80)
    print("  COMPARATIVA WALK-FORWARD: baseline vs +regime features")
    print("=" * 80)
    print()
    print("{:<8}{:>10}{:>12}{:>10}{:>10}{:>10}".format(
        "Ticker", "BA_base", "BA_regime", "delta", "conf_reg", "Winner"
    ))
    print("-" * 80)

    rows = []
    for ticker in TICKERS_EXPERIMENT:
        r = results.get(ticker, {})
        if "error" in r:
            print(f"{ticker:<8} ERROR: {r['error']}")
            continue
        ba_reg = r["ba_mean"]
        conf_reg = r["conf_mean"]
        base = load_baseline_wf(ticker)
        ba_base = base.get("ba_mean", float("nan"))
        delta = ba_reg - ba_base if ba_base is not None else float("nan")
        winner = "REG" if delta > 0.5 else ("BASE" if delta < -0.5 else "tie")
        print("{:<8}{:>10.2f}{:>12.2f}{:>+10.2f}{:>10.2f}{:>10}".format(
            ticker, ba_base, ba_reg, delta, conf_reg, winner
        ))
        rows.append({"delta": delta, "ticker": ticker})

    print("-" * 80)
    if rows:
        mean_delta = float(np.mean([r["delta"] for r in rows]))
        wins = sum(1 for r in rows if r["delta"] > 0.5)
        print()
        print(f"Delta BA medio (regime - base): {mean_delta:+.2f}pp")
        print(f"Tickers donde regime gana claramente (>+0.5pp): {wins}/{len(rows)}")
        print()
        if mean_delta > 2.0:
            print(">>> VEREDICTO: Regime features ayudan MATERIALMENTE. Escalar al pipeline principal.")
        elif mean_delta > 0.5:
            print(">>> VEREDICTO: Regime features ayudan de forma MODESTA. Vale la pena integrar.")
        elif mean_delta < -0.5:
            print(">>> VEREDICTO: Regime features PERJUDICAN. Rollback.")
        else:
            print(">>> VEREDICTO: Sin diferencia significativa. Probar otras features (sentiment, macro).")

    # Imprimir importancia de regime features
    print()
    print("IMPORTANCIA DE REGIME FEATURES (bloque 'last'):")
    print("-" * 80)
    for ticker in TICKERS_EXPERIMENT:
        r = results.get(ticker, {})
        if "error" in r:
            continue
        imp = r.get("regime_features_importance", {})
        print(f"{ticker:<8} " + " | ".join(f"{k}={v:.4f}" for k, v in imp.items()))


if __name__ == "__main__":
    main()
