#!/usr/bin/env python3
"""
Test simple para verificar si podemos actualizar activos sin problemas de RLS.
Ahora usa UPSERT en lugar de UPDATE.
"""

from backend.database import supabase
from datetime import datetime

ticker = "KO"

# Test 1: UPSERT simple (solo precio)
print("=" * 60)
print(f"Test 1: UPSERT SIMPLE (precio + campos clave)")
print("=" * 60)

try:
    response = (
        supabase.table("activos")
        .upsert({
            "ticker": ticker,
            "nombre_completo": "The Coca-Cola Company",
            "precio": 99.99,
            "updated_at": datetime.now().isoformat()
        })
        .execute()
    )
    
    print(f"✅ Response count: {response.count}")
    print(f"✅ Response data: {response.data}")
    
    # Verificar que se guardó
    verify = supabase.table("activos").select("precio").eq("ticker", ticker).execute()
    print(f"✅ Precio en BD ahora: {verify.data[0]['precio']}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 2: UPSERT con JSON
print("\n" + "=" * 60)
print(f"Test 2: UPSERT CON JSON (grafico_prediccion)")
print("=" * 60)

try:
    json_data = {"test": "value", "number": 123}
    response = (
        supabase.table("activos")
        .upsert({
            "ticker": ticker,
            "nombre_completo": "The Coca-Cola Company",
            "senal_ia": "ALCISTA",
            "grafico_prediccion": json_data,
            "updated_at": datetime.now().isoformat()
        })
        .execute()
    )
    
    print(f"✅ Response count: {response.count}")
    print(f"✅ Response data: {response.data}")
    
    # Verificar que se guardó
    verify = supabase.table("activos").select("senal_ia, grafico_prediccion").eq("ticker", ticker).execute()
    print(f"✅ Senal en BD: {verify.data[0]['senal_ia']}")
    print(f"✅ Grafico en BD: {verify.data[0]['grafico_prediccion']}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

