# Matriz de cumplimiento del reto

Esta matriz resume como FraudIA Claims cubre los puntos principales del documento del reto. Sirve para que el equipo y el jurado puedan revisar trazabilidad entre requerimiento, implementacion y evidencia.

| Punto del PDF | Requerimiento | Implementacion en FraudIA | Evidencia |
| --- | --- | --- | --- |
| Datos minimos | Siniestros, polizas, asegurados, vehiculos, proveedores y documentos | Online: dataset empresarial sintetico en Supabase/PostgreSQL. Offline: SQLite reconstruido desde CSV versionados | `docs/datos_supabase.md`, `data/company_synthetic/`, `data/synthetic/`, `database.py` |
| Score de riesgo | Puntaje por siniestro y semaforo verde/amarillo/rojo | `score_final` 0-100 con nivel y accion sugerida | `scoring.py`, tabla `scores` |
| Reglas de negocio | Senales por vigencia, denuncia, frecuencia, documentos, proveedor, monto y dinamica | Motor de reglas con codigos RF/RS/RH, puntos y evidencia | `rules.py`, tabla `alertas` |
| Reglas criticas | Perdida total por robo, adulteracion, lista restrictiva, dinamica imposible | Escalamiento automatico minimo a rojo cuando aplica | `rules.py`, `agent_tools.score_candidate_claim` |
| IA / ML | Modelo de anomalias o clasificacion | IsolationForest por ramo y RandomForest supervisado con etiqueta sintetica | `models.py`, tabla `metricas_modelo` |
| NLP | Analisis de descripcion y narrativas similares | TF-IDF por ramo y similitud narrativa trazada | `nlp.py`, columnas `similitud_narrativa`, `siniestro_similar` |
| Agente IA | Consultas en lenguaje natural | Agente offline y OpenAI opcional con herramientas locales | `offline_agent.py`, `openai_agent.py` |
| Dashboard | Interfaz funcional para analista | Frontend React con centro de mando, bandeja, expediente, agente, auditoria, red, reporte, carga CSV, Vision y prueba del jurado | `frontend/`, `api.py` |
| Red de relaciones | Asegurados, proveedores y casos conectados | Pagina React y endpoint de relaciones para frontend/agente | `GET /relationships`, `frontend/src/pages/Relationships.tsx` |
| Reporte ejecutivo | Resumen para auditoria o gerencia | Pagina React con descarga HTML, KPIs, top casos, proveedores y metricas | `GET /report/summary`, `frontend/src/pages/ExecutiveReport.tsx` |
| Vision | Analisis auxiliar de fotos de siniestros | Endpoint y pagina React para hallazgos visuales sin modificar scores | `POST /vision/analyze`, `vision.py` |
| Carga de datos | Carga/validacion de estructura | Endpoint y pagina React para validar CSV sin reemplazar tablas persistidas | `POST /claims/upload-csv`, `ingestion.py` |
| API futura | Integracion con otros sistemas | API minima FastAPI | `api.py` |
| Seguridad y etica | No acusar, no rechazar, no usar datos reales | Datos sinteticos, disclaimers y revision humana obligatoria | `docs/limitaciones.md`, README, dashboard |
| Reproducibilidad | Codigo ejecutable y pruebas | Script automatizado de pruebas y smoke test | `scripts/run_project_tests.ps1`, `tests/` |

## Mensaje clave para el jurado

FraudIA Claims no decide pagos ni acusa fraude. Prioriza casos para revision humana combinando reglas explicables, modelos de IA, NLP, red de relaciones y evidencia auditable.
