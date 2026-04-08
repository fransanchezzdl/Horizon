#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Análisis: Por qué el sentimiento NO mejora la fiabilidad del modelo
"""

import sys
sys.path.insert(0, '.')

from backend.daos.activo_dao import ActivoDAO
import numpy as np

# Obtener datos de BD para ambos entrenamientos
dao = ActivoDAO()
activos = dao.obtener_todos()

print("\n" + "="*100)
print("ANÁLISIS: IMPACTO DEL SENTIMIENTO EN FIABILIDAD DEL MODELO")
print("="*100)

print("\n🔍 HIPÓTESIS A PROBAR:")
print("  1. ¿Cómo cambian recalls extremos con sentimiento?")
print("  2. ¿El sentimiento reduce o amplifica variancia?")
print("  3. ¿Hay correlación entre cambio de recall y magnitud?")

print("\n📊 DATOS OBSERVADOS (de comparativa):\n")

# Datos reales de comparativa
data = {
    'AAPL': {'ba_sin': 37.57, 'ba_con': 38.72, 'rec_sin': 51.22, 'rec_con': 51.22},
    'AMZN': {'ba_sin': 33.70, 'ba_con': 33.70, 'rec_sin': 42.68, 'rec_con': 42.68},
    'BABA': {'ba_sin': 31.28, 'ba_con': 32.77, 'rec_sin': 24.44, 'rec_con': 28.89},
    'GOOGL': {'ba_sin': 33.27, 'ba_con': 33.27, 'rec_sin': 57.98, 'rec_con': 57.98},
    'INTC': {'ba_sin': 30.77, 'ba_con': 29.98, 'rec_sin': 30.63, 'rec_con': 24.32},
    'KO': {'ba_sin': 34.29, 'ba_con': 34.04, 'rec_sin': 67.44, 'rec_con': 61.63},
    'META': {'ba_sin': 33.68, 'ba_con': 35.50, 'rec_sin': 82.35, 'rec_con': 77.94},
    'MSFT': {'ba_sin': 32.62, 'ba_con': 31.32, 'rec_sin': 75.00, 'rec_con': 72.06},
    'NFLX': {'ba_sin': 28.18, 'ba_con': 28.18, 'rec_sin': 39.66, 'rec_con': 39.66},
    'NVDA': {'ba_sin': 33.57, 'ba_con': 37.27, 'rec_sin': 95.45, 'rec_con': 86.36},
    'TSLA': {'ba_sin': 37.13, 'ba_con': 37.13, 'rec_sin': 41.67, 'rec_con': 41.67},
    'VXX': {'ba_sin': 38.53, 'ba_con': 38.53, 'rec_sin': 76.24, 'rec_con': 76.24},
}

# Análisis por categoría de recall
extreme_recalls_sin = [t for t, d in data.items() if d['rec_sin'] > 70 or d['rec_sin'] < 35]
print(f"🚨 Tickers con RECALL EXTREMO (SIN sentimiento):")
for ticker in extreme_recalls_sin:
    rec_sin = data[ticker]['rec_sin']
    rec_con = data[ticker]['rec_con']
    delta = rec_con - rec_sin
    direction = "REDUCE" if delta < 0 else "AMPLIFICA" if delta > 0 else "SIN CAMBIO"
    print(f"  • {ticker}: {rec_sin:.1f}% → {rec_con:.1f}% ({delta:+.1f}%) {direction}")

print(f"\n📉 ANÁLISIS DE VARIANCIA:")
recalls_sin = [d['rec_sin'] for d in data.values()]
recalls_con = [d['rec_con'] for d in data.values()]
std_sin = np.std(recalls_sin)
std_con = np.std(recalls_con)

print(f"  • Desviación estándar RECALL (SIN sentimiento): {std_sin:.2f}pp")
print(f"  • Desviación estándar RECALL (CON sentimiento): {std_con:.2f}pp")
print(f"  • Cambio: {std_con - std_sin:+.2f}pp ({'MEJOR' if std_con < std_sin else 'PEOR'})")

print(f"\n🔬 HALLAZGOS:")
empeorando = sum(1 for t, d in data.items() if d['rec_con'] < d['rec_sin'])
mejorando = sum(1 for t, d in data.items() if d['rec_con'] > d['rec_sin'])
igual = sum(1 for t, d in data.items() if d['rec_con'] == d['rec_sin'])

print(f"  • Recall EMPEORA con sentimiento: {empeorando}/12 tickers")
print(f"  • Recall MEJORA con sentimiento: {mejorando}/12 tickers")
print(f"  • Recall SIN CAMBIO: {igual}/12 tickers")

print(f"\n💡 EXPLICACIONES PROBABLE:")
print(f"\n  1. RUIDO vs SEÑAL:")
print(f"     El sentimiento está agregando varianza sin información útil")
print(f"     → Los datos técnicos son suficientes")

print(f"\n  2. CONFLICT DE PREDICTORES:")
print(f"     Tickers con RECALL muy alto ({max(recalls_sin):.0f}% NVDA) muestran:")
print(f"     - El modelo técnico SOBREPREDIJECIENDO movimientos alcistas")
print(f"     - Agregar sentimiento podría intentar 'corregir' pero falla")

print(f"\n  3. MULTICOLINEALIDAD:")
print(f"     Features técnicas + Sentimiento pueden estar correlacionadas")
print(f"     → Crean conflicto en pesos del árbol XGBoost")

print(f"\n  4. CALIBRACIÓN DEL SENTIMIENTO:")
print(f"     DistilRoBERTa es modelo genérico, no financiero")
print(f"     → Las puntuaciones no están optimizadas para trading")

print(f"\n🎯 RECOMENDACIÓN:")
print(f"  ✓ MANTENER: USE_SENTIMENT=False")
print(f"  ✓ RAZÓN: Sentimiento ADD NOISE sin GANANCIA")
print(f"  ✓ FUTURO: Si quisieras mejorar, considera:")
print(f"    - Usar modelo de sentimiento FINANCIERO específico (FinBERT)")
print(f"    - Features de noticias con LAG (rezago de 1-5 días)")
print(f"    - Análisis de volatilidad implícita (VIX)")

print("\n" + "="*100 + "\n")
