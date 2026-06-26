from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class Condition(StrEnum):
    NEW = "Neu / unbenutzt"
    VERY_GOOD = "Sehr gut"
    GOOD = "Gut"
    ACCEPTABLE = "Akzeptabel"
    BROKEN = "Defekt / Bastler"


class ShippingMode(StrEnum):
    PICKUP = "Abholung"
    SHIPPING = "Versand"
    BOTH = "Abholung oder Versand"


class Household(StrEnum):
    NON_SMOKER = "Nichtraucherhaushalt"
    PET_FREE_NON_SMOKER = "Tierfreier Nichtraucherhaushalt"
    PETS = "Haustierhaushalt"
    UNKNOWN = "Keine Angabe"


PLATFORM_RESOURCE_SCHEMA_VERSION = 1
REQUIRED_PLATFORM_FIELDS = {"max_title", "sections", "hashtags"}
MIN_TITLE_LIMIT = 30
MAX_TITLE_LIMIT = 140


def validate_platform_resource(payload: dict[str, Any]) -> None:
    """Prüft platforms.json gegen die Domain-Kontrakte.

    Dadurch liegt die Wahrheit für Plattform-Limits nicht verteilt in GUI, Engine
    und JSON, sondern an einer harten Domain-Grenze. Wird eine zentrale
    platforms.json später aktualisiert, muss sie hier durch, bevor die App sie
    akzeptiert.
    """
    if not payload:
        raise ValueError("platforms.json darf nicht leer sein.")
    for platform, config in payload.items():
        if not isinstance(platform, str) or not platform.strip():
            raise ValueError("Plattformname muss ein nichtleerer String sein.")
        if not isinstance(config, dict):
            raise ValueError(f"Plattform {platform!r} muss ein JSON-Objekt sein.")
        missing = REQUIRED_PLATFORM_FIELDS.difference(config)
        if missing:
            raise ValueError(f"Plattform {platform!r} fehlt Pflichtfelder: {', '.join(sorted(missing))}.")
        max_title = config.get("max_title")
        if not isinstance(max_title, int) or not MIN_TITLE_LIMIT <= max_title <= MAX_TITLE_LIMIT:
            raise ValueError(
                f"Plattform {platform!r}: max_title muss zwischen "
                f"{MIN_TITLE_LIMIT} und {MAX_TITLE_LIMIT} liegen."
            )
        sections = config.get("sections")
        if not isinstance(sections, list) or not all(isinstance(item, str) for item in sections):
            raise ValueError(f"Plattform {platform!r}: sections muss eine String-Liste sein.")
        if not isinstance(config.get("hashtags"), bool):
            raise ValueError(f"Plattform {platform!r}: hashtags muss boolesch sein.")
        description_max = config.get("max_description")
        if description_max is not None and (not isinstance(description_max, int) or description_max < 200):
            raise ValueError(f"Plattform {platform!r}: max_description ist ungültig.")
        tone = config.get("tone")
        if tone is not None and not isinstance(tone, str):
            raise ValueError(f"Plattform {platform!r}: tone muss ein String sein.")


def platform_title_limit(payload: dict[str, Any], platform: str, fallback: int = 80) -> int:
    config = payload.get(platform)
    if isinstance(config, dict) and isinstance(config.get("max_title"), int):
        return int(config["max_title"])
    return fallback


@dataclass(slots=True)
class ProductInput:
    category: str = "Sonstiges"
    product_type: str = "Artikel"
    brand: str = ""
    model: str = ""
    size: str = ""
    color: str = ""
    storage: str = ""
    material: str = ""
    dimensions: str = ""
    quantity: int = 1
    condition: Condition = Condition.GOOD
    age_years: int | None = None
    original_price: float | None = None
    desired_price: float | None = None
    accessories: str = ""
    defects: str = ""
    notes: str = ""
    location_hint: str = ""
    shipping: ShippingMode = ShippingMode.BOTH
    household: Household = Household.UNKNOWN
    platform: str = "Kleinanzeigen"
    image_paths: list[Path] = field(default_factory=list)

    def article_phrase(self) -> str:
        parts: list[str] = []
        if self.quantity > 1:
            parts.append(f"{self.quantity}x")
        if self.brand.strip():
            parts.append(self.brand.strip())
        if self.model.strip():
            parts.append(self.model.strip())
        if self.product_type.strip():
            parts.append(self.product_type.strip())
        if self.size.strip():
            parts.append(f"Größe {self.size.strip()}")
        if self.storage.strip():
            parts.append(self.storage.strip())
        return " ".join(parts).strip() or "einen gebrauchten Artikel"

    def to_jsonable(self) -> dict[str, Any]:
        data = asdict(self)
        data["condition"] = str(self.condition)
        data["shipping"] = str(self.shipping)
        data["household"] = str(self.household)
        data["image_paths"] = [str(path) for path in self.image_paths]
        return data

    @classmethod
    def from_jsonable(cls, data: dict[str, Any]) -> ProductInput:
        normalized = dict(data)
        normalized["condition"] = Condition(normalized.get("condition", Condition.GOOD))
        normalized["shipping"] = ShippingMode(normalized.get("shipping", ShippingMode.BOTH))
        normalized["household"] = Household(normalized.get("household", Household.UNKNOWN))
        normalized["image_paths"] = [Path(path) for path in normalized.get("image_paths", [])]
        return cls(**normalized)


@dataclass(frozen=True, slots=True)
class ImageMetrics:
    path: Path
    file_type: str
    width: int | None
    height: int | None
    megapixels: float | None
    brightness: float | None
    contrast: float | None
    sharpness: float | None
    orientation: str
    has_exif: bool
    warnings: tuple[str, ...]
    suggestions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PriceSuggestion:
    low: int
    high: int
    recommended: int
    confidence: str
    explanation: str

    def as_text(self) -> str:
        return f"VB {self.low}–{self.high} €; Empfehlung: {self.recommended} € ({self.confidence})"


@dataclass(frozen=True, slots=True)
class PlatformListing:
    platform: str
    title: str
    short_description: str
    description: str
    hashtags: tuple[str, ...]
    checklist: tuple[str, ...]
    price: PriceSuggestion
    image_summary: tuple[str, ...]

    def full_text(self) -> str:
        tags = " ".join(self.hashtags)
        lines = [
            f"Titel: {self.title}",
            "",
            self.description,
            "",
            f"Preisvorschlag: {self.price.as_text()}",
        ]
        if tags:
            lines.extend(["", f"Hashtags: {tags}"])
        lines.extend(["", "Checkliste:", *(f"- {item}" for item in self.checklist)])
        while lines and lines[-1] == "":
            lines.pop()
        return "\n".join(lines)
