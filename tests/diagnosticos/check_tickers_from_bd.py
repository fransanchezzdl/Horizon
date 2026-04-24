"""
Script de prueba: Verifica qué activos se cargan desde la BD

Este script confirma que todos los activos de tu BD serán entrenados.
"""

import sys

print("\n" + "="*80)
print("🔍 VERIFICACIÓN DE TICKERS A ENTRENAR")
print("="*80)

# Intenta cargar desde BD
try:
    from backend.models.config import get_tickers_from_database, TICKERS
    
    print("\n📡 Intentando cargar desde BD Supabase...")
    bd_tickers = get_tickers_from_database()
    
    stable = bd_tickers.get("stable", [])
    volatile = bd_tickers.get("volatile", [])
    total = len(stable) + len(volatile)
    
    if total > 0:
        print(f"\n✅ Cargados exitosamente {total} tickers desde BD:\n")
        print(f"   STABLE ({len(stable)}):")
        for t in sorted(stable):
            print(f"      • {t}")
        
        print(f"\n   VOLATILE ({len(volatile)}):")
        for t in sorted(volatile):
            print(f"      • {t}")
        
        print(f"\n📊 Total a entrenar: {total} modelos")
        print(f"   Tiempo estimado: {total * 5} - {total * 8} minutos")
    else:
        print(f"\n⚠️  No se cargó nada de BD, usando configuración hardcoded")
        stable = TICKERS.get("stable", [])
        volatile = TICKERS.get("volatile", [])
        total = len(stable) + len(volatile)
        print(f"\n   Total fallback: {total} tickers")
        for t in sorted(stable + volatile):
            print(f"      • {t}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    print(f"\n⚠️  Usando configuración hardcoded")
    from backend.models.config import TICKERS
    stable = TICKERS.get("stable", [])
    volatile = TICKERS.get("volatile", [])
    total = len(stable) + len(volatile)
    print(f"\n   Total: {total} tickers")
    for t in sorted(stable + volatile):
        print(f"      • {t}")

print("\n" + "="*80)
print("\n✅ Para entrenar, ejecuta:")
print("   $env:USE_SENTIMENT=\"False\"; python -m backend.models.train_all\n")
print("="*80 + "\n")
