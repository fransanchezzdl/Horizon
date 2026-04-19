#!/usr/bin/env python3
"""Verifica que las explicaciones XAI se guardaron correctamente en BD"""

import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# Setup
sys.path.insert(0, str(Path(__file__).parent))
load_dotenv()

from backend.daos.explicacion_xai_dao import ExplicacionXAIDAO
from collections import Counter

# Obtener todas las explicaciones
print("📊 Verificando explicaciones XAI en BD...")
print("=" * 80)

try:
    # Acceder directamente usando el DAO
    import os
    from supabase import create_client
    
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    response = supabase.table("xai_explicaciones").select("id, ticker, senal_prediccion, confianza_prediccion, fecha_prediccion").execute()
    
    data = response.data
    print(f"✅ Total de explicaciones: {len(data)}")
    
    if data:
        ticker_counts = Counter([r['ticker'] for r in data])
        print(f"\n📍 Distribución por ticker:")
        for ticker, count in sorted(ticker_counts.items()):
            print(f"   {ticker}: {count} explicación(es)")
        
        print(f"\n🎯 Últimas 3 explicaciones:")
        for row in data[-3:]:
            print(f"   - {row['ticker']}: {row['senal_prediccion']} (confianza: {row['confianza_prediccion']:.1%})")
    else:
        print("⚠️  No hay explicaciones en BD")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("=" * 80)
