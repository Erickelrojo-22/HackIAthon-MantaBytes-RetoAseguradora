# Contexto Para Antigravity: Frontend FraudIA Claims

## Objetivo Del Proyecto

FraudIA Claims es una demo de hackathon para una aseguradora. El sistema prioriza siniestros de `Vehiculos`, `Salud` y `Hogar` con reglas explicables, anomalias, NLP, agente IA opcional y revision humana.

Principio etico obligatorio:

- La IA no acusa fraude.
- La IA no rechaza reclamos.
- La IA no decide pagos.
- El score es una alerta para revision humana.

El frontend nuevo debe verse como un sistema empresarial para analistas, jefatura y auditoria.

## Estado Actual

Rama principal de trabajo:

```text
feature/dashboard-visual-polish
```

Ultimos commits relevantes:

```text
3243c28 Add enterprise demo UI hooks
f4b450c Add enterprise review API
f77ee65 Prepare secure AI deployment for judges
c4bb6e1 Add optional vision analysis page
```

Backend y frontend disponibles:

- FastAPI en `src/fraudia_claims/api.py`.
- Frontend React/Vite en `frontend/`.
- SQLite local por defecto.
- PostgreSQL soportado por variables de entorno.
- OpenAI opcional con fallback offline.

Documentos utiles:

- `README.md`
- `docs/api_frontend.md`
- `docs/despliegue.md`
- `docs/arquitectura.md`
- `docs/uso_ia.md`

## Como Levantar El Backend

Desde la raiz del repo:

```powershell
cd C:\Users\Erick\Desktop\Hackiathon-Aseguradora\HackIAthon-MantaBytes-RetoAseguradora
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\generate_demo_data.py --force
.\.venv\Scripts\python.exe -m uvicorn fraudia_claims.api:app --app-dir src --reload
```

Base local API:

```text
http://127.0.0.1:8000
```

Documentacion interactiva:

```text
http://127.0.0.1:8000/docs
```

Frontend React:

```powershell
cd frontend
npm install
npm run dev
```

## Autenticacion Demo

Endpoint:

```http
POST /auth/login
```

Usuarios:

```text
analista@fraudia.demo  / demo123 / Analista
jefatura@fraudia.demo  / demo123 / Jefatura
auditoria@fraudia.demo / demo123 / Auditoria
```

Ejemplo request:

```json
{
  "email": "analista@fraudia.demo",
  "password": "demo123"
}
```

Ejemplo response:

```json
{
  "access_token": "demo-token-analista",
  "user": {
    "email": "analista@fraudia.demo",
    "name": "Analista Demo",
    "role": "Analista"
  }
}
```

Usar en endpoints protegidos:

```http
Authorization: Bearer demo-token-analista
```

Tokens demo:

```text
demo-token-analista
demo-token-jefatura
demo-token-auditoria
```

## Endpoints Principales Para Frontend

### Health

```http
GET /health
```

No requiere token.

### Centro De Mando

```http
GET /dashboard/kpis
```

Requiere token.

Devuelve:

- `kpis`
- `proveedores_criticos`
- `ciudades_criticas`
- `matriz_riesgo`

Uso sugerido:

- Dashboard inicial tipo centro de mando.
- KPIs superiores.
- Graficos de riesgo por ramo, ciudad y proveedor.

### Bandeja De Revision

```http
GET /claims/risk?limit=50&level=Rojo
```

No requiere token actualmente.

Campos utiles:

- `id_siniestro`
- `score_final`
- `nivel_riesgo`
- `ramo`
- `cobertura`
- `ciudad`
- `monto_reclamado`
- `proveedor`
- `explicacion_resumen`

### Expediente Del Siniestro

```http
GET /claims/{id_siniestro}
```

Devuelve:

- datos del siniestro;
- score dividido;
- proveedor;
- alertas;
- documentos;
- narrativa similar;
- accion sugerida.

Para historial humano:

```http
GET /claims/{id_siniestro}/review-history
```

Para guardar decision:

```http
POST /claims/{id_siniestro}/review-decision
```

Payload:

```json
{
  "status": "Escalado",
  "comentario": "Revision documental requerida."
}
```

Estados permitidos:

```text
En revision
Descartado
Escalado
Confirmado para investigacion
```

Nota: esta decision humana no modifica el score.

### Auditoria

```http
GET /audit-log
```

Requiere rol `Jefatura` o `Auditoria`.

Filtros opcionales:

```text
actor_email
action
resource_type
resource_id
date_from
date_to
limit
```

Uso sugerido:

- Tabla de trazabilidad.
- Filtros por usuario, caso y accion.
- Mostrar que cada accion humana queda registrada.

### Agente IA

```http
POST /agent/question
```

Payload:

```json
{
  "question": "Explica este caso",
  "id_siniestro": "SIN00001",
  "scope": "claim"
}
```

Response:

```json
{
  "answer": "...",
  "source": "OpenAI activo (...) u Offline ...",
  "disclaimer": "Alerta de revision humana; no acusacion ni decision automatica."
}
```

Preguntas sugeridas:

```http
GET /agent/suggested-questions/{id_siniestro}
```

Resumen ejecutivo:

```http
GET /agent/executive-summary?group_by=proveedor&value=Clinica
GET /agent/executive-summary?group_by=ciudad&value=Manta
```

### Carga CSV

```http
POST /claims/upload-csv
```

Multipart:

```text
file=<csv>
```

En v1 valida columnas y registra auditoria. No reemplaza tablas persistidas.

### Score Temporal Para Prueba Del Jurado

```http
POST /score-candidate
```

Payload ejemplo:

```json
{
  "ramo": "Vehiculos",
  "cobertura": "Perdida Total por Robo",
  "monto_reclamado": 29500,
  "suma_asegurada": 30000,
  "dias_desde_inicio_poliza": 1,
  "dias_desde_fin_poliza": 364,
  "dias_entre_ocurrencia_reporte": 5,
  "denuncia_horas": 120,
  "documentos_completos": false,
  "documentos_inconsistentes": true,
  "tercero_identificado": false
}
```

## Pantallas Recomendadas Para El Nuevo Frontend

### 1. Login

- Selector visual de rol o formulario email/password.
- Guardar `access_token` en estado local del frontend.
- Mostrar nombre y rol activo.

### 2. Centro De Mando

Consumir:

- `GET /dashboard/kpis`
- `GET /claims/risk`
- `GET /alerts/provider-pareto`

Componentes:

- KPIs: total siniestros, rojos, amarillos, monto expuesto, monto priorizado, ahorro potencial.
- Grafico distribucion de riesgo.
- Pareto proveedores criticos.
- Concentracion por ciudad.
- Tabla top 10 casos.

### 3. Bandeja De Revision

Consumir:

- `GET /claims/risk`

Filtros frontend:

- nivel;
- ramo;
- ciudad;
- proveedor;
- score minimo.

Click en caso abre expediente.

### 4. Expediente Del Siniestro

Consumir:

- `GET /claims/{id_siniestro}`
- `GET /claims/{id_siniestro}/review-history`
- `POST /claims/{id_siniestro}/review-decision`
- `POST /agent/question`
- `GET /agent/suggested-questions/{id_siniestro}`

Secciones:

- Header: ID, nivel, score, monto, proveedor.
- Score breakdown: reglas, anomalias, NLP, modelo.
- Alertas con evidencia.
- Documentos observados.
- Timeline basico:
  - ocurrencia;
  - reporte;
  - scoring;
  - decisiones humanas.
- Boton `Explicar con IA`.
- Boton `Preguntas sugeridas`.
- Formulario decision humana.
- Disclaimer etico visible.

### 5. Prueba Del Jurado

Consumir:

- `POST /score-candidate`
- `POST /agent/question`

Flujo:

1. Formulario de caso nuevo.
2. Boton `Ejecutar score`.
3. Mostrar score temporal.
4. Boton `Explicar con IA`.
5. Mostrar mensaje: "esto no modifica la base y no acusa fraude".

### 6. Analisis De Imagenes

Actualmente no hay endpoint dedicado de imagen en la API publica.

Opcion recomendada para frontend:

- Crear despues `POST /vision/analyze-image`.
- Multipart `file`.
- Campos opcionales: `id_siniestro`, `ramo`, `cobertura`, `monto_reclamado`.
- Respuesta igual a `vision.py`: estado, severidad, confianza, observaciones, anomalias, disclaimer.

Mientras tanto, esta funcion existe en backend interno:

```text
src/fraudia_claims/vision.py
```

### 7. Auditoria

Consumir:

- `GET /audit-log`

Vista:

- Tabla de eventos.
- Filtros por accion, usuario, recurso.
- Badge por tipo de accion.

## Reglas UX Importantes

- Nunca mostrar "fraude confirmado" como conclusion de la IA.
- Usar textos como:
  - "alerta de revision";
  - "caso priorizado";
  - "requiere revision humana";
  - "posible inconsistencia".
- Las decisiones humanas si pueden decir `Confirmado para investigacion`, pero eso representa paso operativo, no culpabilidad.
- Mostrar disclaimer etico en dashboard, expediente, agente, vision y prueba del jurado.

## Variables De Entorno

Local `.env`:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4-mini
FRAUDIA_DB_BACKEND=sqlite
FRAUDIA_DB_PATH=data/processed/fraudia_claims.db
FRAUDIA_DATABASE_URL=
FRAUDIA_DATA_SOURCE=demo
FRAUDIA_COMPANY_DATA_DIR=data/company_synthetic
```

Para PostgreSQL:

```env
FRAUDIA_DB_BACKEND=postgres
FRAUDIA_DATABASE_URL=postgresql+psycopg://usuario:password@host:5432/fraudia
```

No subir `.env`.

## Pruebas Antes De Trabajar

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m compileall -q src scripts tests
```

Levantar API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn fraudia_claims.api:app --app-dir src --reload
```

Probar Swagger:

```text
http://127.0.0.1:8000/docs
```

## Estado De Git Al Crear Este Contexto

Rama:

```text
feature/dashboard-visual-polish
```

Cambios locales no relacionados que no deben mezclarse automaticamente:

```text
data/processed/fraudia_claims.db
data/synthetic/metricas_modelo.csv
docs/contexto_colaborador.md
```

Si se trabaja frontend, evitar tocar esos archivos salvo que se decida regenerar datos.

## Proximos Pasos Recomendados Para Antigravity

1. Crear carpeta de frontend separado, por ejemplo:

```text
frontend/
```

2. Elegir stack:

```text
React + Vite + TypeScript + Tailwind
```

3. Crear cliente API central:

```text
frontend/src/lib/api.ts
```

4. Crear layout:

- sidebar;
- topbar con usuario/rol;
- rutas;
- proteccion por token.

5. Implementar pantallas en este orden:

- Login.
- Centro de mando.
- Bandeja.
- Expediente.
- Prueba del jurado.
- Auditoria.
- Agente.
- Vision cuando exista endpoint dedicado.

6. Mantener el frontend React como interfaz principal de demo.

## Frase Guia Del Producto

FraudIA Claims no reemplaza al analista: le entrega una bandeja priorizada, explicaciones trazables, evidencia documental, red de relaciones, agente consultable y auditoria para revisar mejor y mas rapido los casos que merecen atencion.
