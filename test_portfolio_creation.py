"""
Script para debugar la creación de portfolios y verificar que se guarda el id_usuario correctamente.
"""
import sys
sys.path.insert(0, 'backend')

from backend.database import supabase
from datetime import datetime

# Datos de test - reemplaza con el UUID del usuario autenticado
TEST_USER_ID = "test-user-uuid-here"  # Necesitas obtener esto del token del usuario

def test_insert_portfolio():
    """Test de INSERT directo para crear portfolio."""
    print("=" * 60)
    print("TEST 1: INSERT Directo en tabla portfolios")
    print("=" * 60)
    
    portfolio_data = {
        "id_usuario": TEST_USER_ID,
        "nombre_portfolio": "Test Portfolio",
        "descripcion": "Portfolio de prueba",
        "riesgo": 0.5,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    print(f"\n📝 Insertando portfolio con datos:")
    for key, value in portfolio_data.items():
        print(f"   {key}: {value}")
    
    try:
        response = (
            supabase.table("portfolios")
            .insert(portfolio_data)
            .execute()
        )
        
        print(f"\n✅ INSERT exitoso")
        print(f"Response data: {response.data}")
        
        if response.data:
            portfolio_id = response.data[0].get('id_portfolio')
            print(f"\n📌 Portfolio creado con ID: {portfolio_id}")
            return portfolio_id
        else:
            print(f"\n❌ No se retornaron datos después del INSERT")
            return None
            
    except Exception as e:
        print(f"\n❌ Error en INSERT: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_select_portfolio(portfolio_id: int):
    """Test de SELECT para obtener el portfolio creado."""
    print("\n" + "=" * 60)
    print(f"TEST 2: SELECT del portfolio {portfolio_id}")
    print("=" * 60)
    
    try:
        response = (
            supabase.table("portfolios")
            .select("*")
            .eq("id_portfolio", portfolio_id)
            .execute()
        )
        
        print(f"\n✅ SELECT exitoso")
        print(f"Response data: {response.data}")
        
        if response.data:
            portfolio = response.data[0]
            print(f"\n📋 Portfolio recuperado:")
            for key, value in portfolio.items():
                print(f"   {key}: {value}")
            
            # Verificar que el id_usuario coincide
            retrieved_user_id = portfolio.get('id_usuario')
            print(f"\n🔍 Verificación:")
            print(f"   ID usuario esperado: {TEST_USER_ID}")
            print(f"   ID usuario recuperado: {retrieved_user_id}")
            print(f"   ¿Coinciden?: {TEST_USER_ID == retrieved_user_id}")
            
            return portfolio
        else:
            print(f"\n❌ Portfolio no encontrado en BD")
            return None
            
    except Exception as e:
        print(f"\n❌ Error en SELECT: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_select_by_user():
    """Test de SELECT filtrando por id_usuario."""
    print("\n" + "=" * 60)
    print(f"TEST 3: SELECT de portfolios del usuario {TEST_USER_ID}")
    print("=" * 60)
    
    try:
        response = (
            supabase.table("portfolios")
            .select("*")
            .eq("id_usuario", TEST_USER_ID)
            .execute()
        )
        
        print(f"\n✅ SELECT exitoso")
        print(f"Total portfolios encontrados: {len(response.data)}")
        
        for i, portfolio in enumerate(response.data):
            print(f"\n   Portfolio {i+1}:")
            for key, value in portfolio.items():
                print(f"      {key}: {value}")
        
        return response.data
            
    except Exception as e:
        print(f"\n❌ Error en SELECT: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_delete_portfolio(portfolio_id: int):
    """Test de DELETE para limpiar datos de test."""
    print("\n" + "=" * 60)
    print(f"TEST 4: DELETE del portfolio {portfolio_id}")
    print("=" * 60)
    
    try:
        response = (
            supabase.table("portfolios")
            .delete()
            .eq("id_portfolio", portfolio_id)
            .execute()
        )
        
        print(f"\n✅ DELETE exitoso")
        return True
            
    except Exception as e:
        print(f"\n❌ Error en DELETE: {e}")
        return False


if __name__ == "__main__":
    # Verificar que TEST_USER_ID no es el valor por defecto
    if TEST_USER_ID == "test-user-uuid-here":
        print("⚠️  IMPORTANTE: Necesitas actualizar TEST_USER_ID con el UUID real del usuario")
        print("\n¿Qué UUID usar?")
        print("1. Obtén el UUID de usuarios autenticados en Supabase")
        print("2. O ejecuta: SELECT id FROM auth.users LIMIT 1")
        print("3. Reemplaza 'test-user-uuid-here' con el valor real")
        sys.exit(1)
    
    print("\n🚀 Iniciando tests de creación de portfolio...\n")
    
    # Test 1: INSERT
    portfolio_id = test_insert_portfolio()
    
    if portfolio_id:
        # Test 2: SELECT
        portfolio = test_select_portfolio(portfolio_id)
        
        # Test 3: SELECT por usuario
        test_select_by_user()
        
        # Test 4: LIMPIAR
        test_delete_portfolio(portfolio_id)
        
        print("\n" + "=" * 60)
        print("✅ Todos los tests completados")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ No se pudo crear el portfolio - ver errores arriba")
        print("=" * 60)
