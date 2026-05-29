# Presentacion ejecutiva - FraudIA Claims

## 1. Problema

Las aseguradoras reciben miles de siniestros con informacion dispersa: polizas, fechas, montos, proveedores, documentos, vehiculos, beneficiarios y narrativas. Revisar todo manualmente consume tiempo y puede ocultar patrones repetidos.

## 2. Solucion

FraudIA Claims es un agente explicable que prioriza siniestros para revision humana. Combina reglas de negocio, IA local, red de relaciones, agente conversacional y auditoria.

Principio central: FraudIA no acusa fraude, no rechaza reclamos y no decide pagos. Solo organiza senales para que un analista revise con evidencia.

## 3. Prototipo funcional

- Frontend React/Vite desplegado en Render.
- Backend FastAPI desplegado en Render.
- Base PostgreSQL/Supabase para dataset empresarial sintetico y SQLite/CSV como fallback local.
- Login demo por rol: Analista, Jefatura y Auditoria.
- Dashboard, bandeja, expediente, decisiones humanas, red, agente IA, Vision, carga CSV y reporte ejecutivo.

## 4. Como funciona

1. Los datos sinteticos se validan y cargan en SQLite o PostgreSQL.
2. El motor de reglas genera alertas con codigo, puntos y evidencia.
3. Los modelos IA locales calculan anomalias numericas, similitud narrativa y probabilidad supervisada demo.
4. El score final ubica cada caso en Verde, Amarillo o Rojo.
5. El agente responde preguntas usando herramientas locales de solo lectura.
6. El analista registra decisiones humanas sin modificar el score base.

## 5. Demo de 10 minutos

1. Login con `analista@fraudia.demo` / `demo123`.
2. Mostrar `Centro de Mando`: casos priorizados, rojos, monto expuesto y proveedores criticos.
3. Abrir `Bandeja` y filtrar por casos rojos.
4. Entrar a un expediente y explicar reglas, documentos, score e IA.
5. Registrar una decision humana como `Escalado`.
6. Abrir `Red de relaciones` para ver asegurados anonimos, siniestros y proveedores conectados.
7. Preguntar al agente: "Que proveedores concentran el 80% de las alertas rojas?"
8. Ejecutar `Prueba del Jurado` con un caso temporal ocurrido 24 horas despues del inicio de poliza.
9. Mostrar `Analisis visual` como apoyo al peritaje humano.
10. Descargar `Reporte ejecutivo` y cerrar con `Auditoria`.

## 6. Impacto operativo

- Reduce tiempo de priorizacion.
- Da trazabilidad al analista y a auditoria.
- Permite revisar concentraciones por proveedor, ciudad y ramo.
- Ayuda a explicar por que un caso debe revisarse primero.
- Mantiene control humano y evita decisiones automaticas.

## 7. Evidencia tecnica para el jurado

- Arquitectura: `docs/arquitectura.md`.
- Modelo de datos: `docs/modelo_datos.md`.
- Explicacion IA: `docs/uso_ia.md`.
- Rubrica de alertas: `docs/rubrica_alertas.md`.
- Matriz de cumplimiento: `docs/matriz_cumplimiento_pdf.md`.
- Checklist de entrega: `docs/checklist_entrega.md`.

## 8. Limitaciones y evolucion

Los datos son sinteticos y las metricas supervisadas son demostrativas. Para produccion se requiere validacion con expertos, calibracion con historicos autorizados, monitoreo de sesgo, seguridad productiva y gobierno de datos.

Proxima evolucion: persistencia de analisis visual, roles productivos, integracion con core asegurador, monitoreo 24/7 y mejora continua del modelo.
