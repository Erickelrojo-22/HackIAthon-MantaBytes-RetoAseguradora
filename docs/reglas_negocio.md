# Reglas de negocio y scoring

## Formula

```text
score_final = min(100, min(puntos_reglas, 60) + puntos_anomalia + puntos_nlp + puntos_modelo)
```

Si una regla critica se activa, el caso escala como minimo a `76` puntos. Si se activa una regla amarilla obligatoria del reto, el caso escala como minimo a `41` puntos.

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

## Escalamientos oficiales del reto

- Minimo rojo: `RF-01` perdida total por robo, `RF-02` adulteracion documental, `RF-03` lista restrictiva y `RF-04` dinamica fisicamente imposible.
- Minimo amarillo: `RF-05` siniestro extremo al borde de vigencia menor a 48 horas, `RF-06` denuncia de robo mayor a 4 dias y `RF-07` narrativa identica o clonada.
- El escalamiento no acusa fraude; solo garantiza que el caso aparezca en la bandeja de revision humana.

## Reglas por ramo

- Vehiculos: perdida total por robo, demora en denuncia, reincidencia de vehiculo/conductor, solo RC, dinamica imposible y tercero no identificado.
- Salud: factura duplicada, procedimiento repetido con proveedor y monto atipico.
- Hogar: factura duplicada, contratista recurrente y monto atipico.

## IA local

- Anomalias: `IsolationForest` por ramo, con fallback robusto si no esta instalado.
- NLP: TF-IDF por ramo, con fallback para narrativas clonadas.
- Modelo supervisado: `RandomForestClassifier` con etiqueta sintetica `etiqueta_fraude_simulada`, probabilidad trazada y metricas `precision`, `recall`, `f1`, `auc_roc` y matriz de confusion.
- El score supervisado aporta hasta 15 puntos y no reemplaza las reglas criticas ni la revision humana.
