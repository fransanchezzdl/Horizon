#!/usr/bin/env python3
"""Diagnosticar caída de confianza BiGRU"""

from backend.daos.activo_dao import ActivoDAO
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Obtener confianzas de tabla activos
print("📊 CONFIANZAS ACTUALES (tabla activos)")
print("=" * 60)
response = supabase.table("activos").select("ticker, confianza_bygru").execute()
for row in response.data:
    ticker = row['ticker']
    conf = row.get('confianza_bygru')
    print(f"{ticker:6} | {conf if conf else 'NULL'}")

# Obtener promedio de confianzas en xai_explicaciones
print("\n📈 CONFIANZAS EN XAI_EXPLICACIONES (historial)")
print("=" * 60)
response = supabase.table("xai_explicaciones").select("ticker, confianza_prediccion").execute()

from collections import defaultdict
by_ticker = defaultdict(list)
for row in response.data:
    ticker = row['ticker']
    conf = row['confianza_prediccion']
    by_ticker[ticker].append(conf)

for ticker in sorted(by_ticker.keys()):
    confs = by_ticker[ticker]
    avg = sum(confs) / len(confs)
    min_c = min(confs)
    max_c = max(confs)
    print(f"{ticker:6} | Avg: {avg:.1%} | Min: {min_c:.1%} | Max: {max_c:.1%} | Count: {len(confs)}")

# Promedio general
all_confs = [c for confs in by_ticker.values() for c in confs]
print(f"\n🎯 PROMEDIO GENERAL XAI: {sum(all_confs)/len(all_confs):.1%}")
