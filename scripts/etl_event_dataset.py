from __future__ import annotations

import argparse
import re
import unicodedata
import zipfile
from hashlib import sha256
from pathlib import Path

import pandas as pd


def ascii_key(value: object) -> str:
    text = str(value)
    try:
        repaired = text.encode("latin1").decode("utf-8")
    except Exception:
        repaired = text
    text = unicodedata.normalize("NFKD", repaired).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def column(frame: pd.DataFrame, name: str) -> str:
    wanted = ascii_key(name)
    lookup = {ascii_key(col): col for col in frame.columns}
    if wanted not in lookup:
        compact_lookup = {key.replace(" ", ""): col for key, col in lookup.items()}
        compact_wanted = wanted.replace(" ", "")
        if compact_wanted in compact_lookup:
            return compact_lookup[compact_wanted]
        available = ", ".join(str(col) for col in frame.columns)
        raise KeyError(f"No existe columna {name!r}. Disponibles: {available}")
    return lookup[wanted]


def series(frame: pd.DataFrame, name: str, default: object = "") -> pd.Series:
    try:
        return frame[column(frame, name)]
    except KeyError:
        return pd.Series([default] * len(frame), index=frame.index)


def yes_no(value) -> bool:
    return str(value).strip().lower() in {"si", "s", "yes", "true", "1"}


def norm_ramo(value: object) -> str:
    text = ascii_key(value)
    if text == "vehiculos":
        return "Vehiculos"
    if text == "salud":
        return "Salud"
    if text == "hogar":
        return "Hogar"
    return str(value).strip()


def slug(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", ascii_key(value).upper()).strip("_")


def stable_int(*parts: object, modulo: int = 100) -> int:
    raw = "|".join(str(part) for part in parts)
    return int(sha256(raw.encode("utf-8")).hexdigest()[:8], 16) % modulo


def stable_choice(key: object, options: tuple[str, ...]) -> str:
    return options[stable_int(key, modulo=len(options))]


def numeric(values: pd.Series) -> pd.Series:
    return pd.to_numeric(values, errors="coerce").fillna(0)


def bool_from_signal(identifier: object, rate_percent: int) -> bool:
    return stable_int(identifier, modulo=100) < rate_percent


def read_excel_from_zip(zip_path: Path) -> dict[str, pd.DataFrame]:
    with zipfile.ZipFile(zip_path) as zf:
        excel_name = [name for name in zf.namelist() if name.lower().endswith(".xlsx")][0]
        return {
            "siniestros": pd.read_excel(zf.open(excel_name), sheet_name="1_Siniestros"),
            "polizas": pd.read_excel(zf.open(excel_name), sheet_name="2_Polizas"),
            "asegurados": pd.read_excel(zf.open(excel_name), sheet_name="3_Asegurados"),
            "proveedores": pd.read_excel(zf.open(excel_name), sheet_name="4_Proveedores"),
            "documentos": pd.read_excel(zf.open(excel_name), sheet_name="5_Documentos"),
        }


def build_document_table(docs: pd.DataFrame, sin: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    occurrence_by_claim = pd.to_datetime(
        sin.set_index(column(sin, "ID Siniestro"))[column(sin, "Fecha Ocurrencia")],
        errors="coerce",
    )
    documentos = pd.DataFrame(
        {
            "id_documento": series(docs, "ID Documento"),
            "id_siniestro": series(docs, "ID Siniestro"),
            "tipo_documento": series(docs, "Tipo Documento"),
            "entregado": series(docs, "Nombre Archivo PDF").fillna("").astype(str).str.strip().ne(""),
            "legible": True,
            "inconsistencia_detectada": False,
            "adulteracion_confirmada": False,
            "archivo_pdf": series(docs, "Nombre Archivo PDF").fillna(""),
        }
    )
    documentos["legible"] = documentos.apply(
        lambda row: bool(row["entregado"]) and not bool_from_signal(row["id_documento"], 5),
        axis=1,
    )
    documentos["inconsistencia_detectada"] = documentos["id_documento"].map(lambda value: bool_from_signal(value, 6))
    documentos["adulteracion_confirmada"] = documentos["id_documento"].map(lambda value: bool_from_signal(value, 2))
    documentos["fecha_emision"] = documentos.apply(
        lambda row: (
            occurrence_by_claim.get(row["id_siniestro"])
            + pd.to_timedelta(stable_int(row["id_documento"], "fecha", modulo=7) - 2, unit="D")
        )
        .date()
        .isoformat()
        if pd.notna(occurrence_by_claim.get(row["id_siniestro"]))
        else "",
        axis=1,
    )
    documentos["observacion"] = documentos.apply(
        lambda row: "Documento no entregado"
        if not bool(row["entregado"])
        else "Documento ilegible"
        if not bool(row["legible"])
        else "Adulteracion simulada detectada"
        if bool(row["adulteracion_confirmada"])
        else "Inconsistencia detectada"
        if bool(row["inconsistencia_detectada"])
        else "Sin observaciones",
        axis=1,
    )
    doc_summary = documentos.groupby("id_siniestro").agg(
        documentos_entregados=("entregado", lambda values: bool(values.astype(bool).all())),
        docs_ilegibles=("legible", lambda values: int((~values.astype(bool)).sum())),
        docs_inconsistentes=("inconsistencia_detectada", lambda values: int(values.astype(bool).sum())),
        docs_adulterados=("adulteracion_confirmada", lambda values: int(values.astype(bool).sum())),
    )
    doc_summary["documentos_completos"] = (
        doc_summary["documentos_entregados"]
        & doc_summary["docs_ilegibles"].eq(0)
        & doc_summary["docs_inconsistentes"].eq(0)
        & doc_summary["docs_adulterados"].eq(0)
    )
    return documentos, doc_summary


def build_tables(source: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    sin = source["siniestros"].copy()
    pol = source["polizas"].copy()
    ase = source["asegurados"].copy()
    prov = source["proveedores"].copy()
    docs = source["documentos"].copy()

    asegurados = pd.DataFrame(
        {
            "id_asegurado": series(ase, "ID Asegurado"),
            "ciudad": series(ase, "Ciudad"),
            "lista_restrictiva": False,
            "nombres_asegurado": series(ase, "Nombres Asegurado"),
            "segmento": series(ase, "Segmento"),
            "perfil_riesgo_historico": series(ase, "Perfil Riesgo Historico"),
        }
    )
    policy_counts = series(pol, "ID Asegurado").groupby(series(pol, "ID Asegurado")).size()
    claim_counts = series(sin, "ID Asegurado").groupby(series(sin, "ID Asegurado")).size()
    risk_profile = asegurados["perfil_riesgo_historico"].astype(str)
    asegurados["antiguedad"] = asegurados["id_asegurado"].map(lambda value: 1 + stable_int(value, "antiguedad", modulo=14))
    asegurados["numero_polizas"] = asegurados["id_asegurado"].map(policy_counts).fillna(0).astype(int)
    asegurados["reclamos_ultimos_12_meses"] = asegurados["id_asegurado"].map(claim_counts).fillna(0).astype(int)
    asegurados["mora_actual"] = risk_profile.str.contains("alto|crit|mora", case=False, na=False) | asegurados["id_asegurado"].map(
        lambda value: bool_from_signal(value, 8)
    )
    asegurados["score_cliente_simulado"] = (
        100
        - asegurados["reclamos_ultimos_12_meses"] * 6
        - asegurados["mora_actual"].astype(int) * 15
        - risk_profile.str.contains("alto|crit", case=False, na=False).astype(int) * 10
        + asegurados["antiguedad"].clip(upper=10) * 2
    ).clip(lower=0, upper=100)

    polizas = pd.DataFrame(
        {
            "id_poliza": series(pol, "ID Poliza"),
            "id_asegurado": series(pol, "ID Asegurado"),
            "ramo": series(pol, "Ramo").map(norm_ramo),
            "fecha_inicio": pd.to_datetime(series(pol, "Fecha Inicio")).dt.date.astype(str),
            "fecha_fin": pd.to_datetime(series(pol, "Fecha Fin")).dt.date.astype(str),
            "suma_asegurada": series(pol, "Suma Asegurada ($)"),
        }
    ).merge(asegurados[["id_asegurado", "ciudad"]], on="id_asegurado", how="left")
    premium_rate = polizas["ramo"].map({"Vehiculos": 0.055, "Salud": 0.075, "Hogar": 0.04}).fillna(0.05)
    deductible_rate = polizas["ramo"].map({"Vehiculos": 0.025, "Salud": 0.015, "Hogar": 0.02}).fillna(0.02)
    polizas["prima"] = numeric(series(pol, "Prima Anual ($)", default=0))
    missing_prima = polizas["prima"].eq(0)
    polizas.loc[missing_prima, "prima"] = (numeric(polizas.loc[missing_prima, "suma_asegurada"]) * premium_rate[missing_prima]).round(2)
    polizas["deducible"] = (numeric(polizas["suma_asegurada"]) * deductible_rate).round(2)
    polizas["canal_venta"] = series(pol, "Canal Venta", default="").replace("", pd.NA).fillna(
        polizas["id_poliza"].map(lambda value: stable_choice(value, ("Agente", "Web", "Broker", "Sucursal")))
    )
    polizas["estado_poliza"] = series(pol, "Estado Poliza", default="").replace("", pd.NA).fillna("Vigente")

    provider_ramo = (
        sin.assign(ramo_norm=series(sin, "Ramo").map(norm_ramo))
        .groupby([series(sin, "ID Proveedor"), "ramo_norm"])
        .size()
        .reset_index(name="n")
        .rename(columns={series(sin, "ID Proveedor").name: "ID Proveedor"})
        .sort_values(["ID Proveedor", "n"], ascending=[True, False])
        .drop_duplicates("ID Proveedor")
        .set_index("ID Proveedor")["ramo_norm"]
    )
    proveedores = pd.DataFrame(
        {
            "id_proveedor": series(prov, "ID Proveedor"),
            "nombre": series(prov, "Nombre Proveedor"),
            "tipo": series(prov, "Tipo"),
            "ramo": series(prov, "ID Proveedor").map(provider_ramo).fillna(series(prov, "Tipo").map(norm_ramo)),
            "ciudad": series(prov, "Ciudad"),
            "lista_restrictiva": series(prov, "En Lista Restrictiva").map(yes_no),
        }
    )

    vehicle_source = series(sin, "Placa Vehiculo Asegurado")
    veh_source = sin[vehicle_source.notna()].copy()
    vehiculos = (
        pd.DataFrame(
            {
                "id_vehiculo": series(veh_source, "Placa Vehiculo Asegurado"),
                "id_poliza": series(veh_source, "ID Poliza"),
                "placa": series(veh_source, "Placa Vehiculo Asegurado"),
                "marca": "",
                "modelo": "",
                "anio": "",
            }
        )
        .drop_duplicates(["id_vehiculo", "id_poliza"])
        .reset_index(drop=True)
    )

    documentos, doc_summary = build_document_table(docs, sin)
    monto_reclamado = numeric(series(sin, "Monto Reclamado ($)"))
    suma_by_policy = polizas.set_index("id_poliza")["suma_asegurada"]
    provider_restricted = proveedores.set_index("id_proveedor")["lista_restrictiva"]
    suma_asegurada = series(sin, "ID Poliza").map(suma_by_policy).fillna(monto_reclamado.clip(lower=1))
    ratio_suma = (monto_reclamado / numeric(suma_asegurada).replace(0, pd.NA)).fillna(0)
    close_to_edge = numeric(series(sin, "Dias desde Inicio Poliza")).le(7) | numeric(series(sin, "Dias hasta Fin Poliza")).le(7)
    report_delay = numeric(series(sin, "Dias Ocurr Reporte"))
    previous_claims = numeric(series(sin, "N Reclamos Previos Asegurado"))
    restrictive_provider = series(sin, "ID Proveedor").map(provider_restricted).fillna(False).astype(bool)
    robbery = series(sin, "Cobertura").astype(str).str.contains("Robo", case=False, na=False)
    docs_complete = series(sin, "ID Siniestro").map(doc_summary["documentos_completos"]).fillna(False).astype(bool)
    risk_points = (
        close_to_edge.astype(int) * 2
        + report_delay.ge(4).astype(int) * 2
        + previous_claims.ge(3).astype(int) * 2
        + ratio_suma.ge(0.9).astype(int) * 2
        + restrictive_provider.astype(int) * 3
        + robbery.astype(int)
        + (~docs_complete).astype(int) * 2
    )
    etiqueta_fraude = risk_points.ge(6) | (restrictive_provider & (robbery | ratio_suma.ge(0.8)))
    estado = pd.Series("Reserva", index=sin.index)
    estado.loc[~etiqueta_fraude & report_delay.le(2)] = "Liquidado"
    estado.loc[~etiqueta_fraude & report_delay.gt(2)] = "Pago Parcial"
    estado.loc[etiqueta_fraude & restrictive_provider] = "Negativa"
    monto_estimado = (monto_reclamado * 0.9).round(2)
    monto_pagado = pd.Series(0.0, index=sin.index)
    monto_pagado.loc[estado.eq("Liquidado")] = (monto_estimado.loc[estado.eq("Liquidado")] * 0.95).round(2)
    monto_pagado.loc[estado.eq("Pago Parcial")] = (monto_estimado.loc[estado.eq("Pago Parcial")] * 0.45).round(2)

    id_vehiculo = series(sin, "Placa Vehiculo Asegurado").fillna("")
    siniestros = pd.DataFrame(
        {
            "id_siniestro": series(sin, "ID Siniestro"),
            "id_poliza": series(sin, "ID Poliza"),
            "id_asegurado": series(sin, "ID Asegurado"),
            "ramo": series(sin, "Ramo").map(norm_ramo),
            "cobertura": series(sin, "Cobertura"),
            "fecha_ocurrencia": pd.to_datetime(series(sin, "Fecha Ocurrencia")).dt.date.astype(str),
            "fecha_reporte": pd.to_datetime(series(sin, "Fecha Reporte")).dt.date.astype(str),
            "monto_reclamado": monto_reclamado,
            "monto_estimado": monto_estimado,
            "monto_pagado": monto_pagado.round(2),
            "estado": estado,
            "sucursal": series(sin, "Sucursal"),
            "descripcion": series(sin, "Descripcion del Evento"),
            "documentos_completos": docs_complete,
            "id_proveedor": series(sin, "ID Proveedor"),
            "beneficiario": series(sin, "ID Proveedor"),
            "dias_desde_inicio_poliza": series(sin, "Dias desde Inicio Poliza"),
            "dias_desde_fin_poliza": series(sin, "Dias hasta Fin Poliza"),
            "dias_entre_ocurrencia_reporte": series(sin, "Dias Ocurr Reporte"),
            "historial_siniestros_asegurado": series(sin, "N Reclamos Previos Asegurado"),
            "etiqueta_fraude_simulada": etiqueta_fraude.astype(int),
            "id_vehiculo": id_vehiculo,
            "id_conductor": id_vehiculo.map(lambda value: f"COND-{value}" if value else ""),
            "solo_rc": series(sin, "Cobertura").eq("Responsabilidad Civil"),
            "tercero_identificado": True,
            "accidente_madrugada": False,
            "dinamica_imposible": False,
            "relato_ilogico": False,
            "denuncia_horas": 24,
            "procedimiento_codigo": series(sin, "Cobertura").map(slug),
            "factura_numero": series(sin, "Numero Parte Policial").fillna(""),
        }
    )

    provider_metrics = siniestros.groupby("id_proveedor").agg(
        reclamos_asociados=("id_siniestro", "count"),
        monto_promedio_reclamado=("monto_reclamado", "mean"),
        porcentaje_casos_observados=("etiqueta_fraude_simulada", "mean"),
    )
    proveedores = proveedores.merge(provider_metrics, on="id_proveedor", how="left")
    proveedores["reclamos_asociados"] = proveedores["reclamos_asociados"].fillna(0).astype(int)
    proveedores["monto_promedio_reclamado"] = proveedores["monto_promedio_reclamado"].fillna(0).round(2)
    proveedores["porcentaje_casos_observados"] = (proveedores["porcentaje_casos_observados"].fillna(0) * 100).round(2)
    proveedores["antiguedad"] = proveedores["id_proveedor"].map(lambda value: 1 + stable_int(value, "antiguedad", modulo=15))

    return {
        "asegurados": asegurados,
        "polizas": polizas,
        "proveedores": proveedores,
        "vehiculos": vehiculos,
        "siniestros": siniestros,
        "documentos": documentos,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", required=True, dest="zip_path")
    parser.add_argument("--output", default="data/company_synthetic")
    args = parser.parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    tables = build_tables(read_excel_from_zip(Path(args.zip_path)))
    for name, frame in tables.items():
        frame.to_csv(output / f"{name}.csv", index=False, encoding="utf-8")

    print(f"CSV generados en {output}")
    for name, frame in tables.items():
        print(f"{name}: {len(frame)} filas, {len(frame.columns)} columnas")


if __name__ == "__main__":
    main()
