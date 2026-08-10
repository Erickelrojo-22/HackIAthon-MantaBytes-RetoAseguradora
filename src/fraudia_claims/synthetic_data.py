from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from fraudia_claims.config import CIUDADES, RAMOS, SCVS_CONTEXT_URL, SEED


@dataclass(frozen=True)
class SyntheticConfig:
    n_per_ramo: int = 1000
    seed: int = SEED


COVERAGES = {
    "Vehiculos": ("Choque", "Robo", "Responsabilidad Civil", "Perdida Total por Robo"),
    "Salud": ("Consulta Especializada", "Cirugia Ambulatoria", "Hospitalizacion", "Medicamentos"),
    "Hogar": ("Incendio", "Danio Agua", "Robo Hogar", "Responsabilidad Civil"),
}

PROVIDER_TYPES = {
    "Vehiculos": "Taller",
    "Salud": "Clinica",
    "Hogar": "Contratista",
}

NORMAL_DESCRIPTIONS = {
    "Vehiculos": (
        "Colision leve en interseccion urbana con parte policial y fotografias del lugar.",
        "Golpe lateral durante maniobra de estacionamiento con tercero identificado.",
        "Impacto posterior en congestion de trafico reportado el mismo dia.",
    ),
    "Salud": (
        "Atencion medica ambulatoria con orden, factura y diagnostico consistente.",
        "Procedimiento programado con respaldo de historia clinica y autorizacion.",
        "Medicamentos prescritos despues de consulta registrada por el proveedor.",
    ),
    "Hogar": (
        "Danio de tuberia interna reportado con fotografias y factura de reparacion.",
        "Afectacion menor por lluvia con informe tecnico y evidencia del inmueble.",
        "Reparacion electrica puntual con documento legible del contratista.",
    ),
}

SUSPICIOUS_DESCRIPTIONS = {
    "Vehiculos": (
        "Vehiculo impactado de madrugada por tercero no identificado que huyo sin dejar rastros ni camaras.",
        "Robo total reportado varios dias despues con factura emitida antes del evento.",
        "Accidente frontal descrito como roce leve, con danos severos y versiones inconsistentes.",
    ),
    "Salud": (
        "Factura repetida por procedimiento similar emitido por el mismo proveedor en corto periodo.",
        "Hospitalizacion reportada tardiamente con soportes incompletos e importes fuera de patron.",
        "Atencion con fechas inconsistentes entre orden medica, factura y fecha del supuesto evento.",
    ),
    "Hogar": (
        "Reparacion mayor por contratista recurrente con factura duplicada y fotos no concluyentes.",
        "Incendio reportado al cierre de vigencia con documentos incompletos y valores altos.",
        "Danio severo sin evidencia suficiente, reportado por proveedor asociado a casos observados.",
    ),
}

CLONED_NARRATIVES = {
    "Vehiculos": "El vehiculo fue impactado de madrugada por un tercero que huyo; no existen camaras ni testigos disponibles.",
    "Salud": "El paciente recibio el mismo procedimiento ambulatorio con factura emitida por el proveedor recurrente observado.",
    "Hogar": "El inmueble presenta dano severo reportado por contratista recurrente, con documentos parciales y factura similar.",
}


def generate_public_context() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "fuente": "SCVS - Portal de informacion de seguros",
                "url": SCVS_CONTEXT_URL,
                "indicador": "Primas y siniestros agregados por ramo",
                "uso_en_prototipo": "Contexto ejecutivo y calibracion manual de narrativa; no alimenta el score.",
                "nota": "Actualizar valores agregados antes del pitch si el equipo descarga cifras vigentes.",
            }
        ]
    )


def _ids(prefix: str, count: int) -> list[str]:
    return [f"{prefix}{i:05d}" for i in range(1, count + 1)]


def _choice(rng: np.random.Generator, values: tuple[str, ...] | list[str]) -> str:
    return str(values[int(rng.integers(0, len(values)))])


def generate_asegurados(rng: np.random.Generator, count: int) -> pd.DataFrame:
    segmentos = ("Individual", "Pyme", "Corporativo", "VIP")
    asegurados = pd.DataFrame(
        {
            "id_asegurado": _ids("ASE", count),
            "segmento": rng.choice(segmentos, count, p=[0.62, 0.22, 0.1, 0.06]),
            "antiguedad_meses": rng.integers(1, 144, count),
            "ciudad": rng.choice(CIUDADES, count),
            "numero_polizas": rng.integers(1, 5, count),
            "reclamos_ultimos_12_meses": rng.choice([0, 1, 2, 3], count, p=[0.72, 0.2, 0.06, 0.02]),
            "mora_actual": rng.random(count) < 0.08,
            "score_cliente_simulado": np.clip(rng.normal(680, 85, count), 300, 900).round(0).astype(int),
            "lista_restrictiva": rng.random(count) < 0.008,
        }
    )
    return asegurados


def generate_proveedores(rng: np.random.Generator) -> pd.DataFrame:
    rows: list[dict] = []
    counter = 1
    counts = {"Vehiculos": 42, "Salud": 38, "Hogar": 34}
    for ramo, count in counts.items():
        for idx in range(count):
            hotspot = idx < 4
            rows.append(
                {
                    "id_proveedor": f"PRV{counter:04d}",
                    "nombre": f"{PROVIDER_TYPES[ramo]} {ramo[:3].upper()} {idx + 1:02d}",
                    "tipo": PROVIDER_TYPES[ramo],
                    "ramo": ramo,
                    "ciudad": _choice(rng, CIUDADES),
                    "reclamos_asociados": 0,
                    "monto_promedio_reclamado": 0.0,
                    "porcentaje_casos_observados": 0.0,
                    "antiguedad_meses": int(rng.integers(3, 180)),
                    "hotspot_demo": hotspot,
                    "lista_restrictiva": hotspot and idx == 0,
                }
            )
            counter += 1
    return pd.DataFrame(rows)


def generate_polizas(
    rng: np.random.Generator, asegurados: pd.DataFrame, n_per_ramo: int
) -> pd.DataFrame:
    rows: list[dict] = []
    policy_counter = 1
    sums = {
        "Vehiculos": (8000, 65000),
        "Salud": (3000, 35000),
        "Hogar": (5000, 90000),
    }
    for ramo in RAMOS:
        for _ in range(max(450, int(n_per_ramo * 0.8))):
            asegurado = asegurados.iloc[int(rng.integers(0, len(asegurados)))]
            start = pd.Timestamp("2024-01-01") + pd.Timedelta(days=int(rng.integers(0, 640)))
            end = start + pd.Timedelta(days=365)
            suma = float(rng.uniform(*sums[ramo]))
            rows.append(
                {
                    "id_poliza": f"POL{policy_counter:05d}",
                    "id_asegurado": asegurado["id_asegurado"],
                    "ramo": ramo,
                    "fecha_inicio": start.date().isoformat(),
                    "fecha_fin": end.date().isoformat(),
                    "prima": round(suma * float(rng.uniform(0.018, 0.08)), 2),
                    "suma_asegurada": round(suma, 2),
                    "deducible": round(suma * float(rng.uniform(0.01, 0.08)), 2),
                    "canal_venta": _choice(rng, ("Agente", "Broker", "Digital", "Banca seguros")),
                    "ciudad": asegurado["ciudad"],
                    "estado_poliza": rng.choice(["Vigente", "Vigente", "Vigente", "Cancelada"], p=[0.42, 0.42, 0.12, 0.04]),
                }
            )
            policy_counter += 1
    return pd.DataFrame(rows)


def generate_vehiculos(rng: np.random.Generator, polizas: pd.DataFrame) -> pd.DataFrame:
    marcas = ("Chevrolet", "Kia", "Hyundai", "Toyota", "Nissan", "Mazda")
    modelos = ("Sedan", "SUV", "Pickup", "Hatchback", "Van")
    vehicle_policies = polizas[polizas["ramo"] == "Vehiculos"].copy()
    rows = []
    for idx, row in vehicle_policies.iterrows():
        n = int(idx) + 1
        rows.append(
            {
                "id_vehiculo": f"VEH{n:05d}",
                "id_poliza": row["id_poliza"],
                "placa": f"EC{int(rng.integers(1000, 9999))}",
                "chasis": f"CHS{int(rng.integers(10**9, 10**10 - 1))}",
                "motor": f"MTR{int(rng.integers(10**8, 10**9 - 1))}",
                "marca": _choice(rng, marcas),
                "modelo": _choice(rng, modelos),
                "anio": int(rng.integers(2014, 2026)),
            }
        )
    return pd.DataFrame(rows)


def _scenario(rng: np.random.Generator) -> str:
    return str(rng.choice(["normal", "amarillo", "rojo"], p=[0.74, 0.18, 0.08]))


def _claim_date(
    rng: np.random.Generator, fecha_inicio: str, fecha_fin: str, scenario: str
) -> pd.Timestamp:
    start = pd.Timestamp(fecha_inicio)
    end = pd.Timestamp(fecha_fin)
    if scenario in {"amarillo", "rojo"} and rng.random() < 0.48:
        return start + pd.Timedelta(days=int(rng.choice([0, 1, 2, 5, 12, 24])))
    if scenario in {"amarillo", "rojo"} and rng.random() < 0.25:
        return end - pd.Timedelta(days=int(rng.choice([0, 1, 3, 8, 18, 28])))
    return start + pd.Timedelta(days=int(rng.integers(35, 330)))


def _claim_amount(rng: np.random.Generator, ramo: str, cobertura: str, suma: float, scenario: str) -> float:
    if scenario == "rojo":
        ratio = float(rng.uniform(0.65, 1.02))
    elif scenario == "amarillo":
        ratio = float(rng.uniform(0.28, 0.75))
    else:
        ratio = {
            "Vehiculos": float(rng.uniform(0.04, 0.35)),
            "Salud": float(rng.uniform(0.03, 0.26)),
            "Hogar": float(rng.uniform(0.03, 0.32)),
        }[ramo]
    if cobertura in {"Perdida Total por Robo", "Hospitalizacion", "Incendio"}:
        ratio *= float(rng.uniform(1.05, 1.35))
    return round(min(suma * ratio, suma * 1.08), 2)


def _description(rng: np.random.Generator, ramo: str, scenario: str) -> str:
    if scenario != "normal" and rng.random() < 0.38:
        return CLONED_NARRATIVES[ramo]
    if scenario == "normal":
        return _choice(rng, NORMAL_DESCRIPTIONS[ramo])
    return _choice(rng, SUSPICIOUS_DESCRIPTIONS[ramo])


def generate_siniestros(
    rng: np.random.Generator,
    polizas: pd.DataFrame,
    proveedores: pd.DataFrame,
    vehiculos: pd.DataFrame,
    n_per_ramo: int,
) -> pd.DataFrame:
    rows: list[dict] = []
    vehicle_by_policy = vehiculos.set_index("id_poliza")
    claim_counter = 1
    for ramo in RAMOS:
        policies_ramo = polizas[polizas["ramo"] == ramo].reset_index(drop=True)
        providers_ramo = proveedores[proveedores["ramo"] == ramo].reset_index(drop=True)
        hotspot_providers = providers_ramo[providers_ramo["hotspot_demo"]].reset_index(drop=True)
        restricted = providers_ramo[providers_ramo["lista_restrictiva"]].reset_index(drop=True)
        for _ in range(n_per_ramo):
            policy = policies_ramo.iloc[int(rng.integers(0, len(policies_ramo)))]
            scenario = _scenario(rng)
            if scenario == "rojo" and len(restricted) and rng.random() < 0.22:
                provider = restricted.iloc[0]
            elif scenario != "normal" and len(hotspot_providers) and rng.random() < 0.62:
                provider = hotspot_providers.iloc[int(rng.integers(0, len(hotspot_providers)))]
            else:
                provider = providers_ramo.iloc[int(rng.integers(0, len(providers_ramo)))]

            if ramo == "Vehiculos" and scenario == "rojo" and rng.random() < 0.36:
                cobertura = "Perdida Total por Robo"
            else:
                cobertura = _choice(rng, COVERAGES[ramo])

            occurrence = _claim_date(rng, policy["fecha_inicio"], policy["fecha_fin"], scenario)
            report_delay = int(
                rng.choice([0, 1, 2, 3], p=[0.25, 0.35, 0.28, 0.12])
                if scenario == "normal"
                else rng.choice([3, 4, 5, 8, 12], p=[0.12, 0.24, 0.25, 0.25, 0.14])
            )
            if scenario == "rojo":
                report_delay = int(rng.choice([5, 8, 10, 14, 18]))
            report = occurrence + pd.Timedelta(days=report_delay)
            suma = float(policy["suma_asegurada"])
            amount = _claim_amount(rng, ramo, cobertura, suma, scenario)
            estimated = round(amount * float(rng.uniform(0.74, 1.08)), 2)
            state = _choice(
                rng,
                (
                    "Reserva",
                    "Pago Total",
                    "Pago Parcial",
                    "Anticipo",
                    "Negativa",
                    "Cierre Sin Consecuencia",
                    "Liquidado",
                ),
            )
            paid = 0.0 if state in {"Reserva", "Negativa", "Cierre Sin Consecuencia"} else round(estimated * float(rng.uniform(0.45, 1.0)), 2)
            vehicle_id = ""
            if ramo == "Vehiculos" and policy["id_poliza"] in vehicle_by_policy.index:
                vehicle_id = str(vehicle_by_policy.loc[policy["id_poliza"], "id_vehiculo"])
            only_rc = ramo == "Vehiculos" and cobertura == "Responsabilidad Civil"
            factura_prefix = {
                "Vehiculos": "TALL",
                "Salud": "CLIN",
                "Hogar": "HOME",
            }[ramo]
            if scenario != "normal" and ramo in {"Salud", "Hogar"} and rng.random() < 0.5:
                factura = f"FAC-OBS-{int(rng.integers(1, 8)):03d}"
            else:
                factura = f"{factura_prefix}-{claim_counter:06d}"
            procedimiento = ""
            if ramo == "Salud":
                procedimiento = str(rng.choice(["PROC-TRAUMA", "PROC-IMG", "PROC-CIR", "PROC-RX"]))
            rows.append(
                {
                    "id_siniestro": f"SIN{claim_counter:05d}",
                    "id_poliza": policy["id_poliza"],
                    "id_asegurado": policy["id_asegurado"],
                    "ramo": ramo,
                    "cobertura": cobertura,
                    "fecha_ocurrencia": occurrence.date().isoformat(),
                    "fecha_reporte": report.date().isoformat(),
                    "monto_reclamado": amount,
                    "monto_estimado": estimated,
                    "monto_pagado": paid,
                    "estado": state,
                    "sucursal": policy["ciudad"],
                    "descripcion": _description(rng, ramo, scenario),
                    "documentos_completos": True,
                    "id_proveedor": provider["id_proveedor"],
                    "beneficiario": provider["nombre"],
                    "dias_desde_inicio_poliza": int((occurrence - pd.Timestamp(policy["fecha_inicio"])).days),
                    "dias_desde_fin_poliza": int((pd.Timestamp(policy["fecha_fin"]) - occurrence).days),
                    "dias_entre_ocurrencia_reporte": report_delay,
                    "historial_siniestros_asegurado": 0,
                    "etiqueta_fraude_simulada": 1 if scenario == "rojo" else 0,
                    "escenario_riesgo": scenario,
                    "id_vehiculo": vehicle_id,
                    "id_conductor": f"CON{int(rng.integers(1, 780)):04d}" if ramo == "Vehiculos" else "",
                    "solo_rc": only_rc,
                    "tercero_identificado": not (ramo == "Vehiculos" and scenario != "normal" and rng.random() < 0.48),
                    "accidente_madrugada": ramo == "Vehiculos" and scenario != "normal" and rng.random() < 0.35,
                    "dinamica_imposible": ramo == "Vehiculos" and scenario == "rojo" and rng.random() < 0.16,
                    "relato_ilogico": ramo == "Vehiculos" and scenario != "normal" and rng.random() < 0.28,
                    "denuncia_horas": int(report_delay * 24 + rng.integers(1, 12)),
                    "procedimiento_codigo": procedimiento,
                    "factura_numero": factura,
                }
            )
            claim_counter += 1
    siniestros = pd.DataFrame(rows)
    siniestros = siniestros.sort_values(["id_asegurado", "fecha_ocurrencia", "id_siniestro"]).reset_index(drop=True)
    siniestros["historial_siniestros_asegurado"] = siniestros.groupby("id_asegurado").cumcount()
    return siniestros.sort_values("id_siniestro").reset_index(drop=True)


def generate_documentos(rng: np.random.Generator, siniestros: pd.DataFrame) -> pd.DataFrame:
    required = {
        "Vehiculos": ("denuncia", "factura_taller", "fotos", "informe_perito"),
        "Salud": ("factura_clinica", "orden_medica", "historia_clinica"),
        "Hogar": ("factura_reparacion", "fotos", "informe_perito"),
    }
    rows: list[dict] = []
    doc_counter = 1
    for _, claim in siniestros.iterrows():
        scenario = claim["escenario_riesgo"]
        for doc_type in required[claim["ramo"]]:
            if scenario == "normal":
                delivered = bool(rng.random() > 0.025)
                legible = bool(rng.random() > 0.02)
                inconsistent = bool(rng.random() < 0.012)
                altered = False
            elif scenario == "amarillo":
                delivered = bool(rng.random() > 0.12)
                legible = bool(rng.random() > 0.10)
                inconsistent = bool(rng.random() < 0.12)
                altered = False
            else:
                delivered = bool(rng.random() > 0.20)
                legible = bool(rng.random() > 0.18)
                inconsistent = bool(rng.random() < 0.30)
                altered = bool(doc_type.startswith("factura") and rng.random() < 0.14)
            rows.append(
                {
                    "id_documento": f"DOC{doc_counter:06d}",
                    "id_siniestro": claim["id_siniestro"],
                    "tipo_documento": doc_type,
                    "entregado": delivered,
                    "legible": legible,
                    "fecha_emision": claim["fecha_reporte"],
                    "inconsistencia_detectada": inconsistent or altered,
                    "adulteracion_confirmada": altered,
                    "observacion": "Alteracion documental simulada (dataset sintetico)" if altered else "",
                }
            )
            doc_counter += 1
    docs = pd.DataFrame(rows)
    doc_ok = docs.groupby("id_siniestro").apply(
        lambda group: bool(group["entregado"].all() and group["legible"].all() and not group["inconsistencia_detectada"].any()),
        include_groups=False,
    )
    siniestros.loc[:, "documentos_completos"] = siniestros["id_siniestro"].map(doc_ok).fillna(False).astype(bool)
    return docs


def update_provider_stats(proveedores: pd.DataFrame, siniestros: pd.DataFrame) -> pd.DataFrame:
    providers = proveedores.copy()
    grouped = siniestros.groupby("id_proveedor").agg(
        reclamos_asociados=("id_siniestro", "count"),
        monto_promedio_reclamado=("monto_reclamado", "mean"),
        porcentaje_casos_observados=("escenario_riesgo", lambda s: float((s != "normal").mean() * 100)),
    )
    providers = providers.drop(columns=["reclamos_asociados", "monto_promedio_reclamado", "porcentaje_casos_observados"])
    providers = providers.merge(grouped, how="left", left_on="id_proveedor", right_index=True)
    providers[["reclamos_asociados", "monto_promedio_reclamado", "porcentaje_casos_observados"]] = providers[
        ["reclamos_asociados", "monto_promedio_reclamado", "porcentaje_casos_observados"]
    ].fillna(0)
    providers["monto_promedio_reclamado"] = providers["monto_promedio_reclamado"].round(2)
    providers["porcentaje_casos_observados"] = providers["porcentaje_casos_observados"].round(2)
    return providers


def generate_all(config: SyntheticConfig | None = None) -> dict[str, pd.DataFrame]:
    cfg = config or SyntheticConfig()
    rng = np.random.default_rng(cfg.seed)
    asegurados = generate_asegurados(rng, max(1400, int(cfg.n_per_ramo * 1.7)))
    proveedores = generate_proveedores(rng)
    polizas = generate_polizas(rng, asegurados, cfg.n_per_ramo)
    vehiculos = generate_vehiculos(rng, polizas)
    siniestros = generate_siniestros(rng, polizas, proveedores, vehiculos, cfg.n_per_ramo)
    documentos = generate_documentos(rng, siniestros)
    proveedores = update_provider_stats(proveedores, siniestros)
    return {
        "contexto_publico": generate_public_context(),
        "asegurados": asegurados,
        "polizas": polizas,
        "proveedores": proveedores,
        "vehiculos": vehiculos,
        "siniestros": siniestros,
        "documentos": documentos,
    }


def write_reference_context(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    generate_public_context().to_csv(path, index=False, encoding="utf-8")
