-- Tabla para guardar explicaciones XAI por predicción
-- Guardamos histórico completo para análisis posterior

-- Nota: Si tienes conflictos con nombres, elimina las tablas viejas manualmente desde Supabase SQL primero
-- Luego ejecuta este script

-- Secuencias para IDs (deben crearse ANTES de las tablas)
CREATE SEQUENCE IF NOT EXISTS xai_explicaciones_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS xai_validacion_id_seq START 1;

CREATE TABLE IF NOT EXISTS public.xai_explicaciones (
  id bigint PRIMARY KEY DEFAULT nextval('xai_explicaciones_id_seq'::regclass),
  
  -- Identificación de la predicción
  ticker text NOT NULL REFERENCES public.activos(ticker) ON DELETE CASCADE,
  fecha_prediccion timestamp with time zone NOT NULL DEFAULT now(),
  
  -- SHAP Analysis
  shap_valores jsonb NOT NULL,  -- Array of {feature_name, shap_value, feature_value}
  shap_grafico text NOT NULL,  -- Base64 encoded SHAP force plot image
  
  -- Feature Importance (Top 20)
  features_top20 jsonb NOT NULL,  -- Array of {feature_name, importancia, contribucion}
  
  -- BiGRU Attention Weights (si aplica)
  pesos_atencion jsonb,  -- Array of {dia, peso_atencion} (temporal patterns)
  
  -- Feature Contribution (cómo cada feature empuja a la predicción)
  contribucion_features jsonb NOT NULL,  -- {feature_name: contribution_value}
  
  -- Metadata
  senal_prediccion text NOT NULL CHECK (senal_prediccion IN ('ALCISTA', 'BAJISTA', 'LATERAL')),
  confianza_prediccion numeric NOT NULL,  -- Confidence score de Platt Scaling
  prediccion_correcta boolean,  -- NULL si no se ha validado, TRUE/FALSE después
  
  -- Feature del modelo
  version_modelo text NOT NULL DEFAULT 'Phase3',  -- Para tracking si reentrenamos
  seed_modelo integer DEFAULT 42,
  
  -- Timestamps
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Índices para queries rápidas
CREATE INDEX IF NOT EXISTS idx_xai_explicaciones_ticker ON public.xai_explicaciones(ticker);
CREATE INDEX IF NOT EXISTS idx_xai_explicaciones_fecha ON public.xai_explicaciones(fecha_prediccion DESC);
CREATE INDEX IF NOT EXISTS idx_xai_explicaciones_ticker_fecha ON public.xai_explicaciones(ticker, fecha_prediccion DESC);

-- Tabla para guardar métricas de validación XAI
-- Permite saber si las explicaciones son realmente útiles
CREATE TABLE IF NOT EXISTS public.xai_validacion (
  id bigint PRIMARY KEY DEFAULT nextval('xai_validacion_id_seq'::regclass),
  
  id_explicacion bigint NOT NULL REFERENCES public.xai_explicaciones(id) ON DELETE CASCADE,
  
  -- User feedback (si el usuario dice si la explicación fue útil)
  util boolean,  -- TRUE = útil, FALSE = no útil, NULL = no validado
  comentario_usuario text,
  
  -- Auto-validation
  shap_consistency numeric,  -- 0-1. Qué tan consistentes son los SHAP values entre predicciones similares
  feature_stability numeric,  -- 0-1. Qué tan estables son los top features entre predicciones
  
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Comentarios para documentación
COMMENT ON TABLE public.xai_explicaciones IS 'Explicaciones XAI para cada predicción - SHAP, feature importance, attention weights';
COMMENT ON TABLE public.xai_validacion IS 'Validación de calidad de explicaciones XAI';
COMMENT ON COLUMN public.xai_explicaciones.shap_valores IS 'Array JSONB: [{feature_name, shap_value, feature_value, shap_abs}, ...]';
COMMENT ON COLUMN public.xai_explicaciones.features_top20 IS 'Top 20 features por importancia: [{feature_name, importancia, contribucion_a_prediccion}, ...]';
COMMENT ON COLUMN public.xai_explicaciones.pesos_atencion IS 'Attention weights del BiGRU: [{dia_relativo, peso_atencion}, ...] para ver qué días pasados importan';
COMMENT ON COLUMN public.xai_explicaciones.contribucion_features IS 'Cómo cada feature contribuye a ALCISTA/BAJISTA: {feature_name: +0.15 o -0.10, ...}';
