import re
from pathlib import Path
from collections import defaultdict

def extract_results_robust(filepath):
    """Extrae BA y Recall de cada ticker del log - versión robusta"""
    if not Path(filepath).exists():
        print(f"Archivo no encontrado: {filepath}")
        return {}
    
    results = defaultdict(dict)
    
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    
    current_ticker = None
    
    for i, line in enumerate(lines):
        # Buscar línea con "XGBoost TICKER VALIDATION RESULTS"
        if 'VALIDATION RESULTS' in line:
            match = re.search(r'XGBoost\s+(\w+)', line)
            if match:
                current_ticker = match.group(1)
                results[current_ticker]['ticker'] = current_ticker
        
        # Buscar Balanced Accuracy
        if 'Balanced Accuracy:' in line and current_ticker:
            match = re.search(r'([\d.]+)%', line)
            if match:
                results[current_ticker]['ba'] = float(match.group(1))
        
        # Buscar Recall (ALCISTA)
        if 'Recall (ALCISTA):' in line and current_ticker:
            match = re.search(r'([\d.]+)%', line)
            if match:
                results[current_ticker]['recall'] = float(match.group(1))
    
    # Filtrar solo los que tienen ambas métricas
    clean_results = {}
    for ticker, data in results.items():
        if 'ba' in data and 'recall' in data:
            clean_results[ticker] = data
    
    return clean_results

# Extraer resultados
sin_sentimiento = extract_results_robust('entrenamiento_v4_sin_sentimiento.txt')
con_sentimiento = extract_results_robust('entrenamiento_v4_con_sentimiento.txt')

print(f"\n[DEBUG] Sin sentimiento encontrados: {len(sin_sentimiento)} tickers")
print(f"[DEBUG] Con sentimiento encontrados: {len(con_sentimiento)} tickers")

# Todos los tickers en orden
all_tickers = sorted(set(list(sin_sentimiento.keys()) + list(con_sentimiento.keys())))

print("\n" + "="*110)
print("COMPARATIVA: v4 SIN SENTIMIENTO vs v4 CON SENTIMIENTO")
print("="*110)
print(f"{'Ticker':<8} | {'BA (sin)':<10} | {'BA (con)':<10} | {'Δ':<7} | {'Recall (sin)':<13} | {'Recall (con)':<13} | {'Δ':<7}")
print("-"*110)

total_ba_sin = 0
total_ba_con = 0
total_recall_sin = 0
total_recall_con = 0
count_ba = 0
count_recall = 0
mejoras_ba = 0
mejoras_recall = 0

for ticker in all_tickers:
    ba_s = sin_sentimiento.get(ticker, {}).get('ba', 0)
    ba_c = con_sentimiento.get(ticker, {}).get('ba', 0)
    rec_s = sin_sentimiento.get(ticker, {}).get('recall', 0)
    rec_c = con_sentimiento.get(ticker, {}).get('recall', 0)
    
    delta_ba = ba_c - ba_s
    delta_rec = rec_c - rec_s
    
    ba_sign = "↑" if delta_ba > 0.5 else "↓" if delta_ba < -0.5 else "→"
    rec_sign = "↑" if delta_rec > 2 else "↓" if delta_rec < -2 else "→"
    
    print(f"{ticker:<8} | {ba_s:>7.2f}% | {ba_c:>7.2f}% | {delta_ba:>+5.2f}% {ba_sign} | {rec_s:>7.2f}% | {rec_c:>7.2f}% | {delta_rec:>+5.2f}% {rec_sign}")
    
    if ba_s > 0:
        total_ba_sin += ba_s
        total_ba_con += ba_c
        count_ba += 1
    
    if rec_s > 0:
        total_recall_sin += rec_s
        total_recall_con += rec_c
        count_recall += 1
    
    if delta_ba > 0.5:
        mejoras_ba += 1
    if delta_rec > 2:
        mejoras_recall += 1

print("-"*110)
avg_ba_sin = total_ba_sin / count_ba if count_ba else 0
avg_ba_con = total_ba_con / count_ba if count_ba else 0
avg_rec_sin = total_recall_sin / count_recall if count_recall else 0
avg_rec_con = total_recall_con / count_recall if count_recall else 0

print(f"{'PROMEDIO':<8} | {avg_ba_sin:>7.2f}% | {avg_ba_con:>7.2f}% | {avg_ba_con - avg_ba_sin:>+5.2f}% | {avg_rec_sin:>7.2f}% | {avg_rec_con:>7.2f}% | {avg_rec_con - avg_rec_sin:>+5.2f}%")
print("="*110)

print(f"\n📊 RESUMEN DE CAMBIOS:")
print(f"  • Tickers con BA mejorada: {mejoras_ba}/{len(all_tickers)}")
print(f"  • Tickers con Recall mejorado: {mejoras_recall}/{len(all_tickers)}")
print(f"  • Cambio neto en BA: {avg_ba_con - avg_ba_sin:+.2f} p.p.")
print(f"  • Cambio neto en Recall: {avg_rec_con - avg_rec_sin:+.2f} p.p.")

# Análisis
print(f"\n📈 ANÁLISIS:")
delta_ba_abs = abs(avg_ba_con - avg_ba_sin)
delta_rec_abs = abs(avg_rec_con - avg_rec_sin)

if delta_ba_abs > 1.0 or delta_rec_abs > 3.0:
    if avg_ba_con > avg_ba_sin and avg_rec_con > avg_rec_sin:
        print(f"  ✅ SENTIMIENTO AYUDA: Mejora significativa en ambas métricas")
        print(f"     - BA: {avg_ba_sin:.2f}% → {avg_ba_con:.2f}% (+{avg_ba_con - avg_ba_sin:.2f}pp)")
        print(f"     - Recall: {avg_rec_sin:.2f}% → {avg_rec_con:.2f}% (+{avg_rec_con - avg_rec_sin:.2f}pp)")
    elif avg_ba_sin > avg_ba_con and avg_rec_sin > avg_rec_con:
        print(f"  ⚠️  SENTIMIENTO PERJUDICA: Empeora en ambas métricas")
        print(f"     - BA: {avg_ba_sin:.2f}% → {avg_ba_con:.2f}% ({avg_ba_con - avg_ba_sin:.2f}pp)")
        print(f"     - Recall: {avg_rec_sin:.2f}% → {avg_rec_con:.2f}% ({avg_rec_con - avg_rec_sin:.2f}pp)")
    else:
        print(f"  ⚖️  RESULTADOS MIXTOS:")
        print(f"     - BA: {avg_ba_sin:.2f}% → {avg_ba_con:.2f}% ({avg_ba_con - avg_ba_sin:+.2f}pp)")
        print(f"     - Recall: {avg_rec_sin:.2f}% → {avg_rec_con:.2f}% ({avg_rec_con - avg_rec_sin:+.2f}pp)")
else:
    print(f"  ≈️  DIFERENCIA MARGINAL (<1% en BA, <3% en recall)")
    print(f"     No hay impacto significativo del sentimiento")

print("\n")
