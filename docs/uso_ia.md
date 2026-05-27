# Uso de IA

FraudIA usa un enfoque hibrido:

1. Reglas explicables para senales del reto.
2. Modelo de anomalias numericas por ramo.
3. Similitud narrativa con TF-IDF.
4. Agente conversacional para consultar resultados.

## Agente offline

El modo offline responde consultas frecuentes:

- Top 10 siniestros con mayor riesgo.
- Proveedores con mayor concentracion de alertas.
- Ramos o ciudades con mayor exposicion.
- Documentos faltantes en casos criticos.
- Detalle explicable de un siniestro `SINxxxxx`.
- Ahorro potencial simulado.
- Ultimo caso evaluado en vivo.
- Resumen ejecutivo.

## OpenAI opcional

Si existen `OPENAI_API_KEY` y `OPENAI_MODEL`, el agente usa la Responses API con herramientas locales:

- `list_risk_cases`
- `get_claim_detail`
- `aggregate_alerts`
- `get_relationship_network`
- `score_candidate_claim`
- `get_impact_summary`

El modelo no escribe en la base ni modifica scores. Si la API falla, el sistema responde offline.
