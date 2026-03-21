# 🔍 Análisis de Problemas en Actualización de `activos` Post-Entrenamiento

## 📋 Resumen Ejecutivo
Después del análisis del código, he identificado **3 problemas críticos** que impiden que la tabla `activos` se actualice correctamente:

---

## 🐛 Problema 1: Validación Deficiente en `DAO.actualizar()`
**Ubicación:** `backend/daos/activo_dao.py` - método `actualizar()`

### El Problema
```python
@staticmethod
def actualizar(ticker: str, update_data: Dict) -> bool:
    try:
        update_data["updated_at"] = datetime.now().isoformat()
        
        response = (
            supabase.table(ActivoDAO.TABLE)
            .update(update_data)
            .eq("ticker", ticker)
            .execute()
        )
        
        # ❌ PROBLEMA: Siempre retorna True sin verificar si la actualización fue exitosa
        print(f"✅ Activo {ticker} actualizado")
        return True  # <-- RETORNA TRUE INCLUSO SI FALLA
    
    except Exception as e:
        print(f"❌ Error actualizando activo {ticker}: {e}")
        return False
```

### Impacto
- **El método no valida que Supabase realmente actualizó los datos**
- Supabase retorna `response.data` vacío en operaciones UPDATE exitosas, pero podría haber errores silenciosos
- No se verifica que el row actualizado exista
- No se verifica que los campos acepten los valores enviados

### Síntomas
- El mensaje de éxito se imprime en `train_single_ticker.py`
- Pero los datos en BD NO se actualizan correctamente
- No hay error visible

---

## 🐛 Problema 2: Falta de Validación en `guardar_datos_post_entrenamiento()`
**Ubicación:** `backend/services/activo_update_service.py`

### El Problema
```python
@staticmethod
def guardar_datos_post_entrenamiento(
    ticker: str,
    ensemble_prediction: Dict,
    training_metrics: Optional[Dict] = None
) -> bool:
    try:
        precio_actual = float(ensemble_prediction.get("current_price", 0))
        senal_ia = ensemble_prediction.get("trend", "LATERAL")
        confianza = float(ensemble_prediction.get("confidence", 0))
        
        # Validar señal
        if senal_ia not in ["ALCISTA", "BAJISTA", "LATERAL"]:
            print(f"⚠️ Señal inválida: {senal_ia}, usando LATERAL")
            senal_ia = "LATERAL"
        
        # .... construcción de grafico_prediccion ....
        
        # ❌ PROBLEMA: No valida que los datos sean válidos ANTES de enviar
        # ❌ PROBLEMA: No controla excepciones específicas
        
        update_data = {
            "precio": precio_actual,
            "senal_ia": senal_ia,
            "confianza_bygru": confianza,
            "grafico_prediccion": grafico_prediccion
        }
        
        # ❌ confía ciegamente en que actualizar() retorna True
        success = activo_dao.actualizar(ticker, update_data)
        
        if success:
            print(f"✅ {ticker} actualizado post-entrenamiento:...")
        else:
            print(f"⚠️ No se pudo actualizar {ticker} en la BD")
        
        return success
    
    except Exception as e:
        print(f"Error: {e}")  # ❌ Captura genérica que oculta detalles
        return False
```

### Impactos Principales
1. **No valida tipos de datos**: `precio_actual` podría ser `None`
2. **No serializa `grafico_prediccion`**: Es un dict con floats que Supabase espera en formato JSON
3. **No verifica si el ticker existe** antes de actualizar
4. **Excepciones genéricas** que no ayudan al debug

---

## 🐛 Problema 3: Posible Rechazo de Campos por Supabase
**Ubicación:** Configuración de Supabase / tipos de datos

### El Problema
El campo `grafico_prediccion` es `JSONB` en PostgreSQL. Cuando se envía un dict de Python:

```python
grafico_prediccion = {
    "predicted_price": float(123.45),
    "training_metrics": {
        "avg_val_loss": float(0.0234),
        # ... más campos numéricos ...
    }
}
```

**Supabase puede rechazar esto si:**
- Los valores contienen `NaN` o `Infinity` (floats especiales)
- El JSON tiene ciclos o referencias circulares
- El JSON es demasiado grande (> 1GB por field)
- Hay tipos incompatibles con JSON standard

---

## ✅ Soluciones Recomendadas

### Solución 1: Mejorar Validación en DAO
**Archivo:** `backend/daos/activo_dao.py`

```python
@staticmethod
def actualizar(ticker: str, update_data: Dict) -> bool:
    """
    Actualiza un activo existente con validaciones robustas.
    
    Returns:
        bool: True si REALMENTE se actualizó, False si falló
    """
    try:
        # 1️⃣ Verificar que el activo existe
        existing = (
            supabase.table(ActivoDAO.TABLE)
            .select("ticker")
            .eq("ticker", ticker)
            .execute()
        )
        
        if not existing.data:
            print(f"❌ Activo {ticker} no existe en BD")
            return False
        
        # 2️⃣ Añadir timestamp
        update_data["updated_at"] = datetime.now().isoformat()
        
        # 3️⃣ Ejecutar actualización
        response = (
            supabase.table(ActivoDAO.TABLE)
            .update(update_data)
            .eq("ticker", ticker)
            .execute()
        )
        
        # 4️⃣ Verificar que se actualizó realmente
        if response.count is not None and response.count > 0:
            print(f"✅ Activo {ticker} actualizado correctamente ({response.count} filas afectadas)")
            return True
        elif response.status_code in [200, 204]:
            # Supabase puede no retornar count en algunos casos
            # Verificar haciendo un SELECT posterior
            verify = (
                supabase.table(ActivoDAO.TABLE)
                .select("updated_at")
                .eq("ticker", ticker)
                .execute()
            )
            if verify.data and verify.data[0]["updated_at"] == update_data["updated_at"]:
                print(f"✅ Activo {ticker} actualizado (verificado)")
                return True
        
        print(f"❌ La actualización de {ticker} no afectó filas")
        return False
    
    except Exception as e:
        print(f"❌ Error actualizando activo {ticker}: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
```

### Solución 2: Sanitizar JSON y Validar Datos
**Archivo:** `backend/services/activo_update_service.py`

```python
import json
import math

@staticmethod
def _sanitizar_json_para_supabase(obj) -> dict:
    """
    Convierte dict a JSON seguro para Supabase (sin NaN, Infinity, etc).
    """
    def converter(o):
        if isinstance(o, float):
            # NaN e Infinity no son válidos en JSON
            if math.isnan(o):
                return None
            elif math.isinf(o):
                return None if o > 0 else None
            return o
        raise TypeError(f"No serializable: {type(o)}")
    
    # Serializar y deserializar para asegurar validez
    json_str = json.dumps(obj, default=converter)
    return json.loads(json_str)

@staticmethod
def guardar_datos_post_entrenamiento(
    ticker: str,
    ensemble_prediction: Dict,
    training_metrics: Optional[Dict] = None
) -> bool:
    """
    Guarda datos post-entrenamiento con validaciones robustas.
    """
    try:
        # 1️⃣ Validaciones básicas
        if not ticker or not isinstance(ticker, str):
            print(f"❌ Ticker inválido: {ticker}")
            return False
        
        # 2️⃣ Extraer y validar precio
        precio_actual = ensemble_prediction.get("current_price")
        if precio_actual is None or not isinstance(precio_actual, (int, float)):
            print(f"❌ Precio inválido: {precio_actual}")
            return False
        precio_actual = float(precio_actual)
        
        # 3️⃣ Validar señal
        senal_ia = ensemble_prediction.get("trend", "LATERAL")
        if senal_ia not in ["ALCISTA", "BAJISTA", "LATERAL"]:
            print(f"⚠️ Señal inválida '{senal_ia}', usando LATERAL")
            senal_ia = "LATERAL"
        
        # 4️⃣ Validar confianza
        confianza = ensemble_prediction.get("confidence", 0)
        if not isinstance(confianza, (int, float)) or confianza < 0 or confianza > 1:
            print(f"⚠️ Confianza inválida: {confianza}, usando 0")
            confianza = 0
        confianza = float(confianza)
        
        # 5️⃣ Construir y sanitizar grafico_prediccion
        grafico_raw = {
            "predicted_price": float(ensemble_prediction.get("predicted_price", 0)),
            "price_upper": float(ensemble_prediction.get("price_upper", 0)),
            "price_lower": float(ensemble_prediction.get("price_lower", 0)),
            "predicted_return": float(ensemble_prediction.get("predicted_return", 0)),
            "predicted_return_pct": float(ensemble_prediction.get("predicted_return_pct", 0)),
            "meta_trend": ensemble_prediction.get("meta_trend", "LATERAL"),
            "meta_score": float(ensemble_prediction.get("meta_score", 0)),
            "xgboost_direction": ensemble_prediction.get("xgboost_direction", "NEUTRAL"),
            "xgboost_probability": float(ensemble_prediction.get("xgboost_probability", 0)),
            "n_individual_models": len(ensemble_prediction.get("individual_predictions", [])),
        }
        
        if training_metrics:
            grafico_raw["training_metrics"] = {
                "avg_val_loss": float(training_metrics.get("avg_val_loss", 0)),
                "avg_directional_accuracy": float(training_metrics.get("avg_directional_accuracy", 0)),
                "avg_mae": float(training_metrics.get("avg_mae", 0)),
                "avg_rmse": float(training_metrics.get("avg_rmse", 0)),
                "dynamic_threshold": float(training_metrics.get("dynamic_threshold", 0)),
                "xgb_directional_accuracy": training_metrics.get("xgb_directional_accuracy"),
            }
        
        # Sanitizar para JSON safety
        grafico_prediccion = ActivoUpdateService._sanitizar_json_para_supabase(grafico_raw)
        
        # 6️⃣ Preparar datos para actualizar
        update_data = {
            "precio": precio_actual,
            "senal_ia": senal_ia,
            "confianza_bygru": confianza,
            "grafico_prediccion": grafico_prediccion
        }
        
        # 7️⃣ Intentar actualizar
        success = activo_dao.actualizar(ticker, update_data)
        
        if success:
            print(f"\n✅ {ticker} actualizado exitosamente:")
            print(f"   • Precio: ${precio_actual:.2f}")
            print(f"   • Señal: {senal_ia}")
            print(f"   • Confianza: {confianza:.2%}")
            print(f"   • Gráfico: {len(grafico_prediccion)} campos")
        else:
            print(f"\n❌ Error actualizando {ticker}")
        
        return success
    
    except Exception as e:
        print(f"\n❌ Excepción en guardar_datos_post_entrenamiento:")
        print(f"   Ticker: {ticker}")
        print(f"   Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
```

### Solución 3: Añadir Logging y Debug
**Archivo:** `train_single_ticker.py`

```python
# Después de guardar
success = activo_update_service.guardar_datos_post_entrenamiento(
    ticker,
    ensemble_pred,
    training_metrics_to_save
)

if success:
    print(f"\n✅ ¡Datos guardados exitosamente en BD para {ticker}!")
    
    # Verificación adicional: leer de la BD para confirmar
    try:
        from backend.services.activo_service import activo_service
        activo_guardado = activo_service.obtener_activo(ticker)
        if activo_guardado:
            print(f"\n📋 Verificación - Datos en BD:")
            print(f"   • Precio: {activo_guardado.get('precio')}")
            print(f"   • Señal: {activo_guardado.get('senal_ia')}")
            print(f"   • Confianza: {activo_guardado.get('confianza_bygru')}")
    except Exception as e:
        print(f"⚠️ No se pudo verificar: {e}")
else:
    print(f"\n❌ Error al guardar en BD")
```

---

## 📊 Checklist para la Corrección

- [ ] **Paso 1:** Implementar validación mejorada en `activo_dao.py`
- [ ] **Paso 2:** Agregar sanitización JSON en `activo_update_service.py`
- [ ] **Paso 3:** Añadir verificación post-guardado en `train_single_ticker.py`
- [ ] **Paso 4:** Probar entrenamiento de un ticker (ej: KO)
- [ ] **Paso 5:** Verificar en BD que precio, señal y confianza se guardaron
- [ ] **Paso 6:** Verificar que `grafico_prediccion` es válido JSON

---

## 🧪 Cómo Probar las Correcciones

```bash
# 1. Entrenar un ticker
python train_single_ticker.py KO

# 2. Verificar en BD
SELECT ticker, precio, senal_ia, confianza_bygru, grafico_prediccion, updated_at 
FROM activos 
WHERE ticker = 'KO';

# 3. Verificar que grafico_prediccion tiene contenido
SELECT grafico_prediccion::text 
FROM activos 
WHERE ticker = 'KO';
```

---

## 💡 Recomendaciones Adicionales

1. **Logging centralizado:** Implementar logger en lugar de prints
2. **Transacciones:** Considerar transacciones BD para mayor atomicidad
3. **Retry mechanism:** Añadir reintentos en caso de fallos temporales
4. **Tests unitarios:** Mock de Supabase para probar sin BD real

