from __future__ import annotations

import html
import os
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from listingturbo.domain import PlatformListing


def export_txt(listing: PlatformListing, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(listing.full_text(), encoding="utf-8")
    return target


def export_html(listing: PlatformListing, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    checklist = "\n".join(f"<li>{html.escape(item)}</li>" for item in listing.checklist)
    tags = " ".join(html.escape(tag) for tag in listing.hashtags)
    image_summary = "\n".join(f"<li>{html.escape(item)}</li>" for item in listing.image_summary)
    document = f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(listing.title)}</title>
<style>
:root {{ color-scheme: light dark; --accent:#2563eb; }}
body {{ font-family: Segoe UI, Arial, sans-serif; max-width: 960px; margin: 32px auto; padding: 0 24px; line-height: 1.55; }}
.card {{ border: 1px solid #9994; border-radius: 16px; padding: 22px; margin: 18px 0; box-shadow: 0 8px 24px #0001; }}
h1 {{ font-size: 1.8rem; }}
h2 {{ color: var(--accent); font-size: 1.15rem; margin-top: 0; }}
pre {{ white-space: pre-wrap; font-family: inherit; }}
.badge {{ display:inline-block; padding:4px 9px; border-radius: 999px; background:#2563eb22; margin:3px; }}
</style>
</head>
<body>
<h1>{html.escape(listing.title)}</h1>
<div class="card"><h2>Inseratstext</h2><pre>{html.escape(listing.description)}</pre></div>
<div class="card"><h2>Preisvorschlag</h2><p>{html.escape(listing.price.as_text())}</p><p>{html.escape(listing.price.explanation)}</p></div>
<div class="card"><h2>Fotoanalyse</h2><ul>{image_summary}</ul></div>
<div class="card"><h2>Checkliste</h2><ul>{checklist}</ul></div>
<div class="card"><h2>Hashtags</h2><p>{tags}</p></div>
</body>
</html>
"""
    target.write_text(document, encoding="utf-8")
    return target


def export_pdf(listing: PlatformListing, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = _wrap_lines(
        [
            f"ListingTurbo Inserat - {listing.platform}",
            "",
            f"Titel: {listing.title}",
            "",
            "Beschreibung:",
            *listing.description.splitlines(),
            "",
            f"Preisvorschlag: {listing.price.as_text()}",
            listing.price.explanation,
            "",
            "Fotoanalyse:",
            *[f"- {item}" for item in listing.image_summary],
            "",
            "Checkliste:",
            *[f"- {item}" for item in listing.checklist],
        ],
        width=92,
    )
    _write_basic_pdf(target, lines)
    return target


def _wrap_lines(lines: list[str], *, width: int) -> list[str]:
    wrapped: list[str] = []
    for line in lines:
        if not line:
            wrapped.append("")
            continue
        current = ""
        for word in line.split():
            candidate = f"{current} {word}".strip()
            if len(candidate) > width and current:
                wrapped.append(current)
                current = word
            else:
                current = candidate
        wrapped.append(current)
    return wrapped


def _write_basic_pdf(path: Path, lines: list[str]) -> None:
    # Minimaler PDF-1.4-Writer ohne externe Runtime. Nicht-lateinische Zeichen
    # werden in eine sichtbare WinAnsi-nahe Repräsentation normalisiert.
    escaped_lines = [_pdf_escape(_pdf_safe_text(line)) for line in lines]
    content_lines = ["BT", "/F1 10 Tf", "50 790 Td", "14 TL"]
    first = True
    for line in escaped_lines:
        if not first:
            content_lines.append("T*")
        content_lines.append(f"({line}) Tj")
        first = False
        if len(content_lines) > 220:
            content_lines.append("ET")
            break
    else:
        content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", errors="strict")

    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream")

    offsets: list[int] = []
    payload = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(payload))
        payload.extend(f"{index} 0 obj\n".encode("ascii"))
        payload.extend(obj)
        payload.extend(b"\nendobj\n")
    xref_start = len(payload)
    payload.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    payload.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        payload.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    payload.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode(
            "ascii"
        )
    )
    path.write_bytes(bytes(payload))


def _latin1_safe(text: str) -> str:
    return _pdf_safe_text(text)


def _pdf_safe_text(text: str) -> str:
    replacements = {
        "€": "EUR",
        "–": "-",
        "—": "-",
        "„": '"',
        "“": '"',
        "”": '"',
        "’": "'",
        "🔥": "[Top]",
        "⭐": "*",
        "✓": "[OK]",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    safe: list[str] = []
    for char in text:
        try:
            char.encode("latin-1")
        except UnicodeEncodeError:
            normalized = unicodedata.normalize("NFKD", char).encode("ascii", errors="ignore").decode("ascii")
            if normalized:
                safe.append(normalized)
            elif unicodedata.category(char).startswith("S"):
                safe.append("*")
        else:
            safe.append(char)
    return "".join(safe)


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _get_font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont | None:
    paths = [
        Path(os.environ.get("SystemRoot", "C:\\Windows")) / "Fonts" / f"{name}.ttf",
        Path(os.environ.get("SystemRoot", "C:\\Windows")) / "Fonts" / f"{name.lower()}.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/System/Library/Fonts/Helvetica.ttc"),
    ]
    for path in paths:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except Exception:
                pass
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def _wrap_text(text: str, draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines


def export_vks_image(listing: PlatformListing, target: Path, image_paths: list[Path] = None) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    
    width = 1200
    height = 800
    
    # Background slate-gray/white gradient representation
    img = Image.new("RGB", (width, height), color=(241, 245, 249))
    draw = ImageDraw.Draw(img)
    
    # shadow
    draw.rectangle([55, 55, width - 45, height - 45], fill=(226, 232, 240))
    
    # main container
    draw.rectangle([50, 50, width - 50, height - 50], fill=(255, 255, 255))
    
    # left accent bar
    draw.rectangle([50, 50, 66, height - 50], fill=(79, 70, 229))
    
    # Fonts
    font_title = _get_font("segoeuib", 42) or _get_font("arialbd", 42) or ImageFont.load_default()
    font_price = _get_font("segoeuib", 64) or _get_font("arialbd", 64) or ImageFont.load_default()
    font_section = _get_font("segoeuib", 24) or _get_font("arialbd", 24) or ImageFont.load_default()
    font_body = _get_font("segoeui", 20) or _get_font("arial", 20) or ImageFont.load_default()
    font_body_bold = _get_font("segoeuib", 20) or _get_font("arialbd", 20) or ImageFont.load_default()
    font_footer = _get_font("segoeui", 16) or _get_font("arial", 16) or ImageFont.load_default()
    
    # Header tag
    draw.text((100, 90), "ANGEBOTSDETAILS", fill=(99, 102, 241), font=font_footer)
    
    # Title (wrapped)
    wrapped_title = _wrap_text(listing.title, draw, font_title, 650)
    y_cursor = 120
    for line in wrapped_title[:2]:
        draw.text((100, y_cursor), line, fill=(15, 23, 42), font=font_title)
        y_cursor += 50
        
    # Tag line / Short Description below title
    if listing.short_description:
        wrapped_sd = _wrap_text(listing.short_description, draw, font_body_bold, 650)
        for sd_line in wrapped_sd[:1]:
            draw.text((100, y_cursor + 5), sd_line, fill=(79, 70, 229), font=font_body_bold)
            y_cursor += 30
            
    # Description / Inseratstext
    y_desc = max(290, y_cursor + 20)
    draw.text((100, y_desc), "BESCHREIBUNG", fill=(71, 85, 105), font=font_section)
    y_desc += 45
    
    desc_lines = listing.description.splitlines()
    description_truncated = False
    for paragraph in desc_lines:
        clean_para = paragraph.strip()
        if not clean_para:
            y_desc += 10
            continue
        wrapped_para = _wrap_text(clean_para, draw, font_body, 680)
        for w_line in wrapped_para:
            if y_desc > height - 120:
                description_truncated = True
                break
            draw.text((100, y_desc), w_line, fill=(51, 65, 85), font=font_body)
            y_desc += 28
        if y_desc > height - 120:
            description_truncated = True
            break
    if description_truncated:
        draw.text((100, height - 120), "... mehr Details online", fill=(79, 70, 229), font=font_body_bold)
            
    # Right Column: Price Box
    price_box_left = 800
    price_box_top = 200
    price_box_right = 1120
    price_box_bottom = 520
    
    draw.rectangle([price_box_left, price_box_top, price_box_right, price_box_bottom], fill=(241, 245, 249), outline=(226, 232, 240), width=2)
    draw.rectangle([price_box_left, price_box_top, price_box_left + 8, price_box_bottom], fill=(16, 185, 129))
    
    draw.text((price_box_left + 30, price_box_top + 30), "UNSER PREISVORSCHLAG", fill=(71, 85, 105), font=font_footer)
    
    rec_price = f"{listing.price.recommended} €"
    draw.text((price_box_left + 30, price_box_top + 70), rec_price, fill=(16, 185, 129), font=font_price)
    
    range_text = f"Verhandlungsbasis\n(VB {listing.price.low} - {listing.price.high} €)"
    draw.text((price_box_left + 30, price_box_top + 175), range_text, fill=(71, 85, 105), font=font_body)
    
    conf_text = f"Status: {listing.price.confidence}"
    draw.text((price_box_left + 30, price_box_top + 260), conf_text, fill=(51, 65, 85), font=font_body_bold)
    
    # Product Image Box
    draw.text((800, 535), "PRODUKTBILD", fill=(100, 116, 139), font=font_footer)
    draw.rectangle([800, 560, 940, 700], fill=(255, 255, 255), outline=(203, 213, 225), width=2)
    
    img_drawn = False
    if image_paths and len(image_paths) > 0:
        first_img_path = Path(image_paths[0])
        if first_img_path.exists():
            try:
                with Image.open(first_img_path) as thumb_img:
                    thumb_img = thumb_img.convert("RGB")
                    thumb_img.thumbnail((136, 136))
                    t_w, t_h = thumb_img.size
                    x_off = 800 + 2 + (136 - t_w) // 2
                    y_off = 560 + 2 + (136 - t_h) // 2
                    img.paste(thumb_img, (x_off, y_off))
                    img_drawn = True
            except Exception:
                pass
                
    if not img_drawn:
        draw.text((820, 610), "Kein Foto\nvorhanden", fill=(148, 163, 184), font=font_footer)

    # Scanner dummy
    draw.text((960, 535), "QR-SCAN-CODE", fill=(100, 116, 139), font=font_footer)
    qr_top = 560
    qr_left = 960
    qr_size = 140
    draw.rectangle([qr_left, qr_top, qr_left + qr_size, qr_top + qr_size], fill=(255, 255, 255), outline=(203, 213, 225), width=2)
    for r in range(4):
        for c in range(4):
            if (r + c) % 2 == 0 or (r == 0 and c == 0) or (r == 3 and c == 3):
                draw.rectangle([qr_left + 15 + c*30, qr_top + 15 + r*30, qr_left + 35 + c*30, qr_top + 35 + r*30], fill=(30, 41, 59))
    
    # Footer
    draw.line([100, height - 90, width - 100, height - 90], fill=(226, 232, 240), width=2)
    footer_text = "Privatverkauf. Alle Angaben ohne Gewähr. Die Ware wird unter Ausschluss jeglicher Gewährleistung verkauft."
    draw.text((100, height - 75), footer_text, fill=(148, 163, 184), font=font_footer)
    
    img.save(target, format="PNG")
    return target
