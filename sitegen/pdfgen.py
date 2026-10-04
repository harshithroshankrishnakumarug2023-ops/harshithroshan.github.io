"""Create clearly labelled placeholder PDFs.

The site ships with two placeholder files so that every link works from day one
(CV download and research proposal). They contain no research content — they
simply say what should replace them.

Usage:
    python -m sitegen.pdfgen "public/documents/cv/harshith-roshan-cv.pdf" "Curriculum vitae"

This writes the file into the repository; ``build.py`` never calls it, so your
own documents can never be overwritten.
"""

from __future__ import annotations

import sys
from pathlib import Path

LETTER_WIDTH, LETTER_HEIGHT = 612, 792
LEFT, TOP = 72, 700
LINE_HEIGHT = 22


def _escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def build_pdf(lines: list[str], path: Path) -> None:
    """Write a single-page PDF containing `lines` (already formatted text)."""
    content_lines = ["BT", "/F1 16 Tf", f"1 0 0 1 {LEFT} {TOP} Tm"]
    for index, line in enumerate(lines):
        if index == 0:
            content_lines.append(f"({_escape(line)}) Tj")
        else:
            content_lines.append(f"0 {-LINE_HEIGHT} Td")
            content_lines.append(f"({_escape(line)}) Tj")
    content_lines += ["ET"]
    stream = "\n".join(content_lines).encode("latin-1", "replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
        % (LETTER_WIDTH, LETTER_HEIGHT),
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(out))


def placeholder(path: Path, title: str, note: str) -> None:
    lines = [
        "PLACEHOLDER DOCUMENT",
        "",
        title,
        "",
        note,
        "",
        "This file contains no academic content. Replace it with your",
        "own PDF and keep the same filename, or update the path in",
        "content/documents.json and rebuild the site.",
    ]
    build_pdf(lines, path)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    target = Path(argv[0])
    title = argv[1] if len(argv) > 1 else target.stem
    note = argv[2] if len(argv) > 2 else ""
    placeholder(target, title, note)
    print(f"Wrote placeholder PDF: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))