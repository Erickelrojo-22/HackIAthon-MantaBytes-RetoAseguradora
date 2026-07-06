# Graficos de contexto - fraude de seguros en Ecuador

Este directorio contiene graficos de apoyo para el pitch de FraudIA Claims.

## Archivos generados

- `outputs/01_ramos_vulnerables_fraude_ecuador.svg`
- `outputs/02_medios_deteccion_fraude_ecuador.svg`
- `outputs/03_primas_por_ramo_2025_ecuador.svg`
- `outputs/04_indicadores_sector_abril_2026.svg`
- `outputs/05_top_aseguradoras_2025_ecuador.svg`
- `outputs/06_causas_judiciales_contexto_anual.svg`
- `outputs/07_causas_judiciales_contexto_provincia.svg`
- `data/datos_graficos_fraude_ecuador.csv`
- `index.html`

## Fuentes usadas

1. Eumed / Observatorio de la Economia Latinoamericana, 2017:
   "Analisis de los fraudes en el sistema asegurador en el Ecuador".
   Se usaron porcentajes de ramos vulnerables y medios de identificacion de fraude reportados por aseguradoras encuestadas.

2. Forbes Ecuador, 2026, con datos de Fedeseg:
   ranking de seguros con mayor prima neta emitida en 2025.

3. Forbes Ecuador, 2026, con datos de la SCVS:
   top 10 aseguradoras por prima neta emitida en 2025.

4. CAMSEG:
   estadisticas sectoriales publicadas para abril de 2026.

5. Datos Abiertos Ecuador / Consejo de la Judicatura:
   causas judiciales desde 2017 hasta corte abril de 2026. Se filtro `Delito` por palabras clave:
   `ESTAFA`, `DEFRAUD`, `FRAUDE` y `FALSIFIC`.

## Nota metodologica

En Ecuador no se encontro un dataset publico nacional con fraude de seguros confirmado caso por caso. Por eso los graficos separan:

- Fraude de seguros segun estudio exploratorio sectorial.
- Volumen y presion operativa del mercado asegurador.
- Contexto judicial de delitos relacionados con estafa, fraude, defraudacion y falsificacion.

Las cifras judiciales son contexto para justificar la relevancia del problema, pero no deben presentarse como "fraudes de seguros confirmados".

## Regenerar

Desde la raiz del repositorio:

```powershell
.\.venv\Scripts\python deliverables\evidencia_visual\fraud_graphics\generate_fraud_charts.py
```

Si existe `source_downloads/cj_datoscausas_2026abril.ods`, el script recalcula los graficos judiciales desde el archivo descargado. Si no existe, usa un respaldo con los valores ya extraidos para mantener reproducibilidad.

