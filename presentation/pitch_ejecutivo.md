# Presentacion ejecutiva - FraudIA Claims

## 1. Problema y oportunidad

Las aseguradoras revisan miles de siniestros con informacion dispersa: fechas, polizas, proveedores, documentos, montos y narrativas. Muchas senales de posible fraude aparecen solo al cruzar variables y relaciones.

## 2. Solucion

FraudIA Claims prioriza siniestros para revision humana con un score explicable. Combina reglas del negocio, deteccion de anomalias, similitud narrativa y un agente consultable en lenguaje natural.

Principio clave: el sistema no acusa fraude, no rechaza reclamos y no decide pagos.

## 3. Demo en vivo

1. Abrir `Demo guiada` para presentar el flujo.
2. Mostrar `Resumen` con KPIs, semaforo y concentracion operativa.
3. Filtrar la `Bandeja de revision` por casos rojos.
4. Explicar un caso rojo en `Detalle del siniestro`.
5. Mostrar `Red de relaciones` para proveedores y asegurados recurrentes.
6. Preguntar al agente: "Que proveedores concentran el 80% de las alertas rojas?"
7. Evaluar un caso nuevo ocurrido 24 horas despues del inicio de poliza.
8. Descargar `Reporte ejecutivo`.

## 4. Arquitectura e IA

El prototipo usa Python, Streamlit, SQLite/CSV, scikit-learn, TF-IDF, NetworkX/Plotly, FastAPI y OpenAI opcional. El LLM solo redacta respuestas usando herramientas locales; el score se calcula fuera del modelo generativo.

## 5. Impacto operativo

La solucion reduce tiempo de priorizacion, concentra la revision en casos de mayor riesgo, deja evidencia trazable y habilita preguntas ejecutivas para analistas, gerencia y auditoria.

## 6. Limitaciones y evolucion

Los datos son sinteticos, las metricas no prueban desempeno productivo y el modelo requiere calibracion con expertos antes de uso real. La siguiente evolucion seria conectar fuentes internas anonimizadas, validacion experta y monitoreo de sesgo/falsos positivos.
