from __future__ import annotations

import re
from pathlib import Path

from listingturbo.core.image_probe import inspect_images
from listingturbo.core.pricing import suggest_price
from listingturbo.core.resources import load_json
from listingturbo.domain import ImageMetrics, PlatformListing, PriceSuggestion, ProductInput


MODE_CATEGORIES = {"Mode", "Kinderkleidung", "Schuhe", "Accessoires"}
ELECTRONICS_CATEGORIES = {"Elektronik"}


def generate_all_platforms(product: ProductInput) -> dict[str, PlatformListing]:
    platforms = load_json("platforms.json")
    return {name: generate_listing(product, name) for name in platforms}


def generate_listing(product: ProductInput, platform: str | None = None) -> PlatformListing:
    selected_platform = platform or product.platform
    platforms = load_json("platforms.json")
    platform_config = platforms.get(selected_platform) or platforms["Kleinanzeigen"]
    image_metrics = inspect_images(product.image_paths)
    price = suggest_price(product)
    title = _build_title(product, selected_platform, int(platform_config.get("max_title", 80)))
    short_description = _build_short_description(product, selected_platform, price)
    description = _build_description(product, selected_platform)
    checklist = _build_checklist(product, selected_platform, image_metrics)
    hashtags = _build_hashtags(product, selected_platform) if bool(platform_config.get("hashtags", False)) else tuple()
    image_summary = _summarize_images(image_metrics)
    return PlatformListing(
        platform=selected_platform,
        title=title,
        short_description=short_description,
        description=description,
        hashtags=hashtags,
        checklist=checklist,
        price=price,
        image_summary=image_summary,
    )


def _build_title(product: ProductInput, platform: str, max_length: int) -> str:
    match platform:
        case "Vinted":
            parts = _unique_non_empty(
                [product.brand, product.product_type, _size_title_part(product), product.color, _condition_short(product)]
            )
        case "eBay":
            parts = _unique_non_empty(
                [product.brand, product.model, product.storage, product.color, product.product_type, _condition_short(product)]
            )
            if product.accessories.strip():
                parts.append("mit Zubehör")
        case "Facebook Marketplace":
            parts = _unique_non_empty([product.brand, product.model, product.product_type, product.storage])
            if product.location_hint.strip():
                parts.append(_locality(product.location_hint))
            if not parts:
                parts = [product.product_type or "Artikel"]
        case _:
            parts = []
            if product.quantity > 1:
                parts.append(f"{product.quantity}x")
            parts.extend(_unique_non_empty([product.brand, product.model, product.product_type, product.storage, product.color]))
            parts.append(_condition_short(product))
            if product.accessories.strip():
                parts.append("mit Zubehör")

    raw = ", ".join(parts).strip(", ") or "Gebrauchter Artikel in gutem Zustand"
    return _trim_title(raw, max_length)


def _size_title_part(product: ProductInput) -> str:
    return f"Gr. {product.size.strip()}" if product.size.strip() else ""


def _condition_short(product: ProductInput) -> str:
    value = str(product.condition)
    replacements = {
        "Neu / unbenutzt": "neu",
        "Sehr gut": "sehr gut",
        "Gut": "gut",
        "Akzeptabel": "gebraucht",
        "Defekt / Bastler": "defekt",
    }
    return replacements.get(value, value)


def _trim_title(title: str, max_length: int) -> str:
    if len(title) <= max_length:
        return title
    title = re.sub(r",\s*mit Zubehör", "", title)
    title = re.sub(r",\s*sehr gut", ", sehr gut", title)
    if len(title) <= max_length:
        return title
    words = title.split()
    trimmed: list[str] = []
    for word in words:
        candidate = " ".join([*trimmed, word])
        if len(candidate) > max_length - 1:
            break
        trimmed.append(word)
    return " ".join(trimmed).rstrip(",")


def _build_short_description(product: ProductInput, platform: str, price: PriceSuggestion) -> str:
    match platform:
        case "Vinted":
            parts = [product.article_phrase(), f"Zustand: {product.condition}"]
            if product.size.strip():
                parts.append(f"Größe: {product.size.strip()}")
            if product.household != "Keine Angabe":
                parts.append(str(product.household))
            return " · ".join(parts)
        case "Facebook Marketplace":
            place = f" in {_locality(product.location_hint)}" if product.location_hint.strip() else ""
            return f"{product.article_phrase()}{place}. {product.condition}. Preisidee: {price.as_text()}."
        case "eBay":
            return f"{product.article_phrase()} | Zustand: {product.condition} | Lieferumfang: {_or_dash(product.accessories)}"
        case _:
            return f"{product.article_phrase()} – {product.condition}. {product.shipping}. Preisidee: {price.as_text()}."


def _build_description(product: ProductInput, platform: str) -> str:
    match platform:
        case "eBay":
            return _build_ebay_description(product)
        case "Vinted":
            return _build_vinted_description(product)
        case "Facebook Marketplace":
            return _build_facebook_description(product)
        case _:
            return _build_kleinanzeigen_description(product)


def _build_kleinanzeigen_description(product: ProductInput) -> str:
    lines: list[str] = [
        f"Ich verkaufe {product.article_phrase()} aus Privatbesitz.",
        "",
        "Kurzüberblick:",
        *_bullet_lines(_detail_lines(product, profile="classifieds")),
    ]
    lines.extend(_section("Zustand", _condition_and_defects(product)))
    lines.extend(_section("Lieferumfang", [product.accessories.strip()] if product.accessories.strip() else []))
    lines.extend(_section("Abholung / Versand", _logistics_lines(product, local_first=True)))
    if product.notes.strip():
        lines.extend(_section("Zusätzliche Hinweise", [product.notes.strip()]))
    lines.extend(
        [
            "",
            "Bei Interesse gerne kurz schreiben. Besichtigung oder Rückfragen sind nach Absprache möglich.",
            "Privatverkauf, daher keine Garantie oder Rücknahme, soweit rechtlich zulässig.",
        ]
    )
    return _clean_lines(lines)


def _build_ebay_description(product: ProductInput) -> str:
    lines: list[str] = [
        "Artikelbeschreibung",
        f"Angeboten wird: {product.article_phrase()}.",
        "",
        "Artikelmerkmale:",
        *_bullet_lines(_detail_lines(product, profile="ebay")),
    ]
    lines.extend(_section("Zustand und Funktion", _condition_and_defects(product, include_function_note=True)))
    lines.extend(_section("Lieferumfang", [product.accessories.strip()] if product.accessories.strip() else ["Nur der beschriebene Artikel ist Bestandteil des Angebots."]))
    lines.extend(_section("Versand / Abwicklung", _logistics_lines(product, local_first=False)))
    if product.notes.strip():
        lines.extend(_section("Weitere Angaben", [product.notes.strip()]))
    lines.extend(
        [
            "",
            "Die Beschreibung wurde nach bestem Wissen und anhand des sichtbaren Zustands erstellt.",
            "Privatverkauf: keine Garantie, keine Gewährleistung und keine Rücknahme, soweit rechtlich zulässig.",
        ]
    )
    return _clean_lines(lines)


def _build_vinted_description(product: ProductInput) -> str:
    lines: list[str] = [
        f"Verkaufe {product.article_phrase()}.",
        "",
        "Für Vinted wichtige Angaben:",
        *_bullet_lines(_detail_lines(product, profile="vinted")),
    ]
    lines.extend(_section("Zustand", _condition_and_defects(product)))
    if product.material.strip():
        lines.extend(_section("Material", [product.material.strip()]))
    if product.accessories.strip() and product.category not in MODE_CATEGORIES:
        lines.extend(_section("Lieferumfang", [product.accessories.strip()]))
    lines.extend(_section("Versand", _vinted_shipping_lines(product)))
    if product.household != "Keine Angabe":
        lines.extend(_section("Haushalt", [str(product.household)]))
    if product.notes.strip():
        lines.extend(_section("Hinweis", [product.notes.strip()]))
    lines.extend(["", "Bei Fragen zu Zustand, Maßen oder weiteren Fotos gerne schreiben."])
    return _clean_lines(lines)


def _build_facebook_description(product: ProductInput) -> str:
    opening = f"{product.article_phrase()} abzugeben."
    if product.location_hint.strip():
        opening = f"{product.article_phrase()} in {_locality(product.location_hint)} abzugeben."
    lines: list[str] = [
        opening,
        "",
        "Schnelle Infos:",
        *_bullet_lines(_detail_lines(product, profile="facebook")),
    ]
    lines.extend(_section("Zustand", _condition_and_defects(product)))
    if product.accessories.strip():
        lines.extend(_section("Dabei", [product.accessories.strip()]))
    lines.extend(_section("Abwicklung", _logistics_lines(product, local_first=True)))
    if product.notes.strip():
        lines.extend(_section("Gut zu wissen", [product.notes.strip()]))
    lines.extend(["", "Schreib mir einfach, wenn du Fragen hast oder vorbeikommen möchtest."])
    return _clean_lines(lines)


def _section(title: str, body: list[str]) -> list[str]:
    cleaned = [item.strip() for item in body if item and item.strip()]
    if not cleaned:
        return []
    return ["", f"{title}:", *_bullet_lines(cleaned)]


def _bullet_lines(lines: list[str]) -> list[str]:
    return [f"- {line}" for line in lines if line and line.strip()]


def _condition_and_defects(product: ProductInput, *, include_function_note: bool = False) -> list[str]:
    phrase_bank = load_json("phrase_bank_de.json")
    condition_line = phrase_bank["condition_lines"].get(str(product.condition), "Der Zustand ist ehrlich beschrieben.")
    lines = [condition_line]
    if product.defects.strip():
        lines.append(product.defects.strip())
    elif include_function_note and product.category in ELECTRONICS_CATEGORIES:
        lines.append("Funktion wird im Text nur zugesichert, soweit sie oben beziehungsweise in den Zusatzangaben beschrieben ist.")
    return lines


def _logistics_lines(product: ProductInput, *, local_first: bool) -> list[str]:
    phrase_bank = load_json("phrase_bank_de.json")
    shipping_line = phrase_bank["shipping_lines"].get(str(product.shipping), "")
    household_line = phrase_bank["household_lines"].get(str(product.household), "")
    place = f"Ort/Abholung: {product.location_hint.strip()}" if product.location_hint.strip() else ""
    values = [place, shipping_line, household_line] if local_first else [shipping_line, place, household_line]
    return [item for item in values if item]


def _vinted_shipping_lines(product: ProductInput) -> list[str]:
    match str(product.shipping):
        case "Versand":
            return ["Versand ist möglich; Versandart nach Absprache beziehungsweise über die Plattform."]
        case "Abholung":
            return ["Abholung ist bevorzugt."]
        case _:
            return ["Versand oder Abholung nach Absprache möglich."]


def _detail_lines(product: ProductInput, *, profile: str) -> list[str]:
    base: list[tuple[str, str]]
    match profile:
        case "ebay":
            base = [
                ("Kategorie", product.category),
                ("Marke", product.brand),
                ("Modell/Variante", product.model),
                ("Artikelart", product.product_type),
                ("Speicher/Größe", product.storage or product.size),
                ("Farbe", product.color),
                ("Material", product.material),
                ("Maße", product.dimensions),
                ("Alter", f"ca. {product.age_years} Jahr(e)" if product.age_years is not None else ""),
            ]
        case "vinted":
            base = [
                ("Marke", product.brand),
                ("Kategorie/Artikel", product.product_type),
                ("Größe", product.size),
                ("Farbe", product.color),
                ("Material", product.material),
                ("Zustand", str(product.condition)),
                ("Anzahl", str(product.quantity) if product.quantity > 1 else ""),
            ]
            if product.category not in MODE_CATEGORIES:
                base.insert(0, ("Plattform-Eignung", "Vinted ist primär für Mode gedacht; für Elektronik meist eBay/Kleinanzeigen bevorzugen."))
        case "facebook":
            base = [
                ("Artikel", product.article_phrase()),
                ("Zustand", str(product.condition)),
                ("Farbe", product.color),
                ("Speicher/Größe", product.storage or product.size),
                ("Ort", product.location_hint),
            ]
        case _:
            base = [
                ("Kategorie", product.category),
                ("Artikel", product.product_type),
                ("Marke", product.brand),
                ("Modell", product.model),
                ("Speicher", product.storage),
                ("Größe", product.size),
                ("Farbe", product.color),
                ("Material", product.material),
                ("Maße", product.dimensions),
                ("Anzahl", str(product.quantity) if product.quantity > 1 else ""),
                ("Alter", f"ca. {product.age_years} Jahr(e)" if product.age_years is not None else ""),
            ]
    return [f"{name}: {value.strip()}" for name, value in base if value and value.strip()]


def _build_checklist(product: ProductInput, platform: str, metrics: list[ImageMetrics]) -> tuple[str, ...]:
    categories = load_json("categories.json")
    category_config = categories.get(product.category, categories["Sonstiges"])
    checks: list[str] = [
        "Persönliche Daten, Seriennummern, Adressen und Spiegelungen in Fotos geprüft.",
        "Zustand ehrlich beschrieben und sichtbare Mängel erwähnt.",
        "Abholung/Versand eindeutig angegeben.",
    ]
    checks.extend(_platform_checks(platform, product))
    checks.extend(category_config.get("risk_checks", []))

    missing = _missing_fields(product, category_config.get("required_fields", []), platform)
    if missing:
        checks.append("Noch ergänzen für bessere Conversion: " + ", ".join(missing) + ".")

    for metric in metrics[:8]:
        for warning in metric.warnings:
            checks.append(f"Foto {Path(metric.path).name}: {warning}")
        for suggestion in metric.suggestions[:2]:
            checks.append(f"Foto {Path(metric.path).name}: {suggestion}")

    if len(product.image_paths) < 3:
        checks.append("Mindestens 3 Fotos erhöhen Vertrauen: Front, Detail, eventuelle Mängel.")
    elif len(product.image_paths) > 12:
        checks.append("Viele Fotos sind gut; die stärksten 8–10 zuerst verwenden.")

    return tuple(dict.fromkeys(checks))


def _platform_checks(platform: str, product: ProductInput) -> list[str]:
    match platform:
        case "eBay":
            return [
                "eBay: Zustandsfeld, Versandkosten und Rücknahmeoption müssen zur Beschreibung passen.",
                "eBay: Lieferumfang vollständig nennen, damit keine Käufererwartung offen bleibt.",
                "Privatverkauf-Hinweis nur verwenden, wenn es tatsächlich ein privater Verkauf ist.",
            ]
        case "Vinted":
            checks = [
                "Vinted: Größe, Marke, Material, Zustand und Trage-/Nutzungsspuren besonders klar angeben.",
                "Vinted: Label-, Größen- und Mängelfotos erhöhen Vertrauen.",
            ]
            if product.category not in MODE_CATEGORIES:
                checks.append("Vinted: Kategorie passt nur eingeschränkt; für Elektronik ist eBay/Kleinanzeigen meist stärker.")
            return checks
        case "Facebook Marketplace":
            return [
                "Facebook: Ort nur grob nennen und genaue Adresse erst nach verbindlicher Absprache teilen.",
                "Facebook: erster Satz muss lokal und schnell erfassbar sein.",
                "Facebook: bei Abholung Treffpunkt und Zahlungsart intern klären.",
            ]
        case _:
            return [
                "Kleinanzeigen: Ort, Abholung/Versand und realistische VB-Angabe klar setzen.",
                "Kleinanzeigen: Seriennummern/IMEI nicht sichtbar lassen und persönliche Daten entfernen.",
                "Privatverkauf-Hinweis ergänzt, sofern gewünscht und rechtlich passend.",
            ]


def _missing_fields(product: ProductInput, required: list[str], platform: str) -> list[str]:
    required_fields = set(required)
    match platform:
        case "eBay":
            required_fields.update({"marke", "modell", "zubehoer"})
        case "Vinted":
            required_fields.update({"groesse", "farbe", "haushalt"})
            if product.category in MODE_CATEGORIES:
                required_fields.update({"material"})
        case "Facebook Marketplace":
            required_fields.update({"abholung"})
        case _:
            required_fields.update({"abholung"})

    mapping = {
        "marke": product.brand,
        "modell": product.model,
        "speicher": product.storage,
        "zubehoer": product.accessories,
        "groesse": product.size,
        "farbe": product.color,
        "zustand": str(product.condition),
        "anzahl": str(product.quantity) if product.quantity > 1 else "",
        "jahreszeit": product.notes,
        "haushalt": str(product.household) if product.household != "Keine Angabe" else "",
        "masse": product.dimensions,
        "material": product.material,
        "abholung": str(product.shipping),
        "leistung": product.notes,
        "titel": product.product_type,
        "umfang": product.accessories,
    }
    labels = {
        "marke": "Marke",
        "modell": "Modell",
        "speicher": "Speicher/Variante",
        "zubehoer": "Zubehör/Lieferumfang",
        "groesse": "Größe",
        "farbe": "Farbe",
        "anzahl": "Anzahl",
        "jahreszeit": "Saison/Jahreszeit",
        "haushalt": "Haushalt",
        "masse": "Maße",
        "material": "Material",
        "abholung": "Abholung/Versand",
        "leistung": "Leistung/technische Daten",
        "titel": "genauer Artikeltyp",
        "umfang": "Umfang/Lieferumfang",
    }
    return [labels.get(field, field) for field in sorted(required_fields) if not mapping.get(field, "").strip()]


def _build_hashtags(product: ProductInput, platform: str) -> tuple[str, ...]:
    raw = [product.category, product.product_type, product.brand, product.model, product.size, product.color]
    if platform == "Facebook Marketplace" and product.location_hint.strip():
        raw.append(_locality(product.location_hint))
    tags: list[str] = []
    for value in raw:
        normalized = re.sub(r"[^0-9A-Za-zÄÖÜäöüß]+", "", value.strip())
        if normalized:
            tags.append("#" + normalized)
    return tuple(dict.fromkeys(tags[:8]))


def _summarize_images(metrics: list[ImageMetrics]) -> tuple[str, ...]:
    if not metrics:
        return ("Keine Fotos ausgewählt.",)
    rows = []
    for metric in metrics:
        size = f"{metric.width}x{metric.height}" if metric.width and metric.height else "unbekannte Größe"
        quality = []
        if metric.brightness is not None:
            quality.append(f"Helligkeit {metric.brightness}")
        if metric.contrast is not None:
            quality.append(f"Kontrast {metric.contrast}")
        if metric.sharpness is not None:
            quality.append(f"Schärfe {metric.sharpness}")
        rows.append(f"{Path(metric.path).name}: {metric.file_type}, {size}, {', '.join(quality) or 'Basisdaten'}")
    return tuple(rows)


def _unique_non_empty(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = value.strip()
        key = clean.casefold()
        if clean and key not in seen:
            result.append(clean)
            seen.add(key)
    return result


def _locality(value: str) -> str:
    clean = value.strip()
    clean = re.sub(r"^Abholung\s+(im\s+Raum\s+|in\s+)?", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s+möglich$", "", clean, flags=re.IGNORECASE)
    return clean or value.strip()


def _or_dash(value: str) -> str:
    return value.strip() or "nicht angegeben"


def _clean_lines(lines: list[str]) -> str:
    cleaned: list[str] = []
    blank = False
    for line in lines:
        item = line.rstrip()
        if not item:
            if not blank and cleaned:
                cleaned.append("")
            blank = True
            continue
        cleaned.append(item)
        blank = False
    while cleaned and not cleaned[-1]:
        cleaned.pop()
    return "\n".join(cleaned)
