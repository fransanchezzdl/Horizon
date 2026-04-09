"""
Extract training results from Supabase after latest XGBoost training
"""
import sys
sys.path.insert(0, 'd:/Uni/TFG/Horizon')

from datetime import datetime
import pandas as pd

try:
    from backend.daos.activo_dao import ActivoDAO
    
    print("=" * 80)
    print("RESULTADOS DEL ÚLTIMO ENTRENAMIENTO - v4 + SENTIMENT LAG")
    print("=" * 80)
    print()
    
    # Get all activos from BD
    activos = ActivoDAO.obtener_todos()
    
    if not activos:
        print("❌ No se encontraron activos en la BD")
        sys.exit(1)
    
    # Extract metrics
    print(f"{'Ticker':<12} {'BA (%)':<12} {'Timestamp':<20} {'Status'}")
    print("─" * 60)
    
    metrics = []
    for activo in activos:
        ticker = getattr(activo, 'ticker', 'N/A')
        ba = getattr(activo, 'confianza_bygru', 0)
        updated = getattr(activo, 'updated_at', 'N/A')
        
        metrics.append({
            'ticker': ticker,
            'ba': ba,
            'updated_at': updated
        })
        
        print(f"{ticker:<12} {ba:>10.2%}   {str(updated):<20} ✓")
    
    print("─" * 60)
    
    # Calculate average
    ba_values = [m['ba'] for m in metrics if m['ba'] > 0]
    if ba_values:
        avg_ba = sum(ba_values) / len(ba_values)
        print(f"{'PROMEDIO':<12} {avg_ba:>10.2%}")
    
    print()
    print("=" * 80)
    print("BASELINE (v4 SIN SENTIMENT):")
    print("   BA = 34.25%, Recall = 55%")
    print()
    print("ESPERADO (v4 + SENTIMENT LAG):")
    print("   BA = 36-37%, Recall = 57-58%")
    print()
    
    if avg_ba > 35:
        print("✅ MEJORA DETECTADA: Sentimiento con LAG está funcionando!")
    elif avg_ba > 34:
        print("🟡 SIN CAMBIO SIGNIFICATIVO")
    else:
        print("⚠️  DEGRADACIÓN: Revisar configuración")
    
    print("=" * 80)
    
except Exception as e:
    print(f"❌ Error al acceder a BD: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
