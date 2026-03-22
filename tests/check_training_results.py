"""
Script para verificar los resultados del entrenamiento.
"""
import os
import json

ticker = "KO"
report_path = f"backend/models/saved_models/{ticker}_report.json"

if os.path.exists(report_path):
    with open(report_path, 'r') as f:
        report = json.load(f)
    
    print('='*70)
    print(f'✅ RESULTADOS DEL ENTRENAMIENTO PARA {ticker}')
    print('='*70)
    
    metrics = report['metrics']
    print(f'\n📈 MÉTRICAS DEL ENSEMBLE BiGRU:')
    print(f'   • Directional Accuracy: {metrics["avg_directional_accuracy"]:.2%}')
    print(f'   • Precision (Alcista):  {metrics["avg_precision_up"]:.2%}')
    print(f'   • Recall (Alcista):     {metrics["avg_recall_up"]:.2%}')
    print(f'   • MAE:                  {metrics["avg_mae"]:.6f}')
    print(f'   • RMSE:                 {metrics["avg_rmse"]:.6f}')
    print(f'   • Baseline Naive:       {metrics["naive_baseline_accuracy"]:.2%}')
    
    if 'xgboost_metrics' in report:
        xgb_metrics = report['xgboost_metrics']
        print(f'\n🌳 MÉTRICAS DE XGBOOST:')
        print(f'   • Directional Accuracy: {xgb_metrics["xgb_directional_accuracy"]:.2%}')
        print(f'   • Precision (Alcista):  {xgb_metrics["xgb_precision_up"]:.2%}')
        print(f'   • Recall (Alcista):     {xgb_metrics["xgb_recall_up"]:.2%}')
        
        print(f'\n🔍 TOP 5 FEATURES MÁS IMPORTANTES (XGBoost):')
        feature_imp = xgb_metrics['feature_importance']
        for i, (feat, imp) in enumerate(list(feature_imp.items())[:5], 1):
            print(f'   {i}. {feat}: {imp:.4f}')
    else:
        print(f'\n⏳ XGBoost aún no se ha entrenado (entrenamiento en progreso)')
    
    improvement = metrics['avg_directional_accuracy'] - metrics["naive_baseline_accuracy"]
    print(f'\n💡 MEJORA SOBRE BASELINE: {improvement:+.2%}')
    
    print(f'\n📅 Entrenado: {report["trained_at"]}')
    print(f'🎯 Tipo de activo: {report["asset_type"]}')
    print(f'📊 Features usadas: {len(report["feature_cols"])} ({", ".join(report["feature_cols"][:5])}...)')
    print('='*70)
else:
    print(f'⏳ El entrenamiento aún no ha finalizado.')
    print(f'   Buscando: {report_path}')
    print(f'\n   El entrenamiento puede tardar 10-15 minutos.')
    print(f'   Ejecuta este script nuevamente en unos minutos.')
