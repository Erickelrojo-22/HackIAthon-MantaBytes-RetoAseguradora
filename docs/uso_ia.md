# Uso de IA

FraudIA usa un enfoque hibrido:

1. Reglas explicables para senales del reto.
2. Modelo de anomalias numericas por ramo.
3. Similitud narrativa con TF-IDF.
4. Modelo supervisado demo entrenado con etiqueta sintetica.
5. Agente conversacional para consultar resultados.

## Agente offline

El modo offline responde consultas frecuentes:

- Top 10 siniestros con mayor riesgo.
- Proveedores con mayor concentracion de alertas.
- Ramos o ciudades con mayor exposicion.
- Documentos faltantes en casos criticos.
- Detalle explicable de un siniestro `SINxxxxx`.
- Asegurados anonimos con mayor frecuencia de reclamos.
- Montos atipicos o cercanos a suma asegurada.
- Siniestros cerca del inicio o fin de poliza.
- Proveedores que concentran aproximadamente el 80% de alertas rojas.
- Metricas del modelo supervisado.
- Resumen ejecutivo.
- Explicacion del ultimo caso evaluado en vivo, usando datos temporales de sesion.

## OpenAI opcional

Si existen `OPENAI_API_KEY` y `OPENAI_MODEL`, el agente usa la Responses API con herramientas locales:

- `list_risk_cases`
- `get_claim_detail`
- `aggregate_alerts`
- `get_relationship_network`
- `score_candidate_claim`
- `get_model_metrics`
- `provider_red_alert_pareto`
- `top_insured_frequency`
- `list_amount_outliers`
- `list_policy_edge_cases`
- `repeated_claim_patterns`
- `executive_report`

El modelo no escribe en la base ni modifica scores. Si la API falla, el sistema responde offline.

Los casos evaluados en vivo no se entregan como herramienta persistente al LLM. Si el usuario pregunta por el ultimo caso temporal, la respuesta se resuelve localmente para evitar que el modelo invente o altere datos.

## Vision opcional

`vision.py` permite analizar fotos de siniestros con la Responses API cuando existen `OPENAI_API_KEY` y `OPENAI_MODEL`. La imagen se envia como `input_image` codificada en data URL, siguiendo el flujo de Vision de OpenAI.

En la version actual el frontend React consume la API y puede mantener resultados visuales de forma temporal en el cliente hasta que se agregue persistencia dedicada. No se persiste la imagen, no modifica `scores` y siempre se presenta como apoyo para revision humana, no como conclusion de fraude.
