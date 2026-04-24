"""
Script para probar la prediccion con el meta-ensemble.
"""
import sys
sys.path.insert(0, '.')

from backend.models.ensemble import predict_ensemble

ticker = 'KO'
print(f'Ejecutando prediccion para {ticker}...\n')

try:
    result = predict_ensemble(ticker)
    
    print('='*70)
    print('PREDICCION COMPLETADA')
    print('='*70)
    
    print(f'\nPRECIO ACTUAL: ${result["current_price"]:.2f}')
    
    print(f'\nTENDENCIA BiGRU (Ensemble): {result["trend"]}')
    print(f'   Confianza: {result["confidence"]:.2%}')
    print(f'   Precio predicho: ${result["predicted_price"]:.2f}')
    print(f'   Banda superior: ${result["price_upper"]:.2f}')
    print(f'   Banda inferior: ${result["price_lower"]:.2f}')
    print(f'   Retorno predicho: {result["predicted_return_pct"]:.2f}%')
    
    print(f'\nXGBOOST:')
    print(f'   Direccion: {result["xgboost_direction"]}')
    print(f'   Probabilidad: {result["xgboost_probability"]:.2%}')
    
    print(f'\nMETA-ENSEMBLE (BiGRU + XGBoost):')
    print(f'   Tendencia final: {result["meta_trend"]}')
    print(f'   Score: {result["meta_score"]:.4f}')
    
    print(f'\nPREDICCIONES INDIVIDUALES:')
    for pred in result["individual_predictions"]:
        print(f'   Modelo {pred["model_id"]}: {pred["predicted_return"]:+.4f}')
    
    print('='*70)
    
except FileNotFoundError as e:
    print(f'\nERROR: Modelos no encontrados.')
    print(f'   {e}')
    print(f'\nDebes entrenar los modelos primero con: python train_model.py')
    sys.exit(1)
except Exception as e:
    print(f'\nERROR durante la prediccion: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
