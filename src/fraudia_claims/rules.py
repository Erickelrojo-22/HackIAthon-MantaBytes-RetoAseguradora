from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd


def _alert(
    claim_id: str,
    code: str,
    category: str,
    severity: str,
    points: int,
    description: str,
    evidence: str,
    critical: bool = False,
) -> dict[str, Any]:
    return {
        "id_siniestro": claim_id,
        "codigo": code,
        "categoria": category,
        "severidad": severity,
        "puntos": int(points),
        "descripcion": description,
        "evidencia": evidence,
        "es_critica": bool(critical),
    }


def apply_rules(features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    alerts: list[dict[str, Any]] = []
    totals: dict[str, int] = defaultdict(int)
    criticals: dict[str, bool] = defaultdict(bool)
    yellow_escalations: dict[str, bool] = defaultdict(bool)

    def add(
        row: pd.Series,
        code: str,
        category: str,
        severity: str,
        points: int,
        description: str,
        evidence: str,
        critical: bool = False,
        min_yellow: bool = False,
    ) -> None:
        claim_id = str(row["id_siniestro"])
        alerts.append(_alert(claim_id, code, category, severity, points, description, evidence, critical))
        totals[claim_id] += int(points)
        criticals[claim_id] = bool(criticals[claim_id] or critical)
        yellow_escalations[claim_id] = bool(yellow_escalations[claim_id] or min_yellow)

    for _, row in features.iterrows():
        claim_id = str(row["id_siniestro"])
        totals[claim_id] += 0
        min_border = min(int(row["dias_desde_inicio_poliza"]), int(row["dias_desde_fin_poliza"]))
        if min_border <= 10:
            add(
                row,
                "RF-05",
                "Vigencia",
                "Alta",
                8,
                "Siniestro muy cercano al inicio o fin de vigencia.",
                f"{min_border} dias al borde de vigencia.",
                min_yellow=min_border <= 1,
            )
        elif min_border <= 30:
            add(row, "RF-05", "Vigencia", "Media", 4, "Siniestro cercano al borde de vigencia.", f"{min_border} dias al borde de vigencia.")

        report_delay = int(row["dias_entre_ocurrencia_reporte"])
        if report_delay > 7:
            add(row, "RF-12", "Reporte", "Media", 5, "Reporte tardio frente a la ocurrencia.", f"Reporte despues de {report_delay} dias.")
        elif report_delay >= 4:
            add(row, "RF-12", "Reporte", "Baja", 3, "Reporte con demora moderada.", f"Reporte despues de {report_delay} dias.")

        history = int(row["historial_siniestros_asegurado"])
        if history >= 3:
            add(row, "RF-08", "Frecuencia", "Alta", 8, "Asegurado con alta frecuencia historica de reclamos.", f"{history} siniestros previos.")
        elif history == 2:
            add(row, "RF-08", "Frecuencia", "Media", 4, "Asegurado con frecuencia historica moderada.", "2 siniestros previos.")

        if bool(row.get("lista_restrictiva_proveedor", False)) or bool(row.get("lista_restrictiva_asegurado", False)):
            add(
                row,
                "RF-03",
                "Lista restrictiva",
                "Critica",
                10,
                "Coincidencia exacta con lista restrictiva simulada.",
                "Proveedor o asegurado marcado en lista restrictiva de demo.",
                critical=True,
            )

        provider_claims = int(row.get("frecuencia_proveedor_total", 0))
        if provider_claims >= 35:
            add(row, "RF-09", "Proveedor", "Media", 5, "Proveedor con alta concentracion de reclamos.", f"{provider_claims} reclamos asociados.")

        if bool(row.get("adulteracion_documental", False)):
            add(
                row,
                "RF-02",
                "Documentos",
                "Critica",
                10,
                "Evidencia simulada de adulteracion documental.",
                "Al menos un documento fue marcado como adulterado.",
                critical=True,
            )
        elif int(row.get("docs_inconsistentes", 0)) > 0:
            add(
                row,
                "RF-11",
                "Documentos",
                "Alta",
                10,
                "Documentos con fechas, valores o legibilidad inconsistentes.",
                f"{int(row['docs_inconsistentes'])} documento(s) inconsistentes.",
            )

        missing_or_illegible = int(row.get("docs_faltantes", 0)) + int(row.get("docs_ilegibles", 0))
        if missing_or_illegible > 0:
            add(
                row,
                "RF-10",
                "Documentos",
                "Media",
                4,
                "Documentos obligatorios incompletos o ilegibles.",
                f"{missing_or_illegible} documento(s) faltantes o ilegibles.",
            )

        if float(row.get("monto_ratio_suma", 0)) >= 0.95 or float(row.get("monto_z_ramo_cobertura", 0)) >= 2.5:
            add(
                row,
                "RF-14",
                "Monto",
                "Media",
                5,
                "Monto reclamado cercano a la suma asegurada o atipico para la cobertura.",
                f"Ratio contra suma asegurada: {float(row['monto_ratio_suma']):.2f}.",
            )

        ramo = row["ramo"]
        if ramo == "Vehiculos":
            if row["cobertura"] == "Perdida Total por Robo":
                add(
                    row,
                    "RF-01",
                    "Cobertura",
                    "Critica",
                    20,
                    "Cobertura de perdida total por robo requiere revision especializada.",
                    "Cobertura PTxRB.",
                    critical=True,
                )
            if "Robo" in str(row["cobertura"]):
                hours = int(row.get("denuncia_horas", 0))
                if hours > 48:
                    add(
                        row,
                        "RF-06",
                        "Denuncia",
                        "Alta",
                        8,
                        "Demora atipica en denuncia de robo.",
                        f"{hours} horas hasta la denuncia.",
                        min_yellow=hours > 96,
                    )
                elif hours >= 24:
                    add(row, "RF-06", "Denuncia", "Media", 4, "Demora moderada en denuncia de robo.", f"{hours} horas hasta la denuncia.")
            vehicle_freq = int(row.get("frecuencia_vehiculo_total", 0))
            if vehicle_freq >= 3:
                add(row, "RF-15", "Frecuencia", "Media", 6, "Vehiculo asociado a multiples siniestros.", f"{vehicle_freq} siniestros del vehiculo.")
            elif vehicle_freq == 2:
                add(row, "RF-15", "Frecuencia", "Baja", 3, "Vehiculo con reincidencia moderada.", "2 siniestros del vehiculo.")
            driver_freq = int(row.get("frecuencia_conductor_total", 0))
            if driver_freq >= 3:
                add(row, "RF-16", "Frecuencia", "Alta", 8, "Conductor presente en multiples siniestros.", f"{driver_freq} siniestros del conductor.")
            elif driver_freq == 2:
                add(row, "RF-16", "Frecuencia", "Media", 4, "Conductor con reincidencia moderada.", "2 siniestros del conductor.")
            if bool(row.get("solo_rc", False)) and int(row.get("frecuencia_rc_vehiculo", 0)) > 2:
                add(row, "RF-17", "Cobertura", "Media", 6, "Frecuencia atipica de reclamos solo RC.", f"{int(row['frecuencia_rc_vehiculo'])} eventos RC del vehiculo.")
            if bool(row.get("dinamica_imposible", False)):
                add(
                    row,
                    "RF-04",
                    "Dinamica",
                    "Critica",
                    20,
                    "Dinamica fisicamente imposible segun datos simulados.",
                    "Flag de dinamica imposible activado.",
                    critical=True,
                )
            elif bool(row.get("relato_ilogico", False)):
                add(row, "RF-18", "Dinamica", "Alta", 6, "Relato ilogico frente al tipo de impacto.", "Inconsistencia narrativa simulada.")
            if bool(row.get("accidente_madrugada", False)):
                add(row, "RF-19", "Dinamica", "Baja", 3, "Accidente multiple o severo reportado de madrugada.", "Flag de madrugada activado.")
            if not bool(row.get("tercero_identificado", True)) and float(row.get("monto_ratio_suma", 0)) > 0.35:
                add(row, "RF-20", "Tercero", "Media", 5, "Danio relevante sin tercero identificado.", "Tercero no identificado con monto relevante.")

        if ramo == "Salud":
            if int(row.get("factura_duplicada_count", 0)) > 1 and str(row.get("factura_numero", "")).startswith("FAC-OBS"):
                add(row, "RS-01", "Factura", "Alta", 8, "Factura repetida en reclamos de salud.", f"Factura {row['factura_numero']} repetida.")
            if int(row.get("repeticion_procedimiento_proveedor", 0)) >= 6:
                add(row, "RS-02", "Proveedor", "Media", 6, "Procedimiento repetido con el mismo proveedor.", f"{int(row['repeticion_procedimiento_proveedor'])} repeticiones.")
            if float(row.get("monto_z_ramo_cobertura", 0)) >= 2:
                add(row, "RS-03", "Monto", "Media", 6, "Monto atipico para prestacion de salud.", f"Z-score {float(row['monto_z_ramo_cobertura']):.2f}.")

        if ramo == "Hogar":
            if int(row.get("factura_duplicada_count", 0)) > 1 and str(row.get("factura_numero", "")).startswith("FAC-OBS"):
                add(row, "RH-01", "Factura", "Alta", 8, "Factura repetida en reclamos de hogar.", f"Factura {row['factura_numero']} repetida.")
            if provider_claims >= 20:
                add(row, "RH-02", "Contratista", "Media", 5, "Contratista recurrente en reclamos observados.", f"{provider_claims} reclamos asociados.")
            if float(row.get("monto_z_ramo_cobertura", 0)) >= 2:
                add(row, "RH-03", "Monto", "Media", 6, "Monto atipico para cobertura de hogar.", f"Z-score {float(row['monto_z_ramo_cobertura']):.2f}.")

    summary = pd.DataFrame(
        [
            {
                "id_siniestro": claim_id,
                "score_reglas": int(points),
                "regla_critica": bool(criticals[claim_id]),
                "regla_min_amarillo": bool(yellow_escalations[claim_id]),
            }
            for claim_id, points in totals.items()
        ]
    )
    alerts_frame = pd.DataFrame(alerts)
    if not alerts_frame.empty:
        alerts_frame.insert(0, "id_alerta", [f"ALT{i:06d}" for i in range(1, len(alerts_frame) + 1)])
    return summary, alerts_frame
