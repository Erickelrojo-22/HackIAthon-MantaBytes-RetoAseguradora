# Pitch FraudIA Claims

## 1 min - Problema

Las aseguradoras revisan siniestros con reglas dispersas, experiencia manual y cruces lentos. Muchas senales aparecen solo al combinar fechas, montos, proveedores, documentos, narrativas y relaciones.

## 1 min - Solucion

FraudIA Claims prioriza casos para revision humana con un score explicable. Combina reglas, anomalias, NLP y un agente consultable. No acusa fraude ni decide pagos.

## 4 min - Demo

1. Abrir resumen y mostrar distribucion de alertas.
2. Filtrar bandeja por casos rojos.
3. Explicar un siniestro rojo: reglas, evidencia, documentos y similitud narrativa.
4. Mostrar red de relaciones entre siniestros, asegurados y proveedores.
5. Preguntar al agente: "Que proveedores concentran mas alertas rojas?"
6. Evaluar un caso nuevo ocurrido 24 horas despues de la poliza.

## 2 min - Arquitectura e IA

Dataset sintetico relacional, SQLite, motor de reglas, IsolationForest por ramo, TF-IDF para narrativas y agente offline/OpenAI opcional con herramientas locales.

## 1 min - Impacto

Reduce tiempo de priorizacion, enfoca al analista en casos de mayor riesgo y deja evidencia trazable para auditoria.

## 1 min - Limitaciones

Datos sinteticos, calibracion pendiente con expertos y decision siempre humana. El score es una alerta, no una conclusion legal.
