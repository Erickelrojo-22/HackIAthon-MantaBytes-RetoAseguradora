# FraudIA Claims

Prototipo funcional para el reto **Detector de Posibles Fraudes en Siniestros usando Inteligencia Artificial**. La solucion prioriza siniestros de `Vehiculos`, `Salud` y `Hogar` mediante reglas explicables, deteccion de anomalias, similitud narrativa y un agente consultable.

Importante: FraudIA genera **alertas de revision humana**. No acusa fraude, no rechaza reclamos y no decide pagos.

## Funcionalidades

- Dataset sintetico reproducible con 3.000 siniestros y tablas relacionales.
- Base SQLite y CSV para inspeccion del jurado.
- Score trazable: reglas + anomalias + NLP.
- Semaforo: Verde `0-40`, Amarillo `41-75`, Rojo `76-100`.
- Dashboard Streamlit con bandeja, detalle, red de relaciones y formulario de caso nuevo.
- Agente offline con preguntas frecuentes del reto.
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

## Ejecutar app

```powershell
.\.venv\Scripts\python -m streamlit run src\fraudia_claims\app\main.py
```

## Modo OpenAI opcional

Copia `.env.example` a `.env` o exporta variables de entorno:

```powershell
$env:OPENAI_API_KEY="tu_api_key"
$env:OPENAI_MODEL="modelo_configurado_por_el_equipo"
```

Si las variables no existen, la app funciona en modo offline. El LLM no modifica scores persistidos; solo redacta respuestas usando herramientas locales.

## Pruebas

```powershell
.\.venv\Scripts\python -m unittest discover -s tests
```

## Demo sugerida

1. Mostrar resumen y explicar que los resultados son alertas, no acusaciones.
2. Abrir la bandeja y filtrar casos rojos.
3. Entrar al detalle de un caso rojo y revisar reglas, documentos y similitud narrativa.
4. Abrir la red de relaciones para evidenciar proveedores o asegurados recurrentes.
5. Preguntar al agente: "Que proveedores concentran mas alertas rojas?"
6. Evaluar un caso nuevo ocurrido 24 horas despues de iniciar la poliza.

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
