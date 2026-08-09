# Contrato API Para Frontend

Base local:

```text
http://127.0.0.1:8000
```

## Autenticacion demo

```http
POST /auth/login
```

Usuarios:

- `analista@fraudia.demo` / `demo123`
- `jefatura@fraudia.demo` / `demo123`
- `auditoria@fraudia.demo` / `demo123`

Usar en endpoints protegidos:

```http
Authorization: Bearer demo-token-analista
```

Publicos: `POST /auth/login`, `GET /health`.

El resto de endpoints de negocio requieren Bearer (roles segun endpoint).

## Centro de mando

```http
GET /dashboard/kpis
```

Respuesta:

- `kpis`: totales, rojos, amarillos, monto expuesto, monto priorizado, ahorro potencial.
- `proveedores_criticos`: top proveedores.
- `ciudades_criticas`: concentracion por ciudad.
- `matriz_riesgo`: matriz ramo/nivel.

## Expediente

```http
GET /claims/{id_siniestro}
GET /claims/{id_siniestro}/review-history
POST /claims/{id_siniestro}/review-decision
```

Decision humana:

```json
{
  "status": "Escalado",
  "comentario": "Revision documental requerida."
}
```

Estados validos:

- `En revision`
- `Descartado`
- `Escalado`
- `Confirmado para investigacion`

La decision humana no modifica `scores`.

## Agente

```http
POST /agent/question
GET /agent/suggested-questions/{id_siniestro}
GET /agent/executive-summary?group_by=proveedor&value=Clinica
```

Pregunta:

```json
{
  "question": "Explica este caso",
  "id_siniestro": "SIN00001",
  "scope": "claim"
}
```

El agente siempre devuelve disclaimer de revision humana y cae a modo offline si OpenAI no esta configurado.

## Auditoria

```http
GET /audit-log
```

Filtros opcionales:

- `actor_email`
- `action`
- `resource_type`
- `resource_id`
- `date_from`
- `date_to`
- `limit`

## Carga CSV

```http
POST /claims/upload-csv
```

Multipart field: `file`.

En v1 valida columnas y registra auditoria, pero no reemplaza tablas persistidas desde este endpoint.

## Red de relaciones

```http
GET /relationships?limit=80
```

Devuelve `nodes` y `edges` para conectar siniestros, asegurados anonimos y proveedores.

## Reporte ejecutivo

```http
GET /report/summary
```

Devuelve resumen, exposicion, ahorro potencial simulado, top casos, proveedores 80/20 y metricas del modelo.

## Vision

```http
POST /vision/analyze
```

Multipart field: `file`. Query opcional: `id_siniestro`.

El analisis visual es auxiliar, no persiste imagenes y no modifica `scores`.
