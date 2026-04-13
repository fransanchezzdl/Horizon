import sys
sys.path.insert(0, '.')

from backend.daos.explicacion_xai_dao import ExplicacionXAIDAO

# Get explanations for AAPL
stats = ExplicacionXAIDAO.obtener_estadisticas('AAPL')
total = stats.get('total', 0)
avg_conf = stats.get('confianza_promedio', 0)

print("AAPL Stats:")
print("  Total:", total)
print("  Avg Confidence:", f"{avg_conf:.2%}")

if total > 0:
    print("\nStatus: Confidence for AAPL = {}%".format(int(avg_conf * 100)))
