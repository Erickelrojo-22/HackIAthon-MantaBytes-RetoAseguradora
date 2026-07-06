from __future__ import annotations

import csv
import html
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable
from xml.etree.ElementTree import iterparse
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs"
DATA_DIR = ROOT / "data"
JUDICIAL_ODS = ROOT / "source_downloads" / "cj_datoscausas_2026abril.ods"

SOURCE_EUMED = "Eumed/OEL 2017: Analisis de los fraudes en el sistema asegurador en el Ecuador"
SOURCE_FORBES_RAMOS = "Forbes Ecuador 2026, con datos Fedeseg: seguros con mayor prima neta 2025"
SOURCE_FORBES_ASEG = "Forbes Ecuador 2026, con datos SCVS: aseguradoras con mayor prima neta 2025"
SOURCE_CAMSEG = "CAMSEG: estadisticas sectoriales, abril 2026"
SOURCE_CJ = "Datos Abiertos Ecuador / Consejo de la Judicatura: causas judiciales, corte abril 2026"


FRAUD_VULNERABLE_RAMOS = [
    ("Vida", 36),
    ("Vehiculos", 27),
    ("Incendio", 18),
    ("Robo", 9),
    ("Transporte", 9),
]

FRAUD_DETECTION_METHODS = [
    ("Quejas", 36),
    ("Informantes internos", 27),
    ("Informantes externos", 27),
    ("Casualidad", 9),
]

MARKET_PREMIUMS_2025 = [
    ("Vida colectiva", 735.9),
    ("Vehiculos", 430.7),
    ("Incendios", 296.5),
    ("Asistencia medica", 154.2),
    ("Ramos tecnicos", 102.9),
    ("Accidentes personales", 90.8),
    ("Responsabilidad civil", 87.0),
    ("Fianzas", 84.7),
    ("Transporte", 80.7),
    ("Multirriesgo", 67.6),
]

SECTOR_APRIL_2026 = [
    ("Primas netas emitidas", 802.8),
    ("Patrimonio", 690.6),
    ("Siniestros pagados", 296.1),
    ("Resultados tecnicos", 78.2),
]

TOP_INSURERS_2025 = [
    ("Equisuiza Seguros", 318.2),
    ("Seguros Pichincha", 271.0),
    ("Chubb Seguros Ecuador", 228.9),
    ("Latina Seguros", 175.2),
    ("Hispana de Seguros", 167.0),
    ("Aseguradora del Sur", 148.5),
    ("AIG Metropolitana", 141.0),
    ("Zurich Seguros Ecuador", 124.3),
    ("Sweaden", 111.6),
    ("Mapfre Ecuador", 79.8),
]

FALLBACK_JUDICIAL_BY_YEAR = [
    ("2016", 6107),
    ("2017", 2977),
    ("2018", 2902),
    ("2019", 3220),
    ("2020", 2339),
    ("2021", 2978),
    ("2022", 2493),
    ("2023", 2259),
    ("2024", 1919),
    ("2025", 1788),
    ("2026", 609),
]

FALLBACK_JUDICIAL_BY_PROVINCE = [
    ("Pichincha", 5753),
    ("Guayas", 5421),
    ("Azuay", 2041),
    ("El Oro", 1932),
    ("Manabi", 1793),
    ("Loja", 1354),
    ("Chimborazo", 1268),
    ("Canar", 1228),
    ("Los Rios", 1175),
    ("Tungurahua", 983),
]


PALETTE = [
    "#0f766e",
    "#2563eb",
    "#dc2626",
    "#ca8a04",
    "#7c3aed",
    "#059669",
    "#ea580c",
    "#0891b2",
    "#be185d",
    "#4b5563",
]


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def fmt_number(value: float, unit: str) -> str:
    if unit == "%":
        return f"{value:.0f}%"
    if unit == "USD M":
        return f"${value:,.1f}M"
    return f"{value:,.0f}"


def clean_label(value: str) -> str:
    replacements = {
        "CAÑAR": "Canar",
        "MANABI": "Manabi",
        "LOS RIOS": "Los Rios",
        "AZUAY": "Azuay",
        "PICHINCHA": "Pichincha",
        "GUAYAS": "Guayas",
        "EL ORO": "El Oro",
        "LOJA": "Loja",
        "CHIMBORAZO": "Chimborazo",
        "TUNGURAHUA": "Tungurahua",
    }
    return replacements.get(value.upper(), value.title())


def wrap_text(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        if len(candidate) > max_chars and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines[:2]


def svg_text(
    x: float,
    y: float,
    text: str,
    size: int = 16,
    weight: int = 400,
    fill: str = "#111827",
    anchor: str = "start",
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="Inter, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}" '
        f'text-anchor="{anchor}">{esc(text)}</text>'
    )


def bar_chart(
    path: Path,
    title: str,
    subtitle: str,
    data: list[tuple[str, float]],
    unit: str,
    source: str,
    *,
    width: int = 1200,
    height: int = 760,
) -> None:
    left = 310
    right = 130
    top = 150
    bottom = 90
    plot_width = width - left - right
    row_gap = 18
    bar_h = max(26, int((height - top - bottom - row_gap * (len(data) - 1)) / len(data)))
    max_value = max(value for _, value in data) or 1
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        svg_text(48, 62, title, 34, 800),
        svg_text(48, 96, subtitle, 17, 400, "#475569"),
        f'<line x1="{left}" y1="{top - 18}" x2="{width - right}" y2="{top - 18}" stroke="#cbd5e1" stroke-width="1"/>',
    ]
    for idx, (label, value) in enumerate(data):
        y = top + idx * (bar_h + row_gap)
        bar_w = max(2, (value / max_value) * plot_width)
        color = PALETTE[idx % len(PALETTE)]
        for line_no, line in enumerate(wrap_text(label, 28)):
            parts.append(svg_text(48, y + 20 + line_no * 18, line, 16, 600, "#334155"))
        parts.append(
            f'<rect x="{left}" y="{y}" width="{plot_width}" height="{bar_h}" rx="6" fill="#e2e8f0"/>'
        )
        parts.append(
            f'<rect x="{left}" y="{y}" width="{bar_w:.1f}" height="{bar_h}" rx="6" fill="{color}"/>'
        )
        value_x = min(left + bar_w + 14, width - right + 92)
        parts.append(svg_text(value_x, y + bar_h / 2 + 6, fmt_number(value, unit), 17, 800, "#0f172a"))
    parts.extend(
        [
            svg_text(48, height - 42, f"Fuente: {source}", 13, 400, "#64748b"),
            "</svg>",
        ]
    )
    path.write_text("\n".join(parts), encoding="utf-8")


def line_chart(
    path: Path,
    title: str,
    subtitle: str,
    data: list[tuple[str, float]],
    unit: str,
    source: str,
    *,
    width: int = 1200,
    height: int = 700,
) -> None:
    left = 90
    right = 60
    top = 150
    bottom = 110
    plot_w = width - left - right
    plot_h = height - top - bottom
    max_value = max(value for _, value in data) or 1
    points = []
    denom = max(len(data) - 1, 1)
    for idx, (_, value) in enumerate(data):
        x = left + (idx / denom) * plot_w
        y = top + plot_h - (value / max_value) * plot_h
        points.append((x, y))
    polygon = " ".join([f"{left},{top + plot_h}", *[f"{x:.1f},{y:.1f}" for x, y in points], f"{left + plot_w},{top + plot_h}"])
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        svg_text(48, 62, title, 34, 800),
        svg_text(48, 96, subtitle, 17, 400, "#475569"),
    ]
    for step in range(5):
        value = max_value * step / 4
        y = top + plot_h - (step / 4) * plot_h
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="#e2e8f0"/>')
        parts.append(svg_text(left - 18, y + 5, fmt_number(value, unit), 13, 500, "#64748b", "end"))
    parts.append(f'<polygon points="{polygon}" fill="#bfdbfe" opacity="0.65"/>')
    parts.append(f'<polyline points="{polyline}" fill="none" stroke="#2563eb" stroke-width="5" stroke-linejoin="round"/>')
    for (label, value), (x, y) in zip(data, points):
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="#dc2626" stroke="#ffffff" stroke-width="3"/>')
        parts.append(svg_text(x, top + plot_h + 34, label, 14, 700, "#334155", "middle"))
        if label in {"2016", "2020", "2026"}:
            parts.append(svg_text(x, y - 16, fmt_number(value, unit), 13, 800, "#0f172a", "middle"))
    parts.extend(
        [
            svg_text(48, height - 42, f"Fuente: {source}", 13, 400, "#64748b"),
            "</svg>",
        ]
    )
    path.write_text("\n".join(parts), encoding="utf-8")


def parse_judicial_context() -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
    if not JUDICIAL_ODS.exists():
        return FALLBACK_JUDICIAL_BY_YEAR, FALLBACK_JUDICIAL_BY_PROVINCE

    table_ns = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
    text_ns = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
    keywords = ("ESTAFA", "DEFRAUD", "FRAUDE", "FALSIFIC")
    header: list[str] | None = None
    by_year: dict[str, int] = defaultdict(int)
    by_province: Counter[str] = Counter()

    with ZipFile(JUDICIAL_ODS) as archive, archive.open("content.xml") as content:
        for _, elem in iterparse(content, events=("end",)):
            if elem.tag != table_ns + "table-row":
                continue
            values: list[str] = []
            for cell in elem.findall(table_ns + "table-cell"):
                remaining = max(12 - len(values), 0)
                if remaining == 0:
                    break
                repeat = int(cell.attrib.get(table_ns + "number-columns-repeated", "1"))
                texts = [p.text for p in cell.iter(text_ns + "p") if p.text]
                value = " ".join(texts).strip()
                values.extend([value] * min(repeat, remaining))
            if any(values):
                if header is None:
                    header = values[:12]
                else:
                    record = dict(zip(header, values[:12]))
                    delito = record.get("Delito", "").upper()
                    if any(keyword in delito for keyword in keywords):
                        try:
                            ingreso = int(float(record.get("Ingreso") or 0))
                        except ValueError:
                            ingreso = 0
                        periodo = record.get("Periodo", "")
                        year = periodo.split("/")[-1] if "/" in periodo else periodo[-4:]
                        if year.isdigit():
                            by_year[year] += ingreso
                        province = clean_label(record.get("Provincia", "N/D"))
                        by_province[province] += ingreso
            elem.clear()

    return (
        [(year, by_year[year]) for year in sorted(by_year)],
        by_province.most_common(10),
    )


def export_csv(judicial_by_year: Iterable[tuple[str, float]], judicial_by_province: Iterable[tuple[str, float]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output = DATA_DIR / "datos_graficos_fraude_ecuador.csv"
    rows: list[tuple[str, str, str, float, str]] = []

    for label, value in FRAUD_VULNERABLE_RAMOS:
        rows.append(("ramos_vulnerables_fraude", label, "%", value, SOURCE_EUMED))
    for label, value in FRAUD_DETECTION_METHODS:
        rows.append(("medios_deteccion_fraude", label, "%", value, SOURCE_EUMED))
    for label, value in MARKET_PREMIUMS_2025:
        rows.append(("primas_por_ramo_2025", label, "USD millones", value, SOURCE_FORBES_RAMOS))
    for label, value in SECTOR_APRIL_2026:
        rows.append(("indicadores_sector_abril_2026", label, "USD millones", value, SOURCE_CAMSEG))
    for label, value in TOP_INSURERS_2025:
        rows.append(("top_aseguradoras_2025", label, "USD millones", value, SOURCE_FORBES_ASEG))
    for label, value in judicial_by_year:
        rows.append(("causas_judiciales_contexto_por_anio", label, "causas ingresadas", value, SOURCE_CJ))
    for label, value in judicial_by_province:
        rows.append(("causas_judiciales_contexto_por_provincia", label, "causas ingresadas", value, SOURCE_CJ))

    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["serie", "categoria", "unidad", "valor", "fuente"])
        writer.writerows(rows)


def write_index(files: list[Path]) -> None:
    cards = "\n".join(
        f'<section><h2>{esc(file.stem.replace("_", " ").title())}</h2><img src="outputs/{esc(file.name)}" alt="{esc(file.stem)}"></section>'
        for file in files
    )
    page = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Graficos FraudIA - Ecuador</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; background: #eef2f7; color: #111827; }}
    main {{ width: min(1180px, calc(100% - 32px)); margin: 32px auto; }}
    h1 {{ margin: 0 0 8px; font-size: 32px; }}
    p {{ margin: 0 0 24px; color: #475569; }}
    section {{ margin: 24px 0; padding: 16px; background: white; border: 1px solid #dbe3ef; border-radius: 8px; }}
    h2 {{ font-size: 18px; margin: 0 0 12px; }}
    img {{ width: 100%; height: auto; display: block; }}
  </style>
</head>
<body>
  <main>
    <h1>Graficos de contexto para FraudIA Claims</h1>
    <p>Usar como apoyo visual. Las cifras judiciales son contexto de estafa/fraude/falsificacion, no fraude de seguros confirmado.</p>
    {cards}
  </main>
</body>
</html>
"""
    (ROOT / "index.html").write_text(page, encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    judicial_by_year, judicial_by_province = parse_judicial_context()
    export_csv(judicial_by_year, judicial_by_province)

    charts = [
        OUTPUT_DIR / "01_ramos_vulnerables_fraude_ecuador.svg",
        OUTPUT_DIR / "02_medios_deteccion_fraude_ecuador.svg",
        OUTPUT_DIR / "03_primas_por_ramo_2025_ecuador.svg",
        OUTPUT_DIR / "04_indicadores_sector_abril_2026.svg",
        OUTPUT_DIR / "05_top_aseguradoras_2025_ecuador.svg",
        OUTPUT_DIR / "06_causas_judiciales_contexto_anual.svg",
        OUTPUT_DIR / "07_causas_judiciales_contexto_provincia.svg",
    ]

    bar_chart(
        charts[0],
        "Ramos percibidos como mas vulnerables al fraude",
        "Encuesta a aseguradoras de Guayaquil; porcentaje de menciones por ramo.",
        FRAUD_VULNERABLE_RAMOS,
        "%",
        SOURCE_EUMED,
    )
    bar_chart(
        charts[1],
        "Medios de identificacion de fraude reportados",
        "Senales humanas y hallazgos casuales dominan la deteccion tradicional.",
        FRAUD_DETECTION_METHODS,
        "%",
        SOURCE_EUMED,
    )
    bar_chart(
        charts[2],
        "Primas netas emitidas por ramo en Ecuador, 2025",
        "Los ramos con mayor volumen concentran mayor presion operativa de revision.",
        MARKET_PREMIUMS_2025,
        "USD M",
        SOURCE_FORBES_RAMOS,
    )
    bar_chart(
        charts[3],
        "Indicadores del sector asegurador ecuatoriano",
        "Cifras publicadas por CAMSEG para abril de 2026.",
        SECTOR_APRIL_2026,
        "USD M",
        SOURCE_CAMSEG,
    )
    bar_chart(
        charts[4],
        "Top 10 aseguradoras por prima neta emitida, 2025",
        "Tamano relativo del mercado donde una herramienta antifraude escala operativamente.",
        TOP_INSURERS_2025,
        "USD M",
        SOURCE_FORBES_ASEG,
    )
    line_chart(
        charts[5],
        "Contexto judicial: estafa, fraude, defraudacion y falsificacion",
        "Causas ingresadas por anio. No equivale a fraude de seguros confirmado.",
        judicial_by_year,
        "",
        SOURCE_CJ,
    )
    bar_chart(
        charts[6],
        "Contexto judicial por provincia",
        "Top 10 provincias por causas ingresadas asociadas a estafa/fraude/falsificacion.",
        judicial_by_province,
        "",
        SOURCE_CJ,
    )
    write_index(charts)
    print(f"Graficos generados en {OUTPUT_DIR}")
    print(f"CSV consolidado en {DATA_DIR / 'datos_graficos_fraude_ecuador.csv'}")


if __name__ == "__main__":
    main()
