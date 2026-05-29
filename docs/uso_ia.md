# Explicacion del modelo de IA

FraudIA Claims usa IA como apoyo a la priorizacion de revision humana. La IA no acusa fraude, no rechaza reclamos y no decide pagos.

## Enfoque hibrido

El score se construye con cuatro fuentes:

1. **Reglas explicables**: senales del reto y criterios de negocio.
2. **Anomalias numericas**: deteccion de montos y comportamientos atipicos por ramo.
3. **NLP**: similitud de narrativas para detectar textos clonados o muy parecidos.
4. **Modelo supervisado demo**: clasificador entrenado con etiqueta sintetica solo para evidencia tecnica.

Formula operativa:

```text
score_final = min(100, min(puntos_reglas, 60) + puntos_anomalia + puntos_nlp + puntos_modelo)
```

Las reglas criticas pueden elevar el caso a rojo aunque la suma base sea menor. Las reglas amarillas obligatorias pueden elevar el caso a amarillo.

## Variables usadas

- Fechas de poliza y ocurrencia del siniestro.
- Dias de demora en reporte.
- Ramo, cobertura, ciudad y monto reclamado.
- Suma asegurada y relacion monto/suma.
- Frecuencia del asegurado, vehiculo, conductor o proveedor.
- Estado documental: entregado, legible, inconsistencia y adulteracion.
- Narrativa del siniestro.
- Proveedor, beneficiario y relaciones operativas.

## Modelos locales

- **IsolationForest por ramo**: asigna puntos cuando un siniestro cae en percentiles altos de anomalia. Si la libreria no esta disponible, se usa fallback robusto por percentiles.
- **TF-IDF por ramo**: calcula similitud maxima entre narrativas del mismo ramo. Textos muy similares generan alerta NLP y trazan el siniestro parecido.
- **RandomForestClassifier demo**: aprende sobre `etiqueta_fraude_simulada` del dataset sintetico. Sus metricas se reportan como evaluacion sintetica, no como eficacia real.

## Agente IA

El agente tiene dos modos:

- **Offline**: router local de intenciones para responder preguntas frecuentes del jurado.
- **OpenAI opcional**: usa herramientas locales de solo lectura y redacta respuestas en lenguaje natural.

Herramientas permitidas:

- Consultar detalle de siniestro.
- Listar casos de mayor riesgo.
- Agrupar alertas por proveedor, ramo o ciudad.
- Consultar red de relaciones.
- Calcular score temporal de un caso nuevo.
- Consultar metricas y resumen ejecutivo.

El LLM no tiene herramientas para modificar scores, insertar decisiones o alterar la base.

## Vision opcional

El modulo Vision analiza imagenes de siniestros cuando existe `OPENAI_API_KEY`. El resultado se muestra como hallazgos visuales auxiliares: observaciones, posibles inconsistencias, severidad, confianza y accion sugerida.

Restricciones:

- No persiste imagenes.
- No modifica `scores`.
- No reemplaza peritaje humano.
- Si OpenAI falla o no hay credenciales, devuelve modo offline sin romper la demo.

## Metricas y trazabilidad

El sistema reporta metricas del modelo supervisado cuando hay etiqueta sintetica: precision, recall, F1, AUC y matriz de confusion. Si el dataset empresarial sintetico no trae etiqueta supervisada, el estado de metricas puede quedar como `skipped`.

Cada alerta conserva:

- Codigo.
- Descripcion.
- Evidencia.
- Puntos asignados.
- Siniestro relacionado cuando aplica.

## Limitaciones

- No se debe interpretar el score como probabilidad legal de fraude.
- Los resultados son demostrativos porque los datos son sinteticos.
- Antes de produccion se requiere validacion con expertos, calibracion por ramo, pruebas con datos historicos autorizados y monitoreo de falsos positivos.
