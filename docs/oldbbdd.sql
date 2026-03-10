-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.activos (
  ticker text NOT NULL,
  nombre_completo text,
  estabilidad text,
  tamano text,
  CONSTRAINT activos_pkey PRIMARY KEY (ticker)
);
CREATE TABLE public.chat_historial (
  id_chat uuid NOT NULL DEFAULT gen_random_uuid(),
  id_usuario uuid NOT NULL,
  mensaje_usuario text NOT NULL,
  respuesta_asesor text NOT NULL,
  tokens_usados integer,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT chat_historial_pkey PRIMARY KEY (id_chat),
  CONSTRAINT chat_history_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.usuarios(id_usuario)
);
CREATE TABLE public.historico_activos (
  id_historico integer NOT NULL DEFAULT nextval('historico_activos_id_historico_seq'::regclass),
  ticker text,
  fecha date,
  precio_cierre numeric,
  prediccion_ia numeric,
  CONSTRAINT historico_activos_pkey PRIMARY KEY (id_historico),
  CONSTRAINT historico_activos_ticker_fkey FOREIGN KEY (ticker) REFERENCES public.activos(ticker)
);
CREATE TABLE public.portfolios (
  id_portfolio integer NOT NULL DEFAULT nextval('portafolios_id_portafolio_seq'::regclass),
  id_usuario uuid,
  nombre_portfolio text,
  descripcion text,
  riesgo real,
  CONSTRAINT portfolios_pkey PRIMARY KEY (id_portfolio),
  CONSTRAINT portafolios_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.usuarios(id_usuario)
);
CREATE TABLE public.usuarios (
  id_usuario uuid NOT NULL,
  nombre text,
  apellidos text,
  email text UNIQUE,
  membresia text DEFAULT 'Gratis'::text,
  CONSTRAINT usuarios_pkey PRIMARY KEY (id_usuario),
  CONSTRAINT usuarios_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES auth.users(id)
);