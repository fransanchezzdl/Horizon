"""
Script de prueba para verificar la integración de Alpha Vantage.

Verifica que:
1. La configuración esté correcta
2. Las features se añadan correctamente
3. El conteo de features sea el esperado
"""

import sys
import os

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.models.config import (
    USE_ADVANCED_FEATURES,
    USE_SENTIMENT,
    get_feature_cols,
    get_asset_type,
    ADVANCED_TECHNICAL_COLS,
)
from backend.models.data_pipeline import download_data, compute_features


def test_configuration():
    """Verifica la configuración actual."""
    print("=" * 60)
    print("VERIFICACIÓN DE CONFIGURACIÓN")
    print("=" * 60)
    print(f"USE_SENTIMENT: {USE_SENTIMENT}")
    print(f"USE_ADVANCED_FEATURES: {USE_ADVANCED_FEATURES}")
    print()


def test_feature_count():
    """Verifica el conteo de features para diferentes tickers."""
    print("=" * 60)
    print("CONTEO DE FEATURES")
    print("=" * 60)
    
    test_tickers = ["KO", "TSLA"]  # Uno estable, uno volátil
    
    for ticker in test_tickers:
        asset_type = get_asset_type(ticker)
        feature_cols = get_feature_cols(ticker)
        
        print(f"\n{ticker} ({asset_type}):")
        print(f"  Total features: {len(feature_cols)}")
        
        # Conteo esperado
        base_count = 9 if asset_type == "stable" else 11
        expected = base_count
        if USE_SENTIMENT:
            expected += 3
        if USE_ADVANCED_FEATURES:
            expected += 10  # Solo 10 features avanzadas seleccionadas
        
        print(f"  Esperado: {expected}")
        print(f"  ✅ Correcto" if len(feature_cols) == expected else f"  ❌ Error")
    
    print()


def test_data_pipeline(ticker="KO"):
    """Prueba el pipeline completo de datos."""
    print("=" * 60)
    print(f"PRUEBA DE PIPELINE DE DATOS ({ticker})")
    print("=" * 60)
    
    try:
        # Descargar datos
        print(f"1. Descargando datos de {ticker}...")
        df = download_data(ticker)
        print(f"   ✅ Descargados {len(df)} filas")
        
        # Calcular features
        print(f"2. Calculando features...")
        asset_type = get_asset_type(ticker)
        include_market_context = asset_type == "volatile"
        df_features = compute_features(
            df,
            include_market_context=include_market_context,
            ticker=ticker
        )
        print(f"   ✅ Calculadas {len(df_features.columns)} features")
        
        # Verificar features técnicas avanzadas
        if USE_ADVANCED_FEATURES:
            adv_features_present = [
                col for col in ADVANCED_TECHNICAL_COLS
                if col in df_features.columns
            ]
            print(f"3. Features técnicas avanzadas:")
            print(f"   Presentes: {len(adv_features_present)}/{len(ADVANCED_TECHNICAL_COLS)}")
            
            if len(adv_features_present) == len(ADVANCED_TECHNICAL_COLS):
                print(f"   ✅ Todas las features avanzadas presentes")
            else:
                print(f"   ⚠️  Faltan features avanzadas")
                missing = set(ADVANCED_TECHNICAL_COLS) - set(adv_features_present)
                print(f"   Faltantes: {missing}")
        
        # Mostrar primeras filas
        print(f"\n4. Primeras 3 filas de features:")
        print(df_features.head(3))
        
        print(f"\n✅ Pipeline completado exitosamente")
        return True
        
    except Exception as e:
        print(f"\n❌ Error en pipeline: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ejecuta todas las pruebas."""
    print("\n" + "=" * 60)
    print("PRUEBA DE INTEGRACIÓN ALPHA VANTAGE")
    print("=" * 60 + "\n")
    
    # 1. Verificar configuración
    test_configuration()
    
    # 2. Verificar conteo de features
    test_feature_count()
    
    # 3. Probar pipeline de datos
    success = test_data_pipeline("KO")
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    
    if success:
        print("✅ Todas las pruebas pasaron correctamente")
        print("\nPróximos pasos:")
        print("1. Asegúrate de que USE_ADVANCED_FEATURES=True en backend/.env")
        print("2. Reentrena el modelo: python train_model.py KO")
        print("3. Compara el accuracy antes y después")
        print("4. Las 10 features técnicas avanzadas se calculan localmente (sin API)")
    else:
        print("❌ Algunas pruebas fallaron")
        print("\nRevisa los errores arriba y verifica:")
        print("1. Que todas las dependencias estén instaladas")
        print("2. Que los archivos de configuración sean correctos")
        print("3. Que tengas conexión a internet para descargar datos")
    
    print()


if __name__ == "__main__":
    main()
