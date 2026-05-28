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

## Persistencia

La misma estructura se carga mediante `database.py` en SQLite local o PostgreSQL. Las tablas actuales son:

- `contexto_publico`
- `asegurados`
- `polizas`
- `proveedores`
- `vehiculos`
- `siniestros`
- `documentos`
- `scores`
- `alertas`
- `metricas_modelo`

Para un dataset empresarial sintetico, el paquete esperado vive fuera del repo en `data/company_synthetic` y pasa por `ingestion.py`, que valida columnas minimas antes de cargar.
La etiqueta de fraude es sintetica y se usa solo para demo, entrenamiento y metricas.

## Alineacion con la guia del reto

- Beneficiarios: se representan en `siniestros.beneficiario` y se relacionan con `proveedores`.
- Conductores: se representan con `siniestros.id_conductor` para reglas de frecuencia vehicular.
- No se crea tabla separada de beneficiarios o conductores en esta version para mantener la demo liviana y reproducible.
- Los documentos son metadatos simulados; no se almacenan archivos reales ni OCR.

## Contexto publico

`contexto_publico.csv` referencia el portal publico de la SCVS para indicadores agregados. Ese contexto no alimenta el score ni etiqueta casos.
