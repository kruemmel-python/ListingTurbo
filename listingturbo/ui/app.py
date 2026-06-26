from __future__ import annotations

import json
import os
import re
import tkinter as tk
import webbrowser
from dataclasses import replace
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    import customtkinter as ctk
except Exception:  # pragma: no cover
    ctk = None  # type: ignore[assignment]

from listingturbo.core.exporter import export_html, export_pdf, export_txt, export_vks_image
from listingturbo.core.image_enhance import enhance_images
from listingturbo.core.image_probe import Image, inspect_images
from listingturbo.core.license import (
    can_generate,
    current_license_state,
    machine_fingerprint,
    record_generation,
    register_license_key,
)
from listingturbo.core.listing_engine import generate_all_platforms
from listingturbo.core.mobile_sync import IMPORT_ROOT, MobileSyncServer
from listingturbo.core.project_store import load_project, save_project
from listingturbo.core.resource_update import check_or_apply_resource_updates
from listingturbo.core.resources import available_categories, available_platforms
from listingturbo.native.backend import backend_info_summary
from listingturbo.domain import Condition, Household, PlatformListing, ProductInput, ShippingMode

try:
    from PIL import ImageTk
except Exception:  # pragma: no cover
    ImageTk = None  # type: ignore[assignment]

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except Exception:  # pragma: no cover
    DND_FILES = None  # type: ignore[assignment]
    TkinterDnD = None  # type: ignore[assignment]


if ctk is not None and TkinterDnD is not None:
    class CustomTkinterDnDRoot(ctk.CTk, TkinterDnD.DnDWrapper):  # type: ignore[misc, valid-type]
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)
            self.TkdndVersion: str | None = None
            try:
                self.TkdndVersion = TkinterDnD._require(self)
            except Exception:
                # DnD is an optional convenience path. The application must remain
                # sellable and startable even when the bundled Tcl tkdnd package is
                # unavailable or blocked by a local Tk installation.
                self.TkdndVersion = None
else:
    CustomTkinterDnDRoot = None  # type: ignore[assignment]


class ListingTurboApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("ListingTurbo Enterprise 1.4")
        self.root.geometry("1280x820")
        self.root.minsize(1100, 720)
        self.image_paths: list[Path] = []
        self.generated: dict[str, PlatformListing] = {}
        self._thumbnail_ref: object | None = None
        self.mobile_sync_server: MobileSyncServer | None = None
        self._build_variables()
        self._build_layout()
        self._refresh_license_label()

    def _build_variables(self) -> None:
        self.category_var = tk.StringVar(value="Elektronik")
        self.platform_var = tk.StringVar(value="Kleinanzeigen")
        self.product_type_var = tk.StringVar(value="Smartphone")
        self.brand_var = tk.StringVar()
        self.model_var = tk.StringVar()
        self.size_var = tk.StringVar()
        self.color_var = tk.StringVar()
        self.storage_var = tk.StringVar()
        self.material_var = tk.StringVar()
        self.dimensions_var = tk.StringVar()
        self.quantity_var = tk.StringVar(value="1")
        self.condition_var = tk.StringVar(value=str(Condition.GOOD))
        self.age_var = tk.StringVar()
        self.original_price_var = tk.StringVar()
        self.desired_price_var = tk.StringVar()
        self.accessories_var = tk.StringVar()
        self.defects_var = tk.StringVar()
        self.notes_var = tk.StringVar()
        self.location_var = tk.StringVar()
        self.shipping_var = tk.StringVar(value=str(ShippingMode.BOTH))
        self.household_var = tk.StringVar(value=str(Household.UNKNOWN))
        self.status_var = tk.StringVar(value="Bereit.")
        self.license_var = tk.StringVar(value="")
        self.license_key_var = tk.StringVar(value="")
        self.mobile_sync_var = tk.StringVar(value="Mobile Sync: gestoppt")

    def _build_layout(self) -> None:
        self._configure_style()
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)
        header = ttk.Frame(outer)
        header.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header, text="ListingTurbo Enterprise", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(header, textvariable=self.license_var, style="Muted.TLabel").pack(side=tk.RIGHT)

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.input_tab = ttk.Frame(self.notebook, padding=10)
        self.output_tab = ttk.Frame(self.notebook, padding=10)
        self.analysis_tab = ttk.Frame(self.notebook, padding=10)
        self.license_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.input_tab, text="1 Eingabe")
        self.notebook.add(self.output_tab, text="2 Inserat")
        self.notebook.add(self.analysis_tab, text="3 Fotoanalyse")
        self.notebook.add(self.license_tab, text="4 Lizenz")

        self._build_input_tab()
        self._build_output_tab()
        self._build_analysis_tab()
        self._build_license_tab()

        status = ttk.Label(outer, textvariable=self.status_var, anchor=tk.W)
        status.pack(fill=tk.X, pady=(10, 0))

    def _configure_style(self) -> None:
        if ctk is not None:
            ctk.set_appearance_mode("system")
            ctk.set_default_color_theme("blue")
        self.root.configure(bg="#111827")
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#111827")
        style.configure("TLabelframe", background="#111827", foreground="#e5e7eb")
        style.configure("TLabelframe.Label", background="#111827", foreground="#e5e7eb")
        style.configure("TLabel", background="#111827", foreground="#e5e7eb")
        style.configure("TButton", padding=7)
        style.configure("TEntry", padding=4)
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), background="#111827", foreground="#f9fafb")
        style.configure("Section.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure("Muted.TLabel", foreground="#93a4b8", background="#111827")
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=7)
        style.configure("Danger.TButton", padding=7)

    def _build_input_tab(self) -> None:
        left = ttk.Frame(self.input_tab)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)
        right = ttk.Frame(self.input_tab)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(14, 0))

        image_box = ttk.LabelFrame(left, text="Fotos", padding=10, style="Section.TLabelframe")
        image_box.pack(fill=tk.BOTH, expand=True)
        self.image_list = tk.Listbox(image_box, height=18, width=44, activestyle="dotbox")
        self.image_list.pack(fill=tk.BOTH, expand=True)
        self.image_list.bind("<<ListboxSelect>>", lambda _event: self._show_selected_thumbnail())
        self._try_enable_drag_and_drop()

        button_row = ttk.Frame(image_box)
        button_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(button_row, text="Fotos hinzufügen", command=self._add_images).pack(side=tk.LEFT)
        ttk.Button(button_row, text="Entfernen", command=self._remove_selected_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_row, text="Leeren", command=self._clear_images).pack(side=tk.LEFT)

        self.preview_label = ttk.Label(image_box, text="Vorschau: Bild auswählen", anchor=tk.CENTER)
        self.preview_label.pack(fill=tk.X, pady=(10, 0))

        form = ttk.LabelFrame(right, text="Artikel-Daten", padding=12, style="Section.TLabelframe")
        form.pack(fill=tk.X)
        for column in range(4):
            form.columnconfigure(column, weight=1)

        row = 0
        self._combo(form, row, 0, "Kategorie", self.category_var, available_categories())
        self._combo(form, row, 2, "Plattform", self.platform_var, available_platforms())
        row += 1
        self._entry(form, row, 0, "Artikeltyp", self.product_type_var)
        self._entry(form, row, 2, "Marke", self.brand_var)
        row += 1
        self._entry(form, row, 0, "Modell / Variante", self.model_var)
        self._entry(form, row, 2, "Speicher", self.storage_var)
        row += 1
        self._entry(form, row, 0, "Größe", self.size_var)
        self._entry(form, row, 2, "Farbe", self.color_var)
        row += 1
        self._entry(form, row, 0, "Material", self.material_var)
        self._entry(form, row, 2, "Maße", self.dimensions_var)
        row += 1
        self._entry(form, row, 0, "Anzahl", self.quantity_var)
        self._combo(form, row, 2, "Zustand", self.condition_var, [str(item) for item in Condition])
        row += 1
        self._entry(form, row, 0, "Alter in Jahren", self.age_var)
        self._entry(form, row, 2, "Neupreis €", self.original_price_var)
        row += 1
        self._entry(form, row, 0, "Wunschpreis €", self.desired_price_var)
        self._combo(form, row, 2, "Versand", self.shipping_var, [str(item) for item in ShippingMode])
        row += 1
        self._combo(form, row, 0, "Haushalt", self.household_var, [str(item) for item in Household])
        self._entry(form, row, 2, "Ort / Abholung", self.location_var)
        row += 1
        self._entry(form, row, 0, "Zubehör / Lieferumfang", self.accessories_var, columnspan=3)
        row += 1
        self._entry(form, row, 0, "Mängel / Hinweise", self.defects_var, columnspan=3)
        row += 1
        self._entry(form, row, 0, "Zusatzinfo / Saison / Technik", self.notes_var, columnspan=3)

        action_box = ttk.Frame(right)
        action_box.pack(fill=tk.X, pady=12)
        ttk.Button(action_box, text="Fotoanalyse", command=self._run_image_analysis).pack(side=tk.LEFT)
        ttk.Button(action_box, text="Fotos verbessern", command=self._enhance_photos).pack(side=tk.LEFT, padx=7)
        ttk.Button(
            action_box,
            text="Inserat generieren",
            command=self._generate_listing,
            style="Primary.TButton",
        ).pack(side=tk.RIGHT)

        persistence = ttk.Frame(right)
        persistence.pack(fill=tk.X)
        ttk.Button(persistence, text="Projekt speichern", command=self._save_project).pack(side=tk.LEFT)
        ttk.Button(persistence, text="Projekt laden", command=self._load_project).pack(side=tk.LEFT, padx=7)
        ttk.Button(persistence, text="Beispieldaten", command=self._load_example_data).pack(side=tk.LEFT)

    def _try_enable_drag_and_drop(self) -> None:
        if TkinterDnD is None or DND_FILES is None:
            self.status_var.set("Drag & Drop nicht geladen; nutze Fotos hinzufügen.")
            return

        try:
            self.root.tk.call("package", "require", "tkdnd")
        except tk.TclError:
            require = getattr(TkinterDnD, "_require", None)
            if callable(require):
                try:
                    require(self.root)
                except Exception:
                    pass

        try:
            self.image_list.drop_target_register(DND_FILES)
            self.image_list.dnd_bind("<<Drop>>", self._on_drop_files)
            self.status_var.set("Bereit. Drag & Drop aktiv.")
        except (AttributeError, RuntimeError, tk.TclError):
            self.status_var.set("Drag & Drop nicht verfügbar; nutze Fotos hinzufügen.")

    def _build_output_tab(self) -> None:
        top = ttk.Frame(self.output_tab)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(top, text="Ausgabeplattform:").pack(side=tk.LEFT)
        self.output_platform_var = tk.StringVar(value="Kleinanzeigen")
        platform_select = ttk.Combobox(
            top,
            textvariable=self.output_platform_var,
            values=available_platforms(),
            state="readonly",
            width=28,
        )
        platform_select.pack(side=tk.LEFT, padx=8)
        platform_select.bind("<<ComboboxSelected>>", lambda _event: self._render_current_listing())
        ttk.Button(top, text="Titel kopieren", command=self._copy_title).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Beschreibung kopieren", command=self._copy_description).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Alles kopieren", command=self._copy_all).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="TXT", command=lambda: self._export("txt")).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top, text="HTML", command=lambda: self._export("html")).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top, text="PDF", command=lambda: self._export("pdf")).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top, text="VKS (Bild)", command=lambda: self._export("vks")).pack(side=tk.RIGHT, padx=4)

        panes = ttk.PanedWindow(self.output_tab, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True)
        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=3)
        panes.add(right, weight=2)

        ttk.Label(left, text="Titel").pack(anchor=tk.W)
        self.title_text = tk.Text(left, height=3, wrap=tk.WORD, font=("Segoe UI", 11, "bold"))
        self.title_text.pack(fill=tk.X, pady=(2, 8))
        ttk.Label(left, text="Beschreibung").pack(anchor=tk.W)
        self.description_text = tk.Text(left, wrap=tk.WORD, font=("Segoe UI", 10))
        self.description_text.pack(fill=tk.BOTH, expand=True)

        ttk.Label(right, text="Preis / Hashtags / Fotozusammenfassung / Checkliste").pack(anchor=tk.W)
        self.side_text = tk.Text(right, wrap=tk.WORD, font=("Segoe UI", 10))
        self.side_text.pack(fill=tk.BOTH, expand=True)

    def _build_analysis_tab(self) -> None:
        button_row = ttk.Frame(self.analysis_tab)
        button_row.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(button_row, text="Analyse aktualisieren", command=self._run_image_analysis).pack(side=tk.LEFT)
        ttk.Button(button_row, text="Native Backend prüfen", command=self._show_native_backend).pack(side=tk.LEFT, padx=(8, 0))
        self.analysis_text = tk.Text(self.analysis_tab, wrap=tk.WORD, font=("Consolas", 10))
        self.analysis_text.pack(fill=tk.BOTH, expand=True)

    def _build_license_tab(self) -> None:
        box = ttk.LabelFrame(self.license_tab, text="Offline-Lizenz", padding=12, style="Section.TLabelframe")
        box.pack(fill=tk.X)
        ttk.Label(
            box,
            text=(
                "Demo: 3 Generierungen pro Tag. Standard: unbegrenzt ohne Wasserzeichen. "
                "Pro: zusätzlich Batch-/Mehrartikel-Workflow. Lizenzschlüssel bleiben lokal."
            ),
            wraplength=900,
        ).pack(anchor=tk.W, pady=(0, 10))
        ttk.Entry(box, textvariable=self.license_key_var, width=110).pack(fill=tk.X)
        ttk.Button(box, text="Lizenz aktivieren", command=self._activate_license).pack(anchor=tk.E, pady=(8, 0))
        self.license_detail = tk.Text(self.license_tab, height=12, wrap=tk.WORD, font=("Consolas", 10))
        self.license_detail.pack(fill=tk.X, pady=(12, 0))
        license_buttons = ttk.Frame(self.license_tab)
        license_buttons.pack(fill=tk.X, pady=8)
        ttk.Button(license_buttons, text="Lizenzstatus aktualisieren", command=self._refresh_license_label).pack(side=tk.LEFT)
        ttk.Button(license_buttons, text="Machine-ID kopieren", command=self._copy_machine_id).pack(side=tk.LEFT, padx=(8, 0))

        sync_box = ttk.LabelFrame(self.license_tab, text="Android / Mobile Sync", padding=12, style="Section.TLabelframe")
        sync_box.pack(fill=tk.X, pady=(12, 0))
        ttk.Label(
            sync_box,
            text=(
                "Lokaler WLAN-Import ohne Cloud. Android sendet .lturbo-Daten und Fotos per HTTP direkt "
                "an diesen Rechner. Freischaltung ab STANDARD-Lizenz."
            ),
            wraplength=900,
        ).pack(anchor=tk.W, pady=(0, 8))
        ttk.Label(sync_box, textvariable=self.mobile_sync_var, style="Muted.TLabel").pack(anchor=tk.W, pady=(0, 8))
        sync_row = ttk.Frame(sync_box)
        sync_row.pack(fill=tk.X)
        ttk.Button(sync_row, text="Sync-Server starten", command=self._start_mobile_sync).pack(side=tk.LEFT)
        ttk.Button(sync_row, text="Sync-Server stoppen", command=self._stop_mobile_sync).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(sync_row, text="Import-Ordner öffnen", command=self._open_mobile_import_folder).pack(side=tk.LEFT, padx=(8, 0))

        data_box = ttk.LabelFrame(self.license_tab, text="Plattformdaten / JSON-Updatekanal", padding=12, style="Section.TLabelframe")
        data_box.pack(fill=tk.X, pady=(12, 0))
        ttk.Label(
            data_box,
            text=(
                "Offline-first: Ohne konfigurierten Updatekanal werden keine Daten geladen. "
                "Für langlebige Installationen kann später ein HTTPS-Manifest für platforms.json, "
                "categories.json, price_rules.json und phrase_bank_de.json aktiviert werden."
            ),
            wraplength=900,
        ).pack(anchor=tk.W, pady=(0, 8))
        row = ttk.Frame(data_box)
        row.pack(fill=tk.X)
        ttk.Button(row, text="Update prüfen", command=lambda: self._check_resource_updates(False)).pack(side=tk.LEFT)
        ttk.Button(row, text="Updates anwenden", command=lambda: self._check_resource_updates(True)).pack(side=tk.LEFT, padx=(8, 0))

    def _entry(
        self,
        parent: ttk.Frame,
        row: int,
        col: int,
        label: str,
        variable: tk.StringVar,
        *,
        columnspan: int = 1,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky=tk.W, pady=4, padx=(0, 6))
        ttk.Entry(parent, textvariable=variable).grid(
            row=row,
            column=col + 1,
            columnspan=columnspan,
            sticky=tk.EW,
            pady=4,
            padx=(0, 14),
        )

    def _combo(
        self,
        parent: ttk.Frame,
        row: int,
        col: int,
        label: str,
        variable: tk.StringVar,
        values: list[str],
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky=tk.W, pady=4, padx=(0, 6))
        ttk.Combobox(parent, textvariable=variable, values=values, state="readonly").grid(
            row=row,
            column=col + 1,
            sticky=tk.EW,
            pady=4,
            padx=(0, 14),
        )

    def _add_images(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Produktfotos auswählen",
            filetypes=[("Bilder", "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff"), ("Alle Dateien", "*.*")],
        )
        self._append_images([Path(path) for path in paths])

    def _on_drop_files(self, event: object) -> None:
        data = getattr(event, "data", "")
        try:
            files = self.root.tk.splitlist(data)
        except tk.TclError:
            files = re.findall(r"\{([^}]+)\}|([^\s]+)", data)
        paths = [Path(item if isinstance(item, str) else next(filter(None, item))) for item in files]
        self._append_images(paths)

    def _append_images(self, paths: list[Path]) -> None:
        existing = {path.resolve() for path in self.image_paths if path.exists()}
        added = 0
        for path in paths:
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if resolved not in existing and path.exists():
                self.image_paths.append(path)
                existing.add(resolved)
                added += 1
        self._refresh_image_list()
        self.status_var.set(f"{added} Foto(s) hinzugefügt. Insgesamt: {len(self.image_paths)}.")

    def _remove_selected_image(self) -> None:
        selection = list(self.image_list.curselection())
        for index in reversed(selection):
            del self.image_paths[index]
        self._refresh_image_list()
        self._thumbnail_ref = None
        self.preview_label.configure(image="", text="Vorschau: Bild auswählen")

    def _clear_images(self) -> None:
        self.image_paths.clear()
        self._refresh_image_list()
        self.preview_label.configure(image="", text="Vorschau: Bild auswählen")

    def _refresh_image_list(self) -> None:
        self.image_list.delete(0, tk.END)
        for path in self.image_paths:
            self.image_list.insert(tk.END, str(path))

    def _show_selected_thumbnail(self) -> None:
        selection = self.image_list.curselection()
        if not selection or Image is None or ImageTk is None:
            return
        path = self.image_paths[selection[0]]
        try:
            with Image.open(path) as image:
                image.thumbnail((360, 230))
                thumbnail = ImageTk.PhotoImage(image.copy())
        except OSError:
            self.preview_label.configure(text="Vorschau nicht lesbar", image="")
            return
        self._thumbnail_ref = thumbnail
        self.preview_label.configure(image=thumbnail, text="")

    def _show_native_backend(self) -> None:
        messagebox.showinfo("ListingTurbo Native Backend", backend_info_summary())
        self.status_var.set("Native Backend geprüft.")

    def _run_image_analysis(self) -> None:
        metrics = inspect_images(self.image_paths)
        lines: list[str] = [backend_info_summary(), ""]
        if not metrics:
            lines.append("Keine Fotos ausgewählt. Füge mindestens 3 Produktbilder hinzu.")
        for metric in metrics:
            lines.append(f"DATEI: {metric.path}")
            lines.append(f"  Format: {metric.file_type}")
            lines.append(f"  Größe: {metric.width}x{metric.height} px | MP: {metric.megapixels}")
            lines.append(f"  Orientierung: {metric.orientation} | EXIF: {'ja' if metric.has_exif else 'nein'}")
            lines.append(
                "  Qualität: "
                f"Helligkeit={metric.brightness}, Kontrast={metric.contrast}, Schärfe={metric.sharpness}"
            )
            if metric.warnings:
                lines.append("  Warnungen:")
                lines.extend(f"    - {item}" for item in metric.warnings)
            if metric.suggestions:
                lines.append("  Empfehlungen:")
                lines.extend(f"    - {item}" for item in metric.suggestions)
            lines.append("")
        self.analysis_text.delete("1.0", tk.END)
        self.analysis_text.insert("1.0", "\n".join(lines))
        self.notebook.select(self.analysis_tab)
        self.status_var.set("Fotoanalyse aktualisiert.")

    def _enhance_photos(self) -> None:
        if not self.image_paths:
            messagebox.showinfo("ListingTurbo", "Bitte zuerst Fotos hinzufügen.")
            return
        output_dir = filedialog.askdirectory(title="Zielordner für verbesserte Fotos wählen")
        if not output_dir:
            return
        results = enhance_images(self.image_paths, Path(output_dir))
        report = "\n".join(f"{item.output.name}: {item.message}" for item in results)
        messagebox.showinfo("Fotoverbesserung abgeschlossen", report)
        self.status_var.set(f"{len(results)} Foto(s) verbessert/exportiert.")

    def _generate_listing(self) -> None:
        if not can_generate():
            self._refresh_license_label()
            messagebox.showwarning(
                "Demo-Limit erreicht",
                "Die Demo hat heute keine freien Generierungen mehr. Aktiviere Standard oder Pro.",
            )
            return
        try:
            product = self._product_from_form()
        except ValueError as exc:
            messagebox.showerror("Eingabe prüfen", str(exc))
            return
        self.generated = generate_all_platforms(product)
        record_generation()
        self._refresh_license_label()
        self.output_platform_var.set(product.platform)
        self._render_current_listing()
        self.notebook.select(self.output_tab)
        self.status_var.set("Inserate für alle Plattformen generiert.")

    def _render_current_listing(self) -> None:
        listing = self._current_listing()
        if listing is None:
            return
        self.title_text.delete("1.0", tk.END)
        self.title_text.insert("1.0", listing.title)
        self.description_text.delete("1.0", tk.END)
        self.description_text.insert("1.0", listing.description)
        side_lines = [
            "PREIS",
            listing.price.as_text(),
            listing.price.explanation,
            "",
            "HASHTAGS",
            " ".join(listing.hashtags) if listing.hashtags else "Keine Hashtags für diese Plattform.",
            "",
            "FOTOZUSAMMENFASSUNG",
            *[f"- {item}" for item in listing.image_summary],
            "",
            "CHECKLISTE",
            *[f"- {item}" for item in listing.checklist],
        ]
        self.side_text.delete("1.0", tk.END)
        self.side_text.insert("1.0", "\n".join(side_lines))

    def _product_from_form(self) -> ProductInput:
        quantity = self._parse_int(self.quantity_var.get(), "Anzahl", minimum=1, default=1)
        age = self._parse_optional_int(self.age_var.get(), "Alter")
        original_price = self._parse_optional_float(self.original_price_var.get(), "Neupreis")
        desired_price = self._parse_optional_float(self.desired_price_var.get(), "Wunschpreis")
        product_type = self.product_type_var.get().strip()
        if not product_type:
            raise ValueError("Artikeltyp darf nicht leer sein.")
        return ProductInput(
            category=self.category_var.get(),
            product_type=product_type,
            brand=self.brand_var.get(),
            model=self.model_var.get(),
            size=self.size_var.get(),
            color=self.color_var.get(),
            storage=self.storage_var.get(),
            material=self.material_var.get(),
            dimensions=self.dimensions_var.get(),
            quantity=quantity,
            condition=Condition(self.condition_var.get()),
            age_years=age,
            original_price=original_price,
            desired_price=desired_price,
            accessories=self.accessories_var.get(),
            defects=self.defects_var.get(),
            notes=self.notes_var.get(),
            location_hint=self.location_var.get(),
            shipping=ShippingMode(self.shipping_var.get()),
            household=Household(self.household_var.get()),
            platform=self.platform_var.get(),
            image_paths=list(self.image_paths),
        )

    def _load_product_into_form(self, product: ProductInput) -> None:
        self.category_var.set(product.category)
        self.platform_var.set(product.platform)
        self.product_type_var.set(product.product_type)
        self.brand_var.set(product.brand)
        self.model_var.set(product.model)
        self.size_var.set(product.size)
        self.color_var.set(product.color)
        self.storage_var.set(product.storage)
        self.material_var.set(product.material)
        self.dimensions_var.set(product.dimensions)
        self.quantity_var.set(str(product.quantity))
        self.condition_var.set(str(product.condition))
        self.age_var.set("" if product.age_years is None else str(product.age_years))
        self.original_price_var.set("" if product.original_price is None else str(product.original_price))
        self.desired_price_var.set("" if product.desired_price is None else str(product.desired_price))
        self.accessories_var.set(product.accessories)
        self.defects_var.set(product.defects)
        self.notes_var.set(product.notes)
        self.location_var.set(product.location_hint)
        self.shipping_var.set(str(product.shipping))
        self.household_var.set(str(product.household))
        self.image_paths = list(product.image_paths)
        self._refresh_image_list()

    def _parse_int(self, value: str, label: str, *, minimum: int, default: int) -> int:
        stripped = value.strip()
        if not stripped:
            return default
        try:
            parsed = int(stripped)
        except ValueError as exc:
            raise ValueError(f"{label} muss eine ganze Zahl sein.") from exc
        if parsed < minimum:
            raise ValueError(f"{label} muss mindestens {minimum} sein.")
        return parsed

    def _parse_optional_int(self, value: str, label: str) -> int | None:
        stripped = value.strip()
        if not stripped:
            return None
        return self._parse_int(stripped, label, minimum=0, default=0)

    def _parse_optional_float(self, value: str, label: str) -> float | None:
        stripped = value.strip().replace(",", ".")
        if not stripped:
            return None
        try:
            parsed = float(stripped)
        except ValueError as exc:
            raise ValueError(f"{label} muss eine Zahl sein.") from exc
        if parsed <= 0:
            raise ValueError(f"{label} muss größer als 0 sein.")
        return parsed

    def _copy_title(self) -> None:
        listing = self._current_listing()
        if listing:
            self._copy(listing.title)

    def _copy_description(self) -> None:
        listing = self._current_listing()
        if listing:
            self._copy(self._watermarked_listing(listing).description)

    def _copy_all(self) -> None:
        listing = self._current_listing()
        if listing:
            self._copy(self._watermarked_listing(listing).full_text())

    def _copy(self, text: str) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_var.set("Text in die Zwischenablage kopiert.")

    def _export(self, kind: str) -> None:
        listing = self._current_listing()
        if listing is None:
            messagebox.showinfo("ListingTurbo", "Bitte zuerst ein Inserat generieren.")
            return
        listing = self._watermarked_listing(listing)
        extension = {"txt": ".txt", "html": ".html", "pdf": ".pdf", "vks": ".png"}[kind]
        path = filedialog.asksaveasfilename(
            title=f"Inserat als {kind.upper()} exportieren" if kind != "vks" else "Verkaufsschild exportieren",
            defaultextension=extension,
            filetypes=[(kind.upper() if kind != "vks" else "PNG", f"*{extension}"), ("Alle Dateien", "*.*")],
        )
        if not path:
            return
        target = Path(path)
        match kind:
            case "txt":
                export_txt(listing, target)
            case "html":
                export_html(listing, target)
            case "pdf":
                export_pdf(listing, target)
            case "vks":
                export_vks_image(listing, target)
            case _:
                raise ValueError(kind)
        self.status_var.set(f"Export geschrieben: {target}")

    def _current_listing(self) -> PlatformListing | None:
        platform = self.output_platform_var.get()
        listing = self.generated.get(platform)
        if listing is None and self.generated:
            listing = next(iter(self.generated.values()))
        if listing is None:
            messagebox.showinfo("ListingTurbo", "Bitte zuerst ein Inserat generieren.")
        return listing

    def _watermarked_listing(self, listing: PlatformListing) -> PlatformListing:
        state = current_license_state()
        if state.can_export_without_watermark:
            return listing
        watermark = "\n\n---\nErstellt mit ListingTurbo Demo."
        return replace(listing, description=listing.description + watermark)

    def _save_project(self) -> None:
        try:
            product = self._product_from_form()
        except ValueError as exc:
            messagebox.showerror("Eingabe prüfen", str(exc))
            return
        path = filedialog.asksaveasfilename(
            title="ListingTurbo-Projekt speichern",
            defaultextension=".lturbo.json",
            filetypes=[("ListingTurbo Projekt", "*.lturbo.json"), ("JSON", "*.json")],
        )
        if not path:
            return
        save_project(product, Path(path))
        self.status_var.set(f"Projekt gespeichert: {path}")

    def _load_project(self) -> None:
        path = filedialog.askopenfilename(
            title="ListingTurbo-Projekt laden",
            filetypes=[("ListingTurbo Projekt", "*.lturbo.json"), ("JSON", "*.json"), ("Alle Dateien", "*.*")],
        )
        if not path:
            return
        try:
            product = load_project(Path(path))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror("Projekt konnte nicht geladen werden", str(exc))
            return
        self._load_product_into_form(product)
        self.status_var.set(f"Projekt geladen: {path}")

    def _load_example_data(self) -> None:
        product = ProductInput(
            category="Elektronik",
            platform="Kleinanzeigen",
            product_type="Smartphone",
            brand="Samsung",
            model="Galaxy S22",
            storage="128 GB",
            color="Schwarz",
            quantity=1,
            condition=Condition.GOOD,
            age_years=3,
            original_price=849,
            accessories="Ladegerät, Schutzhülle, Originalkarton",
            defects="Normale Gebrauchsspuren am Rahmen, Display ohne Risse",
            notes="Kamera, Lautsprecher, WLAN und Laden funktionieren problemlos.",
            location_hint="Abholung im Raum Leipzig möglich",
            shipping=ShippingMode.BOTH,
            household=Household.NON_SMOKER,
            image_paths=list(self.image_paths),
        )
        self._load_product_into_form(product)
        self.status_var.set("Beispieldaten geladen. Eigene Fotos können ergänzt werden.")

    def _check_resource_updates(self, apply: bool) -> None:
        result = check_or_apply_resource_updates(apply=apply)
        messagebox.showinfo("ListingTurbo Plattformdaten", result.message)
        self.status_var.set(result.message)

    def _activate_license(self) -> None:
        state = register_license_key(self.license_key_var.get())
        self._refresh_license_label()
        messagebox.showinfo("Lizenz", state.message)

    def _refresh_license_label(self) -> None:
        state = current_license_state()
        self.license_var.set(
            f"Lizenz: {state.plan} | {'aktiv' if state.valid else 'Demo'} | Demo frei heute: {state.remaining_demo_generations}"
        )
        details = [
            f"Plan: {state.plan}",
            f"Gültig: {state.valid}",
            f"Inhaber: {state.owner or '-'}",
            f"Status: {state.message}",
            f"Freie Demo-Generierungen heute: {state.remaining_demo_generations}",
            f"Export ohne Wasserzeichen: {state.can_export_without_watermark}",
            f"Pro-Batch aktiv: {state.can_batch}",
            f"Mobile Import aktiv: {state.can_mobile_import}",
            f"Machine-ID dieser Installation: {state.machine_id or machine_fingerprint()}",
            f"Lizenz-Machine-ID: {state.licensed_machine_id or '-'}",
            f"Aktivierungs-ID: {state.activation_id or '-'}",
        ]
        if hasattr(self, "license_detail"):
            self.license_detail.delete("1.0", tk.END)
            self.license_detail.insert("1.0", "\n".join(details))

    def _copy_machine_id(self) -> None:
        value = machine_fingerprint()
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.status_var.set(f"Machine-ID kopiert: {value}")

    def _start_mobile_sync(self) -> None:
        state = current_license_state()
        if not state.can_mobile_import:
            messagebox.showwarning(
                "Mobile Sync",
                "Der Android-/Mobile-Import ist ab STANDARD-Lizenz aktiv. Bitte zuerst eine maschinengebundene Lizenz aktivieren.",
            )
            return
        if self.mobile_sync_server is None:
            self.mobile_sync_server = MobileSyncServer()
        try:
            self.mobile_sync_server.start()
        except OSError as exc:
            messagebox.showerror("Mobile Sync", f"Sync-Server konnte nicht gestartet werden: {exc}")
            return
        self.mobile_sync_var.set(
            f"Mobile Sync läuft: {self.mobile_sync_server.display_url} | PIN: {self.mobile_sync_server.token}"
        )
        self.status_var.set("Mobile Sync gestartet. Android-App mit URL und PIN verbinden.")

    def _stop_mobile_sync(self) -> None:
        if self.mobile_sync_server is not None:
            self.mobile_sync_server.stop()
        self.mobile_sync_var.set("Mobile Sync: gestoppt")
        self.status_var.set("Mobile Sync gestoppt.")

    def _open_mobile_import_folder(self) -> None:
        IMPORT_ROOT.mkdir(parents=True, exist_ok=True)
        try:
            if hasattr(os, "startfile"):
                os.startfile(str(IMPORT_ROOT))  # type: ignore[attr-defined]
            else:
                webbrowser.open(IMPORT_ROOT.as_uri())
        except OSError as exc:
            messagebox.showerror("Import-Ordner", str(exc))


def create_root() -> tk.Tk:
    if CustomTkinterDnDRoot is not None:
        try:
            root = CustomTkinterDnDRoot()
            root.configure(fg_color="#111827")
            return root  # type: ignore[return-value]
        except tk.TclError:
            pass
    if ctk is not None:
        try:
            root = ctk.CTk()
            root.configure(fg_color="#111827")
            return root  # type: ignore[return-value]
        except tk.TclError:
            pass
    if TkinterDnD is not None:
        try:
            return TkinterDnD.Tk()
        except tk.TclError:
            pass
    return tk.Tk()


def run() -> None:
    root = create_root()
    app = ListingTurboApp(root)
    root.mainloop()


if __name__ == "__main__":
    run()
