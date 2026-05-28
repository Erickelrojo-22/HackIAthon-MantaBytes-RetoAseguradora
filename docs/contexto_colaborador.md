# Contexto para colaborar en FraudIA Claims

Este documento resume el estado actual del proyecto para que otro integrante del equipo pueda incorporarse rapido y trabajar sin romper la demo.

## 1. Objetivo del proyecto

FraudIA Claims es un prototipo para el reto **Detector de Posibles Fraudes en Siniestros usando Inteligencia Artificial** de Aseguradora del Sur.

El sistema **no acusa fraude, no rechaza reclamos y no decide pagos**. Su objetivo es generar alertas explicables para que un analista humano priorice la revision de siniestros.

Ramos cubiertos en la demo:

- Vehiculos
- Salud
- Hogar

## 2. Estado actual

La demo ya tiene:

- Dataset sintetico reproducible con 3.000 siniestros.
- CSVs en `data/synthetic/`.
- Base SQLite en `data/processed/fraudia_claims.db`.
- Dashboard Streamlit con:
  - Demo guiada
  - Resumen ejecutivo
  - Bandeja de revision
  - Detalle del siniestro
  - Evaluar caso nuevo
  - Red de relaciones
  - Agente IA
  - Reporte ejecutivo
  - Metodologia y limitaciones
- Logo del equipo Manta Bytes integrado en el dashboard.
- Agente offline funcional sin internet.
- OpenAI opcional con fallback offline.
- API FastAPI para integracion futura.
- Tests automatizados.

Rama principal de trabajo actual:

```text
feature/dashboard-visual-polish
```

PR actual:

```text
https://github.com/Erickelrojo-22/HackIAthon-MantaBytes-RetoAseguradora/pull/2
```

## 3. Como correr el proyecto

Desde la raiz del repo:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Ejecutar Streamlit:

```powershell
.\.venv\Scripts\python.exe -m streamlit run src\fraudia_claims\app\main.py
```

Abrir en navegador:

```text
http://localhost:8501
```

Ejecutar API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn fraudia_claims.api:app --app-dir src --reload
```

Ejecutar pruebas:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m compileall -q src scripts tests
```

Script completo Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_project_tests.ps1
```

## 4. Como se inicializa la base de datos

La base se inicializa automaticamente con:

```python
initialize_demo_data(force=False)
```

Ese flujo esta en `src/fraudia_claims/storage.py`.

Si `data/processed/fraudia_claims.db` existe y tiene las tablas/columnas requeridas, se reutiliza.

Si no existe, esta incompleta o se llama con `force=True`, se regenera todo:

1. `synthetic_data.py` crea datos sinteticos.
2. `scoring.py` calcula reglas, anomalias, NLP y modelo supervisado demo.
3. Se guardan CSVs y SQLite.
4. La app, API y agente leen desde SQLite.

Importante: los casos nuevos evaluados en vivo **no se guardan en SQLite**; viven solo en `st.session_state`.

## 5. Arquitectura del sistema

Modulos principales:

- `synthetic_data.py`: genera datos sinteticos.
- `features.py`: arma variables de riesgo.
- `rules.py`: aplica reglas explicables del reto.
- `models.py`: IsolationForest y modelo supervisado demo.
- `nlp.py`: similitud narrativa TF-IDF.
- `scoring.py`: combina puntos y semaforo.
- `storage.py`: CSV, SQLite e inicializacion.
- `agent_tools.py`: consultas seguras y scoring temporal.
- `offline_agent.py`: agente sin internet.
- `openai_agent.py`: OpenAI opcional con fallback.
- `analytics.py`: KPIs y analitica ejecutiva.
- `reports.py`: reporte HTML descargable.
- `network.py`: grafo de relaciones.
- `api.py`: endpoints FastAPI.
- `app/main.py`: orquestador Streamlit.
- `app/pages.py`: paginas de la interfaz.
- `app/components.py`: componentes visuales reutilizables.

## 6. Scoring y reglas

Semaforo:

- `0-40`: Verde
- `41-75`: Amarillo
- `76-100`: Rojo

Formula actual:

```text
score_final = min(100, min(puntos_reglas, 60) + puntos_anomalia + puntos_nlp + puntos_modelo)
```

Reglas criticas que elevan minimo a rojo:

- `RF-01`: perdida total por robo.
- `RF-02`: adulteracion documental.
- `RF-03`: lista restrictiva.
- `RF-04`: dinamica fisicamente imposible.

Reglas que elevan minimo a amarillo:

- `RF-05`: siniestro extremo al borde de vigencia.
- `RF-06`: denuncia de robo mayor a 4 dias.
- `RF-07`: narrativa identica o clonada.

## 7. Agente IA

El agente puede responder preguntas del jurado como:

- Cuales son los 10 siniestros con mayor riesgo?
- Por que este siniestro fue marcado como alto riesgo?
- Que proveedores concentran mas alertas rojas?
- Que proveedores concentran el 80% de las alertas rojas?
- Que ramos tienen mayor porcentaje de casos sospechosos?
- Que ciudades presentan mayor concentracion de alertas?
- Que documentos faltan en los casos criticos?
- Que casos tienen montos atipicos?
- Que siniestros ocurrieron cerca del inicio de la poliza?
- Que patrones se repiten en reclamos sospechosos?
- Genera un resumen ejecutivo.
- Explica el ultimo caso evaluado en vivo.

El modo offline esta en `offline_agent.py`.

OpenAI es opcional. Si no hay `OPENAI_API_KEY` y `OPENAI_MODEL`, la demo sigue funcionando offline.

## 8. Flujo recomendado de demo

1. Abrir `Demo guiada`.
2. Ir a `Resumen` y mostrar KPIs, logo Manta Bytes y graficos.
3. Abrir `Bandeja de revision` y filtrar por rojo.
4. Entrar a `Detalle del siniestro` y explicar reglas/documentos/narrativa.
5. Abrir `Red de relaciones` para ver proveedores recurrentes.
6. En `Agente IA`, preguntar: `Que proveedores concentran el 80% de las alertas rojas?`
7. Ir a `Evaluar caso nuevo`, usar el preset de 24 horas despues de inicio de poliza.
8. Preguntar al agente: `Explica el ultimo caso evaluado en vivo.`
9. Descargar `Reporte ejecutivo`.

## 9. Buenas practicas para contribuir

Antes de trabajar:

```powershell
git fetch origin
git switch feature/dashboard-visual-polish
git pull
```

Crear cambios pequenos y probar:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m compileall -q src scripts tests
```

No hacer:

- No usar datos reales de personas.
- No subir `.env` ni llaves API.
- No cambiar el principio etico del sistema.
- No hacer que el sistema acuse fraude o recomiende rechazo automatico.
- No regenerar datos sin revisar el diff de `data/synthetic/` y `data/processed/`.

## 10. Areas recomendadas para que un compañero ayude

Opciones de mejora de bajo riesgo:

- Pulir textos visuales del dashboard para captura en redes.
- Mejorar el reporte ejecutivo HTML.
- Agregar mas preguntas sugeridas al agente.
- Revisar ortografia y consistencia de docs.
- Crear una presentacion PPTX/PDF a partir de `presentation/pitch_ejecutivo.md`.
- Mejorar el README con capturas.
- Agregar tests para paginas especificas de Streamlit.

Opciones de mejora de riesgo medio:

- Ajustar pesos de scoring.
- Modificar generacion de datos sinteticos.
- Cambiar reglas de negocio.
- Cambiar estructura de tablas.

Si se toca scoring o datos, siempre correr la suite completa y revisar que la demo siga teniendo casos verdes, amarillos y rojos.

## 11. Archivos clave para leer primero

- `README.md`
- `docs/arquitectura.md`
- `docs/modelo_datos.md`
- `docs/reglas_negocio.md`
- `docs/uso_ia.md`
- `presentation/pitch_ejecutivo.md`
- `src/fraudia_claims/app/main.py`
- `src/fraudia_claims/app/pages.py`
- `src/fraudia_claims/agent_tools.py`
- `src/fraudia_claims/storage.py`

## 12. Mensaje clave para el jurado

FraudIA Claims no reemplaza al analista. Le da una bandeja priorizada, explicaciones trazables, red de relaciones, agente consultable y reporte ejecutivo para revisar mejor y mas rapido los siniestros que merecen atencion.
