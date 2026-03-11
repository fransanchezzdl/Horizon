-- =====================================================
-- MIGRACIÓN COMPLETA — TFG-Horizon
-- Fecha: 10/03/2026
-- Ejecutar en: Supabase → SQL Editor
-- IMPORTANTE: Ejecutar de arriba a abajo en orden
-- =====================================================


-- =====================================================
-- PASO 0: FUNCIÓN AUXILIAR PARA updated_at AUTOMÁTICO
-- =====================================================
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- =====================================================
-- PASO 1: TABLA usuarios — Añadir foto_perfil
-- =====================================================
ALTER TABLE public.usuarios
  ADD COLUMN IF NOT EXISTS foto_perfil TEXT;


-- =====================================================
-- PASO 2: TABLA activos — Reestructuración completa
-- =====================================================

-- 2.1 Eliminar columna 'tamano' (sin valor analítico)
ALTER TABLE public.activos
  DROP COLUMN IF EXISTS tamano;

-- 2.2 Convertir 'estabilidad' de TEXT a BOOLEAN
--     Alta/Estable → TRUE | Media/Baja → FALSE
ALTER TABLE public.activos
  ADD COLUMN IF NOT EXISTS estabilidad_bool BOOLEAN;

UPDATE public.activos
SET estabilidad_bool = CASE
  WHEN LOWER(estabilidad) IN ('alta', 'estable') THEN TRUE
  ELSE FALSE
END
WHERE estabilidad IS NOT NULL;

ALTER TABLE public.activos
  DROP COLUMN IF EXISTS estabilidad;

ALTER TABLE public.activos
  RENAME COLUMN estabilidad_bool TO estabilidad;

-- 2.3 Añadir nuevas columnas
ALTER TABLE public.activos
  ADD COLUMN IF NOT EXISTS logo_activo        TEXT,
  ADD COLUMN IF NOT EXISTS precio             NUMERIC(20,8),
  ADD COLUMN IF NOT EXISTS confianza_bygru    NUMERIC(5,4),
  ADD COLUMN IF NOT EXISTS senal_ia           TEXT,
  ADD COLUMN IF NOT EXISTS grafico_prediccion JSONB,
  ADD COLUMN IF NOT EXISTS noticias           JSONB,
  ADD COLUMN IF NOT EXISTS updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- 2.4 Constraint: senal_ia solo puede ser ALCISTA, BAJISTA, LATERAL o NULL
DO $$
BEGIN
  ALTER TABLE public.activos
    ADD CONSTRAINT activos_senal_ia_chk
    CHECK (senal_ia IS NULL OR senal_ia IN ('ALCISTA', 'BAJISTA', 'LATERAL'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- 2.5 Trigger para auto-actualizar updated_at en activos
DROP TRIGGER IF EXISTS trg_activos_updated_at ON public.activos;
CREATE TRIGGER trg_activos_updated_at
  BEFORE UPDATE ON public.activos
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();


-- =====================================================
-- PASO 3: TABLA portfolios — Añadir timestamps y FK segura
-- =====================================================

-- 3.1 Añadir columnas de auditoría
ALTER TABLE public.portfolios
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- 3.2 Trigger auto updated_at
DROP TRIGGER IF EXISTS trg_portfolios_updated_at ON public.portfolios;
CREATE TRIGGER trg_portfolios_updated_at
  BEFORE UPDATE ON public.portfolios
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();

-- 3.3 Asegurar FK con CASCADE: si se borra el usuario, se borran sus portfolios
ALTER TABLE public.portfolios
  DROP CONSTRAINT IF EXISTS portfolios_id_usuario_fkey;

ALTER TABLE public.portfolios
  ADD CONSTRAINT portfolios_id_usuario_fkey
    FOREIGN KEY (id_usuario)
    REFERENCES public.usuarios(id_usuario)
    ON DELETE CASCADE;


-- =====================================================
-- PASO 4: TABLA portfolio_activo — Relación N:M
-- =====================================================

-- 4.1 Eliminar la tabla antigua si existía con otro nombre
DROP TABLE IF EXISTS public.portfolio_stocks CASCADE;

-- 4.2 Crear la tabla intermedia
CREATE TABLE IF NOT EXISTS public.portfolio_activo (
  id_posicion   BIGSERIAL     PRIMARY KEY,
  id_portfolio  INT4          NOT NULL
                  REFERENCES public.portfolios(id_portfolio) ON DELETE CASCADE,
  ticker        TEXT          NOT NULL
                  REFERENCES public.activos(ticker) ON DELETE RESTRICT,

  cantidad      NUMERIC(20,8) NOT NULL CHECK (cantidad > 0),
  precio_compra NUMERIC(20,8) NOT NULL CHECK (precio_compra >= 0),
  fecha_compra  DATE          NOT NULL DEFAULT CURRENT_DATE,
  notas         TEXT,

  created_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

  CONSTRAINT portfolio_activo_unq UNIQUE (id_portfolio, ticker)
);

-- 4.3 Índices para acelerar consultas frecuentes
CREATE INDEX IF NOT EXISTS pa_portfolio_idx ON public.portfolio_activo(id_portfolio);
CREATE INDEX IF NOT EXISTS pa_ticker_idx    ON public.portfolio_activo(ticker);

-- 4.4 Trigger auto updated_at
DROP TRIGGER IF EXISTS trg_portfolio_activo_updated_at ON public.portfolio_activo;
CREATE TRIGGER trg_portfolio_activo_updated_at
  BEFORE UPDATE ON public.portfolio_activo
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();


-- =====================================================
-- PASO 5: ELIMINAR tabla chat_historial
-- =====================================================

-- CASCADE elimina también FKs y dependencias que pudiera tener
DROP TABLE IF EXISTS public.chat_historial CASCADE;


-- =====================================================
-- PASO 6: ACADEMIA — Crear tablas de cursos y progreso
-- =====================================================

-- 6.1 Catálogo de cursos
CREATE TABLE IF NOT EXISTS public.academia_cursos (
  id_curso     TEXT    PRIMARY KEY,
  titulo       TEXT    NOT NULL,
  descripcion  TEXT,
  nivel_minimo TEXT    NOT NULL DEFAULT 'Gratis',
  orden        INT4    NOT NULL DEFAULT 0,
  activo       BOOLEAN NOT NULL DEFAULT TRUE
);

-- 6.2 Progreso del usuario por curso
CREATE TABLE IF NOT EXISTS public.usuario_progreso_academia (
  id_progreso      BIGSERIAL    PRIMARY KEY,
  id_usuario       UUID         NOT NULL
                     REFERENCES public.usuarios(id_usuario) ON DELETE CASCADE,
  id_curso         TEXT         NOT NULL
                     REFERENCES public.academia_cursos(id_curso) ON DELETE CASCADE,

  completado       BOOLEAN      NOT NULL DEFAULT FALSE,
  progreso_pct     NUMERIC(5,2) NOT NULL DEFAULT 0
                     CHECK (progreso_pct >= 0 AND progreso_pct <= 100),
  ultima_leccion   INT4         NOT NULL DEFAULT 0,
  fecha_inicio     TIMESTAMPTZ  DEFAULT NOW(),
  fecha_completado TIMESTAMPTZ,

  CONSTRAINT usuario_curso_unq UNIQUE (id_usuario, id_curso)
);

CREATE INDEX IF NOT EXISTS upa_usuario_idx
  ON public.usuario_progreso_academia(id_usuario);

-- 6.3 Insertar cursos iniciales
INSERT INTO public.academia_cursos (id_curso, titulo, descripcion, nivel_minimo, orden) VALUES
  ('intro-inversiones',   'Introducción a las Inversiones', 'Conceptos básicos del mundo de la inversión.',          'Gratis', 1),
  ('analisis-tecnico',    'Análisis Técnico',               'Indicadores RSI, MACD, Bollinger y su interpretación.', 'Gratis', 2),
  ('gestion-riesgo',      'Gestión del Riesgo',             'Diversificación, correlación y ratio de Sharpe.',       'Gratis', 3),
  ('estrategias-avanzadas','Estrategias Avanzadas',         'Optimización de Markowitz y portfolios con IA.',        'PRO',    4)
ON CONFLICT (id_curso) DO NOTHING;


-- =====================================================
-- PASO 7: POLÍTICAS RLS (Row Level Security)
-- =====================================================

-- ---- USUARIOS ----
ALTER TABLE public.usuarios ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS usuarios_select_own ON public.usuarios;
CREATE POLICY usuarios_select_own ON public.usuarios
  FOR SELECT TO authenticated
  USING (id_usuario = auth.uid());

DROP POLICY IF EXISTS usuarios_update_own ON public.usuarios;
CREATE POLICY usuarios_update_own ON public.usuarios
  FOR UPDATE TO authenticated
  USING (id_usuario = auth.uid())
  WITH CHECK (id_usuario = auth.uid());

DROP POLICY IF EXISTS usuarios_insert_service ON public.usuarios;
CREATE POLICY usuarios_insert_service ON public.usuarios
  FOR INSERT TO service_role
  WITH CHECK (TRUE);

-- ---- ACTIVOS ----
ALTER TABLE public.activos ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS activos_select_auth ON public.activos;
CREATE POLICY activos_select_auth ON public.activos
  FOR SELECT TO authenticated
  USING (TRUE);

DROP POLICY IF EXISTS activos_write_service ON public.activos;
CREATE POLICY activos_write_service ON public.activos
  FOR ALL TO service_role
  USING (TRUE) WITH CHECK (TRUE);

-- ---- PORTFOLIOS ----
ALTER TABLE public.portfolios ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS portfolios_select_own ON public.portfolios;
CREATE POLICY portfolios_select_own ON public.portfolios
  FOR SELECT TO authenticated
  USING (id_usuario = auth.uid());

DROP POLICY IF EXISTS portfolios_insert_own ON public.portfolios;
CREATE POLICY portfolios_insert_own ON public.portfolios
  FOR INSERT TO authenticated
  WITH CHECK (id_usuario = auth.uid());

DROP POLICY IF EXISTS portfolios_update_own ON public.portfolios;
CREATE POLICY portfolios_update_own ON public.portfolios
  FOR UPDATE TO authenticated
  USING (id_usuario = auth.uid())
  WITH CHECK (id_usuario = auth.uid());

DROP POLICY IF EXISTS portfolios_delete_own ON public.portfolios;
CREATE POLICY portfolios_delete_own ON public.portfolios
  FOR DELETE TO authenticated
  USING (id_usuario = auth.uid());

-- ---- PORTFOLIO_ACTIVO ----
ALTER TABLE public.portfolio_activo ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS pa_select_own ON public.portfolio_activo;
CREATE POLICY pa_select_own ON public.portfolio_activo
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.portfolios p
      WHERE p.id_portfolio = portfolio_activo.id_portfolio
        AND p.id_usuario = auth.uid()
    )
  );

DROP POLICY IF EXISTS pa_insert_own ON public.portfolio_activo;
CREATE POLICY pa_insert_own ON public.portfolio_activo
  FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.portfolios p
      WHERE p.id_portfolio = portfolio_activo.id_portfolio
        AND p.id_usuario = auth.uid()
    )
  );

DROP POLICY IF EXISTS pa_update_own ON public.portfolio_activo;
CREATE POLICY pa_update_own ON public.portfolio_activo
  FOR UPDATE TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.portfolios p
      WHERE p.id_portfolio = portfolio_activo.id_portfolio
        AND p.id_usuario = auth.uid()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.portfolios p
      WHERE p.id_portfolio = portfolio_activo.id_portfolio
        AND p.id_usuario = auth.uid()
    )
  );

DROP POLICY IF EXISTS pa_delete_own ON public.portfolio_activo;
CREATE POLICY pa_delete_own ON public.portfolio_activo
  FOR DELETE TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.portfolios p
      WHERE p.id_portfolio = portfolio_activo.id_portfolio
        AND p.id_usuario = auth.uid()
    )
  );

-- ---- ACADEMIA_CURSOS ----
ALTER TABLE public.academia_cursos ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS academia_select ON public.academia_cursos;
CREATE POLICY academia_select ON public.academia_cursos
  FOR SELECT TO authenticated
  USING (activo = TRUE);

DROP POLICY IF EXISTS academia_write_service ON public.academia_cursos;
CREATE POLICY academia_write_service ON public.academia_cursos
  FOR ALL TO service_role
  USING (TRUE) WITH CHECK (TRUE);

-- ---- USUARIO_PROGRESO_ACADEMIA ----
ALTER TABLE public.usuario_progreso_academia ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS upa_select_own ON public.usuario_progreso_academia;
CREATE POLICY upa_select_own ON public.usuario_progreso_academia
  FOR SELECT TO authenticated
  USING (id_usuario = auth.uid());

DROP POLICY IF EXISTS upa_insert_own ON public.usuario_progreso_academia;
CREATE POLICY upa_insert_own ON public.usuario_progreso_academia
  FOR INSERT TO authenticated
  WITH CHECK (id_usuario = auth.uid());

DROP POLICY IF EXISTS upa_update_own ON public.usuario_progreso_academia;
CREATE POLICY upa_update_own ON public.usuario_progreso_academia
  FOR UPDATE TO authenticated
  USING (id_usuario = auth.uid())
  WITH CHECK (id_usuario = auth.uid());

DROP POLICY IF EXISTS upa_delete_own ON public.usuario_progreso_academia;
CREATE POLICY upa_delete_own ON public.usuario_progreso_academia
  FOR DELETE TO authenticated
  USING (id_usuario = auth.uid());


-- =====================================================
-- FIN DE LA MIGRACIÓN
-- Schema resultante:
--   usuarios          → +foto_perfil
--   activos           → reestructurada (BOOLEAN estabilidad, JSONB)
--   portfolios        → +created_at, +updated_at, FK con CASCADE
--   portfolio_activo  → NUEVA (N:M portfolios ↔ activos)
--   chat_historial    → ELIMINADA
--   academia_cursos   → NUEVA
--   usuario_progreso_academia → NUEVA
-- =====================================================
