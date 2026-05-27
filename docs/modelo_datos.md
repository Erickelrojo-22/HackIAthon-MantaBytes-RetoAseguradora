# Modelo de datos

## Tablas principales

- `asegurados`: identificadores anonimos, segmento, ciudad, mora y score simulado.
- `polizas`: vigencia, prima, suma asegurada, deducible, canal y ciudad.
- `proveedores`: talleres, clinicas o contratistas; incluye lista restrictiva simulada y concentracion de reclamos.
- `vehiculos`: placa, chasis, motor, marca, modelo y anio para polizas vehiculares.
- `siniestros`: fechas, cobertura, montos, estado, descripcion, proveedor, flags de demo y etiqueta simulada.
- `documentos`: metadatos de entrega, legibilidad, inconsistencias y adulteracion simulada.
- `scores`: score final y desglose por reglas, anomalias y NLP.
- `alertas`: regla, categoria, severidad, puntos, evidencia y criticidad.
- `metricas_modelo`: metricas reproducibles del modelo supervisado demo.

## Privacidad

Todos los identificadores son ficticios. No se usan datos personales reales ni informacion confidencial de aseguradoras.
La etiqueta de fraude es sintetica y se usa solo para demo, entrenamiento y metricas.

## Contexto publico

`contexto_publico.csv` referencia el portal publico de la SCVS para indicadores agregados. Ese contexto no alimenta el score ni etiqueta casos.
