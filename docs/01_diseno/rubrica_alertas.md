# Rubrica de alertas

Esta rubrica describe como FraudIA Claims convierte senales de riesgo en alertas para revision humana. No es una declaracion de fraude; es una priorizacion operativa para analistas.

## Semaforo

| Nivel | Score | Interpretacion | Accion sugerida |
| --- | ---: | --- | --- |
| Verde | 0-40 | Sin senales relevantes o senales leves | Flujo normal con controles habituales |
| Amarillo | 41-75 | Senales que ameritan validacion documental o contextual | Revision del expediente y documentos |
| Rojo | 76-100 | Senales criticas o acumulacion fuerte de alertas | Revision especializada y trazabilidad humana |

## Pesos del score

| Fuente | Maximo | Criterio |
| --- | ---: | --- |
| Reglas de negocio | 60 | Vigencia, reporte tardio, frecuencia, proveedor, documentos, monto y reglas por ramo |
| Anomalia numerica | 20 | Percentil alto de anomalia por ramo |
| NLP narrativo | 20 | Narrativa clonada o muy similar dentro del mismo ramo |
| Modelo supervisado demo | 15 | Probabilidad sintetica alta, usada solo como apoyo |

El score final se limita a 100. Las reglas criticas y amarillas pueden elevar el nivel minimo aunque la suma base sea menor.

## Reglas criticas: minimo rojo

| Codigo | Senal | Justificacion |
| --- | --- | --- |
| RF-01 | Perdida total por robo | Escenario de alto impacto que requiere revision especializada |
| RF-02 | Adulteracion documental confirmada | Evidencia documental simulada de maxima prioridad |
| RF-03 | Coincidencia con lista restrictiva simulada | Senal de cumplimiento y control operativo |
| RF-04 | Dinamica fisicamente imposible | Inconsistencia tecnica fuerte en la narrativa o datos del caso |

## Reglas obligatorias: minimo amarillo

| Codigo | Senal | Justificacion |
| --- | --- | --- |
| RF-05 | Siniestro extremo dentro de 48 horas de vigencia | Cercania al inicio/fin de poliza con impacto alto |
| RF-06 | Denuncia de robo con demora mayor a 4 dias | Demora atipica en reporte de robo |
| RF-07 | Narrativa identica o clonada | Posible patron repetido que debe verificarse |

## Senales comunes

- Inicio o fin de vigencia cercano.
- Reporte tardio frente a fecha de ocurrencia.
- Alta frecuencia del asegurado.
- Proveedor recurrente con alertas.
- Documentos faltantes, ilegibles, inconsistentes o adulterados.
- Monto reclamado alto o cercano a la suma asegurada.

## Senales por ramo

- **Vehiculos**: robo, perdida total, recurrencia de vehiculo/conductor, cobertura solo RC, tercero no identificado y dinamica imposible.
- **Salud**: factura duplicada, procedimiento repetido con el mismo proveedor, monto atipico o proveedor concentrador.
- **Hogar**: factura duplicada, contratista recurrente, reclamos similares en ventana cercana y monto atipico.

## Evidencia mostrada al analista

Cada alerta visible en el expediente incluye codigo, descripcion, puntos y evidencia. Cuando aplica, se muestra el siniestro similar que genero una alerta de narrativa.

## Principio etico

La rubrica ordena la bandeja de revision. La decision final queda en manos humanas y se registra en historial/auditoria.
