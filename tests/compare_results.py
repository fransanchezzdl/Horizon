"""
Full training results comparison
"""
import sys
sys.path.insert(0, 'd:/Uni/TFG\Horizon')

from backend.daos.activo_dao import ActivoDAO

print("=" * 70)
print("V4 + LAG SENTIMENT - FULL RESULTS (FIXED PIPELINE)")
print("=" * 70)
print()

activos = ActivoDAO.obtener_todos()
activos_sorted = sorted(activos, key=lambda x: getattr(x, 'ticker', ''))

print(f"{'Ticker':<10} {'BA':<12} {'Last Updated':<30}")
print("─" * 70)

ba_values = []
for activo in activos_sorted:
    ticker = getattr(activo, 'ticker', 'N/A')
    ba = getattr(activo, 'confianza_bygru', 0)
    updated = getattr(activo, 'updated_at', 'N/A')
    
    ba_values.append(ba)
    print(f"{ticker:<10} {ba:>10.2%}   {str(updated):<30}")

print("─" * 70)

if ba_values:
    avg_ba = sum(ba_values) / len(ba_values)
    print(f"{'PROMEDIO':<10} {avg_ba:>10.2%}")

print()
print("=" * 70)
print("COMPARISON:")
print("=" * 70)
print(f"v4 SIN Sentimiento:      BA = 34.25%")
print(f"v4 + DistilRoBERTa:      BA = 34.20% (-0.05pp) ❌ FAIL")
print(f"v4 + LAG (Broken):       BA = 33.72% (-0.53pp) ❌ WORSE")
print(f"v4 + LAG (FIXED):        BA = {avg_ba:.2%}")

baseline = 0.3425
if avg_ba > baseline:
    improvement_abs = (avg_ba - baseline) * 100
    improvement = (avg_ba - baseline) / baseline * 100
    print(f"\n✅ MEJORA CONFIRMA DA: +{improvement_abs:.2f}pp (+{improvement:.2f}% relativo)")
    print(f"   Los 12 features de LAG están funcionando correctamente!")
elif avg_ba > 0.3420:
    print(f"\n🔄 COMPARABLE: Similar a v4+DistilRoBERTa pero sin la degradación")
elif avg_ba > 0.3372:
    improvement_abs = (avg_ba - 0.3372) * 100
    print(f"\n📊 PARCIALMENTE CORREGIDO: +{improvement_abs:.2f}pp vs versión anterior rota")
else:
    print(f"\n⚠️  TODAVÍA PEOR: {avg_ba:.2%} vs 34.25% baseline")
print("=" * 70)
