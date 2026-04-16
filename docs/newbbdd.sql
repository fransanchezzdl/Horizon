[
  {
    "table_name": "activos",
    "column_name": "ticker",
    "data_type": "text"
  },
  {
    "table_name": "activos",
    "column_name": "nombre_completo",
    "data_type": "text"
  },
  {
    "table_name": "activos",
    "column_name": "estabilidad",
    "data_type": "boolean"
  },
  {
    "table_name": "activos",
    "column_name": "logo_activo",
    "data_type": "text"
  },
  {
    "table_name": "activos",
    "column_name": "precio",
    "data_type": "numeric"
  },
  {
    "table_name": "activos",
    "column_name": "confianza_bygru",
    "data_type": "numeric"
  },
  {
    "table_name": "activos",
    "column_name": "senal_ia",
    "data_type": "text"
  },
  {
    "table_name": "activos",
    "column_name": "grafico_prediccion",
    "data_type": "jsonb"
  },
  {
    "table_name": "activos",
    "column_name": "noticias",
    "data_type": "jsonb"
  },
  {
    "table_name": "activos",
    "column_name": "updated_at",
    "data_type": "timestamp with time zone"
  },
  {
    "table_name": "cursos",
    "column_name": "id",
    "data_type": "bigint"
  },
  {
    "table_name": "cursos",
    "column_name": "titulo",
    "data_type": "character varying"
  },
  {
    "table_name": "cursos",
    "column_name": "descripcion",
    "data_type": "character varying"
  },
  {
    "table_name": "cursos",
    "column_name": "plan_pro",
    "data_type": "boolean"
  },
  {
    "table_name": "diapositivas",
    "column_name": "id",
    "data_type": "bigint"
  },
  {
    "table_name": "diapositivas",
    "column_name": "id_curso",
    "data_type": "bigint"
  },
  {
    "table_name": "diapositivas",
    "column_name": "contenido",
    "data_type": "text"
  },
  {
    "table_name": "diapositivas",
    "column_name": "num_pag",
    "data_type": "bigint"
  },
  {
    "table_name": "historico_activos",
    "column_name": "id_historico",
    "data_type": "integer"
  },
  {
    "table_name": "historico_activos",
    "column_name": "ticker",
    "data_type": "text"
  },
  {
    "table_name": "historico_activos",
    "column_name": "fecha",
    "data_type": "date"
  },
  {
    "table_name": "historico_activos",
    "column_name": "precio_cierre",
    "data_type": "numeric"
  },
  {
    "table_name": "historico_activos",
    "column_name": "prediccion_ia",
    "data_type": "numeric"
  },
  {
    "table_name": "portfolio_activo",
    "column_name": "id_posicion",
    "data_type": "bigint"
  },
  {
    "table_name": "portfolio_activo",
    "column_name": "id_portfolio",
    "data_type": "integer"
  },
  {
    "table_name": "portfolio_activo",
    "column_name": "ticker",
    "data_type": "text"
  },
  {
    "table_name": "portfolio_activo",
    "column_name": "created_at",
    "data_type": "timestamp with time zone"
  },
  {
    "table_name": "portfolio_activo",
    "column_name": "updated_at",
    "data_type": "timestamp with time zone"
  },
  {
    "table_name": "portfolios",
    "column_name": "id_portfolio",
    "data_type": "integer"
  },
  {
    "table_name": "portfolios",
    "column_name": "id_usuario",
    "data_type": "uuid"
  },
  {
    "table_name": "portfolios",
    "column_name": "nombre_portfolio",
    "data_type": "text"
  },
  {
    "table_name": "portfolios",
    "column_name": "descripcion",
    "data_type": "text"
  },
  {
    "table_name": "portfolios",
    "column_name": "riesgo",
    "data_type": "real"
  },
  {
    "table_name": "portfolios",
    "column_name": "created_at",
    "data_type": "timestamp with time zone"
  },
  {
    "table_name": "portfolios",
    "column_name": "updated_at",
    "data_type": "timestamp with time zone"
  },
  {
    "table_name": "progreso_cursos",
    "column_name": "id",
    "data_type": "bigint"
  },
  {
    "table_name": "progreso_cursos",
    "column_name": "id_usuario",
    "data_type": "uuid"
  },
  {
    "table_name": "progreso_cursos",
    "column_name": "id_curso",
    "data_type": "bigint"
  },
  {
    "table_name": "progreso_cursos",
    "column_name": "diapositiva_alcanzada",
    "data_type": "bigint"
  },
  {
    "table_name": "progreso_cursos",
    "column_name": "completado",
    "data_type": "boolean"
  },
  {
    "table_name": "progreso_cursos",
    "column_name": "puntuacion",
    "data_type": "bigint"
  },
  {
    "table_name": "reflexiones",
    "column_name": "id_reflexion",
    "data_type": "bigint"
  },
  {
    "table_name": "reflexiones",
    "column_name": "cita",
    "data_type": "text"
  },
  {
    "table_name": "reflexiones",
    "column_name": "autor",
    "data_type": "text"
  },
  {
    "table_name": "reflexiones",
    "column_name": "tema",
    "data_type": "text"
  },
  {
    "table_name": "reflexiones",
    "column_name": "titulo_articulo",
    "data_type": "text"
  },
  {
    "table_name": "reflexiones",
    "column_name": "contenido",
    "data_type": "text"
  },
  {
    "table_name": "reflexiones",
    "column_name": "imagen_url",
    "data_type": "text"
  },
  {
    "table_name": "reflexiones",
    "column_name": "tiempo_lectura",
    "data_type": "integer"
  },
  {
    "table_name": "reflexiones",
    "column_name": "tags",
    "data_type": "ARRAY"
  },
  {
    "table_name": "reflexiones",
    "column_name": "activo",
    "data_type": "boolean"
  },
  {
    "table_name": "reflexiones",
    "column_name": "created_at",
    "data_type": "timestamp with time zone"
  },
  {
    "table_name": "usuario_portfolio",
    "column_name": "id_usuario_portfolio",
    "data_type": "bigint"
  },
  {
    "table_name": "usuario_portfolio",
    "column_name": "id_usuario",
    "data_type": "uuid"
  },
  {
    "table_name": "usuario_portfolio",
    "column_name": "id_portfolio",
    "data_type": "integer"
  },
  {
    "table_name": "usuario_portfolio",
    "column_name": "created_at",
    "data_type": "timestamp with time zone"
  },
  {
    "table_name": "chat_rate_limits",
    "column_name": "id_usuario",
    "data_type": "uuid"
  },
  {
    "table_name": "chat_rate_limits",
    "column_name": "window_start",
    "data_type": "timestamp with time zone"
  },
  {
    "table_name": "chat_rate_limits",
    "column_name": "message_count",
    "data_type": "integer"
  },
  {
    "table_name": "chat_rate_limits",
    "column_name": "updated_at",
    "data_type": "timestamp with time zone"
  },
  {
    "table_name": "chat_rate_limits_rls",
    "column_name": "enabled",
    "data_type": "true"
  },
  {
    "table_name": "chat_rate_limits_rls",
    "column_name": "policy",
    "data_type": "service_role only; acceso directo desde cliente denegado"
  },
  {
    "table_name": "activos_rls",
    "column_name": "enabled",
    "data_type": "true"
  },
  {
    "table_name": "activos_rls",
    "column_name": "policy",
    "data_type": "SELECT anon, authenticated; WRITE anon"
  },
  {
    "table_name": "usuarios",
    "column_name": "id_usuario",
    "data_type": "uuid"
  },
  {
    "table_name": "usuarios",
    "column_name": "nombre",
    "data_type": "text"
  },
  {
    "table_name": "usuarios",
    "column_name": "apellidos",
    "data_type": "text"
  },
  {
    "table_name": "usuarios",
    "column_name": "email",
    "data_type": "text"
  },
  {
    "table_name": "usuarios",
    "column_name": "membresia",
    "data_type": "text"
  },
  {
    "table_name": "usuarios",
    "column_name": "foto_perfil",
    "data_type": "text"
  },
  {
    "table_name": "usuarios",
    "column_name": "created_at",
    "data_type": "timestamp with time zone"
  }
]