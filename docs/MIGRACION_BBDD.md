# Migración de Base de Datos — TFG-Horizon

> **Fecha:** 10 de marzo de 2026  
> **Objetivo:** Reestructuración completa del schema `public` en Supabase

---

## Diagrama de relaciones (texto)

```
usuarios (uuid PK)
  │
  ├── 1:N ──▶ portfolios.id_usuario (FK)
  │              │
  │              └── 1:N ──▶ portfolio_activo.id_portfolio (FK)
  │                              │
  │                              └── N:1 ──▶ activos.ticker (FK)
  │
  ├── 1:N ──▶ usuario_progreso_academia.id_usuario (FK)
  │              │
  │              └── N:1 ──▶ academia_cursos.id_curso (string match)
  │
  └── (chat_historial ELIMINADA)
```

**Cardinalidades:**
- `usuarios` 1 → N `portfolios` (un usuario tiene varios portfolios)
- `portfolios` 1 → N `portfolio_activo` (un portfolio tiene varias posiciones)
- `activos` 1 → N `portfolio_activo` (un activo puede estar en varios portfolios)
- `usuarios` 1 → N `usuario_progreso_academia` (progreso individual por curso)

---

## 1. MODIFICAR tabla `usuarios`

### SQL

```sql
-- Añadir campo foto_perfil a la tabla usuarios
ALTER TABLE public.usuarios
  ADD COLUMN IF NOT EXISTS foto_perfil TEXT;

COMMENT ON COLUMN public.usuarios.foto_perfil
  IS 'URL de la imagen de perfil del usuario (almacenada en Supabase Storage o externa)';
```

### Justificación

| Campo          | Motivo                                                                 |
|----------------|------------------------------------------------------------------------|
| `foto_perfil`  | Permite personalizar el perfil en `profile.html` y el avatar del sidebar (`layout.js`). Se almacena como URL (no blob) apuntando a Supabase Storage o un servicio externo. |

> **Nota:** No se modifican los campos existentes (`id_usuario`, `nombre`, `apellidos`, `email`, `membresia`) porque el código actual los usa correctamente en `UsuarioDAO`, `UsuarioResponse`, `AuthService` y `layout.js`.

### Impacto en código

| Archivo                          | Cambio necesario                                      |
|----------------------------------|-------------------------------------------------------|
| `dtos/usuario_dto.py`           | Añadir `foto_perfil: Optional[str] = None`            |
| `daos/usuario_dao.py`           | Añadir `foto_perfil` al SELECT y al INSERT/UPDATE     |
| `frontend/js/profile.js`        | Mostrar/editar la foto de perfil                      |
| `frontend/js/layout.js`         | Mostrar avatar en sidebar si existe foto_perfil       |

---

## 2. REDISEÑAR tabla `activos`

### SQL

```sql
-- Primero eliminamos las columnas antiguas que se reemplazan
ALTER TABLE public.activos
  DROP COLUMN IF EXISTS tamano;

-- Convertir 'estabilidad' de text a boolean
-- Paso 1: Añadir columna temporal
ALTER TABLE public.activos
  ADD COLUMN IF NOT EXISTS estabilidad_bool BOOLEAN;

-- Paso 2: Migrar datos (ajustar según tus valores actuales)
UPDATE public.activos
SET estabilidad_bool = CASE
  WHEN LOWER(estabilidad) IN ('alta', 'estable') THEN TRUE
  ELSE FALSE
END;

-- Paso 3: Eliminar antigua y renombrar
ALTER TABLE public.activos DROP COLUMN IF EXISTS estabilidad;
ALTER TABLE public.activos RENAME COLUMN estabilidad_bool TO estabilidad;

-- Añadir nuevas columnas
ALTER TABLE public.activos
  ADD COLUMN IF NOT EXISTS logo_activo TEXT,
  ADD COLUMN IF NOT EXISTS precio NUMERIC(20,8),
  ADD COLUMN IF NOT EXISTS confianza_bygru NUMERIC(5,4),
  ADD COLUMN IF NOT EXISTS senal_ia TEXT,
  ADD COLUMN IF NOT EXISTS grafico_prediccion JSONB,
  ADD COLUMN IF NOT EXISTS noticias JSONB,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- Constraint para señal_ia
ALTER TABLE public.activos
  ADD CONSTRAINT activos_senal_ia_chk
  CHECK (senal_ia IS NULL OR senal_ia IN ('ALCISTA', 'BAJISTA', 'LATERAL'));

-- Índice para búsquedas frecuentes
CREATE INDEX IF NOT EXISTS activos_nombre_idx
  ON public.activos USING gin (nombre_completo gin_trgm_ops);

-- Trigger para updated_at automático
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_activos_updated_at ON public.activos;
CREATE TRIGGER trg_activos_updated_at
  BEFORE UPDATE ON public.activos
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();
```

### Estructura final de `activos`

| Campo                | Tipo           | Descripción                                              |
|----------------------|----------------|----------------------------------------------------------|
| `ticker`             | TEXT PK        | Símbolo bursátil (existente)                             |
| `nombre_completo`    | TEXT           | Nombre de la empresa (existente)                         |
| `logo_activo`        | TEXT           | URL del logo (para `analysis.html` y tarjetas)           |
| `precio`             | NUMERIC(20,8)  | Último precio descargado de Yahoo Finance                |
| `confianza_bygru`    | NUMERIC(5,4)   | Confianza del ensemble BiGRU (0.0000–1.0000)             |
| `senal_ia`           | TEXT           | Señal de tendencia: ALCISTA/BAJISTA/LATERAL              |
| `grafico_prediccion` | JSONB          | Datos del gráfico de predicción (ver detalle abajo)      |
| `estabilidad`        | BOOLEAN        | `true` = estable, `false` = volátil                      |
| `noticias`           | JSONB          | Array de noticias recientes (ver detalle abajo)          |
| `updated_at`         | TIMESTAMPTZ    | Última actualización automática                          |

### ¿Por qué JSONB para `grafico_prediccion`?

**Justificación:** El gráfico de predicción no es un dato relacional, sino un **blob de datos serializados** que el frontend consume para renderizar un chart. Crear una tabla separada con miles de puntos de datos sería over-engineering para un TFG.

**Estructura recomendada:**

```json
{
  "generado_el": "2026-03-10T14:30:00Z",
  "horizonte_dias": 5,
  "historico": [
    { "fecha": "2026-03-05", "precio": 178.50 },
    { "fecha": "2026-03-06", "precio": 179.20 },
    { "fecha": "2026-03-07", "precio": 180.10 }
  ],
  "prediccion": [
    { "fecha": "2026-03-11", "precio": 181.00, "upper": 183.50, "lower": 178.50 },
    { "fecha": "2026-03-12", "precio": 182.30, "upper": 185.00, "lower": 179.60 }
  ]
}
```

**Ventajas del JSONB:**
- Consultas con operadores `->>`, `@>` directamente en PostgreSQL
- No necesita JOINs, el frontend recibe el JSON completo en una sola consulta
- Fácil de actualizar: un solo UPDATE reemplaza todo el objeto
- Indexable con GIN si necesitas filtrar por campos internos

**¿Cuándo sería mejor una tabla separada?** Solo si necesitaras consultas complejas por punto individual de datos (ej: "dame todos los activos cuya predicción para el 12 de marzo sea > 200"). En vuestro caso, el frontend simplemente renderiza el gráfico completo → JSONB es lo correcto.

### ¿Por qué JSONB para `noticias`?

**Justificación:** Las noticias son datos efímeros (se actualizan periódicamente desde una API externa) y se muestran como un bloque en `analysis.html`. No tienen relaciones con otras tablas.

**Estructura recomendada:**

```json
[
  {
    "titulo": "Apple anuncia nuevos resultados trimestrales",
    "fuente": "Reuters",
    "url": "https://reuters.com/...",
    "fecha": "2026-03-10",
    "sentimiento": "positivo"
  },
  {
    "titulo": "Caída del sector tech por tensiones geopolíticas",
    "fuente": "Bloomberg",
    "url": "https://bloomberg.com/...",
    "fecha": "2026-03-09",
    "sentimiento": "negativo"
  }
]
```

**¿Cuándo sería mejor una tabla separada?** Si implementarais un feed de noticias global con búsquedas full-text, categorización, bookmarks por usuario, etc. Para mostrar 3-5 noticias por ticker en la página de análisis, JSONB es mucho más simple y performante.

### Impacto en código

| Archivo                          | Cambio necesario                                             |
|----------------------------------|--------------------------------------------------------------|
| `dtos/activo_dto.py`            | Reestructurar `ActivoResponse` con los nuevos campos         |
| `daos/activo_dao.py`            | Actualizar SELECT, INSERT y `crear_activo()`                 |
| `services/activo_service.py`    | Endpoint para actualizar precio/señal/gráfico/noticias       |
| `scripts/insertar_activos.py`   | Actualizar datos de seed con nuevos campos                   |
| `frontend/js/search.js`         | Usar `logo_activo`, `precio`, `senal_ia` en result-card      |
| `frontend/js/analysis.js`       | Consumir `grafico_prediccion`, `noticias`, `confianza_bygru` |

---

## 3. REDISEÑAR tabla `portfolios`

### Análisis previo: ¿Simplificar a solo `id_portfolio` y `nombre_portfolio`?

Tu propuesta es eliminar `id_usuario`, `descripcion`, `riesgo` de la tabla portfolios. **Analicemos:**

- **`id_usuario` (FK):** ¡NO se debe eliminar! → Ver punto 5 (portfolio_usuario).
- **`descripcion`:** Útil para diferenciar portfolios. Recomiendo mantenerla.
- **`riesgo`:** Tu modelo BiGRU usa `aversion_riesgo` para calcular blended returns. **Es funcional.** Recomiendo mantenerlo.

### SQL

```sql
-- Renombrar columnas del schema actual para consistencia
-- (tu DAO usa 'usuario_id' y 'id', pero tu schema dice 'id_portfolio' e 'id_usuario')
-- Asumimos el schema de la imagen: id_portfolio, id_usuario, nombre_portfolio, descripcion, riesgo

-- Añadir nuevas columnas útiles
ALTER TABLE public.portfolios
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- Trigger para updated_at
DROP TRIGGER IF EXISTS trg_portfolios_updated_at ON public.portfolios;
CREATE TRIGGER trg_portfolios_updated_at
  BEFORE UPDATE ON public.portfolios
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();
```

### Estructura final de `portfolios`

| Campo              | Tipo          | Descripción                                         |
|--------------------|---------------|-----------------------------------------------------|
| `id_portfolio`     | INT4 PK       | Clave primaria auto-incremental (existente)         |
| `id_usuario`       | UUID FK       | FK → usuarios.id_usuario (existente, **se mantiene**) |
| `nombre_portfolio` | TEXT          | Nombre del portfolio (existente)                    |
| `descripcion`      | TEXT          | Descripción opcional (existente)                    |
| `riesgo`           | FLOAT4        | Aversión al riesgo 0-1 (existente, usado por ML)   |
| `created_at`       | TIMESTAMPTZ   | Fecha de creación (nuevo)                           |
| `updated_at`       | TIMESTAMPTZ   | Última modificación (nuevo)                         |

---

## 4. CREAR tabla `portfolio_activo` (relación N:M)

### Justificación

Actualmente existe `portfolio_stocks` en el código del DAO pero no está en la imagen del schema. Vamos a crear `portfolio_activo` como la tabla intermedia oficial que reemplaza/consolida `portfolio_stocks`.

### SQL

```sql
-- Eliminar tabla antigua si existe
DROP TABLE IF EXISTS public.portfolio_stocks;

-- Crear tabla intermedia portfolio_activo
CREATE TABLE public.portfolio_activo (
  id_posicion    BIGSERIAL PRIMARY KEY,
  id_portfolio   INT4    NOT NULL REFERENCES public.portfolios(id_portfolio) ON DELETE CASCADE,
  ticker         TEXT    NOT NULL REFERENCES public.activos(ticker) ON DELETE RESTRICT,

  -- Datos de la posición
  cantidad       NUMERIC(20,8) NOT NULL CHECK (cantidad > 0),
  precio_compra  NUMERIC(20,8) NOT NULL CHECK (precio_compra >= 0),
  fecha_compra   DATE          NOT NULL DEFAULT CURRENT_DATE,

  -- Metadatos
  notas          TEXT,
  created_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

  -- Un activo solo puede aparecer una vez por portfolio
  CONSTRAINT portfolio_activo_unq UNIQUE (id_portfolio, ticker)
);

-- Índices para consultas frecuentes
CREATE INDEX IF NOT EXISTS pa_portfolio_idx ON public.portfolio_activo(id_portfolio);
CREATE INDEX IF NOT EXISTS pa_ticker_idx    ON public.portfolio_activo(ticker);

-- Trigger updated_at
DROP TRIGGER IF EXISTS trg_portfolio_activo_updated_at ON public.portfolio_activo;
CREATE TRIGGER trg_portfolio_activo_updated_at
  BEFORE UPDATE ON public.portfolio_activo
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();
```

### Justificación de cada campo

| Campo           | Motivo                                                                          |
|-----------------|---------------------------------------------------------------------------------|
| `id_posicion`   | PK auto-incremental, facilita operaciones CRUD individuales                     |
| `id_portfolio`  | FK al portfolio. `ON DELETE CASCADE`: si se borra el portfolio, se borran sus posiciones |
| `ticker`        | FK al activo. `ON DELETE RESTRICT`: no se puede borrar un activo con posiciones abiertas |
| `cantidad`      | Unidades compradas (permite decimales para criptos/fracciones)                  |
| `precio_compra` | Precio al que se compró, necesario para calcular P&L                            |
| `fecha_compra`  | Cuándo se realizó la compra, útil para rendimiento temporal                     |
| `notas`         | Campo libre para que el usuario anote motivos de compra, tesis, etc.            |
| `UNIQUE(...)`   | Evita duplicados: si el usuario quiere añadir más de un activo, debe ACTUALIZAR la posición |

### ¿Por qué `ON DELETE RESTRICT` en ticker?

Si un activo es borrado del catálogo accidentalmente, no queremos que se evaporen las posiciones de los usuarios. Mejor que el DELETE falle y se investigue. Para "deslistar" un activo sin borrarlo, se marca como inactivo (futuro campo `activo boolean`).

### Cómo usar esta tabla desde el frontend

```
[portfolio.html]
├── GET /portfolios/{id}/activos → Listar posiciones
│   → JOIN portfolio_activo pa ON pa.id_portfolio = ?
│     JOIN activos a ON a.ticker = pa.ticker
│   → Devuelve: ticker, nombre, logo, cantidad, precio_compra, precio_actual (de activos.precio)
│
├── POST /portfolios/{id}/activos → Añadir posición
│   → Body: { ticker, cantidad, precio_compra, fecha_compra }
│
├── PUT /portfolios/{id}/activos/{ticker} → Actualizar posición
│   → Body: { cantidad, precio_compra }
│
└── DELETE /portfolios/{id}/activos/{ticker} → Eliminar posición
```

---

## 5. Relación portfolio ↔ usuario: ¿Tabla auxiliar `portfolio_usuario`?

### Respuesta: **NO es necesaria. Mantener la FK directa en `portfolios`.**

### Justificación detallada

Una tabla auxiliar `portfolio_usuario` solo tendría sentido si:
- Un portfolio pudiera pertenecer a **varios** usuarios simultáneamente (relación N:M)
- Existieran **roles** por portfolio (admin, viewer, editor colaborativo)

En TFG-Horizon, la relación es clara: **un usuario tiene N portfolios, un portfolio pertenece a 1 usuario.** Es una relación **1:N pura**.

| Opción                     | Pros                          | Contras                                         |
|----------------------------|-------------------------------|--------------------------------------------------|
| **FK directa en portfolios** | Simple, 1 JOIN menos, estándar | No soporta portfolios compartidos (no lo necesitas) |
| **Tabla auxiliar**         | Soportaría portfolios colaborativos | Over-engineering, JOIN extra innecesario, más RLS que mantener |

**Conclusión:** Mantener `portfolios.id_usuario` como FK directa. Si en el futuro necesitáis portfolios compartidos, se podría crear la tabla auxiliar entonces. YAGNI (You Ain't Gonna Need It).

La FK ya existe. Si necesitas recrearla explícitamente:

```sql
-- Verificar/recrear la FK (solo si no existe)
ALTER TABLE public.portfolios
  DROP CONSTRAINT IF EXISTS portfolios_id_usuario_fkey;

ALTER TABLE public.portfolios
  ADD CONSTRAINT portfolios_id_usuario_fkey
  FOREIGN KEY (id_usuario) REFERENCES public.usuarios(id_usuario) ON DELETE CASCADE;
```

---

## 6. ELIMINAR tabla `chat_historial`

### SQL

```sql
-- Eliminar tabla de forma segura (verificar dependencias primero)
DROP TABLE IF EXISTS public.chat_historial CASCADE;
```

### Justificación

- El `ChatDAO` actual **no usa la base de datos** para el historial: mantiene rate limiting en memoria (`self.mensajes_por_usuario = {}`).
- No hay ningún endpoint que lea ni escriba en `chat_historial`.
- El chat de Gemini en `academia.js` no persiste conversaciones entre sesiones.
- **Si en el futuro necesitáis historial persistente**, se puede recrear una tabla optimizada. Por ahora, es dead code en la BBDD.

---

## 7. Sección ACADEMIA — Recomendación

### Recomendación: **Opción C (Híbrida)** — con matices

### Análisis comparativo

| Criterio                  | Opción A (Full frontend) | Opción B (Full BBDD) | **Opción C (Híbrida)** |
|---------------------------|--------------------------|----------------------|------------------------|
| Complejidad de implementación | ⭐ Baja                | ⭐⭐⭐ Alta          | ⭐⭐ Media              |
| Mantenibilidad            | ⚠️ Regular (HTML duplicado) | ✅ Buena            | ✅ Buena                |
| Consultas SQL requeridas  | 1 tabla                  | 3 tablas + JOINs     | 2 tablas simples        |
| Escalabilidad             | ❌ Pobre                 | ✅ Excelente          | ✅ Suficiente para TFG  |
| Control de acceso por membresía | ⚠️ Solo en frontend (inseguro) | ✅ Backend     | ✅ Backend              |
| Rendimiento               | ✅ Rápido (sin consultas) | ⚠️ Más consultas     | ✅ Rápido               |

### ¿Por qué Opción C?

1. **El contenido de las lecciones (textos, imágenes, pasos) es estático** → No tiene sentido meterlo en BBDD para luego renderizarlo. Mejor en el frontend como HTML/JS.

2. **El catálogo de cursos y el control de acceso SÍ debe estar en BBDD** → Si no, cualquier usuario podría manipular el `localStorage` para desbloquear cursos de pago. El backend decide qué cursos puede ver según su `membresia`.

3. **El progreso del usuario es dinámico y personal** → Tabla en BBDD obligatoria.

### SQL de la Opción C

```sql
-- Tabla de cursos (catálogo ligero — el contenido está en el frontend)
CREATE TABLE public.academia_cursos (
  id_curso          TEXT PRIMARY KEY,         -- Ej: 'intro-inversiones', 'analisis-tecnico'
  titulo            TEXT NOT NULL,
  descripcion       TEXT,
  nivel_minimo      TEXT NOT NULL DEFAULT 'Gratis',  -- Membresía mínima requerida
  orden             INT4 NOT NULL DEFAULT 0,          -- Orden de visualización
  activo            BOOLEAN NOT NULL DEFAULT TRUE     -- Permite ocultar sin borrar
);

COMMENT ON TABLE public.academia_cursos
  IS 'Catálogo de cursos. El contenido de las lecciones está en el frontend (HTML).';

-- Tabla de progreso del usuario
CREATE TABLE public.usuario_progreso_academia (
  id_progreso       BIGSERIAL PRIMARY KEY,
  id_usuario        UUID    NOT NULL REFERENCES public.usuarios(id_usuario) ON DELETE CASCADE,
  id_curso          TEXT    NOT NULL REFERENCES public.academia_cursos(id_curso) ON DELETE CASCADE,
  completado        BOOLEAN NOT NULL DEFAULT FALSE,
  progreso_pct      NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (progreso_pct >= 0 AND progreso_pct <= 100),
  ultima_leccion    INT4    NOT NULL DEFAULT 0,   -- Índice de la última lección vista
  fecha_inicio      TIMESTAMPTZ DEFAULT NOW(),
  fecha_completado  TIMESTAMPTZ,

  CONSTRAINT usuario_curso_unq UNIQUE (id_usuario, id_curso)
);

CREATE INDEX IF NOT EXISTS upa_usuario_idx
  ON public.usuario_progreso_academia(id_usuario);

-- Insertar cursos iniciales
INSERT INTO public.academia_cursos (id_curso, titulo, descripcion, nivel_minimo, orden) VALUES
  ('intro-inversiones', 'Introducción a las Inversiones', 'Aprende los conceptos básicos del mundo de la inversión.', 'Gratis', 1),
  ('analisis-tecnico', 'Análisis Técnico', 'Indicadores RSI, MACD, Bollinger y cómo interpretarlos.', 'Gratis', 2),
  ('gestion-riesgo', 'Gestión del Riesgo', 'Diversificación, correlación y ratio de Sharpe.', 'Gratis', 3),
  ('estrategias-avanzadas', 'Estrategias Avanzadas', 'Optimización de Markowitz y portfolios IA.', 'PRO', 4);
```

### Flujo de la Academia

```
[academia.html]
│
├── GET /academia/cursos → Backend consulta academia_cursos
│   → Filtra por membresia del usuario (Gratis ve 3, PRO ve 4)
│   → Devuelve: [{id_curso, titulo, descripcion, bloqueado: false/true}]
│
├── GET /academia/progreso → Backend consulta usuario_progreso_academia
│   → Devuelve: [{id_curso, completado, progreso_pct, ultima_leccion}]
│
├── POST /academia/progreso → Actualizar progreso de una lección
│   → Body: { id_curso, ultima_leccion, progreso_pct }
│   → UPSERT en usuario_progreso_academia
│
└── Frontend renderiza el contenido de la lección según id_curso + ultima_leccion
    (el HTML/contenido está hardcoded en el frontend)
```

### ¿Por qué `id_curso` es TEXT y no INT?

Porque el frontend hardcodea el contenido referenciando IDs legibles como `'intro-inversiones'`. Esto evita una capa de mapeo INT→STRING y hace el código más legible tanto en SQL como en JavaScript.

---

## 8. POLÍTICAS RLS (Row Level Security)

### Prerequisito: habilitar la extensión pgcrypto si no está activa

```sql
-- =============================================
-- RLS: USUARIOS
-- =============================================
ALTER TABLE public.usuarios ENABLE ROW LEVEL SECURITY;

-- Cada usuario solo puede ver y editar su propio perfil
CREATE POLICY usuarios_select_own ON public.usuarios
  FOR SELECT TO authenticated
  USING (id_usuario = auth.uid());

CREATE POLICY usuarios_update_own ON public.usuarios
  FOR UPDATE TO authenticated
  USING (id_usuario = auth.uid())
  WITH CHECK (id_usuario = auth.uid());

-- El INSERT lo hace el trigger de auth (o el backend con service_role)
CREATE POLICY usuarios_insert_service ON public.usuarios
  FOR INSERT TO service_role
  WITH CHECK (TRUE);


-- =============================================
-- RLS: ACTIVOS (lectura pública para auth, escritura solo service_role)
-- =============================================
ALTER TABLE public.activos ENABLE ROW LEVEL SECURITY;

CREATE POLICY activos_select_auth ON public.activos
  FOR SELECT TO authenticated
  USING (TRUE);

CREATE POLICY activos_write_service ON public.activos
  FOR ALL TO service_role
  USING (TRUE)
  WITH CHECK (TRUE);


-- =============================================
-- RLS: PORTFOLIOS (solo dueño)
-- =============================================
ALTER TABLE public.portfolios ENABLE ROW LEVEL SECURITY;

CREATE POLICY portfolios_select_own ON public.portfolios
  FOR SELECT TO authenticated
  USING (id_usuario = auth.uid());

CREATE POLICY portfolios_insert_own ON public.portfolios
  FOR INSERT TO authenticated
  WITH CHECK (id_usuario = auth.uid());

CREATE POLICY portfolios_update_own ON public.portfolios
  FOR UPDATE TO authenticated
  USING (id_usuario = auth.uid())
  WITH CHECK (id_usuario = auth.uid());

CREATE POLICY portfolios_delete_own ON public.portfolios
  FOR DELETE TO authenticated
  USING (id_usuario = auth.uid());


-- =============================================
-- RLS: PORTFOLIO_ACTIVO (acceso si el portfolio es del usuario)
-- =============================================
ALTER TABLE public.portfolio_activo ENABLE ROW LEVEL SECURITY;

CREATE POLICY pa_select_own ON public.portfolio_activo
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.portfolios p
      WHERE p.id_portfolio = portfolio_activo.id_portfolio
        AND p.id_usuario = auth.uid()
    )
  );

CREATE POLICY pa_insert_own ON public.portfolio_activo
  FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.portfolios p
      WHERE p.id_portfolio = portfolio_activo.id_portfolio
        AND p.id_usuario = auth.uid()
    )
  );

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

CREATE POLICY pa_delete_own ON public.portfolio_activo
  FOR DELETE TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.portfolios p
      WHERE p.id_portfolio = portfolio_activo.id_portfolio
        AND p.id_usuario = auth.uid()
    )
  );


-- =============================================
-- RLS: ACADEMIA_CURSOS (lectura para auth, escritura admin)
-- =============================================
ALTER TABLE public.academia_cursos ENABLE ROW LEVEL SECURITY;

CREATE POLICY academia_cursos_select ON public.academia_cursos
  FOR SELECT TO authenticated
  USING (activo = TRUE);

CREATE POLICY academia_cursos_write ON public.academia_cursos
  FOR ALL TO service_role
  USING (TRUE)
  WITH CHECK (TRUE);


-- =============================================
-- RLS: USUARIO_PROGRESO_ACADEMIA (solo dueño)
-- =============================================
ALTER TABLE public.usuario_progreso_academia ENABLE ROW LEVEL SECURITY;

CREATE POLICY upa_select_own ON public.usuario_progreso_academia
  FOR SELECT TO authenticated
  USING (id_usuario = auth.uid());

CREATE POLICY upa_insert_own ON public.usuario_progreso_academia
  FOR INSERT TO authenticated
  WITH CHECK (id_usuario = auth.uid());

CREATE POLICY upa_update_own ON public.usuario_progreso_academia
  FOR UPDATE TO authenticated
  USING (id_usuario = auth.uid())
  WITH CHECK (id_usuario = auth.uid());

CREATE POLICY upa_delete_own ON public.usuario_progreso_academia
  FOR DELETE TO authenticated
  USING (id_usuario = auth.uid());
```

### Resumen RLS

| Tabla                          | SELECT                  | INSERT           | UPDATE           | DELETE           |
|--------------------------------|-------------------------|------------------|------------------|------------------|
| `usuarios`                     | Solo su registro        | service_role     | Solo su registro | -                |
| `activos`                      | Todos (authenticated)   | service_role     | service_role     | service_role     |
| `portfolios`                   | Solo propios            | Solo propios     | Solo propios     | Solo propios     |
| `portfolio_activo`             | Si portfolio es suyo    | Si portfolio es suyo | Si portfolio es suyo | Si portfolio es suyo |
| `academia_cursos`              | Todos (si `activo=true`)| service_role     | service_role     | service_role     |
| `usuario_progreso_academia`    | Solo su progreso        | Solo propio      | Solo propio      | Solo propio      |

> **Nota importante:** Tu backend usa `SUPABASE_KEY` (anon key). Las políticas RLS se aplican al anon key. Si usas `service_role` key, RLS se bypasea. Asegúrate de que las operaciones de usuario final usen el token JWT del usuario (no la service_role key) para que RLS funcione.

---

## 9. SCRIPT DE MIGRACIÓN COMPLETO (orden de ejecución)

Ejecutar **en este orden** en el SQL Editor de Supabase:

```sql
-- ============================================
-- PASO 0: Función auxiliar (si no existe)
-- ============================================
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ============================================
-- PASO 1: USUARIOS — Añadir foto_perfil
-- ============================================
ALTER TABLE public.usuarios
  ADD COLUMN IF NOT EXISTS foto_perfil TEXT;


-- ============================================
-- PASO 2: ACTIVOS — Reestructurar
-- ============================================
ALTER TABLE public.activos
  DROP COLUMN IF EXISTS tamano;

ALTER TABLE public.activos
  ADD COLUMN IF NOT EXISTS estabilidad_bool BOOLEAN;

UPDATE public.activos
SET estabilidad_bool = CASE
  WHEN LOWER(estabilidad) IN ('alta', 'estable') THEN TRUE
  ELSE FALSE
END;

ALTER TABLE public.activos DROP COLUMN IF EXISTS estabilidad;
ALTER TABLE public.activos RENAME COLUMN estabilidad_bool TO estabilidad;

ALTER TABLE public.activos
  ADD COLUMN IF NOT EXISTS logo_activo TEXT,
  ADD COLUMN IF NOT EXISTS precio NUMERIC(20,8),
  ADD COLUMN IF NOT EXISTS confianza_bygru NUMERIC(5,4),
  ADD COLUMN IF NOT EXISTS senal_ia TEXT,
  ADD COLUMN IF NOT EXISTS grafico_prediccion JSONB,
  ADD COLUMN IF NOT EXISTS noticias JSONB,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

DO $$
BEGIN
  ALTER TABLE public.activos
    ADD CONSTRAINT activos_senal_ia_chk
    CHECK (senal_ia IS NULL OR senal_ia IN ('ALCISTA', 'BAJISTA', 'LATERAL'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DROP TRIGGER IF EXISTS trg_activos_updated_at ON public.activos;
CREATE TRIGGER trg_activos_updated_at
  BEFORE UPDATE ON public.activos
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();


-- ============================================
-- PASO 3: PORTFOLIOS — Añadir timestamps, asegurar FK
-- ============================================
ALTER TABLE public.portfolios
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

DROP TRIGGER IF EXISTS trg_portfolios_updated_at ON public.portfolios;
CREATE TRIGGER trg_portfolios_updated_at
  BEFORE UPDATE ON public.portfolios
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();

-- Asegurar FK con cascade
ALTER TABLE public.portfolios
  DROP CONSTRAINT IF EXISTS portfolios_id_usuario_fkey;
ALTER TABLE public.portfolios
  ADD CONSTRAINT portfolios_id_usuario_fkey
  FOREIGN KEY (id_usuario) REFERENCES public.usuarios(id_usuario) ON DELETE CASCADE;


-- ============================================
-- PASO 4: PORTFOLIO_ACTIVO — Crear tabla intermedia
-- ============================================
DROP TABLE IF EXISTS public.portfolio_stocks;

CREATE TABLE IF NOT EXISTS public.portfolio_activo (
  id_posicion    BIGSERIAL PRIMARY KEY,
  id_portfolio   INT4    NOT NULL REFERENCES public.portfolios(id_portfolio) ON DELETE CASCADE,
  ticker         TEXT    NOT NULL REFERENCES public.activos(ticker) ON DELETE RESTRICT,
  cantidad       NUMERIC(20,8) NOT NULL CHECK (cantidad > 0),
  precio_compra  NUMERIC(20,8) NOT NULL CHECK (precio_compra >= 0),
  fecha_compra   DATE          NOT NULL DEFAULT CURRENT_DATE,
  notas          TEXT,
  created_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
  CONSTRAINT portfolio_activo_unq UNIQUE (id_portfolio, ticker)
);

CREATE INDEX IF NOT EXISTS pa_portfolio_idx ON public.portfolio_activo(id_portfolio);
CREATE INDEX IF NOT EXISTS pa_ticker_idx    ON public.portfolio_activo(ticker);

DROP TRIGGER IF EXISTS trg_portfolio_activo_updated_at ON public.portfolio_activo;
CREATE TRIGGER trg_portfolio_activo_updated_at
  BEFORE UPDATE ON public.portfolio_activo
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();


-- ============================================
-- PASO 5: ELIMINAR chat_historial
-- ============================================
DROP TABLE IF EXISTS public.chat_historial CASCADE;


-- ============================================
-- PASO 6: ACADEMIA — Crear tablas
-- ============================================
CREATE TABLE IF NOT EXISTS public.academia_cursos (
  id_curso          TEXT PRIMARY KEY,
  titulo            TEXT NOT NULL,
  descripcion       TEXT,
  nivel_minimo      TEXT NOT NULL DEFAULT 'Gratis',
  orden             INT4 NOT NULL DEFAULT 0,
  activo            BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS public.usuario_progreso_academia (
  id_progreso       BIGSERIAL PRIMARY KEY,
  id_usuario        UUID    NOT NULL REFERENCES public.usuarios(id_usuario) ON DELETE CASCADE,
  id_curso          TEXT    NOT NULL REFERENCES public.academia_cursos(id_curso) ON DELETE CASCADE,
  completado        BOOLEAN NOT NULL DEFAULT FALSE,
  progreso_pct      NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (progreso_pct >= 0 AND progreso_pct <= 100),
  ultima_leccion    INT4    NOT NULL DEFAULT 0,
  fecha_inicio      TIMESTAMPTZ DEFAULT NOW(),
  fecha_completado  TIMESTAMPTZ,
  CONSTRAINT usuario_curso_unq UNIQUE (id_usuario, id_curso)
);

CREATE INDEX IF NOT EXISTS upa_usuario_idx
  ON public.usuario_progreso_academia(id_usuario);

INSERT INTO public.academia_cursos (id_curso, titulo, descripcion, nivel_minimo, orden) VALUES
  ('intro-inversiones', 'Introducción a las Inversiones', 'Aprende los conceptos básicos del mundo de la inversión.', 'Gratis', 1),
  ('analisis-tecnico', 'Análisis Técnico', 'Indicadores RSI, MACD, Bollinger y cómo interpretarlos.', 'Gratis', 2),
  ('gestion-riesgo', 'Gestión del Riesgo', 'Diversificación, correlación y ratio de Sharpe.', 'Gratis', 3),
  ('estrategias-avanzadas', 'Estrategias Avanzadas', 'Optimización de Markowitz y portfolios IA.', 'PRO', 4)
ON CONFLICT (id_curso) DO NOTHING;
```

---

## 10. DIAGRAMA FINAL

```
┌──────────────┐         ┌───────────────────────┐         ┌──────────────┐
│   usuarios   │         │      portfolios       │         │    activos   │
│──────────────│         │───────────────────────│         │──────────────│
│ id_usuario PK│◀── FK ──│ id_usuario            │         │ ticker    PK │
│ nombre       │    1:N  │ id_portfolio       PK │         │ nombre_compl │
│ apellidos    │         │ nombre_portfolio      │         │ logo_activo  │
│ email        │         │ descripcion           │         │ precio       │
│ foto_perfil  │         │ riesgo                │         │ confianza    │
│ membresia    │         │ created_at            │         │ senal_ia     │
└──────┬───────┘         │ updated_at            │         │ graf_predic  │
       │                 └───────────┬───────────┘         │ estabilidad  │
       │                             │                     │ noticias     │
       │                             │ 1:N                 │ updated_at   │
       │                             │                     └──────┬───────┘
       │                 ┌───────────┴───────────┐                │
       │                 │   portfolio_activo    │                │
       │                 │───────────────────────│     N:1        │
       │                 │ id_posicion        PK │── FK ──────────┘
       │                 │ id_portfolio       FK │
       │                 │ ticker             FK │
       │                 │ cantidad              │
       │                 │ precio_compra         │
       │                 │ fecha_compra          │
       │                 │ notas                 │
       │                 └───────────────────────┘
       │
       │ 1:N      ┌──────────────────────────────┐
       │          │ usuario_progreso_academia     │
       └──────────│──────────────────────────────│
                  │ id_progreso              PK  │       ┌─────────────────┐
                  │ id_usuario               FK  │       │ academia_cursos │
                  │ id_curso                 FK  │── ──▶ │─────────────────│
                  │ completado                   │       │ id_curso     PK │
                  │ progreso_pct                 │       │ titulo          │
                  │ ultima_leccion               │       │ descripcion     │
                  │ fecha_inicio                 │       │ nivel_minimo    │
                  │ fecha_completado             │       │ orden           │
                  └──────────────────────────────┘       │ activo          │
                                                         └─────────────────┘
```
