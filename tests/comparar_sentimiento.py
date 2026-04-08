import re
from pathlib import Path

def extract_results(filepath):
    """Extrae BA y Recall de cada ticker del log"""
    if not Path(filepath).exists():
        print(f"Archivo no encontrado: {filepath}")
        return {}
    
    results = {}
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    # Buscar bloques "XGBoost TICKER VALIDATION RESULTS"
    # Formato: "Balanced Accuracy:    35.47% (metrics principal)"
    # Formato: "Recall (ALCISTA):     24.14%"
    
    pattern = r'XGBoost\s+(\w+)\s+VALIDATION RESULTS:.*?Balanced Accuracy:\s+([\d.]+)%.*?Recall \(ALCISTA\):\s+([\d.]+)%'
    matches = re.findall(pattern, content, re.DOTALL)
    
    for ticker, ba, recall in matches:
        results[ticker] = {
            'ba': float(ba),
            'recall': float(recall)
        }
    
    return results

# Extraer resultados
sin_sentimiento = extract_results('entrenamiento_v4_sin_sentimiento.txt')
con_sentimiento = extract_results('entrenamiento_v4_con_sentimiento.txt')

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
    
    total_ba_sin += ba_s
    total_ba_con += ba_c
    total_recall_sin += rec_s
    total_recall_con += rec_c
    
    if delta_ba > 0.5:
        mejoras_ba += 1
    if delta_rec > 2:
        mejoras_recall += 1

print("-"*110)
avg_ba_sin = total_ba_sin / len(all_tickers) if all_tickers else 0
avg_ba_con = total_ba_con / len(all_tickers) if all_tickers else 0
avg_rec_sin = total_recall_sin / len(all_tickers) if all_tickers else 0
avg_rec_con = total_recall_con / len(all_tickers) if all_tickers else 0

print(f"{'PROMEDIO':<8} | {avg_ba_sin:>7.2f}% | {avg_ba_con:>7.2f}% | {avg_ba_con - avg_ba_sin:>+5.2f}% | {avg_rec_sin:>7.2f}% | {avg_rec_con:>7.2f}% | {avg_rec_con - avg_rec_sin:>+5.2f}%")
print("="*110)

print(f"\n📊 RESUMEN DE CAMBIOS:")
print(f"  • Tickers con BA mejorada: {mejoras_ba}/{len(all_tickers)}")
print(f"  • Tickers con Recall mejorado: {mejoras_recall}/{len(all_tickers)}")
print(f"  • Cambio neto en BA: {avg_ba_con - avg_ba_sin:+.2f}%")
print(f"  • Cambio neto en Recall: {avg_rec_con - avg_rec_sin:+.2f}%")

# Mejor métrica
print(f"\n📈 ANÁLISIS:")
if abs(avg_ba_con - avg_ba_sin) > 1 or abs(avg_rec_con - avg_rec_sin) > 3:
    if avg_ba_con > avg_ba_sin and avg_rec_con > avg_rec_sin:
        print(f"  ✅ SENTIMIENTO AYUDA: Mejora significativa en ambas métricas")
    elif avg_ba_sin > avg_ba_con and avg_rec_sin > avg_rec_con:
        print(f"  ✅ SENTIMIENTO PERJUDICA: Empeora en ambas métricas")
    else:
        print(f"  ⚖️  RESULTADOS MIXTOS: Sentimiento mejora en algunas métricas, empeora en otras")
else:
    print(f"  ≈️  DIFERENCIA MARGINAL: Cambios muy pequeños, no es definitivo")
