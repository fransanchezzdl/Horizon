"""
Baselines comparativos para Horizon XGBoost v6.

Tres estrategias de referencia para contextualizar el BA del modelo:

    1. Random         — predice clase aleatoria uniforme (33.3% teórico)
    2. Buy & Hold     — siempre predice ALCISTA (estrategia pasiva)
    3. SMA Crossover  — ALCISTA si SMA20 > SMA50, BAJISTA si SMA20 < SMA50,
                        LATERAL si dentro de una banda del ±0.5%

Cada baseline se evalúa sobre el mismo test set y con las mismas
etiquetas frozen que usa XGBoost, garantizando comparación justa.

Uso:
    python -m backend.models.baselines --all
    python -m backend.models.baselines --tickers AAPL META BTC-USD
"""

import argparse
import json
import os
from datetime import datetime

import numpy as np
from sklearn.metrics import balanced_accuracy_score, f1_score

from .config import (
    ENSEMBLE_VARIATIONS,
    TICKERS,
    get_asset_type,
    get_config,
    get_feature_cols,
)
from .data_pipeline import prepare_data_multi_window
from .xgboost_model import _load_frozen_thresholds

RANDOM_SEED = 42


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_test_labels(ticker: str) -> tuple[np.ndarray, np.ndarray]:
    """
    Devuelve (y_test_returns, y_test_classes) del split temporal estándar.
    Mismas etiquetas frozen que usa XGBoost → comparación justa.
    """
    config = get_config(ticker)
    asset_type = get_asset_type(ticker)
    ws = max(v["window_size"] for v in ENSEMBLE_VARIATIONS[asset_type])
    data = prepare_data_multi_window(ticker, config, [ws])[ws]

    rets = data.get("y_test_returns", data["y_test"])
    rets = rets.numpy() if hasattr(rets, "numpy") else np.array(rets)
    rets = rets.ravel()

    dn, up = _load_frozen_thresholds(ticker)
    y_cls = np.where(rets <= dn, 0, np.where(rets >= up, 2, 1))
    return rets, y_cls, data


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    ba = float(balanced_accuracy_score(y_true, y_pred))
    f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    acc = float(np.mean(y_true == y_pred))
    return {"ba": round(ba * 100, 2), "f1": round(f1 * 100, 2), "acc": round(acc * 100, 2)}


# ── Estrategias baseline ───────────────────────────────────────────────────────

def baseline_random(y_true: np.ndarray, seed: int = RANDOM_SEED) -> dict:
    """Predice clase aleatoria uniforme — cota inferior teórica."""
    rng = np.random.default_rng(seed)
    y_pred = rng.integers(0, 3, size=len(y_true))
    return _metrics(y_true, y_pred)


def baseline_buy_and_hold(y_true: np.ndarray) -> dict:
    """Siempre predice ALCISTA (2) — estrategia pasiva del inversor minorista."""
    y_pred = np.full(len(y_true), 2, dtype=int)
    return _metrics(y_true, y_pred)


def baseline_sma_crossover(ticker: str, data: dict) -> dict:
    """
    SMA Crossover clásico sobre el precio de cierre del test set.

    Señal:
        SMA20 > SMA50 * 1.005  → ALCISTA (2)
        SMA20 < SMA50 * 0.995  → BAJISTA (0)
        resto                  → LATERAL (1)

    Usa close_test si está disponible; si no, reconstruye desde X_test.
    """
    # Intentar obtener precios de cierre del test
    close_test = data.get("close_test", None)
    if close_test is None:
        # Fallback: usar la primera feature (Close normalizado) de X_test
        X = data["X_test"]
        X = X.numpy() if hasattr(X, "numpy") else np.array(X)
        close_test = X[:, -1, 0]  # último timestep, feature 0 (Close)

    close_test = np.array(close_test).ravel()

    # close_test puede incluir el warmup de la ventana → alinear con y_test
    rets_tmp = data.get("y_test_returns", data["y_test"])
    rets_tmp = rets_tmp.numpy() if hasattr(rets_tmp, "numpy") else np.array(rets_tmp)
    n_test = len(rets_tmp.ravel())
    if len(close_test) > n_test:
        close_test = close_test[-n_test:]

    n = len(close_test)

    # Calcular SMAs acumulativas sobre la secuencia de test
    # SMA20 y SMA50 se calculan con ventana expandida desde el inicio del test
    y_pred = np.ones(n, dtype=int)  # LATERAL por defecto

    for i in range(n):
        window = close_test[: i + 1]
        if len(window) < 2:
            continue
        sma20 = window[-min(20, len(window)):].mean()
        sma50 = window[-min(50, len(window)):].mean()
        if sma20 > sma50 * 1.005:
            y_pred[i] = 2  # ALCISTA
        elif sma20 < sma50 * 0.995:
            y_pred[i] = 0  # BAJISTA

    # Necesitamos y_true alineado
    rets = data.get("y_test_returns", data["y_test"])
    rets = rets.numpy() if hasattr(rets, "numpy") else np.array(rets)
    dn, up = _load_frozen_thresholds(ticker)
    y_true = np.where(rets.ravel() <= dn, 0, np.where(rets.ravel() >= up, 2, 1))

    return _metrics(y_true, y_pred)


# ── Runner por ticker ──────────────────────────────────────────────────────────

def run_baselines_ticker(ticker: str) -> dict:
    """Evalúa los 3 baselines para un ticker y devuelve el resultado."""
    _, y_test, data = _get_test_labels(ticker)
    dn, up = _load_frozen_thresholds(ticker)

    rand  = baseline_random(y_test)
    bah   = baseline_buy_and_hold(y_test)
    sma   = baseline_sma_crossover(ticker, data)

    return {
        "ticker":     ticker,
        "asset_type": get_asset_type(ticker),
        "n_test":     len(y_test),
        "test_dist":  {
            "BAJISTA": round(float((y_test == 0).mean() * 100), 1),
            "LATERAL": round(float((y_test == 1).mean() * 100), 1),
            "ALCISTA": round(float((y_test == 2).mean() * 100), 1),
        },
        "thresholds": {"bajista": round(dn, 6), "alcista": round(up, 6)},
        "random":       rand,
        "buy_and_hold": bah,
        "sma_crossover": sma,
    }


# ── Runner multi-ticker ────────────────────────────────────────────────────────

def run_all(tickers: list, output_path: str = None) -> dict:
    print(f"\n{'='*85}")
    print(f"  BASELINES COMPARATIVOS — Horizon v6")
    print(f"  Tickers: {len(tickers)} | Etiquetas: frozen per-ticker")
    print(f"{'='*85}")
    print(f"{'Ticker':<10} {'Tipo':<10} {'Random BA':<12} {'B&H BA':<12} {'SMA BA':<12} {'n_test'}")
    print(f"{'─'*68}")

    all_results = {}
    rand_bas, bah_bas, sma_bas = [], [], []

    for ticker in tickers:
        try:
            r = run_baselines_ticker(ticker)
            all_results[ticker] = r
            rand_bas.append(r["random"]["ba"])
            bah_bas.append(r["buy_and_hold"]["ba"])
            sma_bas.append(r["sma_crossover"]["ba"])
            print(
                f"{ticker:<10} {r['asset_type']:<10} "
                f"{r['random']['ba']:>8.2f}%    "
                f"{r['buy_and_hold']['ba']:>8.2f}%    "
                f"{r['sma_crossover']['ba']:>8.2f}%    "
                f"{r['n_test']}"
            )
        except Exception as e:
            print(f"{ticker:<10} ERROR: {e}")
            all_results[ticker] = {"error": str(e)}

    print(f"{'─'*68}")
    if rand_bas:
        print(
            f"{'MEDIA':<20} "
            f"{np.mean(rand_bas):>8.2f}%    "
            f"{np.mean(bah_bas):>8.2f}%    "
            f"{np.mean(sma_bas):>8.2f}%"
        )

    print(f"\n  Referencia XGBoost v6: BA media = 35.09%")
    print(f"  Random teórico:        BA = 33.33% (3 clases balanceadas)")

    summary = {
        "_meta": {
            "ran_at":   datetime.now().isoformat(),
            "model":    "XGBoost v6",
            "labeling": "frozen_per_ticker_percentile_33_67",
            "horizon":  "5d",
        },
        "aggregate": {
            "random_ba_mean":       round(float(np.mean(rand_bas)), 2) if rand_bas else None,
            "buy_and_hold_ba_mean": round(float(np.mean(bah_bas)), 2) if bah_bas else None,
            "sma_crossover_ba_mean":round(float(np.mean(sma_bas)), 2) if sma_bas else None,
            "xgboost_v6_ba_mean":   35.09,
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
    parser = argparse.ArgumentParser(description="Baselines comparativos Horizon")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all",     action="store_true")
    group.add_argument("--tickers", nargs="+")
    parser.add_argument("--output", default="docs/baselines_results.json")
    args = parser.parse_args()

    tickers = (TICKERS["stable"] + TICKERS["volatile"]) if args.all else args.tickers
    run_all(tickers, output_path=args.output)


if __name__ == "__main__":
    main()
