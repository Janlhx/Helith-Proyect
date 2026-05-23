# Helith — Documentación de Planificación

> Bot de Discord · Multi-LLM · ML Engineering  
> Autor: Juan (Litxe) · UPB Medellín · 2026

---

## Índice

1. [Visión General](#1-visión-general)
2. [Contexto y Lecciones de Dalet](#2-contexto-y-lecciones-de-dalet)
3. [Identidad del Proyecto](#3-identidad-del-proyecto)
4. [Requisitos Funcionales](#4-requisitos-funcionales)
5. [Requisitos No Funcionales](#5-requisitos-no-funcionales)
6. [Arquitectura](#6-arquitectura)
7. [Stack Tecnológico](#7-stack-tecnológico)
8. [Estructura del Proyecto](#8-estructura-del-proyecto)
9. [DevOps y CI/CD](#9-devops-y-cicd)
10. [Fases de Desarrollo](#10-fases-de-desarrollo)
11. [Diferencias Clave con Dalet](#11-diferencias-clave-con-dalet)
12. [Métricas de Éxito](#12-métricas-de-éxito)
13. [Decisiones Técnicas Registradas](#13-decisiones-técnicas-registradas)

---

## 1. Visión General

Helith es un bot de Discord de segunda generación, desarrollado como sucesor espiritual de Dalet. A diferencia de Dalet, construida incrementalmente sin planificación formal, Helith nace con un proceso de ingeniería de software aplicado: requisitos definidos, arquitectura diseñada antes del código, y decisiones técnicas deliberadas y documentadas.

**Helith no reemplaza a Dalet.** Coexisten cubriendo espacios distintos:

- **Dalet** → conversacional, integración osu!, personalidad sarcástica y pasota
- **Helith** → análisis predictivo con ML, gestión inteligente de recursos LLM, confiabilidad como valor central, personalidad reservada y directa

**Principio rector:** Helith hace menos cosas que Dalet, pero las hace bien. Ningún comando roto llega a producción.

---

## 2. Contexto y Lecciones de Dalet

Dalet fue construida con vibe coding sin arquitectura previa. Con el tiempo acumuló problemas estructurales que informan directamente el diseño de Helith:

| Problema en Dalet                       | Impacto                                                            | Solución en Helith                                                     |
| --------------------------------------- | ------------------------------------------------------------------ | ---------------------------------------------------------------------- |
| Fallback a Llama (calidad muy inferior) | Respuestas incoherentes con la personalidad cuando Gemini se agota | Pool de modelos de calidad comparable, nunca degradar a modelo incapaz |
| Sin monitoreo de tokens                 | El colapso ocurre sin aviso, imposible actuar preventivamente      | Monitoreo predictivo con alertas antes del agotamiento                 |
| Comandos rotos en producción            | Degrada la experiencia, quita interés a los usuarios               | Ninguna feature llega a producción si no pasa tests                    |
| Datos técnicos expuestos públicamente   | Inapropiado en servidores con muchos usuarios                      | Comandos de admin solo accesibles para el administrador del bot        |
| Sin proceso de ingeniería               | Dificulta mantenimiento y evolución del proyecto                   | DDD + documentación + CI/CD desde el día uno                           |

---

## 3. Identidad del Proyecto

### 3.1 Personalidad de Helith

El contrapunto de Dalet. Donde Dalet es sarcástica, ácida y pasota, Helith es reservada y deliberada — habla menos pero cuando habla tiene peso. Escucha antes de hablar.

| Atributo           | Descripción                                                                      |
| ------------------ | -------------------------------------------------------------------------------- |
| Tono               | Reservada, directa, con profundidad. Menos ácida que Dalet.                      |
| Emojis             | Raramente. No performativa.                                                      |
| Roleplay           | No. Solo texto directo.                                                          |
| Relación con Dalet | Son conocidas. Helith puede hacer referencias sutiles a Dalet sin ser su sombra. |
| Creador            | Litxe. No lo menciona a menos que sea relevante.                                 |

### 3.2 Propuesta de Valor

- Multi-servidor desde el diseño, no como afterthought
- ML como funcionalidad real, no como llamada de API disfrazada
- Confiabilidad: si una feature existe, funciona
- Gestión inteligente de tokens — el bot nunca colapsa silenciosamente

---

## 4. Requisitos Funcionales

### RF-01 al RF-03 — Conversación con Gestión de Recursos

- **RF-01:** El bot responde cuando se menciona su nombre directamente (modo reactivo).
  - El contexto de conversación se mantiene por canal, no globalmente.
  - El contexto se trunca inteligentemente preservando los mensajes más relevantes.
- **RF-02:** Modo proactivo configurable por servidor con cooldown por usuario.
  - El administrador define la probabilidad de respuesta espontánea.
  - Cooldown independiente por usuario evita que uno solo agote el presupuesto.
- **RF-03:** Sistema de memoria semántica por servidor.
  - Embeddings almacenados en Supabase (pgvector) para búsqueda de contexto relevante.
  - La memoria se usa como contexto adicional, no como sustituto del historial reciente.

### RF-04 al RF-05 — Router de Intención

- **RF-04:** El router clasifica cada mensaje en una categoría de intención antes de invocar cualquier LLM.
  - Categorías: conversación general, análisis predictivo osu!, consulta de datos, comando administrativo.
  - La clasificación usa lógica determinista o un modelo ligero local — nunca un LLM de API.
- **RF-05:** Cada categoría de intención tiene asignado un dominio responsable.

### RF-06 al RF-08 — ML: Análisis Predictivo de osu!

- **RF-06:** El usuario puede consultar una predicción de tiempo estimado para alcanzar un rank objetivo.
  - Input: username de osu!, rank objetivo.
  - Output: estimación con intervalos de confianza e indicadores de mejora.
- **RF-07:** El modelo se entrena con datos reales de la API de osu! y la base de datos existente de Dalet.
- **RF-08:** Las predicciones incluyen indicadores accionables, no solo un número.

### RF-09 al RF-12 — ML: Monitoreo Predictivo de Tokens

- **RF-09:** El sistema registra cada llamada a LLM con metadata: modelo, tokens, servidor, usuario, timestamp.
- **RF-10:** Un modelo predice el consumo futuro por modelo y por servidor, con alertas preventivas.
- **RF-11:** Dashboard de métricas solo accesible para el administrador del bot.
- **RF-12:** El sistema compara consumo real vs. predicciones anteriores para evaluar la precisión del modelo.

### RF-13 al RF-15 — Administración

- **RF-13:** El administrador puede habilitar/deshabilitar comandos por canal.
- **RF-14:** Comandos de estado técnico solo accesibles para el administrador del bot.
- **RF-15:** El bot reporta su estado al iniciar (versión, modelos disponibles, estado de la DB).

### RF-16 — Búsqueda Web (Tavily)

- **RF-16:** El bot puede realizar búsquedas web en tiempo real usando la API de Tavily para responder a preguntas sobre eventos recientes, noticias o información dinámica.

#### Decisiones de diseño para búsqueda en web (Tavily)

| Decisión               | Definición                                                                                                                                                                                 |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Cuándo busca           | Solo cuando la pregunta requiere información actual — noticias, eventos recientes, precios, cosas que cambian con el tiempo. Conocimiento general que el LLM ya tiene no dispara búsqueda. |
| Dónde vive             | `core/tools/search.py` — herramienta compartida, cualquier dominio puede invocarla                                                                                                         |
| Optimización de tokens | Los resultados de Tavily se resumen a 2-3 datos clave antes de inyectarse al prompt. Nunca el artículo completo.                                                                           |
| Formato de respuesta   | Máximo 3 líneas. Concisa, directa, con espacio para el tono natural de Helith. Sin bloques informativos.                                                                                   |

#### Flujo

Mensaje del usuario
│
▼
Router detecta si necesita info actual
│
┌──┴──┐
No Sí
│ │
│ Tavily busca
│ │
│ Se resume a 2-3 datos clave
│ │
└──► LLM genera respuesta
máximo 3 líneas

#### Ubicación en el proyecto

core/
└── tools/
└── search.py # cliente de Tavily + lógica de resumen

#### Notas

- La detección de si una pregunta requiere búsqueda vive en el router de intención, no en el LLM — evita gastar tokens para decidir si buscar.
- Tavily tiene free tier de 1000 búsquedas/mes — suficiente para staging y early production.
- Si Tavily falla, Helith responde con lo que sabe y lo aclara honestamente si es necesario.

---

### 4.6 Arquitectura de Prompts y Optimización (RAG)

Para evitar que el modelo sufra "Disonancia Cognitiva" (ignorar los datos en tiempo real para mantener su personalidad base), la arquitectura de prompts está dividida estrictamente:

- **System Prompt:** EXCLUSIVAMENTE para la personalidad estática de Helith (`core/llm/prompts.py`).
- **User Prompt (Contexto Situacional):** Los datos recuperados (Búsqueda Web y Memorias Semánticas) se inyectan dinámicamente como encabezados en el historial de conversación, forzando al LLM a asimilarlos como realidad actual sin romper su personaje.

**Estrategia de Escalamiento y Optimización de Tokens:**
- La ventana de chat se limita a los últimos 10 mensajes (Sliding Window).
- Solo se envían las 3 memorias más relevantes.
- Costo promedio por mensaje: ~1,600 tokens (incluyendo personalidad e historial).
- Dado el *Rate Limit Global* de Discord (50 peticiones/5s) y el cooldown local de Helith (60s), el cuello de botella es Discord, no la IA. Esta configuración actual asegura máxima estabilidad y podría soportar más de 100 servidores activos por instancia sin modificaciones profundas.

---

## 5. Requisitos No Funcionales

| ID     | Requisito                  | Descripción                                                                                                  |
| ------ | -------------------------- | ------------------------------------------------------------------------------------------------------------ |
| RNF-01 | Confiabilidad              | Ninguna feature existe en producción si no funciona. Sin comandos rotos.                                     |
| RNF-02 | Resiliencia de DB          | Si Supabase no está disponible, el bot opera en modo degradado con SQLite local. El usuario es notificado.   |
| RNF-03 | Degradación gradual de LLM | El fallback nunca desciende a un modelo incapaz de sostener la personalidad.                                 |
| RNF-04 | Transparencia de errores   | Los errores se registran con contexto suficiente. El usuario recibe un mensaje claro, no silencio.           |
| RNF-05 | Latencia                   | Tiempo de respuesta conversacional máximo de 5 segundos en condiciones normales.                             |
| RNF-06 | Seguridad                  | Información técnica interna nunca expuesta públicamente. Validación de permisos en todos los comandos admin. |

---

## 6. Arquitectura

### 6.1 Decisión de Diseño Central

> El orquestador NO usa un LLM para decidir qué dominio invocar. La clasificación es determinista o usa un modelo ligero local. Esto elimina el costo doble de tokens que tendría un sistema agéntico puro.

### 6.2 Flujo General

```
Discord Event
     │
     ▼
Discord Gateway (domains/bot)
     │
     ▼
Router de Intención ──── clasificación determinista
     │
     ├──► domains/conversation   (conversación general)
     ├──► domains/osu            (predicción de progreso)
     ├──► domains/monitoring     (consultas de métricas)
     └──► domains/admin          (comandos administrativos)
              │
              ▼
         core/llm/pool           (si el dominio necesita LLM)
              │
              ├── Gemini (primario)
              ├── Claude Haiku / GPT-4o mini (fallback 1)
              └── Groq Llama 70B (fallback 2, no conversacional)
```

### 6.3 Estrategia Multi-LLM

| Nivel               | Modelo                     | Uso                                                           |
| ------------------- | -------------------------- | ------------------------------------------------------------- |
| Primario            | Gemini Flash / Pro         | Conversación general, análisis de contexto                    |
| Fallback 1          | Claude Haiku o GPT-4o mini | Calidad comparable, proveedor diferente                       |
| Fallback 2          | Groq + Llama 3.1 70B       | Solo respuestas simples, no conversacionales                  |
| Clasificación local | sentence-transformers      | Router de intención, embeddings de memoria. Sin costo de API. |

### 6.4 Control de Costos

- Rate limiting por usuario (no global)
- Cooldown configurable por servidor
- Context window management con truncado inteligente por relevancia
- Monitoreo predictivo con alertas preventivas

### 6.5 Consideraciones Operacionales

- **Health Check (Flask):** El health check no debe hacer queries a la base de datos, solo confirmar que el proceso está vivo y que el bot está conectado a Discord.
- **Doble uso de UptimeRobot:** Se utiliza para mantener vivo el proceso en Render (evitando que se duerma) y para realizar pings periódicos a Supabase para evitar la pausa por inactividad después de 7 días.

---

## 7. Stack Tecnológico

| Componente                | Tecnología                      | Justificación                                                        |
| ------------------------- | ------------------------------- | -------------------------------------------------------------------- |
| Lenguaje principal        | Python 3.11+                    | Ecosistema ML sin equivalente real en otros lenguajes                |
| Framework Discord         | discord.py                      | Estable, bien documentado                                            |
| Base de datos             | Supabase (PostgreSQL)           | Free tier generoso + pgvector nativo para embeddings                 |
| DB fallback               | SQLite                          | Resiliencia sin dependencia externa                                  |
| Embeddings / memoria      | pgvector en Supabase            | Elimina necesidad de infraestructura separada para vectores          |
| Embeddings locales        | sentence-transformers           | Para el router y generación de embeddings sin costo de API           |
| ML predictivo             | scikit-learn / XGBoost          | Predicción de progreso osu!                                          |
| Monitoreo de tokens       | Modelo propio (scikit-learn)    | Entrenado con datos generados por el propio bot                      |
| LLMs                      | Gemini API, Anthropic API, Groq | Pool multi-proveedor                                                 |
| Hosting del bot           | Render                          | Free tier disponible, desplegado con Flask mínimo para health checks |
| Web Server (Health Check) | Flask                           | Necesario para mantener vivo el proceso en el free tier de Render    |
| Monitoreo / Keep-alive    | UptimeRobot                     | Evita que Render se duerma y que Supabase se pause por inactividad   |
| Gestión de dependencias   | uv                              | Más rápido que pip, moderno                                          |

> **Nota:** PostgreSQL se mantiene como motor de base de datos. Supabase lo provee gestionado con ventajas adicionales (pgvector, dashboard, free tier). _Nota operacional:_ Supabase pausa proyectos inactivos tras 7 días; se mitiga con pings de UptimeRobot.

---

## 8. Estructura del Proyecto

Arquitectura basada en **Domain-Driven Design (DDD)** — cada dominio es autónomo y contiene todo lo que necesita.

```
helith/
├── .github/
│   └── workflows/
│       ├── ci.yml              # tests + lint en push/PR
│       └── cd.yml              # deploy a Render en merge a main/staging
├── core/                       # infraestructura compartida (no es un dominio)
│   ├── db/
│   │   ├── connection.py       # conexión a Supabase
│   │   └── fallback.py         # lógica de fallback a SQLite
│   ├── llm/
│   │   ├── pool.py             # pool multi-LLM con prioridad
│   │   └── fallback.py         # lógica de fallback entre modelos
│   ├── config.py               # variables de entorno
│   └── exceptions.py           # excepciones base del proyecto
├── domains/
│   ├── bot/                    # Discord gateway + router de intención
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── router.py
│   ├── conversation/           # historial, memoria semántica, LLM calls
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── router.py
│   ├── osu/                    # predicción de progreso + integración API osu!
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── router.py
│   ├── monitoring/             # monitoreo y predicción de tokens
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── router.py
│   └── admin/                  # configuración por servidor, permisos
│       ├── models.py
│       ├── repository.py
│       ├── service.py
│       └── router.py
├── tests/
│   ├── unit/                   # tests por dominio
│   └── integration/            # tests de flujos completos
├── docs/                       # documentación técnica adicional
├── .env.example
├── docker-compose.yml          # entorno de desarrollo local
├── pyproject.toml
└── README.md
```

---

## 9. DevOps y CI/CD

### Branches

| Branch        | Propósito                                           |
| ------------- | --------------------------------------------------- |
| `development` | Trabajo diario, features en progreso                |
| `staging`     | Validación antes de producción, ambiente de pruebas |
| `main`        | Producción, solo mergea lo que está verificado      |

### Pipeline CI (GitHub Actions — ci.yml)

Se ejecuta en cada push y pull request:

- Linting con `ruff`
- Type checking con `mypy`
- Tests unitarios con `pytest`
- Tests de integración con `pytest`
- Ningún PR puede mergearse si el pipeline falla

### Pipeline CD (GitHub Actions — cd.yml)

- Merge a `staging` → deploy automático al ambiente de staging en Render
- Merge a `main` → deploy automático a producción en Render

### Tests

- **Unitarios:** router de intención, lógica de rate limiting, monitoreo de tokens, fallback de DB
- **Integración:** flujo completo de fallback LLM, fallback de DB a SQLite, respuesta del bot end-to-end
- **Fixtures:** mocks de APIs externas para no gastar tokens reales en tests

---

## 10. Fases de Desarrollo

> Cada fase produce entregables verificables antes de avanzar. Ninguna funcionalidad se marca como completa si no pasa los tests definidos.

### Fase 1 — Fundamentos

Objetivo: el bot conecta a Discord, responde mensajes básicos, y el sistema multi-LLM con fallback funciona.

- Estructura del repositorio y arquitectura DDD
- Conexión a Discord con manejo de eventos
- Sistema multi-LLM con fallback y logging de cada llamada
- Personalidad base de Helith en system prompt
- Conexión a Supabase con fallback a SQLite
- Pipelines de CI/CD configurados y funcionando

### Fase 2 — Conversación e Identidad

Objetivo: la conversación es coherente, la memoria funciona, y el rate limiting está activo.

- Historial de conversación por canal con context window management
- Memoria semántica con pgvector en Supabase
- Rate limiting por usuario y cooldown configurable por servidor
- Router de intención (versión inicial con lógica determinista)
- Tests unitarios de los módulos core

### Fase 3 — Monitoreo de Tokens

Objetivo: el sistema tiene visibilidad total de su consumo y puede predecir agotamiento.

- Registro de todas las llamadas LLM con metadata completa
- Modelo de predicción de consumo (primera versión, regresión)
- Sistema de alertas para el administrador del bot
- Dashboard básico de métricas basado en Flask (solo admin)
- Comparación consumo real vs. predicción para evaluar el modelo

### Fase 4 — ML Predictivo osu!

Objetivo: la feature diferenciadora de Helith está funcionando con datos reales.

- Pipeline de recolección de datos desde API de osu! y DB de Dalet
- Modelo de predicción de progreso de rank
- Integración con Discord — comando de consulta de predicción
- Iteración del modelo con feedback de usuarios reales

### Fase 5 — Pulido y Estabilización

Objetivo: el bot está listo para operar en múltiples servidores de forma estable y con habilidades de búsqueda avanzadas.

- Integración y optimización de Búsqueda Web (Tavily)
- Comandos de administración completos
- Pruebas de carga bajo múltiples usuarios simultáneos
- Documentación de comandos para usuarios finales
- Revisión de seguridad — ningún dato interno expuesto públicamente
- Despliegue en servidores de prueba antes de rollout completo

---

## 11. Diferencias Clave con Dalet

| Aspecto                 | Dalet                                  | Helith                                                     |
| ----------------------- | -------------------------------------- | ---------------------------------------------------------- |
| Proceso de desarrollo   | Vibe coding sin planificación          | Ingeniería de software: requisitos → arquitectura → código |
| Gestión de tokens       | Sin monitoreo, colapso silencioso      | Monitoreo predictivo, alertas preventivas                  |
| Sistema de fallback LLM | Gemini → Llama (calidad muy diferente) | Pool de modelos de calidad comparable                      |
| Comandos rotos          | Existen en producción                  | No llegan a producción                                     |
| Datos técnicos          | Visibles públicamente                  | Solo accesibles para el administrador                      |
| ML                      | Llamadas a API disfrazadas de ML       | Modelos propios para predicción y monitoreo                |
| Personalidad            | Sarcástica, ácida, pasota              | Reservada, directa, con profundidad                        |
| Enfoque principal       | osu! + conversación general            | ML predictivo + conversación estable                       |
| Arquitectura            | Sin estructura definida                | Domain-Driven Design                                       |
| Infraestructura         | Render + Neon                          | Render + Supabase                                          |
| DevOps                  | Sin CI/CD                              | GitHub Actions + deploy automático por branch              |

---

## 12. Métricas de Éxito

- Cero comandos rotos en producción al final de cada fase
- El bot nunca colapsa silenciosamente — siempre hay respuesta, aunque sea de error
- El modelo de monitoreo predice el agotamiento de tokens con al menos 48 horas de anticipación
- Las predicciones de progreso osu! tienen un error medio aceptable validado con datos reales
- El sistema mantiene coherencia de personalidad bajo carga de múltiples usuarios simultáneos
- Cobertura de tests mínima del 70% en módulos core antes de pasar a producción

---

## 13. Decisiones Técnicas Registradas

Esta sección documenta el razonamiento detrás de decisiones importantes. Útil para no repetir debates ya resueltos.

| Decisión                           | Alternativas consideradas                        | Razón de la elección                                                                                                                                         |
| ---------------------------------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Python como lenguaje principal     | TypeScript, arquitectura mixta                   | Ecosistema ML insustituible. Complejidad de dos runtimes no justificada en esta etapa.                                                                       |
| Render sobre Railway               | Railway, Fly.io, VPS                             | Decisión de usar Render por disponibilidad y facilidad de uso con UptimeRobot para mantenerlo vivo.                                                          |
| Supabase sobre Neon                | Neon, ElephantSQL, Tembo                         | pgvector nativo elimina infraestructura separada para embeddings. Free tier más generoso.                                                                    |
| DDD sobre arquitectura por capas   | Por capas, monorepo                              | Dominios bien definidos desde el inicio. Más intuitivo de navegar. Mejor alineación con lo aprendido en Ingeniería de Software.                              |
| Router determinista, no agéntico   | Sistema agéntico con LLM orquestador             | Un orquestador LLM duplica el gasto de tokens antes de llegar a la funcionalidad real. Clasificación determinista es más robusta y económica.                |
| Pool de LLMs de calidad comparable | Un solo proveedor con fallback a modelo inferior | El problema principal de Dalet fue el fallback a Llama — calidad insuficiente para sostener personalidad. El fallback debe ser transparente para el usuario. |
| uv sobre pip/poetry                | pip, poetry, conda                               | Más rápido, moderno, mejor manejo de dependencias en proyectos nuevos.                                                                                       |

---

_Documento vivo — se actualiza conforme el proyecto avanza._
