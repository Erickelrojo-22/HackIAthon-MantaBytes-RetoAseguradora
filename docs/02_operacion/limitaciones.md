# Limitaciones, seguridad y etica

## Limitaciones

- Los datos son sinteticos; las metricas no prueban desempeno real antifraude.
- La etiqueta simulada sirve para demo y pruebas, no para afirmar verdad legal.
- El score depende de pesos definidos para el reto y requiere calibracion con expertos antes de produccion.
- Las metricas supervisadas se calculan con datos sinteticos y no prueban desempeno real en cartera productiva.
- La similitud textual detecta patrones de narrativa, pero no sustituye revision documental real.
- La red de relaciones evidencia concentraciones, no culpabilidad.

## Seguridad

- No se versionan credenciales.
- `.env` queda ignorado por Git.
- Los identificadores son anonimos.
- La integracion OpenAI es opcional y de solo lectura.

## Principio etico

El sistema debe decir siempre: "posible fraude" o "requiere revision". Nunca debe acusar a un cliente ni automatizar una negativa.
