from __future__ import annotations

from datetime import datetime
import hashlib
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .catalog import (
    BAG_POCKETS,
    BAG_POCKET_LABELS,
    GENDERS,
    HOENN_DEX,
    ITEMS_BY_POCKET,
    ITEM_NAMES,
    MET_TYPES,
    MOVES,
    MOVES_BY_NAME,
    NATURES,
    SPECIES,
    SPECIES_BY_NAME,
    STATUS_CONDITIONS,
    display_name,
)
from .domain import (
    BagEntry,
    PokemonView,
    add_bag_item,
    bag_entries,
    box_names,
    create_pokemon,
    edit_bag_item,
    move_pokemon,
    party_pokemon,
    patch_domain_values,
    patch_pokemon,
    pokemon_creation_defaults,
    remove_bag_item,
    storage_pokemon,
)
from .errors import GammaEditorError
from .gvas import PropertyRecord, parse_gvas, patch_scalar
from .save_service import (
    LoadedSave,
    default_save_dir,
    discover_saves,
    list_backups,
    load_save,
    restore_backup,
    write_save,
)


APP_TITLE = "Gamma Emerald Save Editor"
ENUM_PREFIXES = {
    "Nature": "ENature",
    "Gender": "EPokemonGender",
    "StatusCondition": "ESTATUSEffect",
    "MetType": "EPokemonMetType",
}


def _enum_leaf(value: object) -> str:
    return str(value or "").split("::")[-1]


def _number(value: object, fallback: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return fallback


class PokemonEditor(ttk.Frame):
    """Indigo-style grouped editor for one occupied Gamma Pokémon struct."""

    SCALAR_FIELDS = (
        "Nickname", "Level", "CurrentEXP", "CurrentHP", "MaxHP",
        "HP_IV", "Attack_IV", "Defense_IV", "SpecialAttack_IV", "SpecialDefense_IV", "Speed_IV",
        "HP_EV", "Attack_EV", "Defense_EV", "SpecialAttack_EV", "SpecialDefense_EV", "Speed_EV",
        "Nature", "Gender", "AbilitySlot", "HeldItem", "Friendship", "StatusCondition", "SleepCounter",
        "PokemonID", "OriginalTrainerName", "CurrentTrainerName", "OriginalTrainerID", "CurrentTrainerID",
        "CaughtBallName", "MetLocationOverride", "MetLevel", "MetType", "MemoNote", "EggCyclesRemaining",
        "EggSpeciesName", "EggShinyRolls", "bIsShiny", "bIsFainted", "bIsEgg", "bCannotEvolve",
        "bIsFollowerOut",
    )

    def __init__(self, parent: tk.Misc, app: "SaveEditorApp", title: str) -> None:
        super().__init__(parent, padding=8)
        self.app = app
        self.title_text = title
        self.current: PokemonView | None = None
        self.vars: dict[str, tk.Variable] = {}
        self.move_vars = [tk.StringVar() for _ in range(4)]
        self.current_pp_vars = [tk.StringVar(value="0") for _ in range(4)]
        self.max_pp_vars = [tk.StringVar(value="0") for _ in range(4)]
        self._build()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 7))
        self.heading_var = tk.StringVar(value=f"{self.title_text}: select a slot")
        ttk.Label(top, textvariable=self.heading_var, style="SectionTitle.TLabel").pack(side="left")
        self.apply_button = ttk.Button(top, text="Apply staged changes", command=self.apply, state="disabled")
        self.apply_button.pack(side="right")

        body = ttk.Panedwindow(self, orient="horizontal")
        body.grid(row=1, column=0, sticky="nsew")
        editor = ttk.Frame(body)
        preview = ttk.Frame(body, padding=(12, 6))
        body.add(editor, weight=4)
        body.add(preview, weight=1)

        self.sections = ttk.Notebook(editor)
        self.sections.pack(fill="both", expand=True)
        main = ttk.Frame(self.sections, padding=12)
        stats = ttk.Frame(self.sections, padding=12)
        moves = ttk.Frame(self.sections, padding=12)
        met = ttk.Frame(self.sections, padding=12)
        misc = ttk.Frame(self.sections, padding=12)
        for frame, label in ((main, "Main"), (stats, "Stats"), (moves, "Moves"), (met, "Met"), (misc, "OT / Misc")):
            self.sections.add(frame, text=label)

        for frame in (main, stats, moves, met, misc):
            frame.columnconfigure(1, weight=1)
            frame.columnconfigure(3, weight=1)

        self._choice(main, "Species", "SpeciesData", [item.name for item in SPECIES], 0, 0)
        self._entry(main, "Nickname", "Nickname", 0, 2)
        self._spin(main, "Level", "Level", 1, 0, 1, 100)
        self._entry(main, "EXP", "CurrentEXP", 1, 2)
        self._choice(main, "Nature", "Nature", list(NATURES), 2, 0)
        self._choice(main, "Gender", "Gender", list(GENDERS), 2, 2)
        self._readonly(main, "Ability", "Ability", 3, 0)
        self._spin(main, "Ability slot", "AbilitySlot", 3, 2, 0, 2)
        self._choice(main, "Held item", "HeldItem", list(ITEM_NAMES), 4, 0)
        self._spin(main, "Friendship", "Friendship", 4, 2, 0, 255)
        self._check(main, "Shiny", "bIsShiny", 5, 0)
        self._check(main, "Fainted", "bIsFainted", 5, 2)
        ttk.Label(
            main,
            text="Species replacement uses the verified GE-1.0.0 DataAsset path. Stats and ability are not auto-recalculated.",
            style="Muted.TLabel",
            wraplength=720,
        ).grid(row=6, column=0, columnspan=4, sticky="w", pady=(14, 0))

        self._entry(stats, "Current HP", "CurrentHP", 0, 0)
        self._entry(stats, "Max HP", "MaxHP", 0, 2)
        stat_names = ("HP", "Attack", "Defense", "SpecialAttack", "SpecialDefense", "Speed")
        ttk.Label(stats, text="Stat", style="Bold.TLabel").grid(row=2, column=0, sticky="w", pady=(12, 4))
        ttk.Label(stats, text="IV (0–31)", style="Bold.TLabel").grid(row=2, column=1, sticky="w", pady=(12, 4))
        ttk.Label(stats, text="EV (0–252)", style="Bold.TLabel").grid(row=2, column=2, sticky="w", pady=(12, 4))
        for row, stat in enumerate(stat_names, start=3):
            ttk.Label(stats, text=display_name(stat)).grid(row=row, column=0, sticky="w", pady=3)
            iv = tk.StringVar()
            ev = tk.StringVar()
            self.vars[stat + "_IV"] = iv
            self.vars[stat + "_EV"] = ev
            ev.trace_add("write", lambda *_args: self._update_ev_total())
            ttk.Spinbox(stats, textvariable=iv, from_=0, to=31, width=10).grid(row=row, column=1, sticky="w", pady=3)
            ttk.Spinbox(stats, textvariable=ev, from_=0, to=252, width=10).grid(row=row, column=2, sticky="w", pady=3)
        stat_buttons = ttk.Frame(stats)
        stat_buttons.grid(row=10, column=0, columnspan=4, sticky="w", pady=(12, 0))
        ttk.Button(stat_buttons, text="Max IVs", command=lambda: self._fill_stats("IV", 31)).pack(side="left")
        ttk.Button(stat_buttons, text="Clear EVs", command=lambda: self._fill_stats("EV", 0)).pack(side="left", padx=6)
        ttk.Button(stat_buttons, text="Balanced 510 EV", command=self._balanced_evs).pack(side="left")
        ttk.Checkbutton(
            stat_buttons,
            text="Allow EV total over 510",
            variable=self.app.allow_ev_over_510,
            command=self._update_ev_total,
        ).pack(side="left", padx=(16, 0))
        self.ev_total_var = tk.StringVar(value="EV total: 0 / 510")
        ttk.Label(stats, textvariable=self.ev_total_var, style="Muted.TLabel").grid(
            row=11, column=0, columnspan=4, sticky="w", pady=(8, 0)
        )

        ttk.Label(moves, text="Move", style="Bold.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(moves, text="Current PP", style="Bold.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(moves, text="Max PP", style="Bold.TLabel").grid(row=0, column=2, sticky="w")
        move_values = [""] + [item.name for item in MOVES]
        for index in range(4):
            ttk.Combobox(moves, textvariable=self.move_vars[index], values=move_values, state="readonly", width=30).grid(
                row=index + 1, column=0, sticky="ew", padx=(0, 8), pady=5
            )
            ttk.Spinbox(moves, textvariable=self.current_pp_vars[index], from_=0, to=99, width=10).grid(
                row=index + 1, column=1, sticky="w", padx=(0, 8), pady=5
            )
            ttk.Spinbox(moves, textvariable=self.max_pp_vars[index], from_=0, to=99, width=10).grid(
                row=index + 1, column=2, sticky="w", pady=5
            )
        ttk.Label(
            moves,
            text="Up to four verified move Blueprint paths. Current PP cannot exceed Max PP.",
            style="Muted.TLabel",
        ).grid(row=6, column=0, columnspan=3, sticky="w", pady=(12, 0))

        self._entry(met, "Met location", "MetLocationOverride", 0, 0)
        self._spin(met, "Met level", "MetLevel", 0, 2, 0, 100)
        self._choice(met, "Met type", "MetType", list(MET_TYPES), 1, 0)
        self._entry(met, "Caught ball", "CaughtBallName", 1, 2)
        self._entry(met, "Memo", "MemoNote", 2, 0, span=3)
        self._check(met, "Egg", "bIsEgg", 3, 0)
        self._spin(met, "Egg cycles", "EggCyclesRemaining", 3, 2, 0, 9999)
        self._entry(met, "Egg species", "EggSpeciesName", 4, 0)
        self._spin(met, "Shiny rolls", "EggShinyRolls", 4, 2, 0, 9999)
        self._check(met, "Cannot evolve", "bCannotEvolve", 5, 0)

        self._entry(misc, "Pokémon ID", "PokemonID", 0, 0)
        self._choice(misc, "Status", "StatusCondition", list(STATUS_CONDITIONS), 0, 2)
        self._spin(misc, "Sleep counter", "SleepCounter", 1, 0, 0, 99)
        self._entry(misc, "Original trainer", "OriginalTrainerName", 2, 0)
        self._entry(misc, "Original trainer ID", "OriginalTrainerID", 2, 2)
        self._entry(misc, "Current trainer", "CurrentTrainerName", 3, 0)
        self._entry(misc, "Current trainer ID", "CurrentTrainerID", 3, 2)
        self._check(misc, "Follower out", "bIsFollowerOut", 4, 0)

        ttk.Label(preview, text="Preview", style="SectionTitle.TLabel").pack(anchor="w")
        self.preview = tk.Canvas(preview, width=230, height=300, highlightthickness=1, highlightbackground="#9aa4ad")
        self.preview.pack(fill="both", expand=True, pady=(8, 0))
        self._draw_preview(None)

    def _entry(self, parent, label: str, field: str, row: int, column: int, span: int = 1) -> None:
        var = tk.StringVar()
        self.vars[field] = var
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", padx=(0, 6), pady=5)
        ttk.Entry(parent, textvariable=var).grid(
            row=row, column=column + 1, columnspan=span, sticky="ew", padx=(0, 14), pady=5
        )

    def _spin(self, parent, label: str, field: str, row: int, column: int, low: int, high: int) -> None:
        var = tk.StringVar()
        self.vars[field] = var
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", padx=(0, 6), pady=5)
        ttk.Spinbox(parent, textvariable=var, from_=low, to=high).grid(
            row=row, column=column + 1, sticky="ew", padx=(0, 14), pady=5
        )

    def _choice(self, parent, label: str, field: str, values: list[str], row: int, column: int) -> None:
        var = tk.StringVar()
        self.vars[field] = var
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", padx=(0, 6), pady=5)
        ttk.Combobox(parent, textvariable=var, values=values, state="readonly").grid(
            row=row, column=column + 1, sticky="ew", padx=(0, 14), pady=5
        )

    def _readonly(self, parent, label: str, field: str, row: int, column: int) -> None:
        var = tk.StringVar()
        self.vars[field] = var
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", padx=(0, 6), pady=5)
        ttk.Entry(parent, textvariable=var, state="readonly").grid(
            row=row, column=column + 1, sticky="ew", padx=(0, 14), pady=5
        )

    def _check(self, parent, label: str, field: str, row: int, column: int) -> None:
        var = tk.BooleanVar()
        self.vars[field] = var
        ttk.Checkbutton(parent, text=label, variable=var).grid(
            row=row, column=column, columnspan=2, sticky="w", pady=5
        )

    def _fill_stats(self, suffix: str, value: int) -> None:
        for stat in ("HP", "Attack", "Defense", "SpecialAttack", "SpecialDefense", "Speed"):
            self.vars[stat + "_" + suffix].set(str(value))
        self._update_ev_total()

    def _balanced_evs(self) -> None:
        values = (85, 85, 85, 85, 85, 85)
        for stat, value in zip(("HP", "Attack", "Defense", "SpecialAttack", "SpecialDefense", "Speed"), values):
            self.vars[stat + "_EV"].set(str(value))
        self._update_ev_total()

    def _update_ev_total(self) -> None:
        total = sum(_number(self.vars[field].get()) for field in self.vars if field.endswith("_EV"))
        suffix = "limit disabled" if self.app.allow_ev_over_510.get() else "max 510"
        self.ev_total_var.set(f"EV total: {total} ({suffix})")

    def load(self, pokemon: PokemonView | None) -> None:
        self.current = pokemon
        if pokemon is None:
            self.heading_var.set(f"{self.title_text}: select a slot")
            for var in self.vars.values():
                var.set(False if isinstance(var, tk.BooleanVar) else "")
            for var in (*self.move_vars, *self.current_pp_vars, *self.max_pp_vars):
                var.set("")
            self.apply_button.configure(state="disabled")
            self._draw_preview(None)
            return
        if not pokemon.occupied:
            document = self.app.current_document()
            if document is None:
                self.apply_button.configure(state="disabled")
                return
            location = (
                f"next Party slot {pokemon.slot_index + 1}"
                if pokemon.source == "Party"
                else f"Box {int(pokemon.box_index or 0) + 1}, slot {pokemon.slot_index + 1}"
            )
            self.heading_var.set(f"Create Pokemon - {location}")
            defaults = pokemon_creation_defaults(document)
            for field, var in self.vars.items():
                value = "" if field == "SpeciesData" else defaults.get(field, "")
                if field in ENUM_PREFIXES:
                    value = _enum_leaf(value)
                elif field == "Ability":
                    value = "None"
                if isinstance(var, tk.BooleanVar):
                    var.set(bool(value))
                else:
                    var.set(str(value))
            for var in self.move_vars:
                var.set("")
            for var in (*self.current_pp_vars, *self.max_pp_vars):
                var.set("0")
            self.apply_button.configure(text="Create Pokemon", state="normal")
            self._update_ev_total()
            self._draw_preview(None)
            return
        fields = pokemon.fields
        self.heading_var.set(f"{self.title_text}: Slot {pokemon.slot_index + 1} — {pokemon.species}")
        for field, var in self.vars.items():
            value = fields.get(field, "")
            if field == "SpeciesData":
                value = pokemon.species
            elif field in ENUM_PREFIXES or field == "Ability":
                value = _enum_leaf(value)
            if isinstance(var, tk.BooleanVar):
                var.set(bool(value))
            else:
                var.set(str(value))
        move_names = fields.get("MoveNames", ())
        current_pp = fields.get("CurrentPP", ())
        max_pp = fields.get("MaxPP", ())
        for index in range(4):
            self.move_vars[index].set(display_name(str(move_names[index])) if index < len(move_names) else "")
            self.current_pp_vars[index].set(str(current_pp[index]) if index < len(current_pp) else "0")
            self.max_pp_vars[index].set(str(max_pp[index]) if index < len(max_pp) else "0")
        self.apply_button.configure(text="Apply staged changes", state="normal")
        self._update_ev_total()
        self._draw_preview(pokemon)

    def _draw_preview(self, pokemon: PokemonView | None) -> None:
        canvas = self.preview
        canvas.delete("all")
        width = max(canvas.winfo_width(), 230)
        if pokemon is None:
            canvas.create_rectangle(12, 12, width - 12, 285, fill="#f1f4f6", outline="#aab2b9")
            canvas.create_text(width / 2, 145, text="(Empty slot)", fill="#66717a", font=("Segoe UI", 11))
            return
        fields = pokemon.fields
        category = next((item.category for item in SPECIES if item.name == pokemon.species), "Normal")
        colors = {
            "Water": "#bfe2ff", "Fire": "#ffd0bd", "Grass": "#cbeec5", "Electric": "#fff0a8",
            "Psychic": "#f4c7e5", "Dark": "#c9c1ba", "Steel": "#d7dde5", "Dragon": "#d5cbff",
            "Bug": "#e2edb0", "Poison": "#dfc3ee", "Rock": "#dfd0ad", "Fighting": "#efc0b8",
        }
        bg = colors.get(category, "#e5ecef")
        canvas.create_rectangle(12, 12, width - 12, 285, fill=bg, outline="#77838d", width=2)
        initials = "".join(word[0] for word in pokemon.species.split()[:2]).upper()
        canvas.create_oval(width / 2 - 48, 36, width / 2 + 48, 132, fill="#ffffff", outline="#77838d", width=2)
        canvas.create_text(width / 2, 84, text=initials or "?", font=("Segoe UI", 24, "bold"), fill="#39434b")
        shiny = " ★" if fields.get("bIsShiny") else ""
        canvas.create_text(width / 2, 155, text=pokemon.species + shiny, font=("Segoe UI", 13, "bold"))
        canvas.create_text(width / 2, 179, text=f"Lv. {_number(fields.get('Level'), 1)}  •  {category}")
        hp = max(0, _number(fields.get("CurrentHP")))
        max_hp = max(1, _number(fields.get("MaxHP"), 1))
        ratio = min(1.0, hp / max_hp)
        canvas.create_rectangle(30, 202, width - 30, 220, fill="#5b646b", outline="")
        hp_color = "#43a047" if ratio > 0.5 else "#f9a825" if ratio > 0.2 else "#d32f2f"
        canvas.create_rectangle(32, 204, 32 + (width - 64) * ratio, 218, fill=hp_color, outline="")
        canvas.create_text(width / 2, 235, text=f"HP {hp} / {max_hp}")
        item = str(fields.get("HeldItem", "None"))
        status = _enum_leaf(fields.get("StatusCondition", "None"))
        canvas.create_text(width / 2, 261, text=f"Item: {item}  •  Status: {status}", width=width - 30)

    def apply(self) -> None:
        pokemon = self.current
        document = self.app.current_document()
        if pokemon is None or document is None:
            return
        by_path = {item.path: item for item in document.properties}
        changes: dict[str, object] = {}
        try:
            if pokemon.occupied:
                for field in self.SCALAR_FIELDS:
                    path = pokemon.prefix + "." + field
                    prop = by_path.get(path)
                    if prop is None or not prop.editable or field == "Ability":
                        continue
                    raw: object = self.vars[field].get()
                    if field in ENUM_PREFIXES:
                        raw = f"{ENUM_PREFIXES[field]}::{raw}"
                    value = self.app.coerce_property_value(prop, raw)
                    if value != prop.value:
                        changes[field] = value
            else:
                template_props: dict[str, PropertyRecord] = {}
                for prop in document.properties:
                    if prop.path.startswith("Boxes[") and ".Pokemon" in prop.path:
                        template_props.setdefault(prop.name, prop)
                for field in self.SCALAR_FIELDS:
                    prop = template_props.get(field)
                    if prop is None or field == "Ability":
                        continue
                    raw = self.vars[field].get()
                    if field in ENUM_PREFIXES:
                        raw = f"{ENUM_PREFIXES[field]}::{raw}"
                    changes[field] = self.app.coerce_property_value(prop, raw)

            current_hp = float(self.vars["CurrentHP"].get())
            max_hp = float(self.vars["MaxHP"].get())
            if max_hp <= 0 or current_hp > max_hp:
                raise ValueError("Current HP must be between 0 and Max HP, and Max HP must be positive.")

            species_name = str(self.vars["SpeciesData"].get()).strip()
            species = SPECIES_BY_NAME.get(species_name.casefold())
            if species is None:
                raise ValueError("Choose a Species from the verified GE-1.0.0 catalog.")
            species_change = species if species.name != pokemon.species else None
            if pokemon.occupied and species_change and not messagebox.askyesno(
                APP_TITLE,
                "Change Species DataAsset?\n\nGamma does not store enough verified base-stat metadata for automatic "
                "recalculation yet. Review HP, ability and moves before saving.",
            ):
                return

            moves = []
            current_pp: list[int] = []
            max_pp: list[int] = []
            for index, var in enumerate(self.move_vars):
                name = var.get().strip()
                if not name:
                    continue
                move = MOVES_BY_NAME.get(name.casefold())
                if move is None:
                    raise ValueError(f"Move {name!r} is not in the verified GE-1.0.0 catalog.")
                moves.append(move)
                current_pp.append(int(self.current_pp_vars[index].get()))
                max_pp.append(int(self.max_pp_vars[index].get()))
            if pokemon.occupied:
                old_names = tuple(display_name(str(value)) for value in pokemon.fields.get("MoveNames", ()))
                moves_changed = tuple(move.name for move in moves) != old_names
                pp_changed = tuple(current_pp) != tuple(pokemon.fields.get("CurrentPP", ())) or tuple(max_pp) != tuple(
                    pokemon.fields.get("MaxPP", ())
                )
                self.app.stage_pokemon(
                    pokemon,
                    changes,
                    species=species_change,
                    moves=moves if moves_changed else None,
                    current_pp=current_pp if moves_changed or pp_changed else None,
                    max_pp=max_pp if moves_changed or pp_changed else None,
                )
            else:
                self.app.stage_new_pokemon(
                    pokemon,
                    changes,
                    species=species,
                    moves=moves if moves else None,
                    current_pp=current_pp if moves else None,
                    max_pp=max_pp if moves else None,
                )
        except (ValueError, GammaEditorError) as exc:
            messagebox.showerror(APP_TITLE, str(exc))


class SaveEditorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1360x840")
        self.minsize(1080, 680)
        self.loaded: LoadedSave | None = None
        self.working_gvas: bytes | None = None
        self._cached_gvas: bytes | None = None
        self._cached_document = None
        self.dirty = False
        self.allow_ev_over_510 = tk.BooleanVar(value=False)
        self.party_views: list[PokemonView] = []
        self.storage_views: list[PokemonView] = []
        self.bag_views: list[BagEntry] = []
        self.selected_pokemon_location: tuple[str, int | None, int] = ("party", None, 0)
        self.drag_source: tuple[str, int | None, int] | None = None
        self._build_style()
        self._build_toolbar()
        self._build_tabs()
        self._build_status()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind_all("<Control-s>", lambda _event: self.save())
        self.bind_all("<Control-o>", lambda _event: self.open_dialog())
        self.bind_all("<Control-r>", lambda _event: self.reload())
        self.after(100, self._open_default)

    def _build_style(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("AppTitle.TLabel", font=("Segoe UI", 15, "bold"))
        style.configure("SectionTitle.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("Bold.TLabel", font=("Segoe UI", 9, "bold"))
        style.configure("Muted.TLabel", foreground="#58646e")
        style.configure("Treeview", rowheight=25)

    def _build_toolbar(self) -> None:
        header = ttk.Frame(self, padding=(10, 8))
        header.pack(fill="x")
        ttk.Label(header, text=APP_TITLE, style="AppTitle.TLabel").pack(side="left", padx=(0, 18))
        ttk.Label(header, text="Save File:").pack(side="left")
        self.path_var = tk.StringVar()
        ttk.Entry(header, textvariable=self.path_var, state="readonly").pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(header, text="Refresh", command=self.refresh_saves).pack(side="left", padx=3)
        ttk.Button(header, text="Browse…", command=self.open_dialog).pack(side="left", padx=3)
        ttk.Button(header, text="Load", command=self.reload).pack(side="left", padx=3)
        ttk.Button(header, text="Backups…", command=self.open_backups_dialog).pack(side="left", padx=3)
        self.save_button = ttk.Button(header, text="Save + Backup", command=self.save, state="disabled")
        self.save_button.pack(side="left", padx=(10, 3))

    def _build_tabs(self) -> None:
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self.trainer_tab = ttk.Frame(self.tabs, padding=12)
        self.pokemon_tab = ttk.Frame(self.tabs, padding=8)
        self.bag_tab = ttk.Frame(self.tabs, padding=10)
        self.dex_tab = ttk.Frame(self.tabs, padding=10)
        for frame, label in (
            (self.trainer_tab, "Trainer"), (self.pokemon_tab, "Pokémon"),
            (self.bag_tab, "Bag"), (self.dex_tab, "Pokédex"),
        ):
            self.tabs.add(frame, text=label)
        self._build_trainer()
        self._build_pokemon()
        self._build_bag()
        self._build_dex()

    def _build_pokemon(self) -> None:
        self.pokemon_tab.rowconfigure(0, weight=1)
        self.pokemon_tab.columnconfigure(1, weight=1)
        roster = ttk.Frame(self.pokemon_tab, padding=(2, 2, 10, 2))
        roster.grid(row=0, column=0, sticky="ns")

        ttk.Label(roster, text="Party", style="SectionTitle.TLabel").pack(anchor="w")
        ttk.Label(
            roster, text="Drag a Pokémon card between Party and the current Box.", style="Muted.TLabel"
        ).pack(anchor="w", pady=(1, 6))
        self.party_grid = ttk.Frame(roster)
        self.party_grid.pack(fill="x")
        self.party_cards: list[tk.Label] = []
        for index in range(6):
            card = tk.Label(
                self.party_grid, width=16, height=3, relief="ridge", borderwidth=1,
                bg="#f2f5f7", anchor="center", justify="center", cursor="hand2",
            )
            card.grid(row=index // 3, column=index % 3, sticky="nsew", padx=2, pady=2)
            card.pokemon_location = ("party", None, index)  # type: ignore[attr-defined]
            card.bind("<ButtonPress-1>", lambda _event, loc=card.pokemon_location: self._on_pokemon_press(loc))
            card.bind("<ButtonRelease-1>", self._on_pokemon_release)
            self.party_cards.append(card)

        controls = ttk.Frame(roster)
        controls.pack(fill="x", pady=(14, 5))
        ttk.Label(controls, text="Storage Box:", style="SectionTitle.TLabel").pack(side="left")
        self.box_var = tk.StringVar()
        self.box_combo = ttk.Combobox(controls, textvariable=self.box_var, state="readonly", width=18)
        self.box_combo.pack(side="left", padx=5)
        self.box_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_pokemon_workspace())
        ttk.Button(controls, text="◀", width=3, command=lambda: self._step_box(-1)).pack(side="left")
        ttk.Button(controls, text="▶", width=3, command=lambda: self._step_box(1)).pack(side="left", padx=2)

        self.storage_grid = ttk.Frame(roster)
        self.storage_grid.pack(fill="both", expand=True)
        self.storage_cards: list[tk.Label] = []
        for index in range(30):
            card = tk.Label(
                self.storage_grid, width=10, height=3, relief="ridge", borderwidth=1,
                bg="#f7f8f9", anchor="center", justify="center", cursor="hand2",
            )
            card.grid(row=index // 5, column=index % 5, sticky="nsew", padx=2, pady=2)
            card.bind(
                "<ButtonPress-1>",
                lambda _event, slot=index: self._on_pokemon_press(("storage", self._selected_box_index(), slot)),
            )
            card.bind("<ButtonRelease-1>", self._on_pokemon_release)
            self.storage_cards.append(card)
        for column in range(5):
            self.storage_grid.columnconfigure(column, weight=1)
        for row in range(6):
            self.storage_grid.rowconfigure(row, weight=1)

        self.pokemon_editor = PokemonEditor(self.pokemon_tab, self, "Pokémon")
        self.pokemon_editor.grid(row=0, column=1, sticky="nsew")

    def _build_trainer(self) -> None:
        self.trainer_tab.columnconfigure(1, weight=1)
        ttk.Label(self.trainer_tab, text="Trainer", style="AppTitle.TLabel").grid(row=0, column=0, columnspan=4, sticky="w")
        self.trainer_vars: dict[str, tk.StringVar] = {}
        fields = (
            ("Name", "PlayerName"), ("Trainer ID", "PlayerId"), ("Money", "PlayerMoney"),
            ("Game Corner coins", "GameCornerCoins"), ("Current map", "CurrentMapName"),
            ("Time played (seconds)", "TotalTimePlayed"), ("Hours", "CurrentHours"),
            ("Minutes", "CurrentMinutes"), ("Seconds", "CurrentSeconds"),
        )
        for row, (label, path) in enumerate(fields, start=1):
            ttk.Label(self.trainer_tab, text=label, width=24).grid(row=row, column=0, sticky="w", pady=5)
            var = tk.StringVar()
            self.trainer_vars[path] = var
            ttk.Entry(self.trainer_tab, textvariable=var).grid(row=row, column=1, sticky="ew", pady=5, padx=(0, 16))
        ttk.Button(self.trainer_tab, text="Apply staged changes", command=self.apply_trainer).grid(
            row=len(fields) + 1, column=0, columnspan=2, sticky="w", pady=(16, 0)
        )
        ttk.Label(
            self.trainer_tab,
            text="Trainer Name/ID changes are synchronized to matching owned Pokémon. Changes stay staged until Save + Backup.",
            style="Muted.TLabel",
            wraplength=760,
        ).grid(row=len(fields) + 2, column=0, columnspan=2, sticky="w", pady=(8, 0))

    def _build_party(self) -> None:
        self.party_tab.rowconfigure(0, weight=1)
        self.party_tab.columnconfigure(1, weight=1)
        left = ttk.Frame(self.party_tab, padding=(0, 4, 8, 4))
        left.grid(row=0, column=0, sticky="ns")
        ttk.Label(left, text="Party slots", style="SectionTitle.TLabel").pack(anchor="w", pady=(0, 6))
        self.party_tree = ttk.Treeview(left, columns=("pokemon", "level", "hp"), show="tree headings", height=12)
        self.party_tree.heading("#0", text="#")
        self.party_tree.column("#0", width=38, anchor="center")
        for name, title, width in (("pokemon", "Pokémon", 125), ("level", "Lv", 42), ("hp", "HP", 72)):
            self.party_tree.heading(name, text=title)
            self.party_tree.column(name, width=width, anchor="w")
        self.party_tree.pack(fill="y", expand=True)
        self.party_tree.bind("<<TreeviewSelect>>", self._on_party_selected)
        self.party_editor = PokemonEditor(self.party_tab, self, "Party")
        self.party_editor.grid(row=0, column=1, sticky="nsew")

    def _build_storage(self) -> None:
        self.storage_tab.rowconfigure(1, weight=1)
        self.storage_tab.columnconfigure(1, weight=1)
        controls = ttk.Frame(self.storage_tab)
        controls.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 7))
        ttk.Label(controls, text="Box:").pack(side="left")
        self.box_var = tk.StringVar()
        self.box_combo = ttk.Combobox(controls, textvariable=self.box_var, state="readonly", width=28)
        self.box_combo.pack(side="left", padx=6)
        self.box_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_storage())
        ttk.Button(controls, text="◀", width=4, command=lambda: self._step_box(-1)).pack(side="left")
        ttk.Button(controls, text="▶", width=4, command=lambda: self._step_box(1)).pack(side="left", padx=3)
        ttk.Label(controls, text="Select an empty slot to create a Pokemon.", style="Muted.TLabel").pack(
            side="left", padx=14
        )
        left = ttk.Frame(self.storage_tab, padding=(0, 4, 8, 4))
        left.grid(row=1, column=0, sticky="ns")
        self.storage_tree = ttk.Treeview(left, columns=("pokemon", "level", "item"), show="headings", height=20)
        for name, title, width in (("pokemon", "Slot / Pokémon", 150), ("level", "Lv", 40), ("item", "Item", 90)):
            self.storage_tree.heading(name, text=title)
            self.storage_tree.column(name, width=width, anchor="w")
        self.storage_tree.pack(fill="y", expand=True)
        self.storage_tree.bind("<<TreeviewSelect>>", self._on_storage_selected)
        self.storage_editor = PokemonEditor(self.storage_tab, self, "Storage")
        self.storage_editor.grid(row=1, column=1, sticky="nsew")

    def _build_bag(self) -> None:
        self.bag_tab.rowconfigure(1, weight=1)
        self.bag_tab.columnconfigure(0, weight=1)
        header = ttk.Frame(self.bag_tab)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(header, text="Bag", style="AppTitle.TLabel").pack(side="left")
        ttk.Button(header, text="+ Add Item", command=self.open_add_item_dialog).pack(side="right")
        body = ttk.Panedwindow(self.bag_tab, orient="horizontal")
        body.grid(row=1, column=0, sticky="nsew")
        listing = ttk.Frame(body)
        editor = ttk.Frame(body, padding=14)
        body.add(listing, weight=4)
        body.add(editor, weight=2)
        self.bag_pocket_tabs = ttk.Notebook(listing)
        self.bag_pocket_tabs.pack(fill="both", expand=True)
        self.bag_trees: dict[str, ttk.Treeview] = {}
        for pocket in BAG_POCKETS:
            frame = ttk.Frame(self.bag_pocket_tabs, padding=4)
            self.bag_pocket_tabs.add(frame, text=BAG_POCKET_LABELS[pocket])
            tree = ttk.Treeview(frame, columns=("item", "quantity"), show="headings")
            tree.heading("item", text="Item")
            tree.heading("quantity", text="Quantity")
            tree.column("item", width=320, anchor="w")
            tree.column("quantity", width=100, anchor="center")
            tree.pack(fill="both", expand=True)
            tree.bind("<<TreeviewSelect>>", lambda _event, name=pocket: self._on_bag_selected(name))
            self.bag_trees[pocket] = tree
        ttk.Label(editor, text="Selected item", style="SectionTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        self.bag_pocket_var = tk.StringVar(value="—")
        self.bag_name_var = tk.StringVar()
        self.bag_qty_var = tk.StringVar()
        ttk.Label(editor, text="Pocket").grid(row=1, column=0, sticky="w", pady=(14, 5))
        ttk.Label(editor, textvariable=self.bag_pocket_var, style="Bold.TLabel").grid(row=1, column=1, sticky="w", pady=(14, 5))
        ttk.Label(editor, text="Item").grid(row=2, column=0, sticky="w", pady=5)
        self.bag_name_combo = ttk.Combobox(editor, textvariable=self.bag_name_var, state="readonly")
        self.bag_name_combo.grid(row=2, column=1, sticky="ew", pady=5)
        ttk.Label(editor, text="Quantity").grid(row=3, column=0, sticky="w", pady=5)
        ttk.Spinbox(editor, textvariable=self.bag_qty_var, from_=1, to=9999).grid(row=3, column=1, sticky="ew", pady=5)
        self.bag_apply_button = ttk.Button(editor, text="Apply staged changes", command=self.apply_bag, state="disabled")
        self.bag_apply_button.grid(row=4, column=0, sticky="w", pady=(14, 0))
        self.bag_remove_button = ttk.Button(editor, text="Remove Item", command=self.remove_selected_bag_item, state="disabled")
        self.bag_remove_button.grid(row=4, column=1, sticky="w", pady=(14, 0), padx=(8, 0))
        ttk.Label(editor, text="All edits stay staged until Save + Backup.", style="Muted.TLabel").grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )
        editor.columnconfigure(1, weight=1)

    def _build_dex(self) -> None:
        self.dex_tab.rowconfigure(1, weight=1)
        self.dex_tab.columnconfigure(0, weight=1)
        header = ttk.Frame(self.dex_tab)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(header, text="Pokédex", style="AppTitle.TLabel").pack(side="left")
        ttk.Label(header, text="Search:").pack(side="left", padx=(28, 5))
        self.dex_search_var = tk.StringVar()
        dex_search = ttk.Entry(header, textvariable=self.dex_search_var, width=30)
        dex_search.pack(side="left")
        dex_search.bind("<KeyRelease>", lambda _event: self._refresh_dex(self.current_document()))
        body = ttk.Panedwindow(self.dex_tab, orient="horizontal")
        body.grid(row=1, column=0, sticky="nsew")
        listing = ttk.Frame(body)
        details = ttk.Frame(body, padding=16)
        body.add(listing, weight=2)
        body.add(details, weight=3)
        self.dex_tree = ttk.Treeview(listing, columns=("id", "species", "type"), show="headings")
        for name, title, width in (("id", "Hoenn #", 80), ("species", "Pokémon", 220), ("type", "Primary type", 120)):
            self.dex_tree.heading(name, text=title)
            self.dex_tree.column(name, width=width, anchor="w")
        self.dex_tree.pack(fill="both", expand=True)
        self.dex_tree.bind("<<TreeviewSelect>>", self._on_dex_selected)
        ttk.Label(details, text="Pokémon information", style="SectionTitle.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )
        self.dex_detail_vars: dict[str, tk.StringVar] = {}
        for row, (label, key) in enumerate((
            ("Name", "name"), ("Hoenn number", "number"), ("Primary type", "type"),
            ("Gamma DataAsset", "asset"), ("Owned locations", "owned"),
        ), start=1):
            ttk.Label(details, text=label + ":", width=18).grid(row=row, column=0, sticky="nw", pady=5)
            var = tk.StringVar(value="—")
            self.dex_detail_vars[key] = var
            ttk.Label(details, textvariable=var, wraplength=620).grid(row=row, column=1, sticky="nw", pady=5)
        ttk.Label(
            details,
            text="This Pokédex describes the Pokémon assets available in Gamma GE-1.0.0; it is independent from your in-game Seen/Caught progress.",
            style="Muted.TLabel", wraplength=650,
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(18, 0))
        details.columnconfigure(1, weight=1)

    def _build_legality(self) -> None:
        self.legality_tab.rowconfigure(2, weight=1)
        self.legality_tab.columnconfigure(0, weight=1)
        ttk.Label(self.legality_tab, text="Legality Check", style="AppTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.legality_summary_var = tk.StringVar(value="Open a story save to run checks.")
        ttk.Label(self.legality_tab, textvariable=self.legality_summary_var, style="SectionTitle.TLabel").grid(
            row=1, column=0, sticky="w", pady=8
        )
        self.legality_tree = ttk.Treeview(
            self.legality_tab, columns=("severity", "owner", "message"), show="headings"
        )
        for name, title, width in (
            ("severity", "Severity", 90), ("owner", "Location", 260), ("message", "Finding", 720),
        ):
            self.legality_tree.heading(name, text=title)
            self.legality_tree.column(name, width=width, anchor="w")
        self.legality_tree.grid(row=2, column=0, sticky="nsew")
        self.legality_tree.tag_configure("Error", foreground="#b42318")
        self.legality_tree.tag_configure("Warning", foreground="#9a6700")
        ttk.Label(
            self.legality_tab,
            text="Checks cover catalog membership, Level, IV/EV, HP, friendship, move/PP alignment, duplicate IDs and Bag quantities.",
            style="Muted.TLabel",
        ).grid(row=3, column=0, sticky="w", pady=(8, 0))

    def _build_advanced(self) -> None:
        notebook = ttk.Notebook(self.advanced_tab)
        notebook.pack(fill="both", expand=True)
        overview = ttk.Frame(notebook, padding=12)
        properties = ttk.Frame(notebook, padding=8)
        backups = ttk.Frame(notebook, padding=8)
        diagnostics = ttk.Frame(notebook, padding=8)
        for frame, label in ((overview, "Overview"), (properties, "Properties"), (backups, "Backups"), (diagnostics, "Diagnostics")):
            notebook.add(frame, text=label)
        self.summary_vars: dict[str, tk.StringVar] = {}
        for row, (label, key) in enumerate((
            ("File", "path"), ("Slot", "slot"), ("Save class", "save_class"), ("Engine", "engine"),
            ("GVAS size", "size"), ("SHA-256", "sha"), ("Parser", "parser"),
        )):
            ttk.Label(overview, text=label + ":", width=16).grid(row=row, column=0, sticky="nw", pady=4)
            var = tk.StringVar(value="—")
            self.summary_vars[key] = var
            ttk.Label(overview, textvariable=var, wraplength=900).grid(row=row, column=1, sticky="nw", pady=4)
        overview.columnconfigure(1, weight=1)

        properties.rowconfigure(1, weight=1)
        properties.columnconfigure(0, weight=1)
        filters = ttk.Frame(properties)
        filters.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Label(filters, text="Filter:").pack(side="left")
        self.filter_var = tk.StringVar()
        entry = ttk.Entry(filters, textvariable=self.filter_var, width=40)
        entry.pack(side="left", padx=6)
        entry.bind("<KeyRelease>", lambda _event: self._refresh_properties())
        ttk.Button(filters, text="Edit selected", command=self.edit_selected_property).pack(side="left")
        columns = ("path", "type", "value", "editable")
        self.property_tree = ttk.Treeview(properties, columns=columns, show="headings")
        for name, title, width in (("path", "Schema path", 420), ("type", "Type", 220), ("value", "Value", 360), ("editable", "Edit", 55)):
            self.property_tree.heading(name, text=title)
            self.property_tree.column(name, width=width, anchor="w")
        self.property_tree.grid(row=1, column=0, sticky="nsew")
        self.property_tree.bind("<Double-1>", lambda _event: self.edit_selected_property())

        backups.rowconfigure(1, weight=1)
        backups.columnconfigure(0, weight=1)
        actions = ttk.Frame(backups)
        actions.grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Button(actions, text="Refresh", command=self._refresh_backups).pack(side="left")
        ttk.Button(actions, text="Restore selected", command=self.restore_selected).pack(side="left", padx=6)
        self.backup_tree = ttk.Treeview(backups, columns=("time", "size", "path"), show="headings")
        for name, title, width in (("time", "Time", 180), ("size", "Size", 100), ("path", "Path", 780)):
            self.backup_tree.heading(name, text=title)
            self.backup_tree.column(name, width=width, anchor="w")
        self.backup_tree.grid(row=1, column=0, sticky="nsew")

        diagnostics.rowconfigure(0, weight=1)
        diagnostics.columnconfigure(0, weight=1)
        self.diagnostics = tk.Text(diagnostics, wrap="word", font=("Consolas", 10))
        self.diagnostics.grid(row=0, column=0, sticky="nsew")

    def _build_status(self) -> None:
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w", padding=(8, 3)).pack(fill="x")

    def _open_default(self) -> None:
        saves = discover_saves()
        choice = max(saves, key=lambda path: path.stat().st_size) if saves else None
        if choice:
            self.open_save(choice)
        else:
            self.status_var.set(f"No saves found in {default_save_dir()}")

    def refresh_saves(self) -> None:
        if self.loaded:
            self.reload()
        else:
            self._open_default()

    def open_dialog(self) -> None:
        if not self._confirm_discard():
            return
        path = filedialog.askopenfilename(
            title="Open Gamma Emerald save", initialdir=default_save_dir(),
            filetypes=(("Gamma save", "*.dat"), ("All files", "*.*")),
        )
        if path:
            self.open_save(Path(path))

    def open_backups_dialog(self) -> None:
        if self.loaded is None:
            messagebox.showinfo(APP_TITLE, "Load a save first.")
            return
        dialog = tk.Toplevel(self)
        dialog.title("Save Backups")
        dialog.transient(self)
        dialog.geometry("900x420")
        dialog.rowconfigure(0, weight=1)
        dialog.columnconfigure(0, weight=1)
        tree = ttk.Treeview(dialog, columns=("time", "size", "path"), show="headings")
        for name, title, width in (("time", "Time", 180), ("size", "Size", 100), ("path", "Backup", 560)):
            tree.heading(name, text=title)
            tree.column(name, width=width, anchor="w")
        tree.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        for path in list_backups(self.loaded.path):
            stat = path.stat()
            tree.insert(
                "", "end", iid=str(path),
                values=(datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"), f"{stat.st_size:,}", str(path)),
            )

        def restore() -> None:
            selected = tree.selection()
            if not selected or self.loaded is None:
                return
            backup = Path(selected[0])
            if not messagebox.askyesno(APP_TITLE, f"Restore this backup?\n\n{backup}", parent=dialog):
                return
            try:
                safety = restore_backup(self.loaded.path, backup)
                dialog.destroy()
                self.open_save(self.loaded.path)
                messagebox.showinfo(APP_TITLE, f"Backup restored.\nPre-restore copy: {safety}")
            except (OSError, GammaEditorError) as exc:
                messagebox.showerror(APP_TITLE, str(exc), parent=dialog)

        ttk.Button(dialog, text="Restore selected", command=restore).grid(row=1, column=0, sticky="e", padx=10, pady=(0, 10))

    def open_save(self, path: Path) -> None:
        try:
            self.loaded = load_save(path)
            self.working_gvas = self.loaded.container.payload
            self.dirty = False
            self.path_var.set(str(path))
            self._refresh_all()
            self.status_var.set(f"Loaded {path.name}; integrity checks passed")
        except (OSError, GammaEditorError) as exc:
            messagebox.showerror(APP_TITLE, str(exc))

    def reload(self) -> None:
        if self.loaded and self._confirm_discard():
            self.open_save(self.loaded.path)

    def current_document(self):
        if self.working_gvas is None:
            return None
        if self._cached_gvas is not self.working_gvas:
            self._cached_document = parse_gvas(self.working_gvas)
            self._cached_gvas = self.working_gvas
        return self._cached_document

    def _refresh_all(self) -> None:
        doc = self.current_document()
        if doc is None or self.loaded is None:
            return
        self.party_views = party_pokemon(doc)
        self.bag_views = bag_entries(doc)
        self._refresh_trainer(doc)
        names = box_names(doc)
        current_box = self.box_var.get()
        self.box_combo.configure(values=names)
        self.box_var.set(current_box if current_box in names else (names[0] if names else ""))
        self._refresh_pokemon_workspace()
        self._refresh_bag()
        self._refresh_dex(doc)
        self._update_dirty_ui()

    def _refresh_trainer(self, doc) -> None:
        by_path = {item.path: item for item in doc.properties}
        for path, var in self.trainer_vars.items():
            item = by_path.get(path)
            var.set(str(item.value) if item else "")

    def _refresh_party(self) -> None:
        selected = self.party_tree.selection()
        selected_iid = selected[0] if selected else "0"
        self.party_tree.delete(*self.party_tree.get_children())
        by_slot = {item.slot_index: item for item in self.party_views}
        for index in range(6):
            pokemon = by_slot.get(index)
            if pokemon:
                fields = pokemon.fields
                hp = f"{_number(fields.get('CurrentHP'))}/{_number(fields.get('MaxHP'))}"
                values = (pokemon.species, _number(fields.get("Level")), hp)
            else:
                values = ("(empty)", "", "")
            self.party_tree.insert("", "end", iid=str(index), text=str(index + 1), values=values)
        if self.party_tree.exists(selected_iid):
            self.party_tree.selection_set(selected_iid)
        else:
            self.party_tree.selection_set("0")
        self._on_party_selected()

    def _on_party_selected(self, _event=None) -> None:
        selected = self.party_tree.selection()
        if not selected:
            return
        index = int(selected[0])
        pokemon = next((item for item in self.party_views if item.slot_index == index), None)
        self.party_editor.load(pokemon)

    def _selected_box_index(self) -> int:
        values = list(self.box_combo.cget("values"))
        try:
            return values.index(self.box_var.get())
        except ValueError:
            return 0

    def _step_box(self, delta: int) -> None:
        values = list(self.box_combo.cget("values"))
        if not values:
            return
        index = (self._selected_box_index() + delta) % len(values)
        self.box_var.set(values[index])
        self._refresh_pokemon_workspace()

    def _refresh_pokemon_workspace(self) -> None:
        doc = self.current_document()
        if doc is None:
            return
        self.party_views = party_pokemon(doc)
        box = self._selected_box_index()
        self.storage_views = storage_pokemon(doc, box)
        party_by_slot = {item.slot_index: item for item in self.party_views}
        storage_by_slot = {item.slot_index: item for item in self.storage_views}
        selected = self.selected_pokemon_location
        if selected[0] == "storage" and selected[1] != box:
            selected = ("storage", box, selected[2])
            self.selected_pokemon_location = selected
        for index, card in enumerate(self.party_cards):
            pokemon = party_by_slot.get(index)
            text = f"{index + 1}\n{pokemon.species}\nLv {_number(pokemon.fields.get('Level'))}" if pokemon else f"{index + 1}\n(empty)"
            card.configure(
                text=text,
                bg="#d9edf7" if selected == ("party", None, index) else "#f2f5f7",
                relief="solid" if selected == ("party", None, index) else "ridge",
                borderwidth=2 if selected == ("party", None, index) else 1,
            )
        for index, card in enumerate(self.storage_cards):
            location = ("storage", box, index)
            card.pokemon_location = location  # type: ignore[attr-defined]
            pokemon = storage_by_slot.get(index)
            occupied = bool(pokemon and pokemon.occupied)
            text = f"{index + 1}\n{pokemon.species}\nLv {_number(pokemon.fields.get('Level'))}" if occupied else f"{index + 1}\n—"
            card.configure(
                text=text,
                bg="#d9edf7" if selected == location else ("#eef7e9" if occupied else "#f7f8f9"),
                relief="solid" if selected == location else "ridge",
                borderwidth=2 if selected == location else 1,
            )
        self._select_pokemon_location(selected, refresh_cards=False)

    def _select_pokemon_location(
        self,
        location: tuple[str, int | None, int],
        *,
        refresh_cards: bool = True,
    ) -> None:
        kind, box, slot = location
        self.selected_pokemon_location = location
        if kind == "party":
            pokemon = next((item for item in self.party_views if item.slot_index == slot), None)
            if pokemon is None:
                next_slot = len(self.party_views)
                pokemon = PokemonView(
                    prefix=f"Party[{next_slot}]",
                    source="Party",
                    box_index=None,
                    slot_index=next_slot,
                    species="Empty",
                    occupied=False,
                    fields={},
                )
        else:
            pokemon = next((item for item in self.storage_views if item.slot_index == slot), None)
        self.pokemon_editor.load(pokemon)
        if refresh_cards:
            self._refresh_pokemon_workspace()

    def _on_pokemon_press(self, location: tuple[str, int | None, int]) -> None:
        self._select_pokemon_location(location)
        kind, _box, slot = location
        views = self.party_views if kind == "party" else self.storage_views
        pokemon = next((item for item in views if item.slot_index == slot), None)
        self.drag_source = location if pokemon and pokemon.occupied else None
        if self.drag_source is not None:
            self.status_var.set("Drag to another Party or Storage card to move/swap the complete Pokémon.")
        else:
            self.status_var.set("Choose a Species and click Create Pokemon to fill this empty slot.")

    def _on_pokemon_release(self, event) -> None:
        source = self.drag_source
        self.drag_source = None
        if source is None:
            return
        widget = self.winfo_containing(event.x_root, event.y_root)
        target = None
        while widget is not None:
            target = getattr(widget, "pokemon_location", None)
            if target is not None:
                break
            widget = getattr(widget, "master", None)
        if target is None or target == source:
            return
        doc = self.current_document()
        if doc is None:
            return
        party_count = len(self.party_views)
        try:
            raw = move_pokemon(
                doc,
                source_kind=source[0], source_box=source[1], source_slot=source[2],
                target_kind=target[0], target_box=target[1], target_slot=target[2],
            )
            if target[0] == "party" and target[2] >= party_count:
                target = ("party", None, party_count - (1 if source[0] == "party" else 0))
            self.selected_pokemon_location = target
            self.working_gvas = raw
            self._mark_staged("Staged Pokémon move/swap")
        except (ValueError, GammaEditorError) as exc:
            messagebox.showerror(APP_TITLE, str(exc))

    def _refresh_storage(self) -> None:
        doc = self.current_document()
        if doc is None:
            return
        box = self._selected_box_index()
        self.storage_views = storage_pokemon(doc, box)
        selected = self.storage_tree.selection()
        selected_iid = selected[0] if selected else "0"
        self.storage_tree.delete(*self.storage_tree.get_children())
        by_slot = {item.slot_index: item for item in self.storage_views}
        for index in range(30):
            pokemon = by_slot.get(index)
            if pokemon and pokemon.occupied:
                values = (f"{index + 1}. {pokemon.species}", _number(pokemon.fields.get("Level")), pokemon.fields.get("HeldItem", "None"))
            else:
                values = (f"{index + 1}. (empty)", "", "")
            self.storage_tree.insert("", "end", iid=str(index), values=values)
        if self.storage_tree.exists(selected_iid):
            self.storage_tree.selection_set(selected_iid)
        else:
            self.storage_tree.selection_set("0")
        self._on_storage_selected()

    def _on_storage_selected(self, _event=None) -> None:
        selected = self.storage_tree.selection()
        if not selected:
            return
        index = int(selected[0])
        pokemon = next((item for item in self.storage_views if item.slot_index == index), None)
        self.storage_editor.load(pokemon)

    def _refresh_bag(self) -> None:
        selected_prefix = getattr(self, "selected_bag_prefix", None)
        self.bag_iid_map: dict[tuple[str, str], BagEntry] = {}
        selected_location: tuple[str, str] | None = None
        for pocket, tree in self.bag_trees.items():
            tree.delete(*tree.get_children())
            entries = [item for item in self.bag_views if item.category == pocket]
            for row, item in enumerate(entries):
                iid = str(row)
                tree.insert("", "end", iid=iid, values=(item.name, item.quantity))
                self.bag_iid_map[(pocket, iid)] = item
                if item.prefix == selected_prefix:
                    selected_location = (pocket, iid)
        if selected_location:
            pocket, iid = selected_location
            self.bag_trees[pocket].selection_set(iid)
            self._on_bag_selected(pocket)
        else:
            self.selected_bag_entry = None
            self.bag_pocket_var.set("—")
            self.bag_name_var.set("")
            self.bag_qty_var.set("")
            self.bag_apply_button.configure(state="disabled")
            self.bag_remove_button.configure(state="disabled")

    def _on_bag_selected(self, pocket: str) -> None:
        tree = self.bag_trees[pocket]
        selected = tree.selection()
        if not selected:
            return
        for other_pocket, other_tree in self.bag_trees.items():
            if other_pocket != pocket:
                other_tree.selection_remove(*other_tree.selection())
        item = self.bag_iid_map[(pocket, selected[0])]
        self.selected_bag_entry = item
        self.selected_bag_prefix = item.prefix
        self.bag_pocket_var.set(BAG_POCKET_LABELS.get(pocket, pocket))
        self.bag_name_combo.configure(values=[choice.name for choice in ITEMS_BY_POCKET[pocket]])
        self.bag_name_var.set(item.name)
        self.bag_qty_var.set(str(item.quantity))
        self.bag_apply_button.configure(state="normal")
        self.bag_remove_button.configure(state="normal")

    def open_add_item_dialog(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Add Item")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        pocket_var = tk.StringVar()
        item_var = tk.StringVar()
        qty_var = tk.StringVar(value="1")
        labels = [BAG_POCKET_LABELS[pocket] for pocket in BAG_POCKETS]
        label_to_pocket = {BAG_POCKET_LABELS[pocket]: pocket for pocket in BAG_POCKETS}
        ttk.Label(dialog, text="Pocket").grid(row=0, column=0, sticky="w", padx=12, pady=(14, 6))
        pocket_combo = ttk.Combobox(dialog, textvariable=pocket_var, values=labels, state="readonly", width=28)
        pocket_combo.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=(14, 6))
        ttk.Label(dialog, text="Item").grid(row=1, column=0, sticky="w", padx=12, pady=6)
        item_combo = ttk.Combobox(dialog, textvariable=item_var, state="disabled", width=28)
        item_combo.grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=6)
        ttk.Label(dialog, text="Quantity").grid(row=2, column=0, sticky="w", padx=12, pady=6)
        ttk.Spinbox(dialog, textvariable=qty_var, from_=1, to=9999, width=29).grid(
            row=2, column=1, sticky="ew", padx=(0, 12), pady=6
        )

        def pocket_changed(_event=None) -> None:
            pocket = label_to_pocket.get(pocket_var.get())
            item_var.set("")
            item_combo.configure(
                state="readonly" if pocket else "disabled",
                values=[choice.name for choice in ITEMS_BY_POCKET[pocket]] if pocket else (),
            )

        def add() -> None:
            doc = self.current_document()
            pocket = label_to_pocket.get(pocket_var.get())
            if doc is None or pocket is None or not item_var.get():
                messagebox.showerror(APP_TITLE, "Choose a pocket and an item.", parent=dialog)
                return
            try:
                self.working_gvas = add_bag_item(doc, pocket, item_var.get(), int(qty_var.get()))
                dialog.destroy()
                self._mark_staged(f"Staged add/update: {item_var.get()}")
            except (ValueError, GammaEditorError) as exc:
                messagebox.showerror(APP_TITLE, str(exc), parent=dialog)

        pocket_combo.bind("<<ComboboxSelected>>", pocket_changed)
        ttk.Button(dialog, text="Add Item", command=add).grid(row=3, column=1, sticky="e", padx=12, pady=(10, 14))
        dialog.bind("<Return>", lambda _event: add())

    def remove_selected_bag_item(self) -> None:
        doc = self.current_document()
        item = getattr(self, "selected_bag_entry", None)
        if doc is None or item is None:
            return
        if not messagebox.askyesno(APP_TITLE, f"Remove {item.name} from {BAG_POCKET_LABELS.get(item.category, item.category)}?"):
            return
        try:
            self.working_gvas = remove_bag_item(doc, item)
            self.selected_bag_prefix = None
            self._mark_staged(f"Staged removal: {item.name}")
        except (ValueError, GammaEditorError) as exc:
            messagebox.showerror(APP_TITLE, str(exc))

    def _refresh_dex(self, doc) -> None:
        if doc is None:
            return
        selected = self.dex_tree.selection()
        selected_name = selected[0] if selected else ""
        needle = self.dex_search_var.get().strip().casefold()
        dex_by_name = {name: number for number, name in HOENN_DEX.items()}
        self.dex_tree.delete(*self.dex_tree.get_children())
        for species in SPECIES:
            haystack = f"{species.name} {species.category} {dex_by_name.get(species.name, '')}".casefold()
            if needle and needle not in haystack:
                continue
            self.dex_tree.insert(
                "", "end", iid=species.name,
                values=(dex_by_name.get(species.name, "—"), species.name, species.category),
            )
        children = self.dex_tree.get_children()
        choice = selected_name if selected_name and self.dex_tree.exists(selected_name) else (children[0] if children else "")
        if choice:
            self.dex_tree.selection_set(choice)
            self.dex_tree.see(choice)
            self._on_dex_selected()

    def _on_dex_selected(self, _event=None) -> None:
        selected = self.dex_tree.selection()
        if not selected:
            return
        name = selected[0]
        species = SPECIES_BY_NAME.get(name.casefold())
        if species is None:
            return
        dex_by_name = {value: key for key, value in HOENN_DEX.items()}
        locations: list[str] = []
        for pokemon in self.party_views:
            if pokemon.species == species.name:
                locations.append(f"Party {pokemon.slot_index + 1}")
        doc = self.current_document()
        if doc is not None:
            for box_index, box_name in enumerate(box_names(doc)):
                for pokemon in storage_pokemon(doc, box_index):
                    if pokemon.occupied and pokemon.species == species.name:
                        locations.append(f"{box_name} / Slot {pokemon.slot_index + 1}")
        self.dex_detail_vars["name"].set(species.name)
        self.dex_detail_vars["number"].set(str(dex_by_name.get(species.name, "Not mapped")))
        self.dex_detail_vars["type"].set(species.category)
        self.dex_detail_vars["asset"].set(species.path)
        self.dex_detail_vars["owned"].set(", ".join(locations) if locations else "None in Party/Storage")

    def _refresh_legality(self, doc) -> None:
        findings = legality_issues(doc)
        self.legality_tree.delete(*self.legality_tree.get_children())
        for index, finding in enumerate(findings):
            self.legality_tree.insert(
                "", "end", iid=str(index),
                values=(finding.severity, finding.owner, finding.message), tags=(finding.severity,),
            )
        errors = sum(item.severity == "Error" for item in findings)
        warnings = sum(item.severity == "Warning" for item in findings)
        if not findings:
            self.legality_summary_var.set("No issues found in verified fields.")
        else:
            self.legality_summary_var.set(f"{errors} error(s), {warnings} warning(s)")

    def _refresh_overview(self, doc) -> None:
        assert self.loaded is not None and self.working_gvas is not None
        header = doc.header
        self.summary_vars["path"].set(str(self.loaded.path))
        self.summary_vars["slot"].set(self.loaded.container.slot_name)
        self.summary_vars["save_class"].set(header.save_game_class)
        self.summary_vars["engine"].set(f"{header.engine.major}.{header.engine.minor}.{header.engine.patch} ({header.engine.branch})")
        self.summary_vars["size"].set(f"{len(self.working_gvas):,} bytes")
        self.summary_vars["sha"].set(hashlib.sha256(self.working_gvas).hexdigest())
        self.summary_vars["parser"].set(doc.property_error or f"{len(doc.properties):,} tagged properties parsed")

    def _refresh_properties(self) -> None:
        doc = self.current_document()
        if doc is None:
            return
        needle = self.filter_var.get().strip().casefold()
        self.property_tree.delete(*self.property_tree.get_children())
        for index, prop in enumerate(doc.properties):
            haystack = f"{prop.path} {prop.type_descriptor} {prop.value}".casefold()
            if needle and needle not in haystack:
                continue
            self.property_tree.insert(
                "", "end", iid=str(index),
                values=(prop.path or prop.name, prop.type_descriptor or prop.type_name, repr(prop.value), "yes" if prop.editable else "no"),
            )

    def _refresh_backups(self) -> None:
        self.backup_tree.delete(*self.backup_tree.get_children())
        if self.loaded is None:
            return
        for path in list_backups(self.loaded.path):
            stat = path.stat()
            self.backup_tree.insert(
                "", "end", iid=str(path),
                values=(datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"), f"{stat.st_size:,}", str(path)),
            )

    def _refresh_diagnostics(self, doc) -> None:
        header = doc.header
        lines = [
            f"Container slot : {self.loaded.container.slot_name if self.loaded else '—'}",
            f"Save class     : {header.save_game_class}",
            f"GVAS version   : {header.save_game_version}",
            f"UE4 / UE5 pkg  : {header.package_file_version_ue4} / {header.package_file_version_ue5}",
            f"Engine         : {header.engine.major}.{header.engine.minor}.{header.engine.patch}",
            f"Properties     : {len(doc.properties):,}",
            f"Parser note    : {doc.property_error or 'complete'}",
            f"Catalog        : {len(SPECIES)} species / {len(MOVES)} moves",
            "",
            "Unknown data is preserved byte-for-byte. Verified empty Pokemon structs can be activated; unsupported collections remain locked.",
        ]
        self.diagnostics.configure(state="normal")
        self.diagnostics.delete("1.0", "end")
        self.diagnostics.insert("1.0", "\n".join(lines))
        self.diagnostics.configure(state="disabled")

    def apply_trainer(self) -> None:
        doc = self.current_document()
        if doc is None:
            return
        by_path = {item.path: item for item in doc.properties}
        changes: dict[str, object] = {}
        try:
            for path, var in self.trainer_vars.items():
                prop = by_path.get(path)
                if prop is None or not prop.editable:
                    continue
                value = self.coerce_property_value(prop, var.get())
                if value != prop.value:
                    changes[path] = value
            if not changes:
                self.status_var.set("Trainer: no changes to stage")
                return
            self.working_gvas = patch_domain_values(doc, changes)
            self._mark_staged(f"Staged {len(changes)} Trainer field(s)")
        except (ValueError, GammaEditorError) as exc:
            messagebox.showerror(APP_TITLE, str(exc))

    def stage_pokemon(
        self,
        pokemon: PokemonView,
        scalar_changes: dict[str, object],
        *,
        species=None,
        moves=None,
        current_pp=None,
        max_pp=None,
    ) -> None:
        doc = self.current_document()
        if doc is None:
            return
        self.working_gvas = patch_pokemon(
            doc, pokemon, scalar_changes=scalar_changes, species=species, moves=moves,
            current_pp=current_pp, max_pp=max_pp,
            allow_ev_over_510=self.allow_ev_over_510.get(),
        )
        count = len(scalar_changes) + (1 if species else 0) + (1 if moves is not None else 0)
        self._mark_staged(f"Staged {count} change group(s) for {pokemon.species}")

    def stage_new_pokemon(
        self,
        pokemon: PokemonView,
        scalar_changes: dict[str, object],
        *,
        species,
        moves=None,
        current_pp=None,
        max_pp=None,
    ) -> None:
        doc = self.current_document()
        if doc is None:
            return
        party_slot = (
            pokemon.slot_index
            if pokemon.source == "Party" and pokemon.slot_index < len(self.party_views)
            else len(self.party_views)
        )
        self.configure(cursor="wait")
        self.update_idletasks()
        try:
            self.working_gvas = create_pokemon(
                doc,
                pokemon,
                species=species,
                scalar_changes=scalar_changes,
                moves=moves,
                current_pp=current_pp,
                max_pp=max_pp,
                allow_ev_over_510=self.allow_ev_over_510.get(),
            )
        finally:
            self.configure(cursor="")
        self.selected_pokemon_location = (
            ("party", None, party_slot)
            if pokemon.source == "Party"
            else ("storage", pokemon.box_index, pokemon.slot_index)
        )
        self._mark_staged(f"Created {species.name} in an empty {pokemon.source} slot")

    def apply_bag(self) -> None:
        doc = self.current_document()
        item = getattr(self, "selected_bag_entry", None)
        if doc is None or item is None:
            return
        try:
            quantity = int(self.bag_qty_var.get())
            item_name = self.bag_name_var.get().strip()
            if item_name == item.name and quantity == item.quantity:
                self.status_var.set("Bag: no changes to stage")
                return
            self.working_gvas = edit_bag_item(doc, item, item_name, quantity)
            self.selected_bag_prefix = item.prefix
            self._mark_staged(f"Staged Bag edit: {item.name}")
        except (ValueError, GammaEditorError) as exc:
            messagebox.showerror(APP_TITLE, str(exc))

    def _mark_staged(self, message: str) -> None:
        self.dirty = bool(self.loaded and self.working_gvas != self.loaded.container.payload)
        self._refresh_all()
        self.status_var.set(message + "; live save unchanged")

    def edit_selected_property(self) -> None:
        selected = self.property_tree.selection()
        doc = self.current_document()
        if not selected or doc is None:
            return
        prop = doc.properties[int(selected[0])]
        if not prop.editable:
            messagebox.showinfo(APP_TITLE, "This property is read-only in the verified serializer.")
            return
        if prop.type_name == "EnumProperty":
            messagebox.showinfo(
                APP_TITLE,
                "Enum values are edited through the validated Trainer, Party, or Storage forms.",
            )
            return
        dialog = tk.Toplevel(self)
        dialog.title("Edit property")
        dialog.transient(self)
        dialog.grab_set()
        ttk.Label(dialog, text=prop.path, wraplength=520).pack(anchor="w", padx=12, pady=(12, 4))
        var = tk.StringVar(value=str(prop.value))
        entry = ttk.Entry(dialog, textvariable=var, width=72)
        entry.pack(fill="x", padx=12, pady=6)
        entry.focus_set()
        def apply_value() -> None:
            try:
                value = self.coerce_property_value(prop, var.get())
                self.working_gvas = patch_scalar(doc, prop.path, value)
                dialog.destroy()
                self._mark_staged(f"Staged property {prop.path}")
            except (ValueError, GammaEditorError) as exc:
                messagebox.showerror(APP_TITLE, str(exc), parent=dialog)
        ttk.Button(dialog, text="Apply staged change", command=apply_value).pack(anchor="e", padx=12, pady=(4, 12))
        dialog.bind("<Return>", lambda _event: apply_value())

    @staticmethod
    def coerce_property_value(prop: PropertyRecord, raw: object) -> object:
        if prop.type_name == "BoolProperty":
            if isinstance(raw, bool):
                return raw
            lowered = str(raw).strip().lower()
            if lowered not in {"true", "false", "1", "0", "yes", "no"}:
                raise ValueError("Use true/false or 1/0.")
            return lowered in {"true", "1", "yes"}
        if "Float" in prop.type_name or "Double" in prop.type_name:
            return float(raw)
        if prop.type_name in {
            "Int8Property", "ByteProperty", "UInt8Property", "Int16Property", "UInt16Property",
            "IntProperty", "Int32Property", "UInt32Property", "Int64Property", "UInt64Property",
        }:
            return int(str(raw), 0)
        return str(raw)

    def save(self) -> None:
        if self.loaded is None or self.working_gvas is None or not self.dirty:
            return
        if not messagebox.askyesno(APP_TITLE, "Write all staged changes? A timestamped backup will be created first."):
            return
        try:
            backup = write_save(self.loaded, self.working_gvas)
            self.open_save(self.loaded.path)
            messagebox.showinfo(APP_TITLE, f"Saved and verified.\nBackup: {backup}")
        except (OSError, GammaEditorError) as exc:
            messagebox.showerror(APP_TITLE, str(exc))

    def restore_selected(self) -> None:
        selected = self.backup_tree.selection()
        if self.loaded is None or not selected:
            return
        backup = Path(selected[0])
        if not messagebox.askyesno(APP_TITLE, f"Restore this backup?\n\n{backup}"):
            return
        try:
            safety = restore_backup(self.loaded.path, backup)
            self.open_save(self.loaded.path)
            messagebox.showinfo(APP_TITLE, f"Backup restored.\nPre-restore copy: {safety}")
        except (OSError, GammaEditorError) as exc:
            messagebox.showerror(APP_TITLE, str(exc))

    def _update_dirty_ui(self) -> None:
        self.save_button.configure(state="normal" if self.dirty else "disabled")
        self.title(APP_TITLE + (" *" if self.dirty else ""))

    def _confirm_discard(self) -> bool:
        return not self.dirty or messagebox.askyesno(APP_TITLE, "Discard all staged, unsaved changes?")

    def _on_close(self) -> None:
        if self._confirm_discard():
            self.destroy()


def main() -> None:
    app = SaveEditorApp()
    if "--smoke-test" in sys.argv:
        app._open_default()
        app.update()
        app.update_idletasks()
        app.destroy()
        return
    app.mainloop()
