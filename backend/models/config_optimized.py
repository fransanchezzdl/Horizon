"""
Configuración optimizada con selección de features basada en correlación.

Usa solo las features técnicas avanzadas con mayor correlación con el target.
"""

# Features técnicas avanzadas optimizadas (solo las 10 con mayor correlación)
# Basado en análisis de correlación con el target para KO:
# 1. CMF: 0.0954
# 2. OBV: 0.0699  
# 3. Aroon_Up: 0.0666
# 7. DX: 0.0408
# 8. TSI: 0.0407
# 9. KST: 0.0405
# 10. Aroon_Down: 0.0402
# 11. CCI: 0.0391
# 12. CMO: 0.0368
# 13. Ultimate_Osc: 0.0310

OPTIMIZED_ADVANCED_TECHNICAL_COLS = [
    # Top 10 features técnicas avanzadas por correlación
    "CMF",           # Chaikin Money Flow (0.0954)
    "OBV",           # On Balance Volume (0.0699)
    "Aroon_Up",      # Aroon Up (0.0666)
    "DX",            # Directional Movement (0.0408)
    "TSI",           # True Strength Index (0.0407)
    "KST",           # Know Sure Thing (0.0405)
    "Aroon_Down",    # Aroon Down (0.0402)
    "CCI",           # Commodity Channel Index (0.0391)
    "CMO",           # Chande Momentum Oscillator (0.0368)
    "Ultimate_Osc",  # Ultimate Oscillator (0.0310)
]

# Features eliminadas por baja correlación (<0.03):
# - ADX: 0.0003
# - Stochastic_D: 0.0027
# - MFI: 0.0030
# - Volume_Ratio: 0.0039 (de features base, mantener por ahora)
# - ROC: 0.0102
# - Stochastic_K: 0.0119
# - Williams_R: 0.0145
# - Keltner_PctB: 0.0177
# - Donchian_PctB: 0.0195
