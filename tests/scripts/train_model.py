"""
Script de entrenamiento del modelo Horizon.
"""
import sys
sys.path.insert(0, '.')

print('Iniciando entrenamiento del modelo Horizon...\n')

from backend.models.ensemble import train_ensemble

ticker = 'KO'
print(f'Entrenando ensemble para {ticker}...\n')

try:
    report = train_ensemble(ticker)
    
    print('\n' + '='*70)
    print('ENTRENAMIENTO COMPLETADO')
    print('='*70)
    
    print(f'\nMETRICAS DEL ENSEMBLE BiGRU:')
    print(f'   Directional Accuracy: {report["avg_directional_accuracy"]:.2%}')
    print(f'   Precision (Alcista):  {report["avg_precision_up"]:.2%}')
    print(f'   Recall (Alcista):     {report["avg_recall_up"]:.2%}')
    print(f'   MAE:                  {report["avg_mae"]:.6f}')
    print(f'   RMSE:                 {report["avg_rmse"]:.6f}')
    
    if report.get('xgb_directional_accuracy'):
        print(f'\nMETRICAS DE XGBOOST:')
        print(f'   Directional Accuracy: {report["xgb_directional_accuracy"]:.2%}')
        print(f'   Precision (Alcista):  {report["xgb_precision_up"]:.2%}')
        print(f'   Recall (Alcista):     {report["xgb_recall_up"]:.2%}')
        
        if report.get('xgb_feature_importance'):
            print(f'\nTOP 5 FEATURES MAS IMPORTANTES (XGBoost):')
            feature_imp = report['xgb_feature_importance']
            for i, (feat, imp) in enumerate(list(feature_imp.items())[:5], 1):
                print(f'   {i}. {feat}: {imp:.4f}')
    
    print(f'\nInforme completo guardado en: backend/models/saved_models/{ticker}_report.json')
    print('='*70)
    
except Exception as e:
    print(f'\nERROR durante el entrenamiento: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
