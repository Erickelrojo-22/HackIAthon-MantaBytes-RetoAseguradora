# Backlog priorizado — Auditoría de completitud FraudIA Claims

**Fecha:** 2026-08-09
**Método:** 10 revisiones de código independientes (una por pantalla/área, cruzando frontend con su contrato backend) + pruebas en vivo contra la app desplegada.

Este backlog consolida los hallazgos, deduplicados y fusionados donde se repetían entre pantallas (sobre todo manejo de errores). Cada ítem trae archivos y líneas concretas.

---

## Bloqueantes / Alta prioridad

### 1. Manejo de errores ausente o genérico en queries y mutaciones (cross-cutting)
La mayoría de las páginas destructuran `data`/`isLoading` de `useQuery` pero nunca `isError`, por lo que un 401/500/timeout termina renderizando el mismo estado que "no hay datos" (Dashboard, Claims, ClaimDetail). En ClaimDetail ninguna mutación tiene `onError`. En Agent.tsx/Vision.tsx sí hay `catch`, pero colapsa todo (timeout, 429, 413, red caída) en un mensaje genérico. Agravante: la ruta `claims/:id` sólo usa `ProtectedRoute` (no `RoleRoute`), así que Auditoria ve el formulario de "Decisión humana" aunque el backend le devuelva 403 — invisible por el mismo problema.
**Archivos:** `frontend/src/pages/Dashboard.tsx`, `Claims.tsx`, `ClaimDetail.tsx`, `Agent.tsx`, `Vision.tsx`, `App.tsx`, `src/fraudia_claims/api.py`

### 2. La carga de CSV es un simulacro: valida formato pero no persiste nada
`POST /claims/upload-csv` nunca escribe en las tablas ni dispara rescoring — el propio backend lo admite en un mensaje pequeño, fácil de pasar por alto.
**Archivos:** `src/fraudia_claims/api.py:375-428`, `ingestion.py`, `storage.py`, `frontend/src/pages/UploadCsv.tsx`

### 3. Claims.tsx: paginación inexistente (cap de 100) y filtros Ramo/Ciudad/Score ficticios
`/claims/risk` sólo acepta `level` y `limit` (máx. 100). Los filtros de Ramo/Ciudad/Score/Búsqueda son 100% client-side sobre esa página truncada — incluso las OPCIONES de los dropdowns salen del mismo dataset incompleto.
**Archivos:** `frontend/src/pages/Claims.tsx:10-39`, `src/fraudia_claims/api.py:211-218`, `agent_tools.py:11-36`

### 4. Audit log: 4 de 6 filtros backend no expuestos y sin paginación
El backend soporta `actor_email`, `resource_type`, `date_from`, `date_to` (columnas indexadas); la UI sólo expone `action` y `resourceId`. Cap silencioso en 100 eventos sin indicador de truncamiento.
**Archivos:** `frontend/src/pages/Audit.tsx:11-24`, `src/fraudia_claims/api.py:279-302`, `audit.py:84-124`

### 5. El router local de palabras clave intercepta ~13 de 16 intents antes de llegar a OpenAI
Coincidencias de una sola palabra (`'ramo' in normalized`, `'modelo' in normalized`) capturan preguntas libres que deberían llegar al LLM, aunque haya API key configurada (confirmado en vivo: "¿cómo funciona tu modelo?" → plantilla de métricas, no OpenAI).
**Archivos:** `src/fraudia_claims/agent_intents.py:87-141`, `openai_agent.py:299-305`

### 6. El agente OpenAI sólo soporta una ronda de tool-calling
Si el modelo necesita una segunda ronda (ej. listar casos → detalle de uno), `output_text` queda vacío y cae en silencio a modo offline sin error visible.
**Archivos:** `src/fraudia_claims/openai_agent.py:319-353`

### 7. El intent `session_case` está muerto en la app web
`/agent/question` nunca pasa `session_cases`; preguntar por "el último caso evaluado" siempre responde "no hay casos", incluso justo después de puntuar uno.
**Archivos:** `src/fraudia_claims/api.py:305-317,522`, `agent_responses.py:308-325`, `agent_intents.py:144-145`

### 8. El stub offline de Vision es visualmente indistinguible de un análisis real
Sin `OPENAI_API_KEY`, el resultado enlatado se renderiza con el mismo layout que uno real; "Confianza: 0%" se lee como un score genuino, no como "no evaluado".
**Archivos:** `src/fraudia_claims/vision.py:22-45`, `frontend/src/pages/Vision.tsx:84-98`

### 9. El grafo de relaciones se vuelve ilegible mucho antes del límite del backend
Con 80 nodos (límite hardcodeado en frontend) el espaciado cae a ~7px con círculos de 14-23px de radio — se fusionan visualmente y el clic va al nodo equivocado. El backend ya soporta `limit` ajustable (10-120) pero no hay control en la UI.
**Archivos:** `frontend/src/pages/Relationships.tsx:30,85-86,191-264`, `src/fraudia_claims/api.py:494-500`

### 10. Dashboard: `matriz_riesgo` se pide por la red pero nunca se renderiza
Dataset de heatmap ramo×nivel ya calculado y transmitido, gratis para una visualización de impacto.
**Archivos:** `src/fraudia_claims/analytics.py:102-116`, `api.py:243`, `frontend/src/pages/Dashboard.tsx:14`

### 11. La tarjeta "Ahorro potencial" no concilia con ningún KPI visible
Se calcula sobre `monto_priorizado`, que nunca se muestra; sólo se ve `monto_expuesto` (total, no sólo Rojo/Amarillo). La palabra "simulado" nunca aparece en la UI.
**Archivos:** `src/fraudia_claims/analytics.py:14,50`, `frontend/src/pages/Dashboard.tsx:52-53`

---

## Media prioridad

12. **Dashboard**: KPIs ya calculados (`score_promedio`, `casos_priorizados`, `porcentaje_priorizado`) nunca mostrados.
13. **Estados vacíos sin mensaje dedicado** en Dashboard (dona degenerada con 0 datos) y Audit (filtro sin resultados = header vacío).
14. **ClaimDetail**: `observacion` por documento, `monto_estimado`, `monto_pagado`, `estado`, `proveedor_lista_restrictiva` llegan del backend pero nunca se muestran.
15. **Agente**: `claim_detail` exige palabra clave aunque haya un SIN válido en la pregunta ("cuéntame sobre SIN-1023" no dispara el intent correcto).
16. **Agent.tsx**: sin auto-scroll al mensaje más reciente.
17. **UploadCsv**: la validación de columnas se salta en silencio si el nombre de archivo no coincide exactamente (case-sensitive).
18. **Vision**: no hay endpoint de estado para saber si está en modo offline antes de subir el archivo.
19. **Relationships**: `id_proveedor` nulo colapsaría siniestros en un nodo falso compartido (latente, no visible con datos sintéticos actuales).
20. **Relationships**: el color de arista para nivel Verde reutiliza el color del nodo Proveedor (la leyenda promete verde, nunca se dibuja).
21. **Reporte ejecutivo duplicado**: `reports.py` (backend, rico: metodología, hallazgos documentales, sesión en vivo) está muerto — no lo usa ningún endpoint. El frontend reimplementa una versión más pobre en `ExecutiveReport.tsx`.

---

## Baja prioridad / pulido

- Dashboard: tabla Top 10 sin estado vacío/loading propio.
- Claims: sin estado vacío para 0 resultados filtrados.
- Varios campos del backend (`tipo`, `total_siniestros` por proveedor/ciudad) llegan pero se recortan a nivel de tipos TS antes de poder mostrarse.
- `DashboardKpis` en `lib/api.ts` sólo modela el sub-objeto `kpis`, no el envelope completo.
- ClaimDetail: estado local no se resetea si cambia `:id` sin remount.
- ClaimDetail: `claim.ciudad` tipado como siempre presente pero el endpoint nunca lo devuelve (funciona por fallback a `sucursal`).
- Audit: inputs de filtro sin debounce, re-consultan en cada tecla.
- Vision: sin validación client-side de tamaño/tipo antes del round-trip; archivo no soportado da 200 "offline" pero archivo grande da 413 (inconsistente); `modelo_openai` nunca se muestra.
- Relationships: leyenda no explica que el grosor de arista = score; tabla se corta en 35 filas sin indicador; accesibilidad de teclado pobre con 150+ nodos tab-stop.
- `FAST_LOCAL_QUESTIONS` en `openai_agent.py` es una constante muerta.

---

## Código muerto a limpiar

- `demo.py`: `GUIDED_DEMO_STEPS` (eliminar), `featured_claims()` (mover a fixture de test), `_green_demo_case()` (eliminar, duplicado inalcanzable), `demo_questions()` (eliminar o conectar como chips sugeridos), `session_cases_frame()` (eliminar junto con reports.py, o exponer vía #21).
- `analytics.py: impact_summary()` — eliminar, superado por `executive_kpis()`.
- `storage.py: save_tables_to_sqlite()` — eliminar, alias muerto y engañoso.
- `auth.py: optional_user()` — eliminar salvo plan concreto de endpoint público.
- `ingestion.py: data_quality_report()` — eliminar o conectar a endpoint admin.
- `openai_agent.py: ask_agent()` / `ask_with_openai()` — eliminar, todo pasa por `ask_agent_with_status`.
- `synthetic_data.py: write_reference_context()` — eliminar o invocar desde el script de generación.
- `utils.py: parse_date()` / `bool_to_si_no()` — 0 llamadas en todo el repo.
- `api.py: GET /agent/executive-summary` — endpoint real, autenticado, sin consumidor ni test. Conectar o eliminar.

---

## Plan de ejecución

**Lote 1 (ahora):** los 11 ítems de alta prioridad, agrupados por área de código para minimizar PRs:
- Manejo de errores transversal (frontend)
- Dashboard: matriz_riesgo, reconciliación de ahorro, KPIs faltantes
- Claims: paginación + filtros reales en backend
- Audit: filtros + paginación
- Agente: routing menos agresivo, multi-ronda de tools, session_case wireado
- Vision: distinguir modo offline visualmente
- Relationships: control de límite + fix de legibilidad
- CSV upload: decisión sobre persistencia real vs. relabel honesto
- Reporte ejecutivo: unificar backend/frontend

**Lote 2 (después, si aplica):** media prioridad + limpieza de código muerto.
