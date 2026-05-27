# Reglas de negocio y scoring

## Formula

```text
score_final = min(100, min(puntos_reglas, 60) + puntos_anomalia + puntos_nlp)
```

Si una regla critica se activa, el caso escala como minimo a `76` puntos.

## Semaforo

- `0-40`: Verde, flujo normal.
- `41-75`: Amarillo, revision documental.
- `76-100`: Rojo, revision especializada.

## Reglas comunes

- Siniestro cerca del inicio o fin de vigencia.
- Reporte tardio.
- Frecuencia historica del asegurado.
- Proveedor recurrente o en lista restrictiva simulada.
- Documentos faltantes, ilegibles, inconsistentes o adulterados.
- Monto cercano a la suma asegurada o atipico frente a la cobertura.

## Reglas por ramo

- Vehiculos: perdida total por robo, demora en denuncia, reincidencia de vehiculo/conductor, solo RC, dinamica imposible y tercero no identificado.
- Salud: factura duplicada, procedimiento repetido con proveedor y monto atipico.
- Hogar: factura duplicada, contratista recurrente y monto atipico.

## IA local

- Anomalias: `IsolationForest` por ramo, con fallback robusto si no esta instalado.
- NLP: TF-IDF por ramo, con fallback para narrativas clonadas.
