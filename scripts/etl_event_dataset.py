from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path

import pandas as pd


def yes_no(value) -> bool:
    return str(value).strip().lower() in {"si", "sí", "s", "yes", "true", "1"}


def norm_ramo(value: str) -> str:
    text = str(value).strip()
    return {"Vehículos": "Vehiculos"}.get(text, text)


def slug(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", str(value).upper()).strip("_")


def read_excel_from_zip(zip_path: Path) -> dict[str, pd.DataFrame]:
    with zipfile.ZipFile(zip_path) as zf:
        excel_name = [n for n in zf.namelist() if n.lower().endswith(".xlsx")][0]
        return {
            "siniestros": pd.read_excel(zf.open(excel_name), sheet_name="1_Siniestros"),
            "polizas": pd.read_excel(zf.open(excel_name), sheet_name="2_Polizas"),
            "asegurados": pd.read_excel(zf.open(excel_name), sheet_name="3_Asegurados"),
            "proveedores": pd.read_excel(zf.open(excel_name), sheet_name="4_Proveedores"),
            "documentos": pd.read_excel(zf.open(excel_name), sheet_name="5_Documentos"),
        }


def build_tables(source: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    sin = source["siniestros"].copy()
    pol = source["polizas"].copy()
    ase = source["asegurados"].copy()
    prov = source["proveedores"].copy()
    docs = source["documentos"].copy()

    asegurados = pd.DataFrame(
        {
            "id_asegurado": ase["ID Asegurado"],
            "ciudad": ase["Ciudad"],
            "lista_restrictiva": False,
            "nombres_asegurado": ase.get("Nombres Asegurado", ""),
            "segmento": ase.get("Segmento", ""),
            "perfil_riesgo_historico": ase.get("Perfil Riesgo Histórico", ""),
        }
    )

    polizas = pd.DataFrame(
        {
            "id_poliza": pol["ID Póliza"],
            "id_asegurado": pol["ID Asegurado"],
            "ramo": pol["Ramo"].map(norm_ramo),
            "fecha_inicio": pd.to_datetime(pol["Fecha Inicio"]).dt.date.astype(str),
            "fecha_fin": pd.to_datetime(pol["Fecha Fin"]).dt.date.astype(str),
            "suma_asegurada": pol["Suma Asegurada ($)"],
        }
    ).merge(asegurados[["id_asegurado", "ciudad"]], on="id_asegurado", how="left")

    provider_ramo = (
        sin.assign(ramo_norm=sin["Ramo"].map(norm_ramo))
        .groupby(["ID Proveedor", "ramo_norm"])
        .size()
        .reset_index(name="n")
        .sort_values(["ID Proveedor", "n"], ascending=[True, False])
        .drop_duplicates("ID Proveedor")
        .set_index("ID Proveedor")["ramo_norm"]
    )

    proveedores = pd.DataFrame(
        {
            "id_proveedor": prov["ID Proveedor"],
            "nombre": prov["Nombre Proveedor"],
            "tipo": prov["Tipo"],
            "ramo": prov["ID Proveedor"].map(provider_ramo).fillna(prov["Tipo"].map(norm_ramo)),
            "ciudad": prov["Ciudad"],
            "lista_restrictiva": prov["En Lista Restrictiva"].map(yes_no),
        }
    )

    veh_source = sin[sin["Placa Vehículo Asegurado"].notna()].copy()
    vehiculos = (
        pd.DataFrame(
            {
                "id_vehiculo": veh_source["Placa Vehículo Asegurado"],
                "id_poliza": veh_source["ID Póliza"],
                "placa": veh_source["Placa Vehículo Asegurado"],
                "marca": "",
                "modelo": "",
                "anio": "",
            }
        )
        .drop_duplicates(["id_vehiculo", "id_poliza"])
        .reset_index(drop=True)
    )

    id_vehiculo = sin["Placa Vehículo Asegurado"].fillna("")
    cobertura_slug = sin["Cobertura"].map(slug)

    siniestros = pd.DataFrame(
        {
            "id_siniestro": sin["ID Siniestro"],
            "id_poliza": sin["ID Póliza"],
            "id_asegurado": sin["ID Asegurado"],
            "ramo": sin["Ramo"].map(norm_ramo),
            "cobertura": sin["Cobertura"],
            "fecha_ocurrencia": pd.to_datetime(sin["Fecha Ocurrencia"]).dt.date.astype(str),
            "fecha_reporte": pd.to_datetime(sin["Fecha Reporte"]).dt.date.astype(str),
            "monto_reclamado": sin["Monto Reclamado ($)"],
            "sucursal": sin["Sucursal"],
            "descripcion": sin["Descripción del Evento"],
            "id_proveedor": sin["ID Proveedor"],
            "beneficiario": sin["ID Proveedor"],
            "dias_desde_inicio_poliza": sin["Días desde Inicio Póliza"],
            "dias_desde_fin_poliza": sin["Días hasta Fin Póliza"],
            "dias_entre_ocurrencia_reporte": sin["Días Ocurr→Reporte"],
            "historial_siniestros_asegurado": sin["N° Reclamos Previos Asegurado"],
            "id_vehiculo": id_vehiculo,
            "id_conductor": id_vehiculo.map(lambda x: f"COND-{x}" if x else ""),
            "solo_rc": sin["Cobertura"].eq("Responsabilidad Civil"),
            "tercero_identificado": True,
            "accidente_madrugada": False,
            "dinamica_imposible": False,
            "relato_ilogico": False,
            "denuncia_horas": 24,
            "procedimiento_codigo": cobertura_slug,
            "factura_numero": sin["Número Parte Policial"].fillna(""),
        }
    )

    documentos = pd.DataFrame(
        {
            "id_documento": docs["ID Documento"],
            "id_siniestro": docs["ID Siniestro"],
            "tipo_documento": docs["Tipo Documento"],
            "entregado": True,
            "legible": True,
            "inconsistencia_detectada": False,
            "adulteracion_confirmada": False,
            "archivo_pdf": docs["Nombre Archivo PDF"].fillna(""),
        }
    )

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