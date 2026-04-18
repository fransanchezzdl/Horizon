[
  {
    "table_name": "activos",
    "column_name": "updated_at",
    "data_type": "timestamp with time zone",
    "is_nullable": "NO"
  },
  {
    "table_name": "activos",
    "column_name": "logo_activo",
    "data_type": "text",
    "is_nullable": "YES"
  },
  {
    "table_name": "activos",
    "column_name": "senal_ia",
    "data_type": "text",
    "is_nullable": "YES"
  },
  {
    "table_name": "activos",
    "column_name": "precio_predicho",
    "data_type": "numeric",
    "is_nullable": "YES"
  },
  {
    "table_name": "activos",
    "column_name": "retorno_predicho_pct",
    "data_type": "numeric",
    "is_nullable": "YES"
  },
  {
    "table_name": "activos",
    "column_name": "live_accuracy_30d",
    "data_type": "numeric",
    "is_nullable": "YES"
  },
  {
    "table_name": "activos",
    "column_name": "grafico_prediccion",
    "data_type": "jsonb",
    "is_nullable": "YES"
  },
  {
    "table_name": "activos",
    "column_name": "confianza_bygru",
    "data_type": "numeric",
    "is_nullable": "YES"
  },
  {
    "table_name": "activos",
    "column_name": "precio",
    "data_type": "numeric",
    "is_nullable": "YES"
  },
  {
    "table_name": "activos",
    "column_name": "estabilidad",
    "data_type": "boolean",
    "is_nullable": "YES"
  },
  {
    "table_name": "activos",
    "column_name": "nombre_completo",
    "data_type": "text",
    "is_nullable": "YES"
  },
  {
    "table_name": "activos",
    "column_name": "sector",
    "data_type": "text",
    "is_nullable": "YES"
  },
  {
    "table_name": "activos",
    "column_name": "noticias",
    "data_type": "jsonb",
    "is_nullable": "YES"
  },
  {
    "table_name": "activos",
    "column_name": "senal_actualizada_en",
    "data_type": "timestamp with time zone",
    "is_nullable": "YES"
  },
  {
    "table_name": "activos",
    "column_name": "ticker",
    "data_type": "text",
    "is_nullable": "NO"
  },
  {
    "table_name": "activos",
    "column_name": "probabilidades_xgb",
    "data_type": "jsonb",
    "is_nullable": "YES"
  },
  {
    "table_name": "activos",
    "column_name": "volatilidad_30d",
    "data_type": "numeric",
    "is_nullable": "YES"
  },
  {
    "table_name": "chat_rate_limits",
    "column_name": "window_start",
    "data_type": "timestamp with time zone",
    "is_nullable": "NO"
  },
  {
    "table_name": "chat_rate_limits",
    "column_name": "id_usuario",
    "data_type": "uuid",
    "is_nullable": "NO"
  },
  {
    "table_name": "chat_rate_limits",
    "column_name": "updated_at",
    "data_type": "timestamp with time zone",
    "is_nullable": "NO"
  },
  {
    "table_name": "chat_rate_limits",
    "column_name": "message_count",
    "data_type": "integer",
    "is_nullable": "NO"
  },
  {
    "table_name": "cursos",
    "column_name": "descripcion",
    "data_type": "character varying",
    "is_nullable": "YES"
  },
  {
    "table_name": "cursos",
    "column_name": "plan_pro",
    "data_type": "boolean",
    "is_nullable": "NO"
  },
  {
    "table_name": "cursos",
    "column_name": "titulo",
    "data_type": "character varying",
    "is_nullable": "NO"
  },
  {
    "table_name": "cursos",
    "column_name": "id",
    "data_type": "bigint",
    "is_nullable": "NO"
  },
  {
    "table_name": "diapositivas",
    "column_name": "id",
    "data_type": "bigint",
    "is_nullable": "NO"
  },
  {
    "table_name": "diapositivas",
    "column_name": "id_curso",
    "data_type": "bigint",
    "is_nullable": "NO"
  },
  {
    "table_name": "diapositivas",
    "column_name": "num_pag",
    "data_type": "bigint",
    "is_nullable": "NO"
  },
  {
    "table_name": "diapositivas",
    "column_name": "contenido",
    "data_type": "text",
    "is_nullable": "NO"
  },
  {
    "table_name": "historico_activos",
    "column_name": "fecha",
    "data_type": "date",
    "is_nullable": "YES"
  },
  {
    "table_name": "historico_activos",
    "column_name": "ticker",
    "data_type": "text",
    "is_nullable": "YES"
  },
  {
    "table_name": "historico_activos",
    "column_name": "precio_cierre",
    "data_type": "numeric",
    "is_nullable": "YES"
  },
  {
    "table_name": "historico_activos",
    "column_name": "prediccion_ia",
    "data_type": "numeric",
    "is_nullable": "YES"
  },
  {
    "table_name": "historico_activos",
    "column_name": "id_historico",
    "data_type": "integer",
    "is_nullable": "NO"
  },
  {
    "table_name": "portfolio_activo",
    "column_name": "id_portfolio",
    "data_type": "integer",
    "is_nullable": "NO"
  },
  {
    "table_name": "portfolio_activo",
    "column_name": "id_posicion",
    "data_type": "bigint",
    "is_nullable": "NO"
  },
  {
    "table_name": "portfolio_activo",
    "column_name": "ticker",
    "data_type": "text",
    "is_nullable": "NO"
  },
  {
    "table_name": "portfolio_activo",
    "column_name": "updated_at",
    "data_type": "timestamp with time zone",
    "is_nullable": "NO"
  },
  {
    "table_name": "portfolio_activo",
    "column_name": "created_at",
    "data_type": "timestamp with time zone",
    "is_nullable": "NO"
  },
  {
    "table_name": "portfolios",
    "column_name": "nombre_portfolio",
    "data_type": "text",
    "is_nullable": "YES"
  },
  {
    "table_name": "portfolios",
    "column_name": "descripcion",
    "data_type": "text",
    "is_nullable": "YES"
  },
  {
    "table_name": "portfolios",
    "column_name": "updated_at",
    "data_type": "timestamp with time zone",
    "is_nullable": "NO"
  },
  {
    "table_name": "portfolios",
    "column_name": "created_at",
    "data_type": "timestamp with time zone",
    "is_nullable": "NO"
  },
  {
    "table_name": "portfolios",
    "column_name": "riesgo",
    "data_type": "real",
    "is_nullable": "YES"
  },
  {
    "table_name": "portfolios",
    "column_name": "id_usuario",
    "data_type": "uuid",
    "is_nullable": "YES"
  },
  {
    "table_name": "portfolios",
    "column_name": "id_portfolio",
    "data_type": "integer",
    "is_nullable": "NO"
  },
  {
    "table_name": "prediction_log",
    "column_name": "tendencia_real",
    "data_type": "text",
    "is_nullable": "YES"
  },
  {
    "table_name": "prediction_log",
    "column_name": "id",
    "data_type": "bigint",
    "is_nullable": "NO"
  },
  {
    "table_name": "prediction_log",
    "column_name": "fecha_prediccion",
    "data_type": "date",
    "is_nullable": "NO"
  },
  {
    "table_name": "prediction_log",
    "column_name": "fecha_objetivo",
    "data_type": "date",
    "is_nullable": "NO"
  },
  {
    "table_name": "prediction_log",
    "column_name": "confianza_ensemble",
    "data_type": "numeric",
    "is_nullable": "NO"
  },
  {
    "table_name": "prediction_log",
    "column_name": "precio_entrada",
    "data_type": "numeric",
    "is_nullable": "NO"
  },
  {
    "table_name": "prediction_log",
    "column_name": "dias_horizonte",
    "data_type": "integer",
    "is_nullable": "NO"
  },
  {
    "table_name": "prediction_log",
    "column_name": "resuelta",
    "data_type": "boolean",
    "is_nullable": "NO"
  },
  {
    "table_name": "prediction_log",
    "column_name": "precio_salida",
    "data_type": "numeric",
    "is_nullable": "YES"
  },
  {
    "table_name": "prediction_log",
    "column_name": "correcta",
    "data_type": "boolean",
    "is_nullable": "YES"
  },
  {
    "table_name": "prediction_log",
    "column_name": "fecha_resolucion",
    "data_type": "timestamp with time zone",
    "is_nullable": "YES"
  },
  {
    "table_name": "prediction_log",
    "column_name": "created_at",
    "data_type": "timestamp with time zone",
    "is_nullable": "NO"
  },
  {
    "table_name": "prediction_log",
    "column_name": "ticker",
    "data_type": "text",
    "is_nullable": "NO"
  },
  {
    "table_name": "prediction_log",
    "column_name": "tendencia_predicha",
    "data_type": "text",
    "is_nullable": "NO"
  },
  {
    "table_name": "progreso_cursos",
    "column_name": "id",
    "data_type": "bigint",
    "is_nullable": "NO"
  },
  {
    "table_name": "progreso_cursos",
    "column_name": "puntuacion",
    "data_type": "bigint",
    "is_nullable": "YES"
  },
  {
    "table_name": "progreso_cursos",
    "column_name": "diapositiva_alcanzada",
    "data_type": "bigint",
    "is_nullable": "YES"
  },
  {
    "table_name": "progreso_cursos",
    "column_name": "id_curso",
    "data_type": "bigint",
    "is_nullable": "NO"
  },
  {
    "table_name": "progreso_cursos",
    "column_name": "completado",
    "data_type": "boolean",
    "is_nullable": "NO"
  },
  {
    "table_name": "progreso_cursos",
    "column_name": "id_usuario",
    "data_type": "uuid",
    "is_nullable": "NO"
  },
  {
    "table_name": "reflexiones",
    "column_name": "tema",
    "data_type": "text",
    "is_nullable": "NO"
  },
  {
    "table_name": "reflexiones",
    "column_name": "autor",
    "data_type": "text",
    "is_nullable": "NO"
  },
  {
    "table_name": "reflexiones",
    "column_name": "cita",
    "data_type": "text",
    "is_nullable": "NO"
  },
  {
    "table_name": "reflexiones",
    "column_name": "tiempo_lectura",
    "data_type": "integer",
    "is_nullable": "YES"
  },
  {
    "table_name": "reflexiones",
    "column_name": "activo",
    "data_type": "boolean",
    "is_nullable": "NO"
  },
  {
    "table_name": "reflexiones",
    "column_name": "created_at",
    "data_type": "timestamp with time zone",
    "is_nullable": "NO"
  },
  {
    "table_name": "reflexiones",
    "column_name": "tags",
    "data_type": "ARRAY",
    "is_nullable": "YES"
  },
  {
    "table_name": "reflexiones",
    "column_name": "id_reflexion",
    "data_type": "bigint",
    "is_nullable": "NO"
  },
  {
    "table_name": "reflexiones",
    "column_name": "contenido",
    "data_type": "text",
    "is_nullable": "NO"
  },
  {
    "table_name": "reflexiones",
    "column_name": "titulo_articulo",
    "data_type": "text",
    "is_nullable": "NO"
  },
  {
    "table_name": "usuario_portfolio",
    "column_name": "id_usuario_portfolio",
    "data_type": "bigint",
    "is_nullable": "NO"
  },
  {
    "table_name": "usuario_portfolio",
    "column_name": "created_at",
    "data_type": "timestamp with time zone",
    "is_nullable": "NO"
  },
  {
    "table_name": "usuario_portfolio",
    "column_name": "id_portfolio",
    "data_type": "integer",
    "is_nullable": "NO"
  },
  {
    "table_name": "usuario_portfolio",
    "column_name": "id_usuario",
    "data_type": "uuid",
    "is_nullable": "NO"
  },
  {
    "table_name": "usuarios",
    "column_name": "apellidos",
    "data_type": "text",
    "is_nullable": "YES"
  },
  {
    "table_name": "usuarios",
    "column_name": "id_usuario",
    "data_type": "uuid",
    "is_nullable": "NO"
  },
  {
    "table_name": "usuarios",
    "column_name": "foto_perfil",
    "data_type": "text",
    "is_nullable": "YES"
  },
  {
    "table_name": "usuarios",
    "column_name": "created_at",
    "data_type": "timestamp with time zone",
    "is_nullable": "YES"
  },
  {
    "table_name": "usuarios",
    "column_name": "email",
    "data_type": "text",
    "is_nullable": "YES"
  },
  {
    "table_name": "usuarios",
    "column_name": "membresia",
    "data_type": "text",
    "is_nullable": "YES"
  },
  {
    "table_name": "usuarios",
    "column_name": "nombre",
    "data_type": "text",
    "is_nullable": "YES"
  },
  {
    "table_name": "xai_explicaciones",
    "column_name": "fecha_prediccion",
    "data_type": "timestamp with time zone",
    "is_nullable": "NO"
  },
  {
    "table_name": "xai_explicaciones",
    "column_name": "shap_grafico",
    "data_type": "text",
    "is_nullable": "NO"
  },
  {
    "table_name": "xai_explicaciones",
    "column_name": "shap_valores",
    "data_type": "jsonb",
    "is_nullable": "NO"
  },
  {
    "table_name": "xai_explicaciones",
    "column_name": "senal_prediccion",
    "data_type": "text",
    "is_nullable": "NO"
  },
  {
    "table_name": "xai_explicaciones",
    "column_name": "version_modelo",
    "data_type": "text",
    "is_nullable": "NO"
  },
  {
    "table_name": "xai_explicaciones",
    "column_name": "prediccion_correcta",
    "data_type": "boolean",
    "is_nullable": "YES"
  },
  {
    "table_name": "xai_explicaciones",
    "column_name": "confianza_prediccion",
    "data_type": "numeric",
    "is_nullable": "NO"
  },
  {
    "table_name": "xai_explicaciones",
    "column_name": "contribucion_features",
    "data_type": "jsonb",
    "is_nullable": "NO"
  },
  {
    "table_name": "xai_explicaciones",
    "column_name": "pesos_atencion",
    "data_type": "jsonb",
    "is_nullable": "YES"
  },
  {
    "table_name": "xai_explicaciones",
    "column_name": "ticker",
    "data_type": "text",
    "is_nullable": "NO"
  },
  {
    "table_name": "xai_explicaciones",
    "column_name": "features_top20",
    "data_type": "jsonb",
    "is_nullable": "NO"
  },
  {
    "table_name": "xai_explicaciones",
    "column_name": "id",
    "data_type": "bigint",
    "is_nullable": "NO"
  },
  {
    "table_name": "xai_explicaciones",
    "column_name": "updated_at",
    "data_type": "timestamp with time zone",
    "is_nullable": "NO"
  }
]