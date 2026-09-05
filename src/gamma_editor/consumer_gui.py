from __future__ import annotations

from datetime import datetime
import hashlib
from pathlib import Path
import re
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .catalog import (
    BAG_POCKETS,
    BAG_POCKET_LABELS,
    GENDERS,
    HOLDABLE_ITEM_NAMES,
    HOENN_DEX,
    ITEMS_BY_POCKET,
    ITEM_NAMES,
    MET_TYPES,
    MOVES,
    MOVES_BY_NAME,
    NATURES,
    NATURE_BY_LABEL,
    NATURE_LABELS,
    SPECIES,
    SPECIES_BY_NAME,
    SPECIES_INFO,
    STATUS_CONDITIONS,
    TYPE_COLORS,
    TYPE_ORDER,
    base_pp_for_move,
    calculate_pokemon_stats,
    display_name,
    learnset_for_species,
    max_pp_for_move,
    nature_label,
    pp_up_limit_for_move,
    pp_ups_from_max_pp,
    type_attacks,
    type_defenses,
)
from .domain import (
    BagEntry,
    PokemonClonePreset,
    PokemonView,
    add_bag_item,
    bag_entries,
    box_names,
    copy_pokemon_preset,
    create_pokemon,
    edit_bag_item,
    move_pokemon,
    party_pokemon,
    patch_domain_values,
    patch_pokemon,
    pokemon_creation_defaults,
    pokemon_species_profile,
    release_pokemon,
    set_pokemon_preset,
    remove_bag_item,
    storage_pokemon,
)
from .evolution_data import evolution_family
from .errors import GammaEditorError
from .gvas import PropertyRecord, parse_gvas, patch_scalar
from .item_mod_templates import (
    ITEM_MOD_ARCHETYPES,
    TEMPLATE_BY_KEY,
    player_effect_summary,
    templates_for_archetype,
)
from .mod_builder import (
    BALL_TYPES,
    CUSTOM_ITEM_ID_BASE,
    ItemModSpec,
    ModBuilderError,
    POKEMON_TYPES,
    VITAMIN_EV_AMOUNTS,
    VITAMIN_STATS,
    allocate_custom_item_id,
    build_item_mod,
    custom_item_id_tag,
    discover_toolchain,
    install_item_mod,
    installed_item,
    uninstall_item_mod,
)
from .save_service import (
    LoadedSave,
    default_save_dir,
    discover_saves,
    list_backups,
    load_save,
    restore_backup,
    write_save,
)
from .sprites import SpriteRepository
from .vitamin_runtime import (
    VitaminRuntimeConfig,
    discover_vitamin_runtime_environment,
    install_vitamin_runtime,
    installed_vitamin_runtime_config,
    uninstall_vitamin_runtime,
)


APP_TITLE = "Gamma Emerald Save Editor"
ENUM_PREFIXES = {
    "Ability": "EPokemonAbility",
    "Nature": "ENature",
    "Gender": "EPokemonGender",
    "StatusCondition": "ESTATUSEffect",
    "MetType": "EPokemonMetType",
}
MOVE_SOURCE_FILTERS = (
    "All legal",
    "Level-up (current level)",
    "TM",
    "HM",
    "Egg",
)
MOVE_SOURCE_KEYS = {
    "All legal": "all",
    "Level-up (current level)": "level_up",
    "TM": "tm",
    "HM": "hm",
    "Egg": "egg",
}


def _enum_leaf(value: object) -> str:
    return str(value or "").split("::")[-1]


def _number(value: object, fallback: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return fallback


def pokemon_showdown_preset(pokemon: PokemonView) -> str:
    """Render the copied record as a familiar, readable Showdown-style set."""
    fields = pokemon.fields
    nickname = str(fields.get("Nickname", "")).strip()
    title = pokemon.species if not nickname or nickname.casefold() == "none" else f"{nickname} ({pokemon.species})"
    gender = str(fields.get("Gender", "")).split("::")[-1]
    if gender in {"Male", "Female"}:
        title += f" ({gender[0]})"
    held_item = str(fields.get("HeldItem", "")).strip()
    if held_item and held_item.casefold() != "none":
        title += f" @ {held_item}"
    lines = [title]
    ability = display_name(str(fields.get("Ability", "None")).split("::")[-1])
    if ability.casefold() != "none":
        lines.append(f"Ability: {ability}")
    lines.append(f"Level: {_number(fields.get('Level'), 1)}")
    if bool(fields.get("bIsShiny", False)):
        lines.append("Shiny: Yes")
    stats = (
        ("HP", "HP"), ("Attack", "Atk"), ("Defense", "Def"),
        ("SpecialAttack", "SpA"), ("SpecialDefense", "SpD"), ("Speed", "Spe"),
    )
    evs = " / ".join(f"{_number(fields.get(name + '_EV'))} {label}" for name, label in stats)
    lines.append("EVs: " + evs)
    nature = display_name(str(fields.get("Nature", "Hardy")).split("::")[-1])
    lines.append(f"{nature} Nature")
    ivs = " / ".join(f"{_number(fields.get(name + '_IV'))} {label}" for name, label in stats)
    lines.append("IVs: " + ivs)
    lines.extend(f"- {display_name(str(move))}" for move in fields.get("MoveNames", ()) if str(move))
    return "\n".join(lines)


def party_set_target_slot(party_count: int, clicked_slot: int) -> int | None:
    """Map any displayed empty Party card to the next packed-array position."""
    if not 0 <= party_count < 6 or not party_count <= clicked_slot < 6:
        return None
    return party_count


def _type_text_color(type_name: str) -> str:
    color = TYPE_COLORS.get(type_name, "#a8a77a").lstrip("#")
    red, green, blue = (int(color[index:index + 2], 16) for index in (0, 2, 4))
    luminance = (red * 299 + green * 587 + blue * 114) / 1000
    return "#ffffff" if luminance < 145 else "#111111"


def _light_type_color(type_name: str, white_ratio: float = .72) -> str:
    color = TYPE_COLORS.get(type_name, "#a8a77a").lstrip("#")
    channels = [int(color[index:index + 2], 16) for index in (0, 2, 4)]
    mixed = [round(channel + (255 - channel) * white_ratio) for channel in channels]
    return "#" + "".join(f"{channel:02x}" for channel in mixed)


def filter_choices(values: tuple[str, ...] | list[str], query: str) -> tuple[str, ...]:
    """Case-insensitive live-search with prefix matches before contains matches."""
    needle = query.strip().casefold()
    source = tuple(values)
    if not needle:
        return source
    prefix = [value for value in source if value.casefold().startswith(needle)]
    contains = [value for value in source if needle in value.casefold() and value not in prefix]
    return tuple((*prefix, *contains))


def exact_choice(values: tuple[str, ...] | list[str], value: object) -> str | None:
    """Return the catalog spelling for a case-insensitive exact user entry."""
    needle = str(value).strip().casefold()
    return next((choice for choice in values if choice.casefold() == needle), None)


def validated_enum_value(field: str, value: object) -> str:
    """Normalize a searchable catalog selection to the enum string stored by Gamma."""
    catalogs = {
        "Gender": GENDERS,
        "StatusCondition": STATUS_CONDITIONS,
        "MetType": MET_TYPES,
    }
    allowed = catalogs[field]
    selected = exact_choice(list(allowed), value)
    if selected is None:
        labels = {
            "Gender": "Gender",
            "StatusCondition": "status condition",
            "MetType": "met type",
        }
        raise ValueError(f"Choose a valid {labels[field]}.")
    return f"{ENUM_PREFIXES[field]}::{selected}"


class SearchableCombobox(ttk.Frame):
    """Search entry with a non-focus-stealing popup list.

    Native Windows ttk combobox popdowns take keyboard focus as soon as they are posted, which
    interrupts live typing after the first character. This composite keeps focus in its Entry and
    uses a lightweight popup only for the filtered choices.
    """

    _IGNORED_RELEASE_KEYS = {
        "Up", "Down", "Left", "Right", "Home", "End", "Prior", "Next",
        "Return", "Escape", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R",
    }

    def __init__(self, parent, *, values=(), textvariable=None, width=None, state="normal", **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self._source_values = tuple(str(value) for value in values)
        self._matches = self._source_values
        self._enabled = state != "disabled"
        self.variable = textvariable or tk.StringVar(self)
        self.columnconfigure(0, weight=1)

        entry_options = {"textvariable": self.variable}
        if width is not None:
            entry_options["width"] = width
        self.entry = ttk.Entry(self, **entry_options)
        self.entry.grid(row=0, column=0, sticky="ew")
        self.arrow = ttk.Button(self, text="▾", width=2, takefocus=False, command=self._toggle_popup)
        self.arrow.grid(row=0, column=1, sticky="ns")

        self._popup: tk.Toplevel | None = None
        self._listbox: tk.Listbox | None = None
        self._owner = self.winfo_toplevel()
        self._outside_binding = self._owner.bind("<ButtonPress-1>", self._on_owner_click, add="+")

        self.entry.bind("<KeyRelease>", self._on_key_release, add="+")
        self.entry.bind("<Down>", lambda _event: self._move_selection(1), add="+")
        self.entry.bind("<Up>", lambda _event: self._move_selection(-1), add="+")
        self.entry.bind("<Return>", self._commit_from_keyboard, add="+")
        self.entry.bind("<Escape>", lambda _event: self._hide_popup(), add="+")
        self.entry.bind("<FocusOut>", lambda _event: self.after_idle(self._hide_if_focus_left), add="+")
        self.set_source_values(self._source_values, enabled=self._enabled)

    def destroy(self) -> None:
        self._hide_popup(destroy=True)
        try:
            self._owner.unbind("<ButtonPress-1>", self._outside_binding)
        except tk.TclError:
            pass
        super().destroy()

    def get(self) -> str:
        return str(self.variable.get())

    def set(self, value: object) -> None:
        self.variable.set(str(value))

    def set_source_values(self, values, *, enabled: bool = True) -> None:
        self._source_values = tuple(str(value) for value in values)
        self._matches = self._source_values
        self._enabled = enabled
        widget_state = "normal" if enabled else "disabled"
        self.entry.configure(state=widget_state)
        self.arrow.configure(state=widget_state)
        if not enabled:
            self._hide_popup()

    def _ensure_popup(self) -> None:
        if self._popup is not None and self._popup.winfo_exists():
            return
        popup = tk.Toplevel(self)
        popup.withdraw()
        popup.overrideredirect(True)
        popup.transient(self._owner)
        border = ttk.Frame(popup, relief="solid", borderwidth=1)
        border.pack(fill="both", expand=True)
        listbox = tk.Listbox(
            border,
            activestyle="none",
            exportselection=False,
            highlightthickness=0,
            borderwidth=0,
            selectmode="browse",
        )
        scrollbar = ttk.Scrollbar(border, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        listbox.bind("<ButtonRelease-1>", self._commit_from_mouse)
        listbox.bind("<Return>", self._commit_from_keyboard)
        listbox.bind("<Escape>", lambda _event: self._hide_popup())
        self._popup = popup
        self._listbox = listbox

    def _render_matches(self, matches: tuple[str, ...]) -> None:
        self._ensure_popup()
        assert self._listbox is not None
        self._matches = matches
        self._listbox.delete(0, "end")
        for value in matches:
            self._listbox.insert("end", value)
        self._listbox.selection_clear(0, "end")
        if matches:
            self._listbox.activate(0)

    def _show_popup(self, matches: tuple[str, ...], *, select_text: bool = False) -> None:
        if not self._enabled:
            return
        self._render_matches(matches)
        if not matches:
            self._hide_popup()
            return
        assert self._popup is not None
        self.update_idletasks()
        rows = min(12, len(matches))
        width = max(self.winfo_width(), 180)
        height = rows * 22 + 2
        self._popup.geometry(f"{width}x{height}+{self.winfo_rootx()}+{self.winfo_rooty() + self.winfo_height()}")
        self._popup.deiconify()
        self._popup.lift()
        self.entry.focus_set()
        if select_text:
            self.entry.selection_range(0, "end")
            self.entry.icursor("end")

    def _hide_popup(self, *, destroy: bool = False) -> str:
        if self._popup is not None and self._popup.winfo_exists():
            if destroy:
                self._popup.destroy()
                self._popup = None
                self._listbox = None
            else:
                self._popup.withdraw()
        return "break"

    def _popup_visible(self) -> bool:
        return bool(self._popup is not None and self._popup.winfo_exists() and self._popup.state() == "normal")

    def _toggle_popup(self) -> None:
        if self._popup_visible():
            self._hide_popup()
            self.entry.focus_set()
            return
        self._show_popup(self._source_values, select_text=True)

    def _on_key_release(self, event) -> None:
        if event.keysym in self._IGNORED_RELEASE_KEYS or not self._enabled:
            return
        self._show_popup(filter_choices(self._source_values, self.get()))

    def _move_selection(self, direction: int) -> str:
        if not self._popup_visible():
            self._show_popup(filter_choices(self._source_values, self.get()))
        if self._listbox is None or not self._matches:
            return "break"
        selected = self._listbox.curselection()
        current = selected[0] if selected else (-1 if direction > 0 else 0)
        index = max(0, min(len(self._matches) - 1, current + direction))
        self._listbox.selection_clear(0, "end")
        self._listbox.selection_set(index)
        self._listbox.activate(index)
        self._listbox.see(index)
        return "break"

    def _commit_from_keyboard(self, _event=None) -> str:
        if not self._popup_visible() or self._listbox is None or not self._matches:
            return "break"
        selected = self._listbox.curselection()
        index = selected[0] if selected else self._listbox.index("active")
        self._choose(index)
        return "break"

    def _commit_from_mouse(self, event) -> str:
        if self._listbox is not None and self._matches:
            self._choose(self._listbox.nearest(event.y))
        return "break"

    def _choose(self, index: int) -> None:
        if not 0 <= index < len(self._matches):
            return
        self.variable.set(self._matches[index])
        self._hide_popup()
        self.entry.focus_set()
        self.entry.icursor("end")
        self.event_generate("<<ComboboxSelected>>")

    @staticmethod
    def _is_descendant(widget, ancestor) -> bool:
        current = widget
        while current is not None:
            if current is ancestor:
                return True
            current = getattr(current, "master", None)
        return False

    def _on_owner_click(self, event) -> None:
        if self._is_descendant(event.widget, self):
            return
        if self._popup is not None and self._is_descendant(event.widget, self._popup):
            return
        self._hide_popup()

    def _hide_if_focus_left(self) -> None:
        focus = self.focus_get()
        if focus is None:
            return
        if self._is_descendant(focus, self):
            return
        if self._popup is not None and self._is_descendant(focus, self._popup):
            return
        self._hide_popup()


class PokemonEditor(ttk.Frame):
    """Indigo-style grouped editor for one occupied Gamma Pokémon struct."""

    SCALAR_FIELDS = (
        "Nickname", "Level", "CurrentEXP", "CurrentHP", "MaxHP",
        "HP_IV", "Attack_IV", "Defense_IV", "SpecialAttack_IV", "SpecialDefense_IV", "Speed_IV",
        "HP_EV", "Attack_EV", "Defense_EV", "SpecialAttack_EV", "SpecialDefense_EV", "Speed_EV",
        "Nature", "Gender", "Ability", "AbilitySlot", "HeldItem", "Friendship", "StatusCondition", "SleepCounter",
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
        self.pp_up_vars = [tk.StringVar(value="0") for _ in range(4)]
        self.pp_max_vars = [tk.StringVar(value="—") for _ in range(4)]
        self.move_filter_var = tk.StringVar(value=MOVE_SOURCE_FILTERS[0])
        self.move_source_vars = [tk.StringVar(value="—") for _ in range(4)]
        self.move_combos: list[SearchableCombobox] = []
        self.current_pp_spins: list[ttk.Spinbox] = []
        self.pp_up_spins: list[ttk.Spinbox] = []
        self._pp_up_levels = [0, 0, 0, 0]
        self._loading_move_fields = False
        self._updating_pp_fields = False
        self._evolution_redraw_id: str | None = None
        self._stats_visual_redraw_id: str | None = None
        self._move_chart_redraw_id: str | None = None
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
        body.add(editor, weight=3)
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
        main.rowconfigure(9, weight=1)

        self.species_combo = self._choice(main, "Species", "SpeciesData", [item.name for item in SPECIES], 0, 0)
        self.species_combo.bind("<<ComboboxSelected>>", self._on_species_changed)
        self.vars["SpeciesData"].trace_add("write", lambda *_args: self._on_species_text_changed())
        self._entry(main, "Nickname", "Nickname", 0, 2)
        self._spin(main, "Level", "Level", 1, 0, 1, 100)
        self.vars["Level"].trace_add(
            "write", lambda *_args: (self._update_calculated_stats(), self._refresh_move_choices())
        )
        self._entry(main, "EXP", "CurrentEXP", 1, 2)
        self.nature_combo = self._choice(main, "Nature", "Nature", list(NATURE_LABELS), 2, 0)
        self.nature_combo.bind("<<ComboboxSelected>>", lambda _event: self._update_calculated_stats())
        self.vars["Nature"].trace_add("write", lambda *_args: self._update_calculated_stats())
        self._choice(main, "Gender", "Gender", list(GENDERS), 2, 2)
        self.ability_combo = self._choice(main, "Ability", "Ability", [], 3, 0)
        self.ability_combo.bind("<<ComboboxSelected>>", self._on_ability_changed)
        self._readonly(main, "Ability slot", "AbilitySlot", 3, 2)
        self.held_item_combo = self._choice(main, "Held item", "HeldItem", list(self.app._held_item_names()), 4, 0)
        self._spin(main, "Friendship", "Friendship", 4, 2, 0, 255)
        self._check(main, "Shiny", "bIsShiny", 5, 0)
        self._check(main, "Fainted", "bIsFainted", 5, 2)
        type_bar = ttk.Frame(main)
        type_bar.grid(row=6, column=0, columnspan=4, sticky="w", pady=(7, 0))
        ttk.Label(type_bar, text="Types", style="Bold.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.main_type_labels: list[tk.Label] = []
        for index in range(2):
            label = tk.Label(
                type_bar, text="—", width=10, height=1, relief="solid", borderwidth=1,
                font=("Segoe UI", 8, "bold"), padx=5, pady=2,
            )
            label.grid(row=0, column=index + 1, padx=(0, 5))
            self.main_type_labels.append(label)
        defaults_bar = ttk.Frame(main)
        defaults_bar.grid(row=7, column=0, columnspan=4, sticky="ew", pady=(9, 0))
        ttk.Button(
            defaults_bar,
            text="Load Species Defaults",
            command=self._load_species_defaults_into_form,
        ).pack(side="left")
        self.species_defaults_var = tk.StringVar(
            value="Selecting a Species loads its Lv. 5 base profile, starting moves, stats and met defaults."
        )
        ttk.Label(
            defaults_bar,
            textvariable=self.species_defaults_var,
            style="Muted.TLabel",
            wraplength=620,
        ).pack(side="left", padx=(12, 0), fill="x", expand=True)
        ttk.Label(
            main,
            text="Type to live-search any dropdown. Ability is Species-filtered; (H) marks a Hidden Ability.",
            style="Muted.TLabel",
            wraplength=720,
        ).grid(row=8, column=0, columnspan=4, sticky="w", pady=(8, 8))
        evolution_frame = ttk.LabelFrame(main, text="Evolution Chart", padding=6)
        evolution_frame.grid(row=9, column=0, columnspan=4, sticky="nsew")
        evolution_frame.rowconfigure(0, weight=1)
        evolution_frame.columnconfigure(0, weight=1)
        self.evolution_canvas = tk.Canvas(
            evolution_frame,
            height=220,
            background="#fbfcfd",
            highlightthickness=0,
        )
        self.evolution_canvas.grid(row=0, column=0, sticky="nsew")
        self.evolution_canvas.bind("<Configure>", self._queue_evolution_redraw)

        self._entry(stats, "Current HP", "CurrentHP", 0, 0)
        self._entry(stats, "Max HP", "MaxHP", 0, 2)
        stat_names = ("HP", "Attack", "Defense", "SpecialAttack", "SpecialDefense", "Speed")
        self.base_stat_vars = {stat: tk.StringVar(value="—") for stat in stat_names}
        self.final_stat_vars = {stat: tk.StringVar(value="—") for stat in stat_names}
        self.sync_calculated_hp = tk.BooleanVar(value=True)
        ttk.Label(stats, text="Stat", style="Bold.TLabel").grid(row=2, column=0, sticky="w", pady=(12, 4))
        ttk.Label(stats, text="Base", style="Bold.TLabel").grid(row=2, column=1, sticky="w", pady=(12, 4))
        ttk.Label(stats, text="IV (0–31)", style="Bold.TLabel").grid(row=2, column=2, sticky="w", pady=(12, 4))
        ttk.Label(stats, text="EV (0–252)", style="Bold.TLabel").grid(row=2, column=3, sticky="w", pady=(12, 4))
        ttk.Label(stats, text="Final", style="Bold.TLabel").grid(row=2, column=4, sticky="w", pady=(12, 4))
        for row, stat in enumerate(stat_names, start=3):
            ttk.Label(stats, text=display_name(stat)).grid(row=row, column=0, sticky="w", pady=3)
            ttk.Label(stats, textvariable=self.base_stat_vars[stat], width=8).grid(row=row, column=1, sticky="w", pady=3)
            iv = tk.StringVar()
            ev = tk.StringVar()
            self.vars[stat + "_IV"] = iv
            self.vars[stat + "_EV"] = ev
            iv.trace_add("write", lambda *_args: self._update_calculated_stats())
            ev.trace_add("write", lambda *_args: (self._update_ev_total(), self._update_calculated_stats()))
            ttk.Spinbox(stats, textvariable=iv, from_=0, to=31, width=10).grid(row=row, column=2, sticky="w", pady=3)
            ttk.Spinbox(stats, textvariable=ev, from_=0, to=252, width=10).grid(row=row, column=3, sticky="w", pady=3)
            ttk.Label(stats, textvariable=self.final_stat_vars[stat], style="Bold.TLabel", width=8).grid(
                row=row, column=4, sticky="w", pady=3
            )
        stat_buttons = ttk.Frame(stats)
        stat_buttons.grid(row=10, column=0, columnspan=5, sticky="w", pady=(12, 0))
        ttk.Button(stat_buttons, text="Max IVs", command=lambda: self._fill_stats("IV", 31)).pack(side="left")
        ttk.Button(stat_buttons, text="Clear EVs", command=lambda: self._fill_stats("EV", 0)).pack(side="left", padx=6)
        ttk.Button(stat_buttons, text="Balanced 510 EV", command=self._balanced_evs).pack(side="left", padx=(0, 6))
        ttk.Button(stat_buttons, text="Max all EVs (252)", command=self._max_all_evs).pack(side="left")
        stat_options = ttk.Frame(stats)
        stat_options.grid(row=11, column=0, columnspan=5, sticky="w", pady=(7, 0))
        ttk.Checkbutton(
            stat_options,
            text="Allow EV total over 510 (editor only)",
            variable=self.app.allow_ev_over_510,
            command=self._update_ev_total,
        ).pack(side="left")
        ttk.Checkbutton(
            stat_options,
            text="Sync calculated Max HP",
            variable=self.sync_calculated_hp,
            command=self._update_calculated_stats,
        ).pack(side="left", padx=(16, 0))
        self.ev_total_var = tk.StringVar(value="EV total: 0 / 510")
        ttk.Label(stats, textvariable=self.ev_total_var, style="Muted.TLabel").grid(
            row=12, column=0, columnspan=5, sticky="w", pady=(7, 0)
        )
        self.stat_formula_var = tk.StringVar(value="Choose a mapped Species to calculate final stats.")
        ttk.Label(stats, textvariable=self.stat_formula_var, style="Muted.TLabel", wraplength=760).grid(
            row=13, column=0, columnspan=5, sticky="w", pady=(5, 0)
        )
        stats.rowconfigure(14, weight=1)
        stat_visuals = ttk.Panedwindow(stats, orient="horizontal")
        stat_visuals.grid(row=14, column=0, columnspan=5, sticky="nsew", pady=(10, 0))
        stat_chart_frame = ttk.LabelFrame(stat_visuals, text="Final Stats", padding=4)
        type_chart_frame = ttk.LabelFrame(stat_visuals, text="Type Matchups", padding=4)
        stat_visuals.add(stat_chart_frame, weight=1)
        stat_visuals.add(type_chart_frame, weight=1)
        stat_chart_frame.rowconfigure(0, weight=1)
        stat_chart_frame.columnconfigure(0, weight=1)
        type_chart_frame.rowconfigure(0, weight=1)
        type_chart_frame.columnconfigure(0, weight=1)
        self.final_stats_canvas = tk.Canvas(
            stat_chart_frame, height=170, background="#fbfcfd", highlightthickness=0,
        )
        self.final_stats_canvas.grid(row=0, column=0, sticky="nsew")
        self.type_matchup_canvas = tk.Canvas(
            type_chart_frame, height=170, background="#fbfcfd", highlightthickness=0,
        )
        self.type_matchup_canvas.grid(row=0, column=0, sticky="nsew")
        self.final_stats_canvas.bind("<Configure>", self._queue_stats_visual_redraw)
        self.type_matchup_canvas.bind("<Configure>", self._queue_stats_visual_redraw)

        moves.columnconfigure(0, weight=1)
        moves.columnconfigure(3, weight=1)
        ttk.Label(moves, text="Show moves from").grid(row=0, column=0, sticky="w")
        self.move_filter_combo = SearchableCombobox(
            moves, textvariable=self.move_filter_var, values=MOVE_SOURCE_FILTERS, width=30
        )
        self.move_filter_combo.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(8, 12), pady=(0, 10))
        self.move_filter_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_move_choices())
        self.move_filter_var.trace_add(
            "write",
            lambda *_args: self._refresh_move_choices()
            if str(self.move_filter_var.get()) in MOVE_SOURCE_KEYS else None,
        )
        self.move_catalog_var = tk.StringVar(value="Choose a Species to load its exact GE-1.0.0 learnset.")
        ttk.Label(moves, textvariable=self.move_catalog_var, style="Muted.TLabel").grid(
            row=0, column=3, sticky="w", pady=(0, 10)
        )
        ttk.Label(moves, text="Move", style="Bold.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Label(moves, text="PP", style="Bold.TLabel").grid(row=1, column=1, sticky="w")
        ttk.Label(moves, text="PP Up", style="Bold.TLabel").grid(row=1, column=2, sticky="w")
        ttk.Label(moves, text="Learn source", style="Bold.TLabel").grid(row=1, column=3, sticky="w")
        for index in range(4):
            combo = SearchableCombobox(moves, textvariable=self.move_vars[index], values=(), width=30, state="disabled")
            combo.grid(row=index + 2, column=0, sticky="ew", padx=(0, 8), pady=5)
            self.move_combos.append(combo)
            pp_frame = ttk.Frame(moves)
            pp_frame.grid(row=index + 2, column=1, sticky="w", padx=(0, 8), pady=5)
            pp_spin = ttk.Spinbox(pp_frame, textvariable=self.current_pp_vars[index], from_=0, to=0, width=7)
            pp_spin.pack(side="left")
            ttk.Label(pp_frame, textvariable=self.pp_max_vars[index], style="Muted.TLabel").pack(side="left", padx=(5, 0))
            self.current_pp_spins.append(pp_spin)
            pp_up_spin = ttk.Spinbox(
                moves, textvariable=self.pp_up_vars[index], from_=0, to=3, width=7,
                command=lambda move_index=index: self._on_pp_up_changed(move_index),
            )
            pp_up_spin.grid(row=index + 2, column=2, sticky="w", pady=5)
            self.pp_up_spins.append(pp_up_spin)
            ttk.Label(moves, textvariable=self.move_source_vars[index], style="Muted.TLabel").grid(
                row=index + 2, column=3, sticky="w", padx=(12, 0), pady=5
            )
            self.move_vars[index].trace_add(
                "write", lambda *_args, move_index=index: self._on_move_value_changed(move_index)
            )
            self.pp_up_vars[index].trace_add(
                "write", lambda *_args, move_index=index: self._on_pp_up_changed(move_index)
            )
        ttk.Label(
            moves,
            text=(
                "Level-up choices are capped at the edited level. TM, HM and Egg compatibility comes from the "
                "selected Species DataAsset. PP Up is limited to 0–3 and Max PP is calculated from the move's "
                "GE-1.0.0 Base PP."
            ),
            style="Muted.TLabel",
            wraplength=900,
        ).grid(row=6, column=0, columnspan=4, sticky="w", pady=(12, 0))
        moves.rowconfigure(7, weight=1)
        move_chart_area = ttk.Frame(moves)
        move_chart_area.grid(row=7, column=0, columnspan=4, sticky="nsew", pady=(10, 0))
        for grid_index in range(2):
            move_chart_area.rowconfigure(grid_index, weight=1)
            move_chart_area.columnconfigure(grid_index, weight=1)
        self.move_attack_frames: list[ttk.LabelFrame] = []
        self.move_attack_canvases: list[tk.Canvas] = []
        for index in range(4):
            chart_row, chart_column = divmod(index, 2)
            chart_frame = ttk.LabelFrame(move_chart_area, text=f"Move {index + 1}", padding=3)
            chart_frame.grid(
                row=chart_row, column=chart_column, sticky="nsew",
                padx=(0, 4) if chart_column == 0 else (4, 0),
                pady=(0, 4) if chart_row == 0 else (4, 0),
            )
            chart_frame.rowconfigure(0, weight=1)
            chart_frame.columnconfigure(0, weight=1)
            chart_canvas = tk.Canvas(
                chart_frame, height=90, background="#fbfcfd", highlightthickness=0,
            )
            chart_canvas.grid(row=0, column=0, sticky="nsew")
            chart_canvas.bind("<Configure>", self._queue_move_chart_redraw)
            self.move_attack_frames.append(chart_frame)
            self.move_attack_canvases.append(chart_canvas)

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
        self.preview = tk.Canvas(preview, width=250, height=340, highlightthickness=1, highlightbackground="#9aa4ad")
        self.preview.pack(fill="both", expand=True, pady=(8, 0))
        self.preview.bind("<Configure>", lambda _event: self._draw_preview(self.current))
        self._update_main_type_badges()
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

    def _choice(self, parent, label: str, field: str, values: list[str], row: int, column: int) -> SearchableCombobox:
        var = tk.StringVar()
        self.vars[field] = var
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", padx=(0, 6), pady=5)
        widget = SearchableCombobox(parent, textvariable=var, values=values)
        widget.grid(row=row, column=column + 1, sticky="ew", padx=(0, 14), pady=5)
        return widget

    def _readonly(self, parent, label: str, field: str, row: int, column: int) -> None:
        var = tk.StringVar()
        self.vars[field] = var
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", padx=(0, 6), pady=5)
        ttk.Entry(parent, textvariable=var, state="readonly").grid(
            row=row, column=column + 1, sticky="ew", padx=(0, 14), pady=5
        )

    def _refresh_move_choices(self) -> None:
        if not hasattr(self, "move_combos") or not self.move_combos:
            return
        species_name = str(self.vars["SpeciesData"].get()).strip()
        learnset = learnset_for_species(species_name)
        level = max(1, _number(self.vars["Level"].get(), 1))
        source_key = MOVE_SOURCE_KEYS.get(str(self.move_filter_var.get()), "all")
        choices = learnset.choices(level=level, source=source_key) if learnset is not None else ()
        values = ("", *(move.name for move in choices))
        for combo in self.move_combos:
            combo.set_source_values(values, enabled=learnset is not None)
        if learnset is None:
            self.move_catalog_var.set("Choose a Species to load its exact GE-1.0.0 learnset.")
        else:
            source_name = str(self.move_filter_var.get())
            self.move_catalog_var.set(f"{len(choices)} {source_name.lower()} choice(s) at Lv. {level}")
        for index in range(len(self.move_vars)):
            self._update_move_source_label(index)

    def _on_move_value_changed(self, index: int) -> None:
        self._update_move_source_label(index)
        self._queue_move_chart_redraw()
        move_name = str(self.move_vars[index].get()).strip()
        if move_name.casefold() not in MOVES_BY_NAME:
            self.pp_max_vars[index].set("—")
            self.current_pp_spins[index].configure(from_=0, to=0, state="disabled")
            self.pp_up_spins[index].configure(from_=0, to=0, state="disabled")
            if not self._loading_move_fields:
                self.current_pp_vars[index].set("")
                self.pp_up_vars[index].set("0")
                self._pp_up_levels[index] = 0
            return
        if not self._loading_move_fields:
            self._updating_pp_fields = True
            try:
                self.pp_up_vars[index].set("0")
                self.current_pp_vars[index].set(str(max_pp_for_move(move_name, 0)))
                self._pp_up_levels[index] = 0
            finally:
                self._updating_pp_fields = False
        self._refresh_pp_row(index)

    def _refresh_pp_row(self, index: int) -> None:
        move_name = str(self.move_vars[index].get()).strip()
        if move_name.casefold() not in MOVES_BY_NAME:
            return
        limit = pp_up_limit_for_move(move_name)
        try:
            pp_ups = int(self.pp_up_vars[index].get())
        except ValueError:
            pp_ups = 0
        pp_ups = max(0, min(limit, pp_ups))
        maximum = max_pp_for_move(move_name, pp_ups)
        base = base_pp_for_move(move_name)
        self.current_pp_spins[index].configure(from_=0, to=maximum, state="normal")
        self.pp_up_spins[index].configure(from_=0, to=limit, state="normal" if limit else "disabled")
        self.pp_max_vars[index].set(f"/ {maximum} max (Base {base})")

    def _on_pp_up_changed(self, index: int) -> None:
        if self._loading_move_fields or self._updating_pp_fields:
            return
        move_name = str(self.move_vars[index].get()).strip()
        if move_name.casefold() not in MOVES_BY_NAME:
            return
        try:
            requested = int(self.pp_up_vars[index].get())
        except ValueError:
            return
        limit = pp_up_limit_for_move(move_name)
        new_level = max(0, min(limit, requested))
        old_level = max(0, min(limit, self._pp_up_levels[index]))
        old_maximum = max_pp_for_move(move_name, old_level)
        new_maximum = max_pp_for_move(move_name, new_level)
        current = _number(self.current_pp_vars[index].get(), old_maximum)
        self._updating_pp_fields = True
        try:
            if requested != new_level:
                self.pp_up_vars[index].set(str(new_level))
            self.current_pp_vars[index].set(str(max(0, min(new_maximum, current + new_maximum - old_maximum))))
            self._pp_up_levels[index] = new_level
        finally:
            self._updating_pp_fields = False
        self._refresh_pp_row(index)

    def _update_move_source_label(self, index: int) -> None:
        if not hasattr(self, "move_source_vars"):
            return
        move_name = str(self.move_vars[index].get()).strip()
        if not move_name:
            self.move_source_vars[index].set("—")
            return
        species_name = str(self.vars["SpeciesData"].get()).strip()
        learnset = learnset_for_species(species_name)
        if learnset is None:
            self.move_source_vars[index].set("Choose a Species")
            return
        level = max(1, _number(self.vars["Level"].get(), 1))
        labels = learnset.source_labels(move_name, level=level)
        self.move_source_vars[index].set(" / ".join(labels) if labels else "Not legal for this Species")

    def _queue_move_chart_redraw(self, _event=None) -> None:
        if not hasattr(self, "move_attack_canvases"):
            return
        if self._move_chart_redraw_id is not None:
            self.after_cancel(self._move_chart_redraw_id)
        self._move_chart_redraw_id = self.after_idle(self._draw_move_attack_charts)

    def _draw_move_attack_charts(self) -> None:
        self._move_chart_redraw_id = None
        for index in range(4):
            self._draw_move_attack_chart(index)

    def _draw_move_attack_chart(self, index: int) -> None:
        frame = self.move_attack_frames[index]
        canvas = self.move_attack_canvases[index]
        canvas.delete("all")
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        move_name = str(self.move_vars[index].get()).strip()
        move = MOVES_BY_NAME.get(move_name.casefold())
        if move is None:
            frame.configure(text=f"Move {index + 1}")
            if width >= 80 and height >= 35:
                canvas.create_text(
                    width / 2, height / 2, text="Choose a move to view its attack type chart.",
                    fill="#66717a", font=("Segoe UI", 8), width=max(70, width - 18),
                )
            return
        frame.configure(text=f"{index + 1} · {move.name} · {move.category}")
        if width < 100 or height < 45:
            return
        values = type_attacks((move.category,))
        columns = 9
        x_margin = 4
        y_margin = 3
        cell_width = max(16, (width - x_margin * 2) / columns)
        cell_height = max(18, (height - y_margin * 2) / 2)
        type_height = max(7, cell_height * .46)
        type_font = 6 if cell_width < 27 else 7
        value_font = 6 if cell_width < 27 or cell_height < 23 else 8
        for type_index, type_name in enumerate(TYPE_ORDER):
            row, column = divmod(type_index, columns)
            x0 = x_margin + column * cell_width
            y0 = y_margin + row * cell_height
            x1 = x_margin + (column + 1) * cell_width - 1
            y1 = min(height - 2, y0 + cell_height - 1)
            split = min(y1 - 8, y0 + type_height)
            canvas.create_rectangle(x0, y0, x1, split, fill=TYPE_COLORS[type_name], outline="#ffffff")
            canvas.create_text(
                (x0 + x1) / 2, (y0 + split) / 2, text=type_name[:3].upper(),
                font=("Segoe UI", type_font, "bold"), fill=_type_text_color(type_name),
            )
            multiplier = float(values[type_name])
            background, foreground = self._multiplier_style(multiplier)
            canvas.create_rectangle(x0, split, x1, y1, fill=background, outline="#e1e5e8")
            canvas.create_text(
                (x0 + x1) / 2, (split + y1) / 2,
                text=self._multiplier_text(multiplier) + "×",
                font=("Segoe UI", value_font, "bold"), fill=foreground,
            )

    def _refresh_species_dependent(self, *, choose_default: bool = False) -> None:
        species_name = str(self.vars["SpeciesData"].get()).strip()
        self._refresh_move_choices()
        info = SPECIES_INFO.get(species_name.casefold())
        if info is None or not info.abilities:
            current = str(self.vars["Ability"].get()).strip() or "None"
            self.ability_combo.set_source_values((current,))
            self.vars["Ability"].set(current)
            if choose_default or not self.vars["AbilitySlot"].get():
                self.vars["AbilitySlot"].set("0")
            return
        labels = [item.label for item in info.abilities]
        current = str(self.vars["Ability"].get()).strip()
        selected = next(
            (item for item in info.abilities if current.casefold() in {
                item.label.casefold(), item.name.casefold(), item.enum_name.casefold(),
            }),
            None,
        )
        if selected is None and (choose_default or not current or current.casefold() == "none"):
            selected = info.abilities[0]
        self.ability_combo.set_source_values(labels)
        if selected is not None:
            self.vars["Ability"].set(selected.label)
            self.vars["AbilitySlot"].set(str(selected.slot))

    def _on_species_changed(self, _event=None) -> None:
        self._load_species_defaults_into_form()

    @staticmethod
    def _types_for_species(species_name: str) -> tuple[str, ...]:
        info = SPECIES_INFO.get(species_name.casefold())
        if info is not None and info.types:
            return info.types
        species = SPECIES_BY_NAME.get(species_name.casefold())
        return (species.category,) if species is not None else ()

    def _update_main_type_badges(self) -> None:
        if not hasattr(self, "main_type_labels"):
            return
        species_name = str(self.vars["SpeciesData"].get()).strip()
        types = self._types_for_species(species_name)
        for index, label in enumerate(self.main_type_labels):
            if index >= len(types):
                if index == 0:
                    label.grid()
                    label.configure(text="—", bg="#e5e9ec", fg="#55616a")
                else:
                    label.grid_remove()
                continue
            type_name = types[index]
            label.grid()
            label.configure(
                text=type_name.upper(), bg=TYPE_COLORS[type_name], fg=_type_text_color(type_name),
            )

    def _on_species_text_changed(self) -> None:
        species_name = str(self.vars["SpeciesData"].get()).strip()
        if species_name.casefold() in SPECIES_BY_NAME:
            self._refresh_species_dependent(choose_default=False)
        else:
            self._refresh_move_choices()
        self._update_calculated_stats()
        self._update_main_type_badges()
        self._queue_evolution_redraw()
        if hasattr(self, "preview"):
            self._draw_preview(self.current)

    def _load_species_defaults_into_form(self) -> None:
        document = self.app.current_document()
        species_name = str(self.vars["SpeciesData"].get()).strip()
        species = SPECIES_BY_NAME.get(species_name.casefold())
        if document is None or species is None:
            self.species_defaults_var.set("Choose an exact GE-1.0.0 Species before loading defaults.")
            return
        try:
            profile = pokemon_species_profile(document, species.name, level=5)
        except GammaEditorError as exc:
            self.species_defaults_var.set(str(exc))
            return

        # Species conversion keeps the record's collision-free identity and ownership. Everything
        # species/gameplay-derived is reset in the form and remains staged until Apply + Save.
        preserved = {
            "PokemonID", "OriginalTrainerName", "CurrentTrainerName",
            "OriginalTrainerID", "CurrentTrainerID",
        } if self.current is not None and self.current.occupied else set()
        self._loading_move_fields = True
        try:
            for field, value in profile.scalar_defaults.items():
                var = self.vars.get(field)
                if var is None or field in preserved:
                    continue
                if field == "Nature":
                    value = nature_label(_enum_leaf(value))
                elif field in ENUM_PREFIXES:
                    value = _enum_leaf(value)
                var.set(bool(value) if isinstance(var, tk.BooleanVar) else str(value))
            for index in range(4):
                if index < len(profile.moves):
                    self.move_vars[index].set(profile.moves[index].name)
                    self.current_pp_vars[index].set(str(profile.current_pp[index]))
                    self.pp_up_vars[index].set("0")
                else:
                    self.move_vars[index].set("")
                    self.current_pp_vars[index].set("")
                    self.pp_up_vars[index].set("0")
                self._pp_up_levels[index] = 0
        finally:
            self._loading_move_fields = False
        self.sync_calculated_hp.set(True)
        self._refresh_species_dependent(choose_default=True)
        for index in range(4):
            self._refresh_pp_row(index)
        self._update_ev_total()
        self._update_calculated_stats()
        self._draw_preview(self.current)
        self._queue_evolution_redraw()
        mode = "conversion" if preserved else "creation"
        self.species_defaults_var.set(
            f"Loaded {species.name} Lv. 5 {mode} profile: Ability, starting moves/PP, HP, IV/EV, status and met data."
        )

    def _queue_evolution_redraw(self, _event=None) -> None:
        if not hasattr(self, "evolution_canvas"):
            return
        if self._evolution_redraw_id is not None:
            self.after_cancel(self._evolution_redraw_id)
        self._evolution_redraw_id = self.after_idle(self._draw_evolution_chart)

    def _draw_evolution_chart(self) -> None:
        self._evolution_redraw_id = None
        canvas = self.evolution_canvas
        canvas.delete("all")
        species_name = str(self.vars["SpeciesData"].get()).strip()
        species = SPECIES_BY_NAME.get(species_name.casefold())
        width = max(canvas.winfo_width(), 240)
        height = max(canvas.winfo_height(), 190)
        if species is None:
            canvas.create_text(
                width / 2,
                height / 2,
                text="Choose a Species to view its evolution family.",
                fill="#66717a",
                font=("Segoe UI", 10),
            )
            return
        layers, edges = evolution_family(species.name)
        # Prefer the old-editor-style horizontal chart. A very narrow but tall
        # pane can still switch to vertical; ordinary and minimum app sizes
        # remain horizontal because that makes better use of their short chart.
        horizontal = width >= 320 or height < 260 or len(layers) <= 2
        largest_layer = max(len(layer) for layer in layers)
        node_half_width = 44 if width >= 420 else 36
        row_gap = height / (largest_layer + 1)
        node_half_height = min(38, max(22, row_gap / 2 - 4))
        positions: dict[str, tuple[float, float]] = {}
        if horizontal:
            x_margin = node_half_width + 20
            for layer_index, layer in enumerate(layers):
                x = width / 2 if len(layers) == 1 else x_margin + layer_index * (width - 2 * x_margin) / (len(layers) - 1)
                for item_index, name in enumerate(layer):
                    y = (item_index + 1) * height / (len(layer) + 1)
                    positions[name] = (x, y)
        else:
            y_margin = 48
            for layer_index, layer in enumerate(layers):
                y = height / 2 if len(layers) == 1 else y_margin + layer_index * (height - 2 * y_margin) / (len(layers) - 1)
                for item_index, name in enumerate(layer):
                    x = (item_index + 1) * width / (len(layer) + 1)
                    positions[name] = (x, y)

        for edge in edges:
            source_x, source_y = positions[edge.source]
            target_x, target_y = positions[edge.target]
            if horizontal:
                start = (source_x + node_half_width + 3, source_y)
                end = (target_x - node_half_width - 3, target_y)
            else:
                start = (source_x, source_y + node_half_height + 2)
                end = (target_x, target_y - node_half_height - 2)
            canvas.create_line(*start, *end, fill="#66717a", width=2, arrow="last", arrowshape=(8, 10, 4))
            label_x = (start[0] + end[0]) / 2
            label_y = (start[1] + end[1]) / 2 - (10 if horizontal else 0)
            label = canvas.create_text(
                label_x,
                label_y,
                text=edge.condition,
                fill="#55616a",
                font=("Segoe UI", 8),
                width=110,
            )
            bounds = canvas.bbox(label)
            if bounds:
                background = canvas.create_rectangle(*bounds, fill="#fbfcfd", outline="")
                canvas.tag_lower(background, label)

        for name, (x, y) in positions.items():
            selected = name.casefold() == species.name.casefold()
            canvas.create_rectangle(
                x - node_half_width,
                y - node_half_height,
                x + node_half_width,
                y + node_half_height,
                fill="#fff4cf" if selected else "#ffffff",
                outline="#e3a008" if selected else "#9aa4ad",
                width=2 if selected else 1,
            )
            image = self.app.sprites.get(name, 32)
            compact = node_half_height < 32
            icon_y = y - (8 if compact else 12)
            if image is not None:
                canvas.create_image(x, icon_y, image=image)
            else:
                initials = "".join(part[0] for part in name.split()[:2]).upper() or "?"
                canvas.create_text(x, icon_y, text=initials, font=("Segoe UI", 10, "bold"), fill="#46515a")
            canvas.create_text(
                x,
                y + (17 if compact else 24),
                text=name,
                font=("Segoe UI", 8 if compact else 9, "bold" if selected else "normal"),
                width=node_half_width * 2 - 4,
            )

    def _on_ability_changed(self, _event=None) -> None:
        info = SPECIES_INFO.get(str(self.vars["SpeciesData"].get()).strip().casefold())
        if info is None:
            return
        label = str(self.vars["Ability"].get()).casefold()
        choice = next((item for item in info.abilities if item.label.casefold() == label), None)
        if choice is not None:
            self.vars["AbilitySlot"].set(str(choice.slot))

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

    def _max_all_evs(self) -> None:
        self.app.allow_ev_over_510.set(True)
        self._fill_stats("EV", 252)
        self._update_calculated_stats()

    def _update_ev_total(self) -> None:
        total = sum(_number(self.vars[field].get()) for field in self.vars if field.endswith("_EV"))
        suffix = "510 cap disabled" if self.app.allow_ev_over_510.get() else "max 510"
        self.ev_total_var.set(f"EV total: {total} ({suffix})")

    def _queue_stats_visual_redraw(self, _event=None) -> None:
        if not hasattr(self, "final_stats_canvas"):
            return
        if self._stats_visual_redraw_id is not None:
            self.after_cancel(self._stats_visual_redraw_id)
        self._stats_visual_redraw_id = self.after_idle(self._draw_stats_visuals)

    def _draw_stats_visuals(self) -> None:
        self._stats_visual_redraw_id = None
        self._draw_final_stats_chart()
        self._draw_type_matchups()

    def _draw_final_stats_chart(self) -> None:
        canvas = self.final_stats_canvas
        canvas.delete("all")
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width < 80 or height < 80:
            return
        rows = (
            ("HP", "HP"), ("Atk", "Attack"), ("Def", "Defense"),
            ("SpA", "SpecialAttack"), ("SpD", "SpecialDefense"), ("Spe", "Speed"),
        )
        try:
            values = [int(self.final_stat_vars[key].get()) for _label, key in rows]
        except ValueError:
            canvas.create_text(
                width / 2, height / 2, text="Choose a mapped Species to chart final stats.",
                fill="#66717a", font=("Segoe UI", 9), width=max(100, width - 24),
            )
            return
        left, right, top, bottom = 18, 12, 34, 28
        chart_width = max(1, width - left - right)
        chart_height = max(1, height - top - bottom)
        ceiling = max(10, max(values))
        slot_width = chart_width / len(rows)
        bar_width = max(8, min(34, slot_width * .58))
        colors = ("#ef5350", "#ff9f43", "#f2c94c", "#42a5f5", "#66bb6a", "#ab75dc")
        for fraction in (.25, .5, .75, 1.0):
            y = top + chart_height * (1 - fraction)
            canvas.create_line(left, y, width - right, y, fill="#dfe4e8", dash=(2, 3))
        for index, ((label, _key), value, color) in enumerate(zip(rows, values, colors)):
            x = left + slot_width * (index + .5)
            bar_height = chart_height * value / ceiling
            y = top + chart_height - bar_height
            canvas.create_rectangle(
                x - bar_width / 2, y, x + bar_width / 2, top + chart_height,
                fill=color, outline="#ffffff",
            )
            canvas.create_text(x, max(22, y - 8), text=str(value), font=("Segoe UI", 8, "bold"), fill="#30363b")
            canvas.create_text(x, height - 13, text=label, font=("Segoe UI", 8), fill="#4f5961")
        level = _number(self.vars["Level"].get(), 1)
        canvas.create_text(
            left, 10, anchor="w", text=f"Lv. {level} · highest bar = {ceiling}",
            font=("Segoe UI", 8), fill="#66717a",
        )

    @staticmethod
    def _multiplier_text(value: float) -> str:
        return "¼" if value == .25 else "½" if value == .5 else f"{int(value) if value.is_integer() else value:g}"

    @staticmethod
    def _multiplier_style(value: float) -> tuple[str, str]:
        if value == 0:
            return "#343a40", "#ffffff"
        if value <= .25:
            return "#8e0000", "#ffffff"
        if value < 1:
            return "#c62828", "#ffffff"
        if value >= 4:
            return "#2e7d32", "#ffffff"
        if value > 1:
            return "#66a80f", "#ffffff"
        return "#ffffff", "#30363b"

    def _draw_type_matchups(self) -> None:
        canvas = self.type_matchup_canvas
        canvas.delete("all")
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width < 100 or height < 100:
            return
        species_name = str(self.vars["SpeciesData"].get()).strip()
        info = SPECIES_INFO.get(species_name.casefold())
        if info is None:
            canvas.create_text(
                width / 2, height / 2, text="Choose a mapped Species to chart type matchups.",
                fill="#66717a", font=("Segoe UI", 9), width=max(100, width - 24),
            )
            return
        sections = (
            ("Attack · best STAB", type_attacks(info.types)),
            ("Defense · incoming", type_defenses(info.types)),
        )
        section_height = height / 2
        columns = 9
        x_margin = 5
        cell_width = max(16, (width - x_margin * 2) / columns)
        title_height = min(20, max(14, section_height * .28))
        grid_height = max(20, section_height - title_height - 2)
        cell_height = grid_height / 2
        type_height = max(7, cell_height * .46)
        type_font = 6 if cell_width < 27 else 7
        value_font = 6 if cell_width < 27 or cell_height < 20 else 8
        for section_index, (title, values) in enumerate(sections):
            section_y = section_index * section_height
            canvas.create_text(
                x_margin, section_y + title_height / 2, anchor="w", text=title,
                font=("Segoe UI", 7 if section_height < 75 else 8, "bold"), fill="#30363b",
            )
            if section_index == 0:
                canvas.create_text(
                    width - x_margin, section_y + title_height / 2, anchor="e", text=" / ".join(info.types),
                    font=("Segoe UI", 7), fill="#66717a",
                )
            for index, type_name in enumerate(TYPE_ORDER):
                row, column = divmod(index, columns)
                x0 = x_margin + column * cell_width
                y0 = section_y + title_height + row * cell_height
                x1 = x_margin + (column + 1) * cell_width - 1
                y1 = y0 + cell_height - 1
                split = min(y1 - 10, y0 + type_height)
                canvas.create_rectangle(x0, y0, x1, split, fill=TYPE_COLORS[type_name], outline="#ffffff")
                canvas.create_text(
                    (x0 + x1) / 2, (y0 + split) / 2, text=type_name[:3].upper(),
                    font=("Segoe UI", type_font, "bold"), fill=_type_text_color(type_name),
                )
                multiplier = float(values[type_name])
                background, foreground = self._multiplier_style(multiplier)
                canvas.create_rectangle(x0, split, x1, y1, fill=background, outline="#e1e5e8")
                canvas.create_text(
                    (x0 + x1) / 2, (split + y1) / 2,
                    text=self._multiplier_text(multiplier) + "×",
                    font=("Segoe UI", value_font, "bold"), fill=foreground,
                )

    def _update_calculated_stats(self) -> None:
        if not hasattr(self, "final_stat_vars"):
            return
        stat_names = ("HP", "Attack", "Defense", "SpecialAttack", "SpecialDefense", "Speed")
        species_name = str(self.vars["SpeciesData"].get()).strip()
        species = SPECIES_BY_NAME.get(species_name.casefold())
        info = SPECIES_INFO.get(species_name.casefold())
        if species is None or info is None:
            for stat in stat_names:
                self.base_stat_vars[stat].set("—")
                self.final_stat_vars[stat].set("—")
            self.stat_formula_var.set("Choose a mapped Species to calculate final stats.")
            self._queue_stats_visual_redraw()
            return
        for stat in stat_names:
            self.base_stat_vars[stat].set(str(info.base_stats[stat]))
        try:
            level = int(self.vars["Level"].get())
            nature = NATURE_BY_LABEL.get(str(self.vars["Nature"].get()).strip().casefold())
            if nature is None:
                raise ValueError("Choose a Nature to calculate final stats.")
            ivs = {stat: int(self.vars[stat + "_IV"].get()) for stat in stat_names}
            evs = {stat: int(self.vars[stat + "_EV"].get()) for stat in stat_names}
            calculated = calculate_pokemon_stats(species.name, level, nature, ivs, evs)
        except (TypeError, ValueError) as exc:
            for stat in stat_names:
                self.final_stat_vars[stat].set("—")
            self.stat_formula_var.set(str(exc))
            self._queue_stats_visual_redraw()
            return
        for stat in stat_names:
            self.final_stat_vars[stat].set(str(calculated[stat]))
        self.stat_formula_var.set(
            f"Final stats at Lv. {level} with {nature_label(nature)}. "
            "Gamma stores Level/Nature/IV/EV; only Max HP is persisted as a final stat."
        )
        self._queue_stats_visual_redraw()
        if self.sync_calculated_hp.get():
            calculated_hp = calculated["HP"]
            old_current_hp = _number(self.vars["CurrentHP"].get(), calculated_hp)
            if self.current is not None and not self.current.occupied:
                old_current_hp = calculated_hp
            self.vars["MaxHP"].set(str(calculated_hp))
            self.vars["CurrentHP"].set(str(min(max(0, old_current_hp), calculated_hp)))

    def load(self, pokemon: PokemonView | None) -> None:
        self.current = pokemon
        if pokemon is None:
            self._loading_move_fields = True
            self.sync_calculated_hp.set(False)
            self.heading_var.set(f"{self.title_text}: select a slot")
            for var in self.vars.values():
                var.set(False if isinstance(var, tk.BooleanVar) else "")
            for var in (*self.move_vars, *self.current_pp_vars):
                var.set("")
            for var in self.pp_up_vars:
                var.set("0")
            self._pp_up_levels = [0, 0, 0, 0]
            self._loading_move_fields = False
            self.apply_button.configure(state="disabled")
            self._update_calculated_stats()
            self._draw_preview(None)
            return
        if not pokemon.occupied:
            self._loading_move_fields = True
            self.sync_calculated_hp.set(True)
            document = self.app.current_document()
            if document is None:
                self._loading_move_fields = False
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
                if field == "Nature":
                    value = nature_label(_enum_leaf(value))
                elif field in ENUM_PREFIXES:
                    value = _enum_leaf(value)
                if isinstance(var, tk.BooleanVar):
                    var.set(bool(value))
                else:
                    var.set(str(value))
            for var in self.move_vars:
                var.set("")
            for var in self.current_pp_vars:
                var.set("")
            for var in self.pp_up_vars:
                var.set("0")
            self._pp_up_levels = [0, 0, 0, 0]
            self._loading_move_fields = False
            self.apply_button.configure(text="Create Pokemon", state="normal")
            self._refresh_species_dependent(choose_default=False)
            self._update_ev_total()
            self._update_calculated_stats()
            self._draw_preview(None)
            return
        fields = pokemon.fields
        self._loading_move_fields = True
        self.sync_calculated_hp.set(False)
        self.heading_var.set(f"{self.title_text}: Slot {pokemon.slot_index + 1} — {pokemon.species}")
        for field, var in self.vars.items():
            value = fields.get(field, "")
            if field == "SpeciesData":
                value = pokemon.species
            elif field == "Nature":
                leaf = _enum_leaf(value)
                value = nature_label(leaf) if leaf in NATURES else leaf
            elif field in ENUM_PREFIXES:
                value = _enum_leaf(value)
            if isinstance(var, tk.BooleanVar):
                var.set(bool(value))
            else:
                var.set(str(value))
        move_names = fields.get("MoveNames", ())
        current_pp = fields.get("CurrentPP", ())
        max_pp = fields.get("MaxPP", ())
        for index in range(4):
            move_name = display_name(str(move_names[index])) if index < len(move_names) else ""
            self.move_vars[index].set(move_name)
            self.current_pp_vars[index].set(str(current_pp[index]) if index < len(current_pp) else "0")
            inferred = pp_ups_from_max_pp(move_name, max_pp[index]) if move_name and index < len(max_pp) else 0
            self.pp_up_vars[index].set(str(inferred if inferred is not None else 0))
            self._pp_up_levels[index] = inferred if inferred is not None else 0
        self._loading_move_fields = False
        for index in range(4):
            self._on_move_value_changed(index)
        self.apply_button.configure(text="Apply staged changes", state="normal")
        self._refresh_species_dependent(choose_default=False)
        self._update_ev_total()
        self._update_calculated_stats()
        self._draw_preview(pokemon)

    def _draw_preview(self, pokemon: PokemonView | None) -> None:
        canvas = self.preview
        canvas.delete("all")
        width = max(canvas.winfo_width(), 120)
        height = max(canvas.winfo_height(), 330)
        margin = 8 if width < 180 else 12
        selected_name = str(self.vars["SpeciesData"].get()).strip()
        selected_species = SPECIES_BY_NAME.get(selected_name.casefold())
        if selected_species is None and pokemon is not None and pokemon.occupied:
            selected_species = SPECIES_BY_NAME.get(pokemon.species.casefold())
        if selected_species is None:
            canvas.create_rectangle(margin, 12, width - margin, height - 12, fill="#f1f4f6", outline="#aab2b9")
            canvas.create_text(
                width / 2, height / 2, text="(Empty slot)", fill="#66717a",
                font=("Segoe UI", 11), width=max(80, width - 24),
            )
            return
        fields = dict(pokemon.fields) if pokemon is not None else {}
        for field, var in self.vars.items():
            value = var.get()
            if value != "":
                fields[field] = value
        types = self._types_for_species(selected_species.name) or (selected_species.category,)
        canvas.create_rectangle(
            margin, 12, width - margin, height - 12,
            fill=_light_type_color(types[0]), outline="",
        )
        if len(types) > 1:
            canvas.create_rectangle(
                width / 2, 12, width - margin, height - 12,
                fill=_light_type_color(types[1]), outline="",
            )
        canvas.create_rectangle(
            margin, 12, width - margin, height - 12,
            fill="", outline="#77838d", width=2,
        )
        sprite = self.app.sprites.get(selected_species.name, 96 if width < 180 else 128)
        if sprite is not None:
            canvas.create_image(width / 2, 88, image=sprite)
        else:
            initials = "".join(word[0] for word in selected_species.name.split()[:2]).upper()
            canvas.create_oval(width / 2 - 54, 30, width / 2 + 54, 138, fill="#ffffff", outline="#77838d", width=2)
            canvas.create_text(width / 2, 84, text=initials or "?", font=("Segoe UI", 24, "bold"), fill="#39434b")
        shiny = " ★" if fields.get("bIsShiny") else ""
        text_width = max(86, width - 24)
        canvas.create_text(
            width / 2, 160, text=selected_species.name + shiny,
            font=("Segoe UI", 12 if width < 180 else 13, "bold"), width=text_width,
        )
        canvas.create_text(
            width / 2, 184, text=f"Lv. {_number(fields.get('Level'), 1)}", width=text_width,
        )
        badge_gap = 4
        badge_width = min(72, (width - margin * 2 - badge_gap * (len(types) - 1)) / len(types))
        badge_total = badge_width * len(types) + badge_gap * (len(types) - 1)
        badge_left = (width - badge_total) / 2
        for index, type_name in enumerate(types):
            x0 = badge_left + index * (badge_width + badge_gap)
            x1 = x0 + badge_width
            canvas.create_rectangle(x0, 198, x1, 218, fill=TYPE_COLORS[type_name], outline="#ffffff")
            canvas.create_text(
                (x0 + x1) / 2, 208, text=type_name.upper(),
                font=("Segoe UI", 7 if width < 180 else 8, "bold"),
                fill=_type_text_color(type_name),
            )
        hp = max(0, _number(fields.get("CurrentHP")))
        max_hp = max(1, _number(fields.get("MaxHP"), 1))
        ratio = min(1.0, hp / max_hp)
        hp_margin = 16 if width < 180 else 30
        canvas.create_rectangle(hp_margin, 230, width - hp_margin, 248, fill="#5b646b", outline="")
        hp_color = "#43a047" if ratio > 0.5 else "#f9a825" if ratio > 0.2 else "#d32f2f"
        canvas.create_rectangle(
            hp_margin + 2, 232,
            hp_margin + 2 + (width - 2 * hp_margin - 4) * ratio, 246,
            fill=hp_color, outline="",
        )
        canvas.create_text(width / 2, 265, text=f"HP {hp} / {max_hp}")
        item = str(fields.get("HeldItem", "None"))
        status = _enum_leaf(fields.get("StatusCondition", "None"))
        canvas.create_text(width / 2, 295, text=f"Item: {item}  •  Status: {status}", width=text_width)

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
                    if prop is None or not prop.editable:
                        continue
                    raw: object = self.vars[field].get()
                    if field == "Nature":
                        canonical = NATURE_BY_LABEL.get(str(raw).casefold())
                        if canonical is None:
                            raise ValueError("Choose a valid Nature.")
                        raw = f"ENature::{canonical}"
                    elif field == "Ability":
                        info = SPECIES_INFO.get(str(self.vars["SpeciesData"].get()).strip().casefold())
                        choice = next(
                            (item for item in info.abilities if item.label.casefold() == str(raw).casefold()), None
                        ) if info else None
                        if info and choice is None:
                            raise ValueError("Choose an Ability valid for the selected Species.")
                        raw = f"EPokemonAbility::{choice.enum_name if choice else raw}"
                    elif field == "HeldItem":
                        raw = exact_choice(list(self.app._held_item_names()), raw)
                        if raw is None:
                            raise ValueError("Choose a valid holdable item.")
                    elif field in {"Gender", "StatusCondition", "MetType"}:
                        raw = validated_enum_value(field, raw)
                    elif field in ENUM_PREFIXES:
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
                    if prop is None:
                        continue
                    raw = self.vars[field].get()
                    if field == "Nature":
                        canonical = NATURE_BY_LABEL.get(str(raw).casefold())
                        if canonical is None:
                            raise ValueError("Choose a valid Nature.")
                        raw = f"ENature::{canonical}"
                    elif field == "Ability":
                        info = SPECIES_INFO.get(str(self.vars["SpeciesData"].get()).strip().casefold())
                        choice = next(
                            (item for item in info.abilities if item.label.casefold() == str(raw).casefold()), None
                        ) if info else None
                        if info and choice is None:
                            raise ValueError("Choose an Ability valid for the selected Species.")
                        raw = f"EPokemonAbility::{choice.enum_name if choice else raw}"
                    elif field == "HeldItem":
                        raw = exact_choice(list(self.app._held_item_names()), raw)
                        if raw is None:
                            raise ValueError("Choose a valid holdable item.")
                    elif field in {"Gender", "StatusCondition", "MetType"}:
                        raw = validated_enum_value(field, raw)
                    elif field in ENUM_PREFIXES:
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
                "Change Species DataAsset and apply the loaded Species profile?\n\n"
                "The form has reset level/EXP, HP, Nature, gender, Ability, IV/EV, moves/PP, status and met data. "
                "The existing unique identity and Trainer ownership are preserved.",
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
                pp_ups = int(self.pp_up_vars[index].get())
                maximum = max_pp_for_move(move.name, pp_ups)
                current = int(self.current_pp_vars[index].get())
                if not 0 <= current <= maximum:
                    raise ValueError(f"{move.name} PP must be between 0 and {maximum}.")
                current_pp.append(current)
                max_pp.append(maximum)
            move_names = tuple(move.name for move in moves)
            if len({name.casefold() for name in move_names}) != len(move_names):
                raise ValueError("A Pokémon cannot have the same move in more than one slot.")
            edited_level = int(self.vars["Level"].get())
            learnset = learnset_for_species(species.name)
            legal_names = {
                move.name.casefold()
                for move in (learnset.choices(level=edited_level) if learnset is not None else ())
            }
            invalid_moves = [move.name for move in moves if move.name.casefold() not in legal_names]
            if pokemon.occupied:
                old_names = tuple(display_name(str(value)) for value in pokemon.fields.get("MoveNames", ()))
                moves_changed = move_names != old_names
                level_changed = edited_level != _number(pokemon.fields.get("Level"), edited_level)
                if invalid_moves and (moves_changed or species_change is not None or level_changed):
                    raise ValueError(
                        f"{', '.join(invalid_moves)} is not legal for {species.name} at Lv. {edited_level} "
                        "from its exact GE-1.0.0 Level-up, TM, HM or Egg learnset."
                    )
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
                if invalid_moves:
                    raise ValueError(
                        f"{', '.join(invalid_moves)} is not legal for {species.name} at Lv. {edited_level} "
                        "from its exact GE-1.0.0 Level-up, TM, HM or Egg learnset."
                    )
                self.app.stage_new_pokemon(
                    pokemon,
                    changes,
                    species=species,
                    moves=moves,
                    current_pp=current_pp,
                    max_pp=max_pp,
                )
        except (ValueError, GammaEditorError) as exc:
            messagebox.showerror(APP_TITLE, str(exc))


class SaveEditorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.smoke_test = "--smoke-test" in sys.argv
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
        self.clone_preset: PokemonClonePreset | None = None
        self.clone_preset_var = tk.StringVar(value="Clone preset: none")
        self.mod_toolchain = discover_toolchain()
        self.custom_item_spec = installed_item(self.mod_toolchain)
        self.sprites = SpriteRepository(self)
        self.empty_slot_sprite = tk.PhotoImage(master=self, width=32, height=32)
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
        self.mod_builder_tab = ttk.Frame(self.tabs, padding=12)
        for frame, label in (
            (self.trainer_tab, "Trainer"), (self.pokemon_tab, "Pokémon"),
            (self.bag_tab, "Bag"), (self.dex_tab, "Pokédex"),
        ):
            self.tabs.add(frame, text=label)
        self.tabs.add(self.mod_builder_tab, text="Item Mod Builder")
        self._build_trainer()
        self._build_pokemon()
        self._build_bag()
        self._build_dex()
        self._build_mod_builder()

    def _build_mod_builder(self) -> None:
        tab = self.mod_builder_tab
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)
        ttk.Label(tab, text="Template-based Item Mod Builder", style="AppTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            tab,
            text=(
                "GE-1.0.0 only. Clone a shipped behavior/visual template for healing, status, revive, PP, "
                "vitamin, candy, evolution/utility, held item, Berry, TM or Poké Ball. Close the game first."
            ),
            style="Muted.TLabel",
            wraplength=1040,
        ).grid(row=1, column=0, sticky="w", pady=(3, 12))

        body = ttk.Panedwindow(tab, orient="horizontal")
        body.grid(row=2, column=0, sticky="nsew")
        form = ttk.LabelFrame(body, text="Item wizard", padding=12)
        environment = ttk.LabelFrame(body, text="Local mod toolchain", padding=12)
        body.add(form, weight=3)
        body.add(environment, weight=2)
        form.columnconfigure(1, weight=1)

        self.mod_archetype_var = tk.StringVar(value="HP Restore")
        self.mod_template_var = tk.StringVar(value="Potion")
        self.mod_internal_name_var = tk.StringVar(value="CustomItem")
        self.mod_display_name_var = tk.StringVar(value="Custom Item")
        self.mod_description_var = tk.StringVar(value="A custom item built from a verified Gamma template.")
        self.mod_item_id_var = tk.StringVar()
        self.mod_item_id_info_var = tk.StringVar()
        self.mod_buy_price_var = tk.StringVar(value="500")
        self.mod_sell_price_var = tk.StringVar(value="250")
        self.mod_hp_restore_var = tk.StringVar(value="50")
        self.mod_hp_percent_var = tk.StringVar(value="50")
        self.mod_berry_restore_var = tk.StringVar(value="10")
        self.mod_berry_threshold_var = tk.StringVar(value="0")
        self.mod_hp_turn_var = tk.StringVar(value="6.25")
        self.mod_attack_multiplier_var = tk.StringVar(value="2.0")
        self.mod_special_attack_multiplier_var = tk.StringVar(value="2.0")
        self.mod_type_multiplier_var = tk.StringVar(value="1.2")
        self.mod_ball_rate_var = tk.StringVar(value="2.0")
        self.mod_ball_type_var = tk.StringVar(value="UltraBall")
        self.mod_vitamin_stat_var = tk.StringVar(value="Attack")
        self.mod_vitamin_ev_amount_var = tk.StringVar(value="10")
        self.mod_boosted_type_var = tk.StringVar(value="Normal")
        self.mod_move_var = tk.StringVar(value="Surf")

        ttk.Label(form, text="Archetype", width=21).grid(row=0, column=0, sticky="w", pady=5)
        self.mod_archetype_combo = ttk.Combobox(
            form, textvariable=self.mod_archetype_var, values=ITEM_MOD_ARCHETYPES, state="readonly"
        )
        self.mod_archetype_combo.grid(row=0, column=1, sticky="ew", pady=5)
        self.mod_archetype_combo.bind("<<ComboboxSelected>>", self._on_mod_archetype_changed)
        ttk.Label(form, text="Behavior / visual template", width=21).grid(row=1, column=0, sticky="w", pady=5)
        self.mod_template_combo = ttk.Combobox(form, textvariable=self.mod_template_var, state="readonly")
        self.mod_template_combo.grid(row=1, column=1, sticky="ew", pady=5)
        self.mod_template_combo.bind("<<ComboboxSelected>>", lambda _event: self._update_mod_template_fields())

        fields = (
            ("Internal asset name", self.mod_internal_name_var),
            ("Display + Bag name", self.mod_display_name_var),
            ("Description", self.mod_description_var),
            ("Item ID", self.mod_item_id_var),
            ("Buy price", self.mod_buy_price_var),
            ("Sell price", self.mod_sell_price_var),
        )
        for row, (label, variable) in enumerate(fields, start=2):
            ttk.Label(form, text=label, width=21).grid(row=row, column=0, sticky="w", pady=5)
            if label == "Item ID":
                item_id_row = ttk.Frame(form)
                item_id_row.grid(row=row, column=1, sticky="ew", pady=5)
                item_id_row.columnconfigure(0, weight=1)
                ttk.Entry(item_id_row, textvariable=variable).grid(row=0, column=0, sticky="ew")
                ttk.Button(
                    item_id_row,
                    text="Next CSTM ID",
                    command=lambda: self._assign_next_custom_item_id(show_error=True),
                ).grid(row=0, column=1, padx=(6, 0))
                ttk.Label(
                    item_id_row,
                    textvariable=self.mod_item_id_info_var,
                    style="Muted.TLabel",
                ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 0))
            else:
                ttk.Entry(form, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=5)

        self.mod_dynamic_frame = ttk.LabelFrame(form, text="Template fields", padding=(8, 5))
        self.mod_dynamic_frame.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(8, 2))
        self.mod_dynamic_frame.columnconfigure(1, weight=1)
        dynamic_specs = (
            ("HPRestoreAmount", "HP restored", ttk.Entry, self.mod_hp_restore_var, None),
            ("HPRestorePercentage", "HP restored (%)", ttk.Entry, self.mod_hp_percent_var, None),
            ("BerryHPRestore", "Berry HP restored", ttk.Entry, self.mod_berry_restore_var, None),
            ("BerryActivationThreshold", "Berry threshold", ttk.Entry, self.mod_berry_threshold_var, None),
            ("HPRestorePerTurn", "HP restored / turn (%)", ttk.Entry, self.mod_hp_turn_var, None),
            ("AttackMultiplier", "Attack multiplier", ttk.Entry, self.mod_attack_multiplier_var, None),
            (
                "SpecialAttackMultiplier", "Sp. Attack multiplier", ttk.Entry,
                self.mod_special_attack_multiplier_var, None,
            ),
            ("TypeBoostMultiplier", "Type multiplier", ttk.Entry, self.mod_type_multiplier_var, None),
            ("CatchRateModifier", "Catch-rate multiplier", ttk.Entry, self.mod_ball_rate_var, None),
            ("VitaminStat", "Vitamin stat", ttk.Combobox, self.mod_vitamin_stat_var, VITAMIN_STATS),
            (
                "EVBoostAmount", "EV boost / use", ttk.Combobox,
                self.mod_vitamin_ev_amount_var, tuple(str(value) for value in VITAMIN_EV_AMOUNTS),
            ),
            ("BoostedType", "Boosted type", ttk.Combobox, self.mod_boosted_type_var, POKEMON_TYPES),
            ("PokeballType", "Ball behavior enum", ttk.Combobox, self.mod_ball_type_var, BALL_TYPES),
            ("TeachableMove", "Teachable move", SearchableCombobox, self.mod_move_var, tuple(move.name for move in MOVES)),
        )
        self.mod_dynamic_rows: dict[str, tuple[ttk.Label, tk.Widget]] = {}
        for row, (key, label, widget_type, variable, values) in enumerate(dynamic_specs):
            label_widget = ttk.Label(self.mod_dynamic_frame, text=label, width=21)
            label_widget.grid(row=row, column=0, sticky="w", pady=3)
            if widget_type is SearchableCombobox:
                widget = SearchableCombobox(self.mod_dynamic_frame, textvariable=variable)
                widget.set_source_values(values or ())
            elif widget_type is ttk.Combobox:
                widget = ttk.Combobox(
                    self.mod_dynamic_frame, textvariable=variable, values=values or (), state="readonly"
                )
            else:
                widget = ttk.Entry(self.mod_dynamic_frame, textvariable=variable)
            widget.grid(row=row, column=1, sticky="ew", pady=3)
            self.mod_dynamic_rows[key] = (label_widget, widget)

        behavior = ttk.LabelFrame(form, text="Effects", padding=(8, 5))
        behavior.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(10, 8))
        self.mod_behavior_info_var = tk.StringVar()
        self.mod_template_info_var = tk.StringVar()
        ttk.Label(behavior, textvariable=self.mod_behavior_info_var, wraplength=620).pack(fill="x", anchor="w")
        ttk.Label(
            behavior, textvariable=self.mod_template_info_var, style="Muted.TLabel", wraplength=620,
        ).pack(fill="x", anchor="w", pady=(4, 0))
        buttons = ttk.Frame(form)
        buttons.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        self.mod_build_button = ttk.Button(buttons, text="Build .pak...", command=self.build_item_mod_only)
        self.mod_build_button.pack(side="left")
        self.mod_install_button = ttk.Button(buttons, text="Build + Install...", command=self.build_and_install_item_mod)
        self.mod_install_button.pack(side="left", padx=6)
        self.mod_uninstall_button = ttk.Button(
            buttons, text="Uninstall editor mod", command=self.uninstall_current_item_mod, state="disabled"
        )
        self.mod_uninstall_button.pack(side="left")

        top = ttk.Frame(environment)
        top.pack(fill="x")
        ttk.Label(top, text="Required components", style="SectionTitle.TLabel").pack(side="left")
        ttk.Button(top, text="Refresh", command=self._refresh_mod_builder_status).pack(side="right")
        self.mod_status_frame = ttk.Frame(environment)
        self.mod_status_frame.pack(fill="both", expand=True, pady=(8, 0))

        runtime = ttk.LabelFrame(environment, text="Vitamin runtime rules", padding=(8, 6))
        runtime.pack(fill="x", pady=(10, 0))
        runtime.columnconfigure(1, weight=1)
        self.mod_runtime_stat_cap_var = tk.StringVar(value="252")
        self.mod_runtime_total_cap_var = tk.StringVar(value="510")
        self.mod_runtime_scope_var = tk.StringVar(value="Custom CSTM Vitamins only")
        self.mod_runtime_status_var = tk.StringVar(value="Checking runtime hook support...")
        runtime_fields = (
            ("Per-stat cap", self.mod_runtime_stat_cap_var, ("100", "252")),
            ("Total EV cap", self.mod_runtime_total_cap_var, ("510", "Unlimited")),
            (
                "Apply to",
                self.mod_runtime_scope_var,
                ("Custom CSTM Vitamins only", "All Vitamins"),
            ),
        )
        for row, (label, variable, values) in enumerate(runtime_fields):
            ttk.Label(runtime, text=label, width=14).grid(row=row, column=0, sticky="w", pady=2)
            ttk.Combobox(
                runtime,
                textvariable=variable,
                values=values,
                state="readonly",
            ).grid(row=row, column=1, sticky="ew", pady=2)
        runtime_buttons = ttk.Frame(runtime)
        runtime_buttons.grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 2))
        self.mod_runtime_install_button = ttk.Button(
            runtime_buttons,
            text="Install runtime rules",
            command=self.install_vitamin_runtime_rules,
        )
        self.mod_runtime_install_button.pack(side="left")
        self.mod_runtime_uninstall_button = ttk.Button(
            runtime_buttons,
            text="Uninstall runtime rules",
            command=self.uninstall_vitamin_runtime_rules,
            state="disabled",
        )
        self.mod_runtime_uninstall_button.pack(side="left", padx=6)
        ttk.Label(
            runtime,
            textvariable=self.mod_runtime_status_var,
            style="Muted.TLabel",
            wraplength=420,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(3, 0))

        self.mod_environment_var = tk.StringVar(value="Checking...")
        ttk.Label(environment, textvariable=self.mod_environment_var, style="Muted.TLabel", wraplength=430).pack(
            fill="x", pady=(10, 0)
        )
        ttk.Label(
            environment,
            text=(
                "External Cobblemon PNG/OGG files are source media only: Gamma needs UE 5.6-cooked Texture/"
                "Sprite/SoundWave assets. The supplied ZIP has no license file, so it is not bundled."
            ),
            style="Muted.TLabel",
            wraplength=430,
        ).pack(fill="x", pady=(12, 0))
        self.mod_item_id_var.trace_add("write", self._update_custom_item_id_info)
        for variable in (
            self.mod_display_name_var,
            self.mod_hp_restore_var,
            self.mod_hp_percent_var,
            self.mod_berry_restore_var,
            self.mod_berry_threshold_var,
            self.mod_hp_turn_var,
            self.mod_attack_multiplier_var,
            self.mod_special_attack_multiplier_var,
            self.mod_type_multiplier_var,
            self.mod_ball_rate_var,
            self.mod_ball_type_var,
            self.mod_vitamin_stat_var,
            self.mod_vitamin_ev_amount_var,
            self.mod_boosted_type_var,
            self.mod_move_var,
        ):
            variable.trace_add("write", self._update_mod_effect_summary)
        self._assign_next_custom_item_id()
        self._on_mod_archetype_changed()
        self._refresh_mod_builder_status()

    def _on_mod_archetype_changed(self, _event=None) -> None:
        templates = templates_for_archetype(self.mod_archetype_var.get())
        labels = tuple(template.label for template in templates)
        self.mod_template_combo.configure(values=labels)
        if self.mod_template_var.get() not in labels:
            self.mod_template_var.set(labels[0] if labels else "")
        self._update_mod_template_fields()

    def _selected_mod_template(self):
        return next(
            (
                template
                for template in templates_for_archetype(self.mod_archetype_var.get())
                if template.label == self.mod_template_var.get()
            ),
            None,
        )

    def _update_custom_item_id_info(self, *_args) -> None:
        try:
            item_id = int(self.mod_item_id_var.get())
        except ValueError:
            self.mod_item_id_info_var.set("ItemID is a signed 32-bit integer; letters are not accepted by Gamma.")
            return
        tag = custom_item_id_tag(item_id)
        if tag:
            self.mod_item_id_info_var.set(f"{tag} · stored by Gamma as numeric int32 {item_id}")
        else:
            self.mod_item_id_info_var.set("Manual numeric ID · Gamma's ItemID field cannot contain letters")

    def _assign_next_custom_item_id(self, *, show_error: bool = False) -> None:
        try:
            if self.smoke_test:
                item_id = CUSTOM_ITEM_ID_BASE + 1
            else:
                used = (self.custom_item_spec.item_id,) if self.custom_item_spec else ()
                item_id = allocate_custom_item_id(used_ids=used)
            self.mod_item_id_var.set(str(item_id))
        except ModBuilderError as exc:
            self.mod_item_id_info_var.set(str(exc))
            if show_error:
                messagebox.showerror(APP_TITLE, str(exc))

    def _update_mod_template_fields(self) -> None:
        template = self._selected_mod_template()
        visible = set(template.editable_fields if template else ())
        for key, (label, widget) in self.mod_dynamic_rows.items():
            if key in visible:
                label.grid()
                widget.grid()
            else:
                label.grid_remove()
                widget.grid_remove()
        if template:
            risk = " Experimental runtime path." if template.experimental else ""
            self._update_mod_effect_summary()
            self.mod_template_info_var.set(
                f"Clones {template.label}'s cooked icon, flags, effects and dependencies; only the fields shown above change."
                f"{risk} ItemID is numeric-only; CSTM IDs are generated sequentially. One installed editor patch/item at a time."
            )
        else:
            self.mod_behavior_info_var.set("")
            self.mod_template_info_var.set("Choose a supported template.")

    def _update_mod_effect_summary(self, *_args) -> None:
        if not hasattr(self, "mod_behavior_info_var"):
            return
        template = self._selected_mod_template()
        if not template:
            self.mod_behavior_info_var.set("")
            return
        values = {
            "HPRestoreAmount": self.mod_hp_restore_var.get(),
            "HPRestorePercentage": self.mod_hp_percent_var.get(),
            "BerryHPRestore": self.mod_berry_restore_var.get(),
            "BerryActivationThreshold": self.mod_berry_threshold_var.get(),
            "HPRestorePerTurn": self.mod_hp_turn_var.get(),
            "AttackMultiplier": self.mod_attack_multiplier_var.get(),
            "SpecialAttackMultiplier": self.mod_special_attack_multiplier_var.get(),
            "TypeBoostMultiplier": self.mod_type_multiplier_var.get(),
            "CatchRateModifier": self.mod_ball_rate_var.get(),
            "VitaminStat": self.mod_vitamin_stat_var.get(),
            "EVBoostAmount": self.mod_vitamin_ev_amount_var.get(),
            "BoostedType": self.mod_boosted_type_var.get(),
            "PokeballType": self.mod_ball_type_var.get(),
            "TeachableMove": self.mod_move_var.get(),
        }
        self.mod_behavior_info_var.set(
            player_effect_summary(template, item_name=self.mod_display_name_var.get(), values=values)
        )

    def _refresh_mod_builder_status(self) -> None:
        self.mod_toolchain = discover_toolchain()
        self.custom_item_spec = installed_item(self.mod_toolchain)
        self.vitamin_runtime_environment = discover_vitamin_runtime_environment(self.mod_toolchain)
        self.vitamin_runtime_config = installed_vitamin_runtime_config(self.vitamin_runtime_environment)
        for child in self.mod_status_frame.winfo_children():
            child.destroy()
        for row, (label, value, ok) in enumerate(self.mod_toolchain.status_rows()):
            ttk.Label(
                self.mod_status_frame,
                text="OK" if ok else "MISSING",
                foreground="#147a34" if ok else "#b42318",
            ).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=2)
            ttk.Label(self.mod_status_frame, text=label).grid(row=row, column=1, sticky="w", pady=2)
            ttk.Label(self.mod_status_frame, text=value, style="Muted.TLabel", wraplength=300).grid(
                row=row, column=2, sticky="w", padx=(8, 0), pady=2
            )
        installed = self.custom_item_spec
        self.mod_uninstall_button.configure(state="normal" if installed else "disabled")
        self.mod_build_button.configure(state="normal" if self.mod_toolchain.ready else "disabled")
        self.mod_install_button.configure(state="normal" if self.mod_toolchain.ready else "disabled")
        self.mod_environment_var.set(
            f"Installed editor item: {installed.display_name} (ID {installed.item_id})."
            if installed
            else (
                "Toolchain ready; no editor-owned patch installed."
                if self.mod_toolchain.ready
                else "Toolchain incomplete; see missing rows above."
            )
        )
        if hasattr(self, "pokemon_editor"):
            self.pokemon_editor.held_item_combo.set_source_values(self._held_item_names())
        runtime = self.vitamin_runtime_environment
        installed_runtime = self.vitamin_runtime_config
        runtime_conflict = bool(
            not installed_runtime
            and (
                (runtime.loader_target and runtime.loader_target.exists())
                or (runtime.ue4ss_target and runtime.ue4ss_target.exists())
            )
        )
        self.mod_runtime_install_button.configure(
            state="normal" if runtime.ready and not runtime_conflict else "disabled",
            text="Update runtime rules" if installed_runtime else "Install runtime rules",
        )
        self.mod_runtime_uninstall_button.configure(state="normal" if installed_runtime else "disabled")
        if installed_runtime:
            self.mod_runtime_stat_cap_var.set(str(installed_runtime.stat_cap))
            self.mod_runtime_total_cap_var.set(
                str(installed_runtime.total_cap) if installed_runtime.total_cap is not None else "Unlimited"
            )
            self.mod_runtime_scope_var.set(
                "All Vitamins" if installed_runtime.scope == "all" else "Custom CSTM Vitamins only"
            )
            total = installed_runtime.total_cap if installed_runtime.total_cap is not None else "Unlimited"
            scope = "all Vitamins" if installed_runtime.scope == "all" else "custom CSTM Vitamins"
            self.mod_runtime_status_var.set(
                f"Installed: {installed_runtime.stat_cap}/stat, {total} total, {scope}. Close the game before updating."
            )
        elif runtime_conflict:
            self.mod_runtime_status_var.set(
                "An unmanaged UE4SS/dwmapi installation exists; the editor will not overwrite or delete it."
            )
        elif runtime.ready:
            self.mod_runtime_status_var.set(
                "Ready. This installs an editor-owned UE4SS hook; it is separate from the item .pak."
            )
        else:
            self.mod_runtime_status_var.set("Local GE-1.0.0 UE4SS runtime source is missing or incomplete.")

    def _vitamin_runtime_config_from_form(self) -> VitaminRuntimeConfig:
        total_text = self.mod_runtime_total_cap_var.get()
        scope = "all" if self.mod_runtime_scope_var.get() == "All Vitamins" else "custom"
        return VitaminRuntimeConfig(
            stat_cap=int(self.mod_runtime_stat_cap_var.get()),
            total_cap=None if total_text == "Unlimited" else int(total_text),
            scope=scope,
        ).validated()

    def install_vitamin_runtime_rules(self) -> None:
        try:
            config = self._vitamin_runtime_config_from_form()
            total = config.total_cap if config.total_cap is not None else "Unlimited"
            scope = "every Vitamin" if config.scope == "all" else "CSTM custom Vitamins only"
            action = "Update" if self.vitamin_runtime_config else "Install"
            if not messagebox.askyesno(
                APP_TITLE,
                f"{action} runtime Vitamin rules?\n\n"
                f"Per-stat cap: {config.stat_cap}\nTotal cap: {total}\nScope: {scope}\n\n"
                "This installs an editor-owned UE4SS loader beside the game executable. Close Gamma first.",
            ):
                return
            install_vitamin_runtime(config, self.vitamin_runtime_environment)
            self._refresh_mod_builder_status()
            messagebox.showinfo(
                APP_TITLE,
                "Vitamin runtime rules installed and ownership manifest verified. Launch Gamma normally to activate them.",
            )
        except (ValueError, ModBuilderError) as exc:
            messagebox.showerror(APP_TITLE, str(exc))

    def uninstall_vitamin_runtime_rules(self) -> None:
        if not messagebox.askyesno(
            APP_TITLE,
            "Uninstall the editor-owned Vitamin runtime rules?\n\n"
            "Vitamin behavior returns to Gamma's native 100/stat and 510-total caps.",
        ):
            return
        try:
            uninstall_vitamin_runtime(self.vitamin_runtime_environment)
            self._refresh_mod_builder_status()
            messagebox.showinfo(APP_TITLE, "Vitamin runtime rules uninstalled; vanilla behavior is restored.")
        except ModBuilderError as exc:
            messagebox.showerror(APP_TITLE, str(exc))

    def _item_mod_spec_from_form(self) -> ItemModSpec:
        try:
            template = self._selected_mod_template()
            if template is None:
                raise ModBuilderError("Choose an item archetype and behavior template.")
            visible = set(template.editable_fields)
            overrides: dict[str, object] = {}
            if "BerryHPRestore" in visible:
                overrides["BerryHPRestore"] = int(self.mod_berry_restore_var.get())
            if "EVBoostAmount" in visible:
                overrides["EVBoostAmount"] = int(self.mod_vitamin_ev_amount_var.get())
            for key, variable in (
                ("HPRestorePercentage", self.mod_hp_percent_var),
                ("BerryActivationThreshold", self.mod_berry_threshold_var),
                ("HPRestorePerTurn", self.mod_hp_turn_var),
                ("AttackMultiplier", self.mod_attack_multiplier_var),
                ("SpecialAttackMultiplier", self.mod_special_attack_multiplier_var),
                ("TypeBoostMultiplier", self.mod_type_multiplier_var),
                ("CatchRateModifier", self.mod_ball_rate_var),
            ):
                if key in visible:
                    overrides[key] = float(variable.get())
            for key, variable in (
                ("VitaminStat", self.mod_vitamin_stat_var),
                ("BoostedType", self.mod_boosted_type_var),
                ("PokeballType", self.mod_ball_type_var),
            ):
                if key in visible:
                    overrides[key] = variable.get()
            if "TeachableMove" in visible:
                move = MOVES_BY_NAME.get(self.mod_move_var.get().strip().casefold())
                if move is None:
                    raise ModBuilderError("Choose a verified shipped move for the TM.")
                overrides["TeachableMove"] = {"package": move.path, "asset": move.object_name}
            return ItemModSpec(
                internal_name=self.mod_internal_name_var.get().strip(),
                display_name=self.mod_display_name_var.get(),
                description=self.mod_description_var.get(),
                item_id=int(self.mod_item_id_var.get()),
                buy_price=int(self.mod_buy_price_var.get()),
                sell_price=int(self.mod_sell_price_var.get()),
                hp_restore_amount=int(self.mod_hp_restore_var.get()),
                template_key=template.key,
                property_overrides=overrides,
            ).validated()
        except ValueError as exc:
            raise ModBuilderError("Item ID, prices and integer effect amounts need whole numbers; multipliers need numbers.") from exc

    def _choose_mod_output(self) -> Path | None:
        selected = filedialog.askdirectory(title="Choose folder for the built item patch")
        return Path(selected) if selected else None

    def build_item_mod_only(self) -> None:
        output = self._choose_mod_output()
        if output is None:
            return
        self.configure(cursor="wait")
        self.update_idletasks()
        try:
            built = build_item_mod(self._item_mod_spec_from_form(), output, self.mod_toolchain)
            messagebox.showinfo(
                APP_TITLE,
                f"Built and SHA-256 verified:\n{built.pak_path}\n\nThe game installation was not changed.",
            )
            self._assign_next_custom_item_id()
        except ModBuilderError as exc:
            messagebox.showerror(APP_TITLE, str(exc))
        finally:
            self.configure(cursor="")

    def build_and_install_item_mod(self) -> None:
        output = self._choose_mod_output()
        if output is None:
            return
        installed = installed_item(self.mod_toolchain)
        replacing = installed is not None
        reference = self._loaded_custom_item_reference(installed) if installed else None
        if reference:
            messagebox.showerror(
                APP_TITLE,
                f"The currently installed item is still referenced by {reference}.\n\n"
                "Remove it there and use Save + Backup before replacing its runtime patch.",
            )
            return
        prompt = "Build and install this item patch into Pokémon Gamma Emerald?"
        if replacing:
            prompt += "\n\nThe currently installed editor item will be backed up and replaced."
        if not messagebox.askyesno(APP_TITLE, prompt):
            return
        self.configure(cursor="wait")
        self.update_idletasks()
        try:
            built = build_item_mod(self._item_mod_spec_from_form(), output, self.mod_toolchain)
            target = install_item_mod(built, self.mod_toolchain, replace_owned=replacing)
            self._refresh_mod_builder_status()
            messagebox.showinfo(
                APP_TITLE,
                f"Installed and verified:\n{target}\n\nThe item is now available in Bag > Add Item under {built.spec.pocket}.",
            )
            self._assign_next_custom_item_id()
        except ModBuilderError as exc:
            messagebox.showerror(APP_TITLE, str(exc))
        finally:
            self.configure(cursor="")

    def uninstall_current_item_mod(self) -> None:
        custom = installed_item(self.mod_toolchain)
        reference = self._loaded_custom_item_reference(custom) if custom else None
        if reference:
            messagebox.showerror(
                APP_TITLE,
                f"Remove {custom.display_name} from {reference} and use Save + Backup before uninstalling its runtime patch.",
            )
            return
        if not messagebox.askyesno(
            APP_TITLE, "Uninstall the editor-owned item patch?\n\nThe base game pak is never touched."
        ):
            return
        try:
            uninstall_item_mod(self.mod_toolchain)
            self._refresh_mod_builder_status()
            messagebox.showinfo(APP_TITLE, "Editor-owned item patch uninstalled.")
        except ModBuilderError as exc:
            messagebox.showerror(APP_TITLE, str(exc))

    def _loaded_custom_item_reference(self, custom: ItemModSpec) -> str | None:
        """Describe the first loaded-save reference that would be orphaned by patch removal."""
        doc = self.current_document()
        if doc is None:
            return None
        target = custom.display_name.casefold()
        if any(entry.name.casefold() == target for entry in bag_entries(doc)):
            return "the loaded Bag"
        pokemon = list(party_pokemon(doc))
        for box_index in range(len(box_names(doc))):
            pokemon.extend(item for item in storage_pokemon(doc, box_index) if item.occupied)
        for item in pokemon:
            held = str(item.fields.get("HeldItem", "")).split("::")[-1].strip()
            if held.casefold() == target:
                location = "the loaded Party" if item.source == "Party" else "a loaded Storage box"
                return f"{location} (held by {item.species})"
        return None

    def _bag_item_names(self, pocket: str) -> tuple[str, ...]:
        names = [choice.name for choice in ITEMS_BY_POCKET[pocket]]
        custom = getattr(self, "custom_item_spec", None)
        if custom and custom.pocket == pocket and custom.display_name not in names:
            names.append(custom.display_name)
        return tuple(names)

    def _custom_bag_items(self, pocket: str) -> tuple[str, ...]:
        custom = getattr(self, "custom_item_spec", None)
        return (custom.display_name,) if custom and custom.pocket == pocket else ()

    def _held_item_names(self) -> tuple[str, ...]:
        names = list(HOLDABLE_ITEM_NAMES)
        custom = getattr(self, "custom_item_spec", None)
        if custom and custom.archetype in {"Held Item", "Berry"} and custom.display_name not in names:
            names.append(custom.display_name)
        return tuple(names)

    def _build_pokemon(self) -> None:
        self.pokemon_tab.rowconfigure(0, weight=1)
        self.pokemon_tab.columnconfigure(1, weight=1)
        roster = ttk.Frame(self.pokemon_tab, padding=(2, 2, 10, 2))
        roster.grid(row=0, column=0, sticky="ns")

        ttk.Label(roster, text="Party", style="SectionTitle.TLabel").pack(anchor="w")
        ttk.Label(
            roster, text="Drag to move; right-click to Copy, Set, or Release.", style="Muted.TLabel"
        ).pack(anchor="w", pady=(1, 6))
        ttk.Label(roster, textvariable=self.clone_preset_var, style="Muted.TLabel").pack(
            anchor="w", pady=(0, 6)
        )
        self.party_grid = ttk.Frame(roster)
        self.party_grid.pack(fill="x")
        self.party_cards: list[tk.Label] = []
        for index in range(6):
            card = tk.Label(
                self.party_grid, width=116, height=82, relief="ridge", borderwidth=1,
                bg="#f2f5f7", anchor="center", justify="center", cursor="hand2",
                image=self.empty_slot_sprite, compound="top",
            )
            card.grid(row=index // 3, column=index % 3, sticky="nsew", padx=2, pady=2)
            card.pokemon_location = ("party", None, index)  # type: ignore[attr-defined]
            card.bind("<ButtonPress-1>", lambda _event, loc=card.pokemon_location: self._on_pokemon_press(loc))
            card.bind("<ButtonRelease-1>", self._on_pokemon_release)
            card.bind("<Button-3>", lambda event, loc=card.pokemon_location: self._open_pokemon_context(event, loc))
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
                self.storage_grid, width=78, height=68, relief="ridge", borderwidth=1,
                bg="#f7f8f9", anchor="center", justify="center", cursor="hand2",
                image=self.empty_slot_sprite, compound="top",
            )
            card.grid(row=index // 5, column=index % 5, sticky="nsew", padx=2, pady=2)
            card.bind(
                "<ButtonPress-1>",
                lambda _event, slot=index: self._on_pokemon_press(("storage", self._selected_box_index(), slot)),
            )
            card.bind("<ButtonRelease-1>", self._on_pokemon_release)
            card.bind(
                "<Button-3>",
                lambda event, slot=index: self._open_pokemon_context(
                    event, ("storage", self._selected_box_index(), slot)
                ),
            )
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
        ttk.Button(header, text="Catalog Info", command=self.show_item_catalog_info).pack(side="right", padx=6)
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
        self.bag_name_combo = SearchableCombobox(editor, textvariable=self.bag_name_var)
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
        for name, title, width in (("id", "Hoenn #", 80), ("species", "Pokémon", 220), ("type", "Type(s)", 140)):
            self.dex_tree.heading(name, text=title)
            self.dex_tree.column(name, width=width, anchor="w")
        self.dex_tree.pack(fill="both", expand=True)
        self.dex_tree.bind("<<TreeviewSelect>>", self._on_dex_selected)
        ttk.Label(details, text="Pokémon information", style="SectionTitle.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )
        details.rowconfigure(2, weight=1)
        details.columnconfigure(0, weight=1)
        info = ttk.Frame(details)
        info.grid(row=1, column=0, sticky="ew")
        info.columnconfigure(1, weight=1)
        self.dex_detail_vars: dict[str, tk.StringVar] = {}
        fields = (
            ("Name", "name"), ("Hoenn number", "number"), ("Types", "type"),
            ("Abilities", "abilities"), ("Height / Weight", "size"),
            ("Gamma DataAsset", "asset"), ("Owned locations", "owned"),
        )
        for row, (label, key) in enumerate(fields):
            ttk.Label(info, text=label + ":", width=18).grid(row=row, column=0, sticky="nw", pady=3)
            var = tk.StringVar(value="—")
            self.dex_detail_vars[key] = var
            ttk.Label(info, textvariable=var, wraplength=650).grid(row=row, column=1, sticky="nw", pady=3)

        lower = ttk.Frame(details)
        lower.grid(row=2, column=0, sticky="nsew", pady=(14, 0))
        lower.columnconfigure(0, weight=1)
        lower.columnconfigure(1, weight=1)
        ttk.Label(lower, text="Base stats", style="SectionTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(lower, text="Type defenses", style="SectionTitle.TLabel").grid(row=0, column=1, sticky="w", padx=(18, 0))
        self.dex_stats_canvas = tk.Canvas(lower, width=390, height=230, highlightthickness=0, bg="#ffffff")
        self.dex_stats_canvas.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        defenses = ttk.Frame(lower)
        defenses.grid(row=1, column=1, sticky="nw", padx=(18, 0), pady=(6, 0))
        self.dex_defense_labels: dict[str, tk.Label] = {}
        for index, type_name in enumerate(TYPE_ORDER):
            row, column = divmod(index, 6)
            label = tk.Label(
                defenses, text=type_name[:3].upper() + "\n1×", width=6, height=2,
                relief="solid", borderwidth=1, bg=TYPE_COLORS[type_name], fg=_type_text_color(type_name),
                font=("Segoe UI", 8, "bold"),
            )
            label.grid(row=row, column=column, padx=1, pady=1)
            self.dex_defense_labels[type_name] = label
        self.dex_note_var = tk.StringVar()
        ttk.Label(details, textvariable=self.dex_note_var, style="Muted.TLabel", wraplength=700).grid(
            row=3, column=0, sticky="w", pady=(12, 0)
        )

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
            self.clone_preset = None
            self.clone_preset_var.set("Clone preset: none")
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
            text = f"#{index + 1}  {pokemon.species}\nLv {_number(pokemon.fields.get('Level'))}" if pokemon else f"#{index + 1}\n(empty)"
            image = self.sprites.get(pokemon.species, 32) if pokemon else None
            card.configure(
                text=text,
                image=image or self.empty_slot_sprite,
                bg="#d9edf7" if selected == ("party", None, index) else "#f2f5f7",
                relief="solid" if selected == ("party", None, index) else "ridge",
                borderwidth=2 if selected == ("party", None, index) else 1,
            )
        for index, card in enumerate(self.storage_cards):
            location = ("storage", box, index)
            card.pokemon_location = location  # type: ignore[attr-defined]
            pokemon = storage_by_slot.get(index)
            occupied = bool(pokemon and pokemon.occupied)
            text = f"{index + 1}  {pokemon.species}\nLv {_number(pokemon.fields.get('Level'))}" if occupied else f"{index + 1}\n—"
            image = self.sprites.get(pokemon.species, 32) if occupied and pokemon else None
            card.configure(
                text=text,
                image=image or self.empty_slot_sprite,
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

    def _pokemon_at(self, location: tuple[str, int | None, int]) -> PokemonView | None:
        kind, box, slot = location
        if kind == "party":
            return next((item for item in self.party_views if item.slot_index == slot), None)
        doc = self.current_document()
        if doc is None or box is None:
            return None
        return next((item for item in storage_pokemon(doc, box) if item.slot_index == slot), None)

    def _open_pokemon_context(self, event, location: tuple[str, int | None, int]) -> None:
        self.drag_source = None
        self._select_pokemon_location(location)
        pokemon = self._pokemon_at(location)
        target = self._set_target_at(location)
        menu = tk.Menu(self, tearoff=False)
        occupied_state = "normal" if pokemon and pokemon.occupied else "disabled"
        set_state = "normal" if self.clone_preset is not None and target is not None else "disabled"
        menu.add_command(
            label="Clone (Copy)", state=occupied_state,
            command=lambda: self.copy_pokemon_clone_preset(location),
        )
        menu.add_command(
            label="Set", state=set_state,
            command=lambda: self.set_pokemon_clone_preset(location),
        )
        menu.add_separator()
        menu.add_command(
            label="Release (Delete)", state=occupied_state,
            command=lambda: self.release_selected_pokemon(location),
        )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _set_target_at(self, location: tuple[str, int | None, int]) -> PokemonView | None:
        kind, box, slot = location
        if kind == "party":
            target_slot = party_set_target_slot(len(self.party_views), slot)
            if target_slot is None:
                return None
            return PokemonView(
                prefix=f"Party[{target_slot}]", source="Party", box_index=None,
                slot_index=target_slot, species="Empty", occupied=False, fields={},
            )
        pokemon = self._pokemon_at(location)
        return pokemon if pokemon is not None and not pokemon.occupied else None

    def copy_pokemon_clone_preset(self, location: tuple[str, int | None, int]) -> None:
        doc = self.current_document()
        source = self._pokemon_at(location)
        if doc is None or source is None or not source.occupied:
            return
        try:
            self.clone_preset = copy_pokemon_preset(doc, source)
            preset_text = pokemon_showdown_preset(source)
            clipboard_note = ""
            try:
                self.clipboard_clear()
                self.clipboard_append(preset_text)
                self.update_idletasks()
            except tk.TclError:
                clipboard_note = " (system clipboard unavailable)"
            self.clone_preset_var.set(f"Clone preset: {source.species} (ready to Set)")
            self.status_var.set(
                f"Copied {source.species} preset{clipboard_note}; "
                "right-click an empty Party/Storage slot and choose Set"
            )
        except (ValueError, GammaEditorError) as exc:
            messagebox.showerror(APP_TITLE, str(exc))

    def set_pokemon_clone_preset(self, location: tuple[str, int | None, int]) -> None:
        doc = self.current_document()
        preset = self.clone_preset
        target = self._set_target_at(location)
        if doc is None or preset is None or target is None:
            return
        self.configure(cursor="wait")
        self.update_idletasks()
        try:
            self.working_gvas = set_pokemon_preset(doc, preset, target)
            actual_location = (
                ("party", None, target.slot_index) if location[0] == "party" else location
            )
            self.selected_pokemon_location = actual_location
            place = (
                f"Party {actual_location[2] + 1}"
                if location[0] == "party"
                else f"{self.box_var.get()} / slot {location[2] + 1}"
            )
            redirected = (
                f" (redirected from clicked Party {location[2] + 1} to the nearest empty slot)"
                if location[0] == "party" and location[2] != target.slot_index
                else ""
            )
            self._mark_staged(f"Set cloned {preset.species} preset into {place}{redirected}")
        except (ValueError, GammaEditorError) as exc:
            messagebox.showerror(APP_TITLE, str(exc))
        finally:
            self.configure(cursor="")

    def release_selected_pokemon(self, location: tuple[str, int | None, int]) -> None:
        doc = self.current_document()
        pokemon = self._pokemon_at(location)
        if doc is None or pokemon is None or not pokemon.occupied:
            return
        place = (
            f"Party {pokemon.slot_index + 1}"
            if pokemon.source == "Party"
            else f"{self.box_var.get()} / slot {pokemon.slot_index + 1}"
        )
        if not messagebox.askyesno(
            APP_TITLE,
            f"Release {pokemon.species} from {place}?\n\n"
            "This deletion stays staged until Save + Backup.",
        ):
            return
        try:
            self.working_gvas = release_pokemon(doc, pokemon)
            if pokemon.source == "Party":
                remaining = len(party_pokemon(parse_gvas(self.working_gvas)))
                self.selected_pokemon_location = ("party", None, min(pokemon.slot_index, remaining - 1))
            else:
                self.selected_pokemon_location = location
            self._mark_staged(f"Released {pokemon.species} from {place}")
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
        self.bag_name_combo.set_source_values(self._bag_item_names(pocket))
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
        item_combo = SearchableCombobox(dialog, textvariable=item_var, width=28)
        item_combo.set_source_values((), enabled=False)
        item_combo.grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=6)
        ttk.Label(dialog, text="Quantity").grid(row=2, column=0, sticky="w", padx=12, pady=6)
        ttk.Spinbox(dialog, textvariable=qty_var, from_=1, to=9999, width=29).grid(
            row=2, column=1, sticky="ew", padx=(0, 12), pady=6
        )

        def pocket_changed(_event=None) -> None:
            pocket = label_to_pocket.get(pocket_var.get())
            item_var.set("")
            item_combo.set_source_values(
                self._bag_item_names(pocket) if pocket else (),
                enabled=bool(pocket),
            )

        def add() -> None:
            doc = self.current_document()
            pocket = label_to_pocket.get(pocket_var.get())
            selected_name = exact_choice(list(self._bag_item_names(pocket)), item_var.get()) if pocket else None
            if doc is None or pocket is None or selected_name is None:
                messagebox.showerror(APP_TITLE, "Choose a pocket and an item.", parent=dialog)
                return
            try:
                self.working_gvas = add_bag_item(
                    doc,
                    pocket,
                    selected_name,
                    int(qty_var.get()),
                    additional_items=self._custom_bag_items(pocket),
                )
                dialog.destroy()
                self._mark_staged(f"Staged add/update: {selected_name}")
            except (ValueError, GammaEditorError) as exc:
                messagebox.showerror(APP_TITLE, str(exc), parent=dialog)

        pocket_combo.bind("<<ComboboxSelected>>", pocket_changed)
        ttk.Button(dialog, text="Add Item", command=add).grid(row=3, column=1, sticky="e", padx=12, pady=(10, 14))
        dialog.bind("<Return>", lambda _event: add())

    def show_item_catalog_info(self) -> None:
        counts = ", ".join(
            f"{BAG_POCKET_LABELS[pocket]}: {len(ITEMS_BY_POCKET[pocket])}"
            for pocket in BAG_POCKETS
        )
        messagebox.showinfo(
            APP_TITLE,
            "This list is the GE-1.0.0 asset catalog, not the full Pokémon-series item pool.\n\n"
            f"Verified writable items (86 total): {counts}.\n\n"
            "The executable names 8 additional Ball enums—Dive, Dusk, Heal, Master, Nest, Net, "
            "Quick and Safari—but this build has no matching ItemData + Ball Blueprint for them. "
            "They stay unavailable to prevent runtime-invalid saves.",
        )

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
            info = SPECIES_INFO.get(species.name.casefold())
            types = info.types if info else (species.category,)
            abilities = " ".join(item.name for item in info.abilities) if info else ""
            haystack = f"{species.name} {' '.join(types)} {abilities} {dex_by_name.get(species.name, '')}".casefold()
            if needle and needle not in haystack:
                continue
            self.dex_tree.insert(
                "", "end", iid=species.name,
                values=(dex_by_name.get(species.name, "—"), species.name, " / ".join(types)),
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
        info = SPECIES_INFO.get(species.name.casefold())
        locations: list[str] = []
        for pokemon in self.party_views:
            if pokemon.species == species.name:
                locations.append(f"Party {pokemon.slot_index + 1}")
        doc = self.current_document()
        if doc is not None:
            names = box_names(doc)
            for prop in doc.properties:
                if prop.name != "SpeciesData" or not prop.path.startswith("Boxes["):
                    continue
                if f"DA_{species.name}" not in str(prop.value):
                    continue
                match = re.match(r"^Boxes\[(\d+)]\.Pokemon(?:\[(\d+)])?\.SpeciesData$", prop.path)
                if match:
                    box_index = int(match.group(1))
                    slot_index = int(match.group(2) or 0)
                    locations.append(f"{names[box_index]} / Slot {slot_index + 1}")
        self.dex_detail_vars["name"].set(species.name)
        self.dex_detail_vars["number"].set(str(dex_by_name.get(species.name, "Not mapped")))
        self.dex_detail_vars["type"].set(" / ".join(info.types) if info else f"{species.category} (asset folder)")
        self.dex_detail_vars["abilities"].set(
            "  •  ".join(item.label for item in info.abilities) if info else "Game-specific / not mapped"
        )
        self.dex_detail_vars["size"].set(
            f"{info.height_m:g} m / {info.weight_kg:g} kg" if info else "Game-specific / not mapped"
        )
        self.dex_detail_vars["asset"].set(species.path)
        self.dex_detail_vars["owned"].set(", ".join(locations) if locations else "None in Party/Storage")
        self._draw_dex_stats(info)
        if info:
            defenses = type_defenses(info.types)
            for type_name, label in self.dex_defense_labels.items():
                multiplier = defenses[type_name]
                text = "¼" if multiplier == .25 else "½" if multiplier == .5 else str(int(multiplier))
                label.configure(text=type_name[:3].upper() + f"\n{text}×")
            self.dex_note_var.set("(H) marks a Hidden Ability. Type defenses show incoming damage multipliers.")
        else:
            for type_name, label in self.dex_defense_labels.items():
                label.configure(text=type_name[:3].upper() + "\n—")
            self.dex_note_var.set("This game-specific species has no standard metadata mapping; its save fields remain preserved.")

    def _draw_dex_stats(self, info) -> None:
        canvas = self.dex_stats_canvas
        canvas.delete("all")
        if info is None:
            canvas.create_text(12, 24, anchor="w", text="No mapped base-stat data", fill="#66717a")
            return
        rows = (
            ("HP", "HP"), ("Attack", "Attack"), ("Defense", "Defense"),
            ("Sp. Atk", "SpecialAttack"), ("Sp. Def", "SpecialDefense"), ("Speed", "Speed"),
        )
        colors = ("#ff6b35", "#98d51d", "#f7d23b", "#ff8a2a", "#80cf25", "#f3c82e")
        for index, ((label, key), color) in enumerate(zip(rows, colors)):
            y = 20 + index * 30
            value = int(info.base_stats[key])
            canvas.create_text(8, y, anchor="w", text=label, fill="#59636b")
            canvas.create_text(82, y, anchor="e", text=str(value), fill="#31383d")
            canvas.create_rectangle(96, y - 6, 96 + 260 * min(value, 255) / 255, y + 6, fill=color, outline="")
        canvas.create_text(
            8, 205, anchor="w", text=f"Total  {sum(info.base_stats.values())}",
            font=("Segoe UI", 10, "bold"),
        )

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
            selected_name = exact_choice(list(self._bag_item_names(item.category)), self.bag_name_var.get())
            if selected_name is None:
                raise ValueError(f"Choose a valid item from the {BAG_POCKET_LABELS[item.category]} pocket.")
            item_name = selected_name
            if item_name == item.name and quantity == item.quantity:
                self.status_var.set("Bag: no changes to stage")
                return
            self.working_gvas = edit_bag_item(
                doc,
                item,
                item_name,
                quantity,
                additional_items=self._custom_bag_items(item.category),
            )
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
        app.tabs.select(app.pokemon_tab)
        app.pokemon_editor.sections.select(0)
        app.update()
        app.update_idletasks()
        combo = app.pokemon_editor.species_combo
        combo.entry.focus_force()
        combo.entry.delete(0, "end")
        for key in ("m", "u"):
            combo.entry.event_generate(f"<KeyPress-{key}>")
            combo.entry.event_generate(f"<KeyRelease-{key}>")
            app.update()
        if combo.get() != "mu" or not combo._popup_visible() or app.focus_get() is not combo.entry:
            raise RuntimeError("Searchable dropdown lost focus while typing")
        combo._hide_popup()
        combo.set("Mudkip")
        combo._toggle_popup()
        app.update()
        combo.entry.event_generate("<KeyPress-t>")
        combo.entry.event_generate("<KeyRelease-t>")
        app.update()
        if (
            combo.get() != "t"
            or "Torchic" not in combo._matches
            or not combo._popup_visible()
            or app.focus_get() is not combo.entry
        ):
            raise RuntimeError("Arrow-opened searchable dropdown did not accept typing")
        combo._hide_popup()
        combo.set("Torchic")
        app.pokemon_editor.vars["Level"].set("8")
        app.pokemon_editor.move_filter_var.set("Level-up (current level)")
        app.update()
        level_moves = app.pokemon_editor.move_combos[0]._source_values
        if "Focus Energy" not in level_moves or "Ember" in level_moves:
            raise RuntimeError("Torchic level-up move filter does not honor the edited level")
        combo.set("Wingull")
        app.pokemon_editor.move_filter_var.set("HM")
        app.update()
        if app.pokemon_editor.move_combos[0]._source_values != ("", "Fly"):
            raise RuntimeError("Wingull exact HM move filter is incorrect")
        app.pokemon_editor.move_vars[0].set("Scratch")
        app.update()
        if app.pokemon_editor.current_pp_vars[0].get() != "35" or "Base 35" not in app.pokemon_editor.pp_max_vars[0].get():
            raise RuntimeError("Scratch Base PP was not loaded into the move editor")
        app.pokemon_editor.pp_up_vars[0].set("3")
        app.update()
        if app.pokemon_editor.current_pp_vars[0].get() != "56" or "/ 56 max" not in app.pokemon_editor.pp_max_vars[0].get():
            raise RuntimeError("PP Up scaling did not update Scratch PP to 56")
        combo.set("Torchic")
        app.pokemon_editor._load_species_defaults_into_form()
        app.update()
        if (
            app.pokemon_editor.vars["Level"].get() != "5"
            or app.pokemon_editor.vars["Ability"].get() != "Blaze"
            or tuple(var.get() for var in app.pokemon_editor.move_vars[:2]) != ("Growl", "Scratch")
            or app.pokemon_editor.vars["MaxHP"].get() != "19"
            or app.pokemon_editor.vars["MetType"].get() != "Gift"
        ):
            raise RuntimeError("Species selection did not load the complete base profile")
        app.pokemon_editor.evolution_canvas.configure(width=500, height=220)
        app.pokemon_editor._draw_evolution_chart()
        if len(app.pokemon_editor.evolution_canvas.find_all()) < 10:
            raise RuntimeError("Responsive evolution chart did not render the Torchic family")
        app.pokemon_editor.sections.select(1)
        app.update()
        app.pokemon_editor._max_all_evs()
        app.update()
        if (
            not app.allow_ev_over_510.get()
            or any(app.pokemon_editor.vars[stat + "_EV"].get() != "252" for stat in (
                "HP", "Attack", "Defense", "SpecialAttack", "SpecialDefense", "Speed",
            ))
            or "1512" not in app.pokemon_editor.ev_total_var.get()
        ):
            raise RuntimeError("Max all EVs did not enable the override and set all six EVs to 252")
        app.pokemon_editor.final_stats_canvas.configure(width=360, height=180)
        app.pokemon_editor.type_matchup_canvas.configure(width=360, height=180)
        app.pokemon_editor._draw_stats_visuals()
        if len(app.pokemon_editor.final_stats_canvas.find_all()) < 20:
            raise RuntimeError("Responsive final-stat column chart did not render")
        if len(app.pokemon_editor.type_matchup_canvas.find_all()) < 100:
            raise RuntimeError("Attack/defense type matchup chart did not render all 18 types")
        app.pokemon_editor.sections.select(2)
        for move_var, move_name in zip(
            app.pokemon_editor.move_vars,
            ("Tackle", "Rock Slide", "Surf", "Ice Beam"),
        ):
            move_var.set(move_name)
        app.update()
        app.pokemon_editor._draw_move_attack_charts()
        expected_types = ("Normal", "Rock", "Water", "Ice")
        for index, expected_type in enumerate(expected_types):
            if expected_type not in str(app.pokemon_editor.move_attack_frames[index].cget("text")):
                raise RuntimeError(f"Move {index + 1} chart did not load its attack type")
            if len(app.pokemon_editor.move_attack_canvases[index].find_all()) < 60:
                raise RuntimeError(f"Move {index + 1} attack type chart did not render all 18 types")
        app.pokemon_editor.sections.select(0)
        app.pokemon_editor.vars["SpeciesData"].set("Lucario")
        app.update()
        if tuple(label.cget("text") for label in app.pokemon_editor.main_type_labels) != ("FIGHTING", "STEEL"):
            raise RuntimeError("Main tab did not render Lucario's exact dual types")
        if app.pokemon_editor.main_type_labels[0].cget("fg") != "#ffffff":
            raise RuntimeError("Dark Fighting badge did not choose readable contrasting text")
        if app.sprites.available_directory is not None and app.sprites.get("Torchic", 128) is None:
            raise RuntimeError("Local Pokemon sprite cache is present but Torchic did not load")
        app.tabs.select(app.mod_builder_tab)
        app._refresh_mod_builder_status()
        app.update()
        if len(app.mod_toolchain.status_rows()) != 7:
            raise RuntimeError("Item Mod Builder environment checklist is incomplete")
        if app.mod_toolchain.ready and str(app.mod_build_button.cget("state")) == "disabled":
            raise RuntimeError("Item Mod Builder stayed disabled with a complete local toolchain")
        if app._item_mod_spec_from_form().helper_payload()["object_name"] != "DA_CustomItem":
            raise RuntimeError("Item Mod Builder default wizard values are invalid")
        if "CSTM-000001" not in app.mod_item_id_info_var.get():
            raise RuntimeError("Item Mod Builder did not expose the numeric CSTM Item ID tag")
        app.mod_archetype_var.set("Vitamin")
        app._on_mod_archetype_changed()
        app.update()
        vitamin_fields = app._selected_mod_template().editable_fields
        if "EVBoostAmount" not in vitamin_fields or app.mod_vitamin_ev_amount_var.get() != "10":
            raise RuntimeError("Vitamin EV amount dropdown did not load its verified default")
        if "grants 10 Attack EVs" not in app.mod_behavior_info_var.get():
            raise RuntimeError("Vitamin effect summary did not follow the current EV fields")
        app.mod_archetype_var.set("Held Item")
        app._on_mod_archetype_changed()
        app.update()
        if "doubles the prize money" not in app.mod_behavior_info_var.get():
            raise RuntimeError("Held Item behavior summary did not follow the selected template")
        app.mod_archetype_var.set("TM")
        app._on_mod_archetype_changed()
        app.update()
        if "teaches it Surf" not in app.mod_behavior_info_var.get():
            raise RuntimeError("TM effect summary did not follow the selected move")
        runtime_config = app._vitamin_runtime_config_from_form()
        if runtime_config != VitaminRuntimeConfig(252, 510, "custom"):
            raise RuntimeError("Vitamin runtime controls did not load their conservative defaults")
        if app.vitamin_runtime_environment.ready and "UE4SS" not in app.mod_runtime_status_var.get():
            raise RuntimeError("Vitamin runtime environment status was not rendered")
        app.destroy()
        return
    app.mainloop()
