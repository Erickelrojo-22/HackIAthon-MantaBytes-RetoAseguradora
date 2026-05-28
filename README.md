# FraudIA Claims

Prototipo funcional para el reto **Detector de Posibles Fraudes en Siniestros usando Inteligencia Artificial**. La solucion prioriza siniestros de `Vehiculos`, `Salud` y `Hogar` mediante reglas explicables, deteccion de anomalias, similitud narrativa y un agente consultable.

Importante: FraudIA genera **alertas de revision humana**. No acusa fraude, no rechaza reclamos y no decide pagos.

## Funcionalidades

- Dataset sintetico reproducible con 3.000 siniestros y tablas relacionales.
- Base PostgreSQL para despliegue y SQLite/CSV como fallback local para inspeccion del jurado.
- Score trazable: reglas + anomalias + NLP.
- Modelo supervisado demo con etiqueta sintetica y metricas reproducibles.
- Semaforo: Verde `0-40`, Amarillo `41-75`, Rojo `76-100`.
- Dashboard Streamlit con demo guiada, resumen ejecutivo, bandeja, detalle, red de relaciones, caso nuevo y reporte descargable.
- Agente offline con preguntas frecuentes del reto y explicacion del ultimo caso evaluado en vivo.
- Analisis opcional de imagenes con OpenAI Vision en sesion, sin modificar scores.
- API minima FastAPI para integracion futura.
- Integracion OpenAI opcional con herramientas locales de solo lectura.

## Instalacion

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

Si no deseas crear entorno virtual, instala las dependencias en tu entorno preferido y ejecuta los comandos desde la raiz del repositorio.

## Generar datos

```powershell
.\.venv\Scripts\python scripts\generate_demo_data.py --force
```

Esto crea:

- `data/raw/contexto_publico.csv`
- `data/synthetic/*.csv`
- `data/processed/fraudia_claims.db`

Por defecto el proyecto usa SQLite local para que la demo arranque en cualquier maquina. Para usar PostgreSQL:

```powershell
$env:FRAUDIA_DB_BACKEND="postgres"
$env:FRAUDIA_DATABASE_URL="postgresql+psycopg://usuario:password@localhost:5432/fraudia"
.\.venv\Scripts\python scripts\generate_demo_data.py --force
```

En despliegue cloud se configuran esas variables como secretos. No subas credenciales al repositorio.

## Dataset empresarial sintetico

Si el equipo recibe datos sinteticos de la empresa, cargarlos fuera del repo en `data/company_synthetic` con:

```text
asegurados.csv
polizas.csv
proveedores.csv
vehiculos.csv
siniestros.csv
documentos.csv
README_DATOS.md
```

Luego activar:

```powershell
$env:FRAUDIA_DATA_SOURCE="company_synthetic"
$env:FRAUDIA_COMPANY_DATA_DIR="data/company_synthetic"
.\.venv\Scripts\python scripts\generate_demo_data.py --force
```

El loader valida columnas antes de cargar. No se debe versionar ese dataset hasta confirmar autorizacion y naturaleza 100% sintetica.

## Ejecutar app

```powershell
.\.venv\Scripts\python -m streamlit run src\fraudia_claims\app\main.py
```

## Ejecutar API

```powershell
.\.venv\Scripts\python -m uvicorn fraudia_claims.api:app --app-dir src --reload
```

Endpoints principales:

- `GET /health`
- `GET /claims/risk?limit=10&level=Rojo`
- `GET /claims/{id_siniestro}`
- `GET /alerts/aggregate?group_by=proveedor`
- `GET /alerts/provider-pareto`
- `GET /relationships?limit=60`
- `GET /report/summary`
- `GET /metrics`
- `POST /score-candidate`

## Ejecutar en VS Code

1. Abre esta carpeta en VS Code.
2. Acepta el interprete recomendado: `.venv\Scripts\python.exe`.
3. Ve a `Terminal > Run Task...`.
4. Ejecuta `FraudIA: Run Streamlit app`.
5. Abre `http://127.0.0.1:8501` en el navegador.

Tareas disponibles:

- `FraudIA: Run Streamlit app`
- `FraudIA: Generate demo data`
- `FraudIA: Run tests`
- `FraudIA: Compile check`

Tambien puedes usar `Run and Debug > FraudIA: Streamlit` para levantar la app desde el depurador.

## Modo OpenAI opcional

Copia `.env.example` a `.env` y agrega la API key localmente:

```powershell
Copy-Item .env.example .env
notepad .env
```

El modelo recomendado para la demo queda preconfigurado como `gpt-5.4-mini`. Cada integrante debe poner su propia `OPENAI_API_KEY` en su archivo `.env` local, o usar variables de entorno del despliegue. No subas `.env` ni credenciales reales al repositorio.

Si las variables no existen, la app funciona en modo offline. El LLM no modifica scores persistidos; solo redacta respuestas usando herramientas locales.

Para que jurados o invitados prueben la IA sin configurar nada, despliega el proyecto y guarda `OPENAI_API_KEY` como secreto del servidor. En Render, `render.yaml` ya deja `OPENAI_MODEL=gpt-5.4-mini` y SQLite demo preconfigurados; solo falta agregar el secreto `OPENAI_API_KEY` en el panel de Environment. En Streamlit Cloud, copia `.streamlit/secrets.example.toml` en la seccion Secrets y reemplaza el placeholder por la key real.

## Pruebas

```powershell
.\.venv\Scripts\python -m unittest discover -s tests
```

Prueba automatizada completa en Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_project_tests.ps1
```

El script crea/usa `.venv`, instala dependencias, valida datos, ejecuta tests y verifica API + Streamlit.

## Demo sugerida

1. Abrir `Demo guiada` para seguir el flujo del pitch.
2. Mostrar `Resumen` y explicar que los resultados son alertas, no acusaciones.
3. Abrir la `Bandeja de revision` y filtrar casos rojos.
4. Entrar al `Detalle del siniestro` destacado y revisar reglas, documentos y similitud narrativa.
5. Abrir `Red de relaciones` para evidenciar proveedores o asegurados recurrentes.
6. En `Agente IA`, preguntar: "Que proveedores concentran el 80% de las alertas rojas?"
7. Evaluar un caso nuevo con el preset de 24 horas despues de iniciar la poliza.
8. Preguntar al agente: "Explica el ultimo caso evaluado en vivo."
9. Descargar el `Reporte ejecutivo` y mostrar el disclaimer etico.

Preguntas del jurado cubiertas por el agente:

- "Cuales son los 10 siniestros con mayor riesgo?"
- "Por que el siniestro SINxxxxx fue marcado como alto riesgo?"
- "Que proveedores concentran mas alertas rojas?"
- "Que ramos tienen mayor porcentaje de casos sospechosos?"
- "Que ciudades presentan mayor concentracion de alertas?"
- "Que asegurados tienen mayor frecuencia de reclamos?"
- "Que documentos faltan en los casos criticos?"
- "Que casos tienen montos atipicos?"
- "Que siniestros ocurrieron cerca del inicio de la poliza?"
- "Que patrones se repiten en los reclamos sospechosos?"
- "Genera un resumen ejecutivo de los casos criticos."
- "Recomienda que casos deberia revisar primero el analista."

## Estructura

```text
data/
docs/
presentation/
scripts/
src/fraudia_claims/
tests/
```

La documentacion tecnica vive en `docs/` y el guion del pitch en `presentation/pitch.md`.

Documentos utiles:

- `docs/arquitectura.md`
- `docs/modelo_datos.md`
- `docs/reglas_negocio.md`
- `docs/uso_ia.md`
- `docs/despliegue.md`
- `docs/api_frontend.md`
