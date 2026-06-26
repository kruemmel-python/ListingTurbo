from __future__ import annotations

import math
import logging
import struct
from pathlib import Path
from statistics import mean, pstdev

from listingturbo.domain import ImageMetrics
from listingturbo.native.backend import analyze_rgb_bytes

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps, UnidentifiedImageError
except Exception as exc:  # pragma: no cover - exercised only when Pillow is absent
    logger.warning("Pillow ist nicht verfügbar; Bildanalyse läuft im eingeschränkten Modus.", exc_info=exc)
    Image = None  # type: ignore[assignment]
    ImageEnhance = None  # type: ignore[assignment]
    ImageFilter = None  # type: ignore[assignment]
    ImageOps = None  # type: ignore[assignment]

    class UnidentifiedImageError(Exception):
        pass


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def inspect_images(paths: list[Path]) -> list[ImageMetrics]:
    return [inspect_image(path) for path in paths]


def inspect_image(path: Path) -> ImageMetrics:
    normalized = Path(path)
    warnings: list[str] = []
    suggestions: list[str] = []

    if not normalized.exists():
        return ImageMetrics(
            path=normalized,
            file_type="unbekannt",
            width=None,
            height=None,
            megapixels=None,
            brightness=None,
            contrast=None,
            sharpness=None,
            orientation="unbekannt",
            has_exif=False,
            warnings=("Datei existiert nicht.",),
            suggestions=("Bild erneut auswählen.",),
        )

    if normalized.suffix.lower() not in SUPPORTED_EXTENSIONS:
        warnings.append(f"Ungewöhnliches Bildformat: {normalized.suffix or 'ohne Endung'}")
        suggestions.append("Für Marktplätze sind JPG oder PNG meist am zuverlässigsten.")

    if Image is None:
        width, height, file_type = _read_dimensions_without_pillow(normalized)
        if width is None or height is None:
            warnings.append("Bilddaten konnten ohne Pillow nicht vollständig gelesen werden.")
            suggestions.append("requirements.txt installieren, damit Fotoanalyse und Verbesserung aktiv sind.")
        return _metrics_from_known_values(
            path=normalized,
            file_type=file_type,
            width=width,
            height=height,
            warnings=warnings,
            suggestions=suggestions,
            has_exif=False,
            brightness=None,
            contrast=None,
            sharpness=None,
        )

    try:
        with Image.open(normalized) as image:
            file_type = (image.format or normalized.suffix.lstrip(".") or "unbekannt").upper()
            has_exif = bool(getattr(image, "getexif", lambda: {})())
            corrected = ImageOps.exif_transpose(image)
            width, height = corrected.size
            brightness, contrast, sharpness, native_note = _probe_quality(corrected)
            if native_note:
                suggestions.append(native_note)
    except (OSError, UnidentifiedImageError) as exc:
        warnings.append(f"Bild konnte nicht gelesen werden: {exc}")
        suggestions.append("Datei prüfen oder als JPG/PNG erneut exportieren.")
        return ImageMetrics(
            path=normalized,
            file_type="unlesbar",
            width=None,
            height=None,
            megapixels=None,
            brightness=None,
            contrast=None,
            sharpness=None,
            orientation="unbekannt",
            has_exif=False,
            warnings=tuple(warnings),
            suggestions=tuple(suggestions),
        )

    return _metrics_from_known_values(
        path=normalized,
        file_type=file_type,
        width=width,
        height=height,
        warnings=warnings,
        suggestions=suggestions,
        has_exif=has_exif,
        brightness=brightness,
        contrast=contrast,
        sharpness=sharpness,
    )


def _probe_quality(image: object) -> tuple[float | None, float | None, float | None, str]:
    rgb_probe = image.convert("RGB")
    rgb_probe.thumbnail((512, 512))
    width, height = rgb_probe.size
    stride = width * 3
    native = analyze_rgb_bytes(rgb_probe.tobytes(), width, height, stride)
    if native is not None and native.available:
        return native.brightness, native.contrast, native.sharpness, f"Native Analyse aktiv: {native.backend_name}."

    gray_probe = rgb_probe.convert("L")
    pixels = list(gray_probe.getdata())
    brightness = mean(pixels) if pixels else None
    contrast = pstdev(pixels) if len(pixels) > 1 else None
    sharpness = _estimate_sharpness(gray_probe)
    return brightness, contrast, sharpness, ""


def _metrics_from_known_values(
    *,
    path: Path,
    file_type: str,
    width: int | None,
    height: int | None,
    warnings: list[str],
    suggestions: list[str],
    has_exif: bool,
    brightness: float | None,
    contrast: float | None,
    sharpness: float | None,
) -> ImageMetrics:
    megapixels = round((width * height) / 1_000_000, 2) if width and height else None
    orientation = _orientation(width, height)

    if width and height:
        if width < 1000 or height < 1000:
            warnings.append("Auflösung ist niedrig; Käufer zoomen Details oft stark hinein.")
            suggestions.append("Ein helleres Detailfoto mit mindestens 1000 px Kantenlänge ergänzen.")
        if megapixels is not None and megapixels > 16:
            suggestions.append("Für Uploads kann eine optimierte 2000-px-Version schneller laden.")

    if brightness is not None:
        if brightness < 72:
            warnings.append("Foto wirkt deutlich zu dunkel.")
            suggestions.append("Aufhellen oder bei Tageslicht neu fotografieren.")
        elif brightness > 220:
            warnings.append("Foto wirkt überbelichtet.")
            suggestions.append("Belichtung reduzieren, damit Kratzer und Details sichtbar bleiben.")

    if contrast is not None and contrast < 28:
        warnings.append("Foto hat wenig Kontrast; der Artikel hebt sich schwach vom Hintergrund ab.")
        suggestions.append("Neutralen Hintergrund wählen oder Kontrastverbesserung nutzen.")

    if sharpness is not None and sharpness < 9:
        warnings.append("Foto wirkt unscharf oder verwackelt.")
        suggestions.append("Neues Detailfoto mit ruhiger Hand oder Auflage machen.")

    if has_exif:
        suggestions.append("EXIF-Metadaten beim Export entfernen, um Standort-/Geräteinfos zu vermeiden.")

    return ImageMetrics(
        path=path,
        file_type=file_type,
        width=width,
        height=height,
        megapixels=megapixels,
        brightness=round(brightness, 1) if brightness is not None else None,
        contrast=round(contrast, 1) if contrast is not None else None,
        sharpness=round(sharpness, 1) if sharpness is not None else None,
        orientation=orientation,
        has_exif=has_exif,
        warnings=tuple(dict.fromkeys(warnings)),
        suggestions=tuple(dict.fromkeys(suggestions)),
    )


def _orientation(width: int | None, height: int | None) -> str:
    if not width or not height:
        return "unbekannt"
    if math.isclose(width, height, rel_tol=0.05):
        return "quadratisch"
    return "quer" if width > height else "hoch"


def _estimate_sharpness(image: object) -> float | None:
    if ImageFilter is None:
        return None
    edge_image = image.filter(ImageFilter.FIND_EDGES)
    pixels = list(edge_image.getdata())
    return pstdev(pixels) if len(pixels) > 1 else 0.0


def _read_dimensions_without_pillow(path: Path) -> tuple[int | None, int | None, str]:
    try:
        with path.open("rb") as handle:
            header = handle.read(32)
            if header.startswith(b"\x89PNG\r\n\x1a\n"):
                width, height = struct.unpack(">II", header[16:24])
                return width, height, "PNG"
            if header[:2] == b"\xff\xd8":
                return (*_jpeg_dimensions(path), "JPEG")
            if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
                return (*_webp_dimensions(path), "WEBP")
    except OSError:
        return None, None, "unbekannt"
    return None, None, path.suffix.lstrip(".").upper() or "unbekannt"


def _jpeg_dimensions(path: Path) -> tuple[int | None, int | None]:
    try:
        with path.open("rb") as handle:
            handle.read(2)
            while True:
                marker_start = handle.read(1)
                if marker_start != b"\xff":
                    return None, None
                marker = handle.read(1)
                while marker == b"\xff":
                    marker = handle.read(1)
                if marker in {b"\xc0", b"\xc1", b"\xc2", b"\xc3"}:
                    handle.read(3)
                    height, width = struct.unpack(">HH", handle.read(4))
                    return width, height
                segment_size_data = handle.read(2)
                if len(segment_size_data) != 2:
                    return None, None
                segment_size = struct.unpack(">H", segment_size_data)[0]
                handle.seek(segment_size - 2, 1)
    except OSError:
        return None, None


def _webp_dimensions(path: Path) -> tuple[int | None, int | None]:
    try:
        with path.open("rb") as handle:
            data = handle.read(64)
        chunk = data[12:16]
        if chunk == b"VP8X" and len(data) >= 30:
            width = 1 + int.from_bytes(data[24:27], "little")
            height = 1 + int.from_bytes(data[27:30], "little")
            return width, height
    except OSError:
        return None, None
    return None, None
