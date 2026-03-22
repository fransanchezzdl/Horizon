#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test para verificar que usuarios_portfolios se esta guardando correctamente
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.database import supabase
from backend.daos.portfolio_dao import PortfolioDAO
from datetime import datetime

# TEST: Obtener un usuario de test
print("=" * 60)
print("TEST: Verificar usuarios_portfolios")
print("=" * 60)

# Obtener usuarios disponibles
try:
    usuarios_response = supabase.table("usuarios").select("id_usuario, email").limit(1).execute()
    if usuarios_response.data:
        test_usuario = usuarios_response.data[0]
        usuario_id = test_usuario['id_usuario']
        print("\n[OK] Usuario de test encontrado:")
        print("   ID: {}".format(usuario_id))
        print("   Email: {}".format(test_usuario.get('email', 'N/A')))
    else:
        print("[ERROR] No se encontraron usuarios en la BD")
        sys.exit(1)
except Exception as e:
    print("[ERROR] Error obteniendo usuarios: {}".format(e))
    sys.exit(1)

# TEST: Crear un nuevo portfolio
print("\n[INFO] Intentando crear portfolio...")
portfolio_data = {
    "id_usuario": usuario_id,
    "nombre_portfolio": "Test Portfolio {}".format(datetime.now().strftime('%H%M%S')),
    "descripcion": "Portfolio de test para verificar usuarios_portfolios",
    "riesgo": 0.5,
}

portfolio_id = PortfolioDAO.crear(portfolio_data)

if portfolio_id:
    print("\n[OK] Portfolio creado con ID: {}".format(portfolio_id))
    
    # Verificar que se guardo en usuario_portfolio
    print("\n[INFO] Verificando que la relacion se guardo en usuario_portfolio...")
    try:
        relacion_response = (
            supabase.table("usuario_portfolio")
            .select("*")
            .eq("id_usuario", usuario_id)
            .eq("id_portfolio", portfolio_id)
            .execute()
        )
        
        if relacion_response.data:
            print("[OK] Relacion encontrada en usuario_portfolio:")
            print("   {}".format(relacion_response.data[0]))
        else:
            print("[ERROR] NO se encontro relacion en usuario_portfolio")
            print("   Buscando: usuario={}, portfolio={}".format(usuario_id, portfolio_id))
            
            # Debug: Mostrar todas las relaciones del usuario
            todas_relaciones = (
                supabase.table("usuario_portfolio")
                .select("*")
                .eq("id_usuario", usuario_id)
                .execute()
            )
            print("\n   Todas las relaciones del usuario:")
            if todas_relaciones.data:
                for rel in todas_relaciones.data:
                    print("   - {}".format(rel))
            else:
                print("   No hay relaciones para este usuario")
                    
    except Exception as e:
        print("[ERROR] Error verificando relacion: {}".format(e))
else:
    print("[ERROR] No se pudo crear el portfolio")

print("\n" + "=" * 60)
