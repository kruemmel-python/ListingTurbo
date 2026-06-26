from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from listingturbo.core.image_probe import Image, ImageEnhance, ImageOps, inspect_image
from listingturbo.native.backend import enhance_rgb_bytes


@dataclass(frozen=True, slots=True)
class EnhancedImage:
    source: Path
    output: Path
    changed: bool
    message: str


def enhance_images(paths: list[Path], output_dir: Path, *, max_edge: int = 2000) -> list[EnhancedImage]:
    output_dir.mkdir(parents=True, exist_ok=True)
    return [enhance_image(path, output_dir, max_edge=max_edge) for path in paths]


def enhance_image(path: Path, output_dir: Path, *, max_edge: int = 2000) -> EnhancedImage:
    source = Path(path)
    safe_stem = _safe_filename(source.stem) or "foto"
    target = output_dir / f"{safe_stem}_listingturbo.jpg"

    if Image is None or ImageEnhance is None or ImageOps is None:
        fallback = output_dir / source.name
        shutil.copy2(source, fallback)
        return EnhancedImage(
            source=source,
            output=fallback,
            changed=False,
            message="Pillow nicht verfügbar; Originalbild wurde unverändert kopiert.",
        )

    metrics = inspect_image(source)
    with Image.open(source) as image:
        fixed = ImageOps.exif_transpose(image).convert("RGB")
        fixed.thumbnail((max_edge, max_edge))
        fixed = ImageOps.autocontrast(fixed, cutoff=1)

        brightness_factor = 1.0
        contrast_factor = 1.0
        sharpen_amount = 0.0

        if metrics.brightness is not None:
            match metrics.brightness:
                case value if value < 72:
                    brightness_factor = 1.20
                case value if value > 220:
                    brightness_factor = 0.92
                case _:
                    pass

        if metrics.contrast is not None and metrics.contrast < 32:
            contrast_factor = 1.12

        if metrics.sharpness is not None and metrics.sharpness < 12:
            sharpen_amount = 0.18

        native = enhance_rgb_bytes(
            fixed.tobytes(),
            fixed.size[0],
            fixed.size[1],
            fixed.size[0] * 3,
            brightness_factor=brightness_factor,
            contrast_factor=contrast_factor,
            sharpen_amount=sharpen_amount,
        )
        native_message = ""
        if native is not None and native.available and native.data is not None:
            fixed = Image.frombytes("RGB", fixed.size, native.data)
            native_message = f" Native Backend: {native.backend_name}."
        else:
            if brightness_factor != 1.0:
                fixed = ImageEnhance.Brightness(fixed).enhance(brightness_factor)
            if contrast_factor != 1.0:
                fixed = ImageEnhance.Contrast(fixed).enhance(contrast_factor)
            if sharpen_amount > 0.0:
                fixed = ImageEnhance.Sharpness(fixed).enhance(1.0 + sharpen_amount)

        fixed.save(target, "JPEG", quality=90, optimize=True, progressive=True)

    return EnhancedImage(
        source=source,
        output=target,
        changed=True,
        message="Foto wurde ausgerichtet, EXIF-bereinigt, kontrastoptimiert und als Marktplatz-JPG exportiert." + native_message,
    )


def _safe_filename(text: str) -> str:
    allowed = []
    for char in text.strip():
        if char.isalnum() or char in {"-", "_"}:
            allowed.append(char)
        elif char.isspace():
            allowed.append("_")
    return "".join(allowed)[:80]
