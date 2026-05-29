from __future__ import annotations

import re
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "presentation" / "pitch_ejecutivo.md"
TARGET = ROOT / "presentation" / "pitch_ejecutivo.pdf"

PAGE_WIDTH = 612
PAGE_HEIGHT = 792
LEFT = 54
TOP = 740
BOTTOM = 54
LINE_HEIGHT = 14


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _clean_markdown(line: str) -> tuple[str, int, bool]:
    stripped = line.strip()
    if not stripped:
        return "", 11, False
    if stripped.startswith("# "):
        return stripped[2:].strip(), 20, True
    if stripped.startswith("## "):
        return stripped[3:].strip(), 15, True
    stripped = re.sub(r"`([^`]+)`", r"\1", stripped)
    stripped = stripped.replace("**", "")
    return stripped, 11, False


def _wrap_line(text: str, size: int) -> list[str]:
    width = 72 if size <= 11 else 58
    if text.startswith(("- ", "* ")):
        body = text[2:].strip()
        wrapped = textwrap.wrap(body, width=width - 4) or [""]
        return [f"- {wrapped[0]}", *[f"  {line}" for line in wrapped[1:]]]
    numbered = re.match(r"^(\d+)\.\s+(.*)$", text)
    if numbered:
        prefix = f"{numbered.group(1)}. "
        wrapped = textwrap.wrap(numbered.group(2), width=width - len(prefix)) or [""]
        return [f"{prefix}{wrapped[0]}", *[f"{' ' * len(prefix)}{line}" for line in wrapped[1:]]]
    return textwrap.wrap(text, width=width) or [text]


def _markdown_to_pages(source: Path) -> list[list[tuple[str, int, bool]]]:
    pages: list[list[tuple[str, int, bool]]] = [[]]
    y = TOP
    for raw_line in source.read_text(encoding="utf-8").splitlines():
        text, size, bold = _clean_markdown(raw_line)
        if not text:
            y -= LINE_HEIGHT
            continue
        lines = _wrap_line(text, size)
        block_height = len(lines) * LINE_HEIGHT + (8 if bold else 2)
        if y - block_height < BOTTOM:
            pages.append([])
            y = TOP
        for index, line in enumerate(lines):
            pages[-1].append((line, size if index == 0 else min(size, 11), bold and index == 0))
            y -= LINE_HEIGHT
        y -= 8 if bold else 2
    return pages


def _page_stream(lines: list[tuple[str, int, bool]], page_number: int, total_pages: int) -> str:
    commands = ["BT"]
    y = TOP
    for text, size, bold in lines:
        font = "F2" if bold else "F1"
        commands.append(f"/{font} {size} Tf")
        commands.append(f"1 0 0 1 {LEFT} {y} Tm")
        commands.append(f"({_escape_pdf_text(text)}) Tj")
        y -= LINE_HEIGHT if size <= 11 else LINE_HEIGHT + 4
    commands.append("/F1 9 Tf")
    commands.append(f"1 0 0 1 {LEFT} 32 Tm")
    commands.append(f"(FraudIA Claims - Pitch ejecutivo | Pagina {page_number} de {total_pages}) Tj")
    commands.append("ET")
    return "\n".join(commands)


def _build_pdf(pages: list[list[tuple[str, int, bool]]]) -> bytes:
    objects: list[bytes] = []
    total_pages = len(pages)
    catalog_id = 1
    pages_id = 2
    font_regular_id = 3
    font_bold_id = 4
    first_page_id = 5
    page_ids = [first_page_id + i * 2 for i in range(total_pages)]
    content_ids = [first_page_id + i * 2 + 1 for i in range(total_pages)]

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {total_pages} >>".encode("latin-1"))
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")

    for index, page in enumerate(pages):
        page_id = page_ids[index]
        content_id = content_ids[index]
        page_object = (
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 {font_regular_id} 0 R /F2 {font_bold_id} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        )
        stream = _page_stream(page, index + 1, total_pages).encode("cp1252", errors="replace")
        content_object = b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream"
        assert page_id == len(objects) + 1
        objects.append(page_object.encode("latin-1"))
        assert content_id == len(objects) + 1
        objects.append(content_object)

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for obj_id, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{obj_id} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")

    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)


def main() -> int:
    pages = _markdown_to_pages(SOURCE)
    TARGET.write_bytes(_build_pdf(pages))
    print(f"PDF generado: {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
