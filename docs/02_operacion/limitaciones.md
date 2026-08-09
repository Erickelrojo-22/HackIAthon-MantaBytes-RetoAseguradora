# Limitaciones, seguridad y etica

## Limitaciones

- Los datos son sinteticos; las metricas no prueban desempeno real antifraude.
- La etiqueta simulada sirve para demo y pruebas, no para afirmar verdad legal.
- El score depende de pesos definidos para el reto y requiere calibracion con expertos antes de produccion.
- Las metricas supervisadas se calculan con datos sinteticos y no prueban desempeno real en cartera productiva.
- **Fuga de etiqueta conocida**: en el generador sintetico, `etiqueta_fraude_simulada` determina tambien el monto, la demora de reporte y otras variables que el modelo supervisado usa como features. Eso produce metricas artificialmente altas (en algunos datasets, AUC/precision/recall cercanos a 1.0). Interpretar esas metricas como prueba de integracion del pipeline, no como evidencia de deteccion real.
- El dataset `company_synthetic` recibido por el equipo tiene columnas con un unico valor (`dinamica_imposible`, `lista_restrictiva`, etc.) que dejan inactivas varias reglas de negocio; no se usa en el despliegue publico hasta curarlo.
- La similitud textual detecta patrones de narrativa, pero no sustituye revision documental real.
- La red de relaciones evidencia concentraciones, no culpabilidad.

## Seguridad

- No se versionan credenciales reales (`.env` ignorado por Git).
- Los identificadores son anonimos.
- La integracion OpenAI es opcional y de solo lectura.
- Solo `/auth/login` y `/health` son publicos; el resto exige Bearer demo.
- CORS se restringe con `FRAUDIA_CORS_ORIGINS` (localhost por defecto; Render apunta al frontend).
- Upload CSV limita tamano (`FRAUDIA_MAX_CSV_BYTES`) y hay rate limit basico en agent/vision/upload/score.
- Auth sigue siendo demo (password/tokens estaticos): apta para jurado, no para produccion.
- `data/company_synthetic/` esta en `.gitignore`; no re-versionar datasets no autorizados.

## Principio etico

El sistema debe decir siempre: "posible fraude" o "requiere revision". Nunca debe acusar a un cliente ni automatizar una negativa.
