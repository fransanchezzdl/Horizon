# Arquitectura del Proyecto Horizon

Este documento describe la arquitectura funcional del proyecto a nivel de capas y responsabilidades. Su objetivo es servir como referencia estable para el desarrollo de nuevas funcionalidades, endpoints y servicios.

## Principios de diseño

- Separación clara de responsabilidades entre frontend, controladores, servicios y acceso a datos.
- Validación de entrada y salida mediante DTOs.
- Reutilización de lógica de negocio en servicios, evitando duplicación en controladores.
- Acceso a base de datos encapsulado en DAOs.
- Evolución por módulos de dominio, manteniendo el mismo patrón arquitectónico.

## Vista general por capas

### Capa de presentación

Responsable de renderizar interfaz y gestionar eventos de usuario.

Incluye:

- Páginas HTML del frontend.
- Lógica de interacción en JavaScript.
- Llamadas HTTP al backend para lectura y escritura de datos.

Responsabilidades:

- Mostrar estado de la aplicación.
- Recoger entradas del usuario.
- Invocar endpoints del backend.
- Aplicar reglas de sesión y navegación.

No debe contener lógica de negocio de dominio ni acceso directo a base de datos.

### Capa de controladores

Representada por los endpoints del backend.

Incluye:

- Definición de rutas HTTP.
- Parseo de requests y serialización de responses.
- Inyección de dependencias como autenticación.
- Delegación del trabajo a servicios.

Responsabilidades:

- Actuar como frontera entre API y lógica de negocio.
- Aplicar contratos de entrada y salida con DTOs.
- Gestionar códigos HTTP y excepciones de forma consistente.

No debe contener lógica de negocio compleja ni consultas directas a base de datos.

### Capa de servicios

Contiene la lógica de negocio del sistema.

Incluye:

- Reglas de dominio.
- Orquestación de operaciones entre DAOs y componentes externos.
- Composición de resultados para devolver al controlador.

Responsabilidades:

- Validar reglas funcionales.
- Coordinar procesos de varios pasos.
- Mantener coherencia de comportamiento entre endpoints.

Los servicios son el punto principal de extensión cuando se añaden nuevas capacidades al sistema.

### Capa de acceso a datos

Encapsulada mediante DAOs.

Incluye:

- Consultas y operaciones CRUD.
- Mapeo de estructuras persistidas a objetos de aplicación.
- Manejo de detalles de proveedor o cliente de base de datos.

Responsabilidades:

- Aislar la persistencia del resto de capas.
- Proveer interfaces claras para lectura y escritura.
- Evitar que controladores o frontend conozcan detalles de almacenamiento.

## Uso de DTOs

Los DTOs definen el contrato de datos entre cliente y servidor y entre capas internas.

Tipos habituales:

- DTOs de request: validan estructura y formato de entrada.
- DTOs de response: normalizan salida y evitan exponer estructuras internas.

Beneficios:

- Validación temprana de datos.
- Consistencia en el contrato API.
- Menor acoplamiento entre modelos internos y representación pública.

## Flujo típico de una operación

1. La vista envía una solicitud HTTP.
2. El controlador recibe y valida el request con un DTO.
3. El controlador delega en el servicio correspondiente.
4. El servicio aplica reglas de negocio y usa DAOs para persistencia.
5. El DAO ejecuta la operación de datos y devuelve resultado.
6. El servicio transforma y devuelve la respuesta al controlador.
7. El controlador responde con DTO de salida y código HTTP adecuado.

## Ejemplo de referencia: login

El caso de login ilustra el patrón general:

1. La vista de login envía credenciales al endpoint de autenticación.
2. El controlador delega en el servicio de autenticación.
3. El servicio valida credenciales contra proveedor de autenticación y recupera perfil de usuario vía DAO.
4. El servicio devuelve token y datos de usuario.
5. El controlador serializa la respuesta según DTO.
6. La vista almacena sesión y continúa al área protegida.

Este patrón es el mismo que debe seguir cualquier nueva funcionalidad del proyecto.

## Escalabilidad y mantenimiento

Para nuevas funcionalidades:

- Crear o extender DTOs para contratos de entrada y salida.
- Añadir endpoints mínimos en controladores, delegando en servicios.
- Implementar o reutilizar lógica de negocio en servicios.
- Centralizar operaciones de persistencia en DAOs.
- Mantener la misma convención de errores y respuestas.

Con este enfoque, la arquitectura se mantiene predecible, testeable y fácil de extender al crecer el número de módulos.
