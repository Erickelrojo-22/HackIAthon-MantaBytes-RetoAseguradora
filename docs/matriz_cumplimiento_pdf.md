# Matriz de cumplimiento del reto

Esta matriz resume como FraudIA Claims cubre los puntos principales del documento del reto. Sirve para que el equipo y el jurado puedan revisar trazabilidad entre requerimiento, implementacion y evidencia.

| Punto del PDF | Requerimiento | Implementacion en FraudIA | Evidencia |
| --- | --- | --- | --- |
| Datos minimos | Siniestros, polizas, asegurados, vehiculos, proveedores y documentos | Dataset sintetico reproducible y base SQLite/CSV | `data/synthetic/`, `data/processed/fraudia_claims.db`, `synthetic_data.py` |
| Score de riesgo | Puntaje por siniestro y semaforo verde/amarillo/rojo | `score_final` 0-100 con nivel y accion sugerida | `scoring.py`, tabla `scores` |
| Reglas de negocio | Senales por vigencia, denuncia, frecuencia, documentos, proveedor, monto y dinamica | Motor de reglas con codigos RF/RS/RH, puntos y evidencia | `rules.py`, tabla `alertas` |
| Reglas criticas | Perdida total por robo, adulteracion, lista restrictiva, dinamica imposible | Escalamiento automatico minimo a rojo cuando aplica | `rules.py`, `agent_tools.score_candidate_claim` |
| IA / ML | Modelo de anomalias o clasificacion | IsolationForest por ramo y RandomForest supervisado con etiqueta sintetica | `models.py`, tabla `metricas_modelo` |
| NLP | Analisis de descripcion y narrativas similares | TF-IDF por ramo y similitud narrativa trazada | `nlp.py`, columnas `similitud_narrativa`, `siniestro_similar` |
| Agente IA | Consultas en lenguaje natural | Agente offline y OpenAI opcional con herramientas locales | `offline_agent.py`, `openai_agent.py` |
| Dashboard | Interfaz funcional para analista | Streamlit con resumen, bandeja, detalle, red, agente y reporte | `app/main.py`, `app/pages.py` |
| Red de relaciones | Asegurados, proveedores y casos conectados | Grafo NetworkX/Plotly sobre casos de mayor riesgo | `network.py` |
| Reporte ejecutivo | Resumen para auditoria o gerencia | Reporte HTML con KPIs, top casos, proveedores, ciudades y documentos | `reports.py` |
| API futura | Integracion con otros sistemas | API minima FastAPI | `api.py` |
| Seguridad y etica | No acusar, no rechazar, no usar datos reales | Datos sinteticos, disclaimers y revision humana obligatoria | `docs/limitaciones.md`, README, dashboard |
| Reproducibilidad | Codigo ejecutable y pruebas | Script automatizado de pruebas y smoke test | `scripts/run_project_tests.ps1`, `tests/` |

## Mensaje clave para el jurado

FraudIA Claims no decide pagos ni acusa fraude. Prioriza casos para revision humana combinando reglas explicables, modelos de IA, NLP, red de relaciones y evidencia auditable.
