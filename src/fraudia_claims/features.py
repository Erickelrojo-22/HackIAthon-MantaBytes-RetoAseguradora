from __future__ import annotations

import numpy as np
import pandas as pd


def _empty_doc_summary() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "id_siniestro",
            "docs_faltantes",
            "docs_ilegibles",
            "docs_inconsistentes",
            "adulteracion_documental",
        ]
    )


def build_feature_frame(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    claims = tables["siniestros"].copy()
    policies = tables["polizas"].rename(
        columns={
            "ramo": "ramo_poliza",
            "ciudad": "ciudad_poliza",
            "fecha_inicio": "fecha_inicio_poliza",
            "fecha_fin": "fecha_fin_poliza",
        }
    )
    providers = tables["proveedores"].rename(
        columns={
            "ramo": "ramo_proveedor",
            "ciudad": "ciudad_proveedor",
            "lista_restrictiva": "lista_restrictiva_proveedor",
        }
    )
    insured = tables["asegurados"].rename(
        columns={
            "ciudad": "ciudad_asegurado",
            "lista_restrictiva": "lista_restrictiva_asegurado",
        }
    )
    vehicles = tables.get("vehiculos", pd.DataFrame())
    docs = tables.get("documentos", pd.DataFrame())
    if docs.empty:
        doc_summary = _empty_doc_summary()
    else:
        doc_summary = docs.groupby("id_siniestro").agg(
            docs_faltantes=("entregado", lambda s: int((~s.astype(bool)).sum())),
            docs_ilegibles=("legible", lambda s: int((~s.astype(bool)).sum())),
            docs_inconsistentes=("inconsistencia_detectada", lambda s: int(s.astype(bool).sum())),
            adulteracion_documental=("adulteracion_confirmada", lambda s: bool(s.astype(bool).any())),
        ).reset_index()

    frame = (
        claims.merge(policies, on=["id_poliza", "id_asegurado"], how="left")
        .merge(providers, on="id_proveedor", how="left")
        .merge(insured, on="id_asegurado", how="left")
        .merge(doc_summary, on="id_siniestro", how="left")
    )
    if not vehicles.empty:
        frame = frame.merge(vehicles[["id_poliza", "id_vehiculo", "placa", "marca", "modelo", "anio"]], on=["id_poliza", "id_vehiculo"], how="left")

    for col in ["docs_faltantes", "docs_ilegibles", "docs_inconsistentes"]:
        frame[col] = frame[col].fillna(0).astype(int)
    frame["adulteracion_documental"] = frame["adulteracion_documental"].fillna(False).astype(bool)
    frame["lista_restrictiva_proveedor"] = frame["lista_restrictiva_proveedor"].fillna(False).astype(bool)
    frame["lista_restrictiva_asegurado"] = frame["lista_restrictiva_asegurado"].fillna(False).astype(bool)
    frame["suma_asegurada"] = frame["suma_asegurada"].fillna(frame["monto_reclamado"].clip(lower=1))
    frame["monto_ratio_suma"] = frame["monto_reclamado"] / frame["suma_asegurada"].replace(0, np.nan)
    frame["monto_ratio_suma"] = frame["monto_ratio_suma"].replace([np.inf, -np.inf], np.nan).fillna(0)

    frame["frecuencia_asegurado_total"] = frame.groupby("id_asegurado")["id_siniestro"].transform("count")
    frame["frecuencia_proveedor_total"] = frame.groupby("id_proveedor")["id_siniestro"].transform("count")
    frame["frecuencia_vehiculo_total"] = frame.groupby("id_vehiculo")["id_siniestro"].transform("count")
    frame.loc[frame["id_vehiculo"].fillna("") == "", "frecuencia_vehiculo_total"] = 0
    frame["frecuencia_conductor_total"] = frame.groupby("id_conductor")["id_siniestro"].transform("count")
    frame.loc[frame["id_conductor"].fillna("") == "", "frecuencia_conductor_total"] = 0

    vehicle_rc_counts = frame[frame["solo_rc"].astype(bool)].groupby("id_vehiculo")["id_siniestro"].transform("count")
    frame["frecuencia_rc_vehiculo"] = 0
    frame.loc[frame["solo_rc"].astype(bool), "frecuencia_rc_vehiculo"] = vehicle_rc_counts

    frame["factura_duplicada_count"] = frame.groupby("factura_numero")["id_siniestro"].transform("count")
    frame.loc[frame["factura_numero"].fillna("") == "", "factura_duplicada_count"] = 0
    procedure_key = frame["procedimiento_codigo"].fillna("") + "|" + frame["id_proveedor"].fillna("")
    frame["repeticion_procedimiento_proveedor"] = procedure_key.groupby(procedure_key).transform("count")
    frame.loc[frame["procedimiento_codigo"].fillna("") == "", "repeticion_procedimiento_proveedor"] = 0

    avg_by_cov = frame.groupby(["ramo", "cobertura"])["monto_reclamado"].transform("mean")
    std_by_cov = frame.groupby(["ramo", "cobertura"])["monto_reclamado"].transform("std").replace(0, np.nan)
    frame["monto_z_ramo_cobertura"] = ((frame["monto_reclamado"] - avg_by_cov) / std_by_cov).replace([np.inf, -np.inf], np.nan).fillna(0)
    return frame
