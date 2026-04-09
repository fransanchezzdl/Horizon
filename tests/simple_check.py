"""
Quick check of training results from BD
"""
import sys
sys.path.insert(0, 'd:/Uni/TFG/Horizon')

print("Starting...")

try:
    print("1. Importing modules...")
    from backend.daos.activo_dao import ActivoDAO
    
    print("2. Getting activos from DB...")
    activos = ActivoDAO.obtener_todos()
    
    print(f"3. Found {len(activos)} activos")
    
    print("\nResults:")
    for activo in activos[:3]:
        ticker = getattr(activo, 'ticker', '?')
        ba = getattr(activo, 'confianza_bygru', 0)
        print(f"{ticker}: {ba:.2%}")
    
    print("\nDone!")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
