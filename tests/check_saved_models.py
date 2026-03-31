"""
Script de diagnóstico: Verificar qué modelos están guardados en saved_models/

Revisa:
1. BiGRU models para cada ticker
2. XGBoost models para cada ticker
3. Stacking meta-models
4. Reportes JSON
"""

import os
from pathlib import Path

# Configuración
SAVED_MODELS_DIR = "backend/models/saved_models"
TICKERS = ["KO", "AAPL", "GC=F", "SI=F", "TSLA", "NVDA", "BTC-USD", "ETH-USD"]

print("\n" + "="*80)
print("📁 DIAGNÓSTICO DE MODELOS GUARDADOS")
print("="*80)

if not os.path.exists(SAVED_MODELS_DIR):
    print(f"\n❌ Directorio no encontrado: {SAVED_MODELS_DIR}")
    exit(1)

print(f"\n📍 Directorio: {SAVED_MODELS_DIR}\n")

# ── Por cada ticker ────────────────────────────────────────────────────────
for ticker in TICKERS:
    print(f"\n{'─'*80}")
    print(f"🔍 {ticker}")
    print(f"{'─'*80}")
    
    # BiGRU models
    bigru_found = []
    for i in range(10):  # Buscar hasta 10 modelos
        model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_model_{i}.pth")
        if os.path.exists(model_path):
            size_mb = os.path.getsize(model_path) / (1024**2)
            bigru_found.append(i)
            print(f"   ✅ BiGRU modelo {i}: {size_mb:.2f} MB")
    
    if not bigru_found:
        print(f"   ❌ Ningún modelo BiGRU encontrado")
    else:
        print(f"      └─ Total: {len(bigru_found)} modelos")
    
    # XGBoost model
    xgb_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost.pkl")
    if os.path.exists(xgb_path):
        size_mb = os.path.getsize(xgb_path) / (1024**2)
        print(f"   ✅ XGBoost: {size_mb:.2f} MB")
    else:
        print(f"   ❌ XGBoost NO ENCONTRADO")
    
    # Stacking meta-model
    stacking_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_stacking_metalearner.pkl")
    if os.path.exists(stacking_path):
        size_mb = os.path.getsize(stacking_path) / (1024**2)
        print(f"   ✅ Stacking Meta-Model: {size_mb:.2f} MB")
    else:
        print(f"   ℹ️  Stacking Meta-Model no disponible (aún no entrenado)")
    
    # Reportes
    report_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_report.json")
    stacking_report = os.path.join(SAVED_MODELS_DIR, f"{ticker}_stacking_report.json")
    
    if os.path.exists(report_path):
        print(f"   📄 Report JSON: ✅")
    if os.path.exists(stacking_report):
        print(f"   📄 Stacking Report JSON: ✅")

# ── Resumen final ──────────────────────────────────────────────────────────
print(f"\n{'='*80}")
print("📊 RESUMEN")
print(f"{'='*80}")

xgb_available = 0
for ticker in TICKERS:
    xgb_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost.pkl")
    if os.path.exists(xgb_path):
        xgb_available += 1

print(f"\n✅ XGBoost disponibles: {xgb_available}/{len(TICKERS)}")

if xgb_available < len(TICKERS):
    print(f"\n⚠️  XGBoost faltantes para:")
    for ticker in TICKERS:
        xgb_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost.pkl")
        if not os.path.exists(xgb_path):
            print(f"     • {ticker}")

print(f"\n" + "="*80 + "\n")
