CREATE TABLE public.activos (
  ticker text NOT NULL,
  nombre_completo text,
  estabilidad boolean,
  logo_activo text,
  precio numeric,
  confianza_bygru numeric,
  senal_ia text CHECK (senal_ia IS NULL OR (senal_ia = ANY (ARRAY['ALCISTA'::text, 'BAJISTA'::text, 'LATERAL'::text]))),
  grafico_prediccion jsonb,
  noticias jsonb,
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  senal_actualizada_en timestamp with time zone,
  precio_predicho numeric,
  retorno_predicho_pct numeric,
  live_accuracy_30d numeric,
  sector text,
  probabilidades_xgb jsonb,
  volatilidad_30d numeric,
  CONSTRAINT activos_pkey PRIMARY KEY (ticker)
);
CREATE TABLE public.chat_rate_limits (
  id_usuario uuid NOT NULL,
  window_start timestamp with time zone NOT NULL DEFAULT now(),
  message_count integer NOT NULL DEFAULT 0,
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT chat_rate_limits_pkey PRIMARY KEY (id_usuario),
  CONSTRAINT chat_rate_limits_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.usuarios(id_usuario)
);
CREATE TABLE public.cursos (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  titulo character varying NOT NULL UNIQUE,
  descripcion character varying,
  plan_pro boolean NOT NULL DEFAULT false,
  CONSTRAINT cursos_pkey PRIMARY KEY (id)
);
CREATE TABLE public.diapositivas (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  id_curso bigint NOT NULL,
  contenido text NOT NULL,
  num_pag bigint NOT NULL,
  CONSTRAINT diapositivas_pkey PRIMARY KEY (id, id_curso),
  CONSTRAINT diapositivas_id_curso_fkey FOREIGN KEY (id_curso) REFERENCES public.cursos(id)
);
CREATE TABLE public.portfolio_activo (
  id_posicion bigint NOT NULL DEFAULT nextval('portfolio_activo_id_posicion_seq'::regclass),
  id_portfolio integer NOT NULL,
  ticker text NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT portfolio_activo_pkey PRIMARY KEY (id_posicion),
  CONSTRAINT portfolio_activo_id_portfolio_fkey FOREIGN KEY (id_portfolio) REFERENCES public.portfolios(id_portfolio),
  CONSTRAINT portfolio_activo_ticker_fkey FOREIGN KEY (ticker) REFERENCES public.activos(ticker)
);
CREATE TABLE public.portfolios (
  id_portfolio integer NOT NULL DEFAULT nextval('portafolios_id_portafolio_seq'::regclass),
  id_usuario uuid,
  nombre_portfolio text,
  descripcion text,
  riesgo real,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT portfolios_pkey PRIMARY KEY (id_portfolio),
  CONSTRAINT portafolios_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.usuarios(id_usuario)
);
CREATE TABLE public.prediction_log (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  ticker text NOT NULL,
  fecha_prediccion date NOT NULL,
  fecha_objetivo date NOT NULL,
  tendencia_predicha text NOT NULL CHECK (tendencia_predicha = ANY (ARRAY['ALCISTA'::text, 'BAJISTA'::text, 'LATERAL'::text])),
  confianza_ensemble numeric NOT NULL,
  precio_entrada numeric NOT NULL,
  dias_horizonte integer NOT NULL DEFAULT 5,
  resuelta boolean NOT NULL DEFAULT false,
  tendencia_real text CHECK (tendencia_real IS NULL OR (tendencia_real = ANY (ARRAY['ALCISTA'::text, 'BAJISTA'::text, 'LATERAL'::text]))),
  precio_salida numeric,
  correcta boolean,
  fecha_resolucion timestamp with time zone,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT prediction_log_pkey PRIMARY KEY (id),
  CONSTRAINT prediction_log_ticker_fkey FOREIGN KEY (ticker) REFERENCES public.activos(ticker)
);
CREATE TABLE public.progreso_cursos (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  id_usuario uuid NOT NULL,
  id_curso bigint NOT NULL,
  diapositiva_alcanzada bigint,
  completado boolean NOT NULL DEFAULT false,
  puntuacion bigint,
  CONSTRAINT progreso_cursos_pkey PRIMARY KEY (id, id_usuario, id_curso),
  CONSTRAINT progreso_cursos_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.usuarios(id_usuario),
  CONSTRAINT progreso_cursos_id_curso_fkey FOREIGN KEY (id_curso) REFERENCES public.cursos(id)
);
CREATE TABLE public.reflexiones (
  id_reflexion bigint NOT NULL DEFAULT nextval('reflexiones_id_reflexion_seq'::regclass),
  cita text NOT NULL,
  autor text NOT NULL,
  tema text NOT NULL,
  titulo_articulo text NOT NULL,
  contenido text NOT NULL,
  tiempo_lectura integer,
  tags ARRAY,
  activo boolean NOT NULL DEFAULT true,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT reflexiones_pkey PRIMARY KEY (id_reflexion)
);
CREATE TABLE public.usuario_portfolio (
  id_usuario_portfolio bigint NOT NULL DEFAULT nextval('usuario_portfolio_id_usuario_portfolio_seq'::regclass),
  id_usuario uuid NOT NULL,
  id_portfolio integer NOT NULL UNIQUE,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT usuario_portfolio_pkey PRIMARY KEY (id_usuario_portfolio),
  CONSTRAINT usuario_portfolio_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.usuarios(id_usuario),
  CONSTRAINT usuario_portfolio_id_portfolio_fkey FOREIGN KEY (id_portfolio) REFERENCES public.portfolios(id_portfolio)
);
CREATE TABLE public.usuarios (
  id_usuario uuid NOT NULL,
  nombre text,
  apellidos text,
  email text UNIQUE,
  membresia text DEFAULT 'Gratis'::text,
  foto_perfil text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT usuarios_pkey PRIMARY KEY (id_usuario),
  CONSTRAINT usuarios_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES auth.users(id)
);
CREATE TABLE public.xai_explicaciones (
  id bigint NOT NULL DEFAULT nextval('xai_explicaciones_id_seq'::regclass),
  ticker text NOT NULL,
  fecha_prediccion timestamp with time zone NOT NULL DEFAULT now(),
  shap_valores jsonb NOT NULL,
  shap_grafico text NOT NULL,
  features_top20 jsonb NOT NULL,
  contribucion_features jsonb NOT NULL,
  senal_prediccion text NOT NULL CHECK (senal_prediccion = ANY (ARRAY['ALCISTA'::text, 'BAJISTA'::text, 'LATERAL'::text])),
  confianza_prediccion numeric NOT NULL,
  prediccion_correcta boolean,
  version_modelo text NOT NULL DEFAULT 'Phase3'::text,
  seed_modelo integer DEFAULT 42,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT xai_explicaciones_pkey PRIMARY KEY (id),
  CONSTRAINT xai_explicaciones_ticker_fkey FOREIGN KEY (ticker) REFERENCES public.activos(ticker)
);
CREATE TABLE public.xai_validacion (
  id bigint NOT NULL DEFAULT nextval('xai_validacion_id_seq'::regclass),
  id_explicacion bigint NOT NULL,
  util boolean,
  comentario_usuario text,
  shap_consistency numeric,
  feature_stability numeric,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT xai_validacion_pkey PRIMARY KEY (id),
  CONSTRAINT xai_validacion_id_explicacion_fkey FOREIGN KEY (id_explicacion) REFERENCES public.xai_explicaciones(id)
);