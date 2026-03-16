"""
Script de prueba para entrenar el modelo Horizon con análisis de sentimiento.
"""
import sys
sys.path.insert(0, '.')

print('🚀 Iniciando entrenamiento del modelo Horizon con análisis de sentimiento...\n')

from backend.models.ensemble import train_ensemble

# Entrenar con Coca-Cola (activo estable)
ticker = 'KO'
print(f'📊 Entrenando ensemble para {ticker}...\n')

try:
    report = train_ensemble(ticker)
    
    print('\n' + '='*70)
    print('✅ ENTRENAMIENTO COMPLETADO')
    print('='*70)
    
    # Mostrar métricas principales
    metrics = report['metrics']
    print(f'\n📈 MÉTRICAS DEL ENSEMBLE BiGRU:')
    print(f'   • Directional Accuracy: {metrics["avg_directional_accuracy"]:.2%}')
    print(f'   • Precision (Alcista):  {metrics["avg_precision_up"]:.2%}')
    print(f'   • Recall (Alcista):     {metrics["avg_recall_up"]:.2%}')
    print(f'   • MAE:                  {metrics["avg_mae"]:.6f}')
    print(f'   • RMSE:                 {metrics["avg_rmse"]:.6f}')
    print(f'   • Baseline Naive:       {metrics["naive_baseline_accuracy"]:.2%}')
    
    # Mostrar métricas de XGBoost
    xgb_metrics = report['xgboost_metrics']
    print(f'\n🌳 MÉTRICAS DE XGBOOST:')
    print(f'   • Directional Accuracy: {xgb_metrics["xgb_directional_accuracy"]:.2%}')
    print(f'   • Precision (Alcista):  {xgb_metrics["xgb_precision_up"]:.2%}')
    print(f'   • Recall (Alcista):     {xgb_metrics["xgb_recall_up"]:.2%}')
    
    # Mostrar top 5 features más importantes
    print(f'\n🔍 TOP 5 FEATURES MÁS IMPORTANTES (XGBoost):')
    feature_imp = xgb_metrics['feature_importance']
    for i, (feat, imp) in enumerate(list(feature_imp.items())[:5], 1):
        print(f'   {i}. {feat}: {imp:.4f}')
    
    # Comparación con baseline
    improvement = metrics['avg_directional_accuracy'] - metrics['naive_baseline_accuracy']
    print(f'\n💡 MEJORA SOBRE BASELINE: {improvement:+.2%}')
    
    print(f'\n📁 Informe completo guardado en: backend/models/saved_models/{ticker}_report.json')
    print('='*70)
    
except Exception as e:
    print(f'\n❌ ERROR durante el entrenamiento: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
