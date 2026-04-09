#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from pathlib import Path

def extract_summary_table(filepath):
    """Extrae la tabla RESUMEN FINAL del archivo de log"""
    if not Path(filepath).exists():
        print(f"Archivo no encontrado: {filepath}")
        return {}
    
    results = {}
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Buscar la tabla con el resumen (después de "RESUMEN FINAL")
    # Formato:
    # Ticker       XGB Acc      Precision    Recall       BD              Tiempo
    # KO           34.40%       35.48%       63.95%  [OK] BD OK          92.7s
    
    # Buscar línea del ticker (solo nombres válidos)
    valid_tickers = ['AAPL', 'BABA', 'GOOGL', 'KO', 'MSFT', 'NVDA', 'TSLA', 'VXX', 'AMZN', 'INTC', 'META', 'NFLX']
    
    for line in content.split('\n'):
        # Detectar si la línea contiene un ticker válido
        for ticker in valid_tickers:
            if ticker in line and '%' in line:
                # Extraer BA y Recall (buscar dos porcentajes en la línea)
                percentages = re.findall(r'([\d.]+)%', line)
                if len(percentages) >= 3:  # BA, Precision, Recall
                    ba = float(percentages[0])
                    # precision = float(percentages[1])  # No lo necesito
                    recall = float(percentages[2])
                    results[ticker] = {'ba': ba, 'recall': recall}
                break
    
    return results

# Extraer resultados
sin_sentimiento = extract_summary_table('entrenamiento_v4_sin_sentimiento.txt')
con_sentimiento = extract_summary_table('entrenamiento_v4_con_sentimiento.txt')

print(f"\n[DEBUG] Sin sentimiento encontrados: {len(sin_sentimiento)} tickers")
print(f"[DEBUG] Con sentimiento encontrados: {len(con_sentimiento)} tickers")

if len(sin_sentimiento) == 0 or len(con_sentimiento) == 0:
    print("ERROR: No se pudieron extraer los datos. Verificando archivos...")
    print("\nÚltimas líneas sin sentimiento:")
    with open('entrenamiento_v4_sin_sentimiento.txt', 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        for line in lines[-30:]:
            if 'KO' in line or 'AAPL' in line or 'MSFT' in line or '34' in line or '37' in line or '31' in line:
                print(f"  {line.rstrip()}")
    exit(1)

# Todos los tickers en orden
all_tickers = sorted(set(list(sin_sentimiento.keys()) + list(con_sentimiento.keys())))

print("\n" + "="*110)
print("COMPARATIVA: v4 SIN SENTIMIENTO vs v4 CON SENTIMIENTO")
print("="*110)
print(f"{'Ticker':<8} | {'BA (sin)':<10} | {'BA (con)':<10} | {'Δ BA':<8} | {'Recall (sin)':<13} | {'Recall (con)':<13} | {'Δ Recall':<8}")
print("-"*110)

total_ba_sin = 0
total_ba_con = 0
total_recall_sin = 0
total_recall_con = 0
count = len(all_tickers)
mejoras_ba = 0
mejoras_recall = 0
desmejoraas_ba = 0
desmejoraas_rec = 0

for ticker in all_tickers:
    ba_s = sin_sentimiento.get(ticker, {}).get('ba', 0)
    ba_c = con_sentimiento.get(ticker, {}).get('ba', 0)
    rec_s = sin_sentimiento.get(ticker, {}).get('recall', 0)
    rec_c = con_sentimiento.get(ticker, {}).get('recall', 0)
    
    delta_ba = ba_c - ba_s
    delta_rec = rec_c - rec_s
    
    ba_sign = "↑" if delta_ba > 0.5 else "↓" if delta_ba < -0.5 else "→"
    rec_sign = "↑" if delta_rec > 2 else "↓" if delta_rec < -2 else "→"
    
    print(f"{ticker:<8} | {ba_s:>7.2f}% | {ba_c:>7.2f}% | {delta_ba:>+6.2f}% {ba_sign} | {rec_s:>7.2f}% | {rec_c:>7.2f}% | {delta_rec:>+6.2f}% {rec_sign}")
    
    total_ba_sin += ba_s
    total_ba_con += ba_c
    total_recall_sin += rec_s
    total_recall_con += rec_c
    
    if delta_ba > 0.5:
        mejoras_ba += 1
    elif delta_ba < -0.5:
        desmejoraas_ba += 1
        
    if delta_rec > 2:
        mejoras_recall += 1
    elif delta_rec < -2:
        desmejoraas_rec += 1

print("-"*110)
avg_ba_sin = total_ba_sin / count if count else 0
avg_ba_con = total_ba_con / count if count else 0
avg_rec_sin = total_recall_sin / count if count else 0
avg_rec_con = total_recall_con / count if count else 0

print(f"{'PROMEDIO':<8} | {avg_ba_sin:>7.2f}% | {avg_ba_con:>7.2f}% | {avg_ba_con - avg_ba_sin:>+6.2f}% | {avg_rec_sin:>7.2f}% | {avg_rec_con:>7.2f}% | {avg_rec_con - avg_rec_sin:>+6.2f}%")
print("="*110)

print(f"\n📊 RESUMEN DE CAMBIOS (Análisis de Sentimiento):")
print(f"  • Tickers con BA mejorada: {mejoras_ba}/{count}")
print(f"  • Tickers con BA desmejora: {desmejoraas_ba}/{count}")
print(f"  • Tickers con Recall mejorado: {mejoras_recall}/{count}")
print(f"  • Tickers con Recall desmejora: {desmejoraas_rec}/{count}")
print(f"  • Cambio neto en BA: {avg_ba_con - avg_ba_sin:+.2f}p.p.")
print(f"  • Cambio neto en Recall: {avg_rec_con - avg_rec_sin:+.2f}p.p.")

# Análisis
print(f"\n🎯 CONCLUSIÓN:")
delta_ba_abs = abs(avg_ba_con - avg_ba_sin)
delta_rec_abs = abs(avg_rec_con - avg_rec_sin)

if delta_ba_abs > 1.0 or delta_rec_abs > 3.0:
    if avg_ba_con > avg_ba_sin and avg_rec_con > avg_rec_sin:
        print(f"  ✅ SENTIMIENTO AYUDA")
        print(f"     El análisis de sentimiento mejora AMBAS métricas de forma significativa")
        print(f"     Recomendación: MANTENER USE_SENTIMENT=True")
    elif avg_ba_sin > avg_ba_con and avg_rec_sin > avg_rec_con:
        print(f"  ⚠️  SENTIMIENTO PERJUDICA")
        print(f"     El análisis de sentimiento empeora AMBAS métricas")
        print(f"     Recomendación: CAMBIAR a USE_SENTIMENT=False")
    else:
        print(f"  ⚖️  RESULTADOS MIXTOS")
        ba_better = "CON sentimiento" if avg_ba_con > avg_ba_sin else "SIN sentimiento"
        rec_better = "CON sentimiento" if avg_rec_con > avg_rec_sin else "SIN sentimiento"
        print(f"     → BA mejor {ba_better}")
        print(f"     → Recall mejor {rec_better}")
else:
    print(f"  ≈️  DIFERENCIA MARGINAL (<1% en BA, <3% en recall)")
    print(f"     El sentimiento no tiene impacto significativo")
    print(f"     Recomendación: MANTENER SIN SENTIMIENTO (más rápido, sin cambios reales)")

print("\n")
