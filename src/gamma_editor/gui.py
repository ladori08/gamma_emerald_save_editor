from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from .codec import decode_ges1
from .domain import bag_rows, party_rows, patch_domain_value, progress_rows, storage_rows, trainer_rows
from .errors import GammaEditorError
from .gvas import patch_scalar, parse_gvas
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


class SaveEditorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1120x720")
        self.minsize(900, 580)
        self.loaded: LoadedSave | None = None
        self.working_gvas: bytes | None = None
        self.dirty = False

        self._build_style()
        self._build_toolbar()
        self._build_tabs()
        self._build_status()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._open_default)

    def _build_style(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Muted.TLabel", foreground="#555555")

    def _build_toolbar(self) -> None:
        bar = ttk.Frame(self, padding=(10, 8))
        bar.pack(fill="x")
        ttk.Label(bar, text=APP_TITLE, style="Title.TLabel").pack(side="left", padx=(0, 18))
        ttk.Button(bar, text="Open", command=self.open_dialog).pack(side="left", padx=3)
        ttk.Button(bar, text="Reload", command=self.reload).pack(side="left", padx=3)
        self.save_button = ttk.Button(bar, text="Save + Backup", command=self.save, state="disabled")
        self.save_button.pack(side="left", padx=3)
        ttk.Button(bar, text="Export GVAS", command=self.export_gvas).pack(side="left", padx=3)
        ttk.Button(bar, text="Stage GVAS", command=self.import_gvas).pack(side="left", padx=3)

    def _build_tabs(self) -> None:
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        self.overview = ttk.Frame(self.tabs, padding=14)
        self.properties_tab = ttk.Frame(self.tabs, padding=10)
        self.gameplay_tab = ttk.Frame(self.tabs, padding=14)
        self.backups_tab = ttk.Frame(self.tabs, padding=10)
        self.diagnostics_tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(self.overview, text="Overview")
        self.tabs.add(self.properties_tab, text="Properties")
        self.tabs.add(self.gameplay_tab, text="Trainer / Party / Bag")
        self.tabs.add(self.backups_tab, text="Backups")
        self.tabs.add(self.diagnostics_tab, text="Diagnostics")
        self._build_overview()
        self._build_properties()
        self._build_gameplay()
        self._build_backups()
        self._build_diagnostics()

    def _build_overview(self) -> None:
        self.overview.columnconfigure(1, weight=1)
        self.summary_vars: dict[str, tk.StringVar] = {}
        labels = [
            ("File", "path"),
            ("Slot", "slot"),
            ("Save class", "save_class"),
            ("Engine", "engine"),
            ("GVAS size", "size"),
            ("SHA-256", "sha"),
            ("Parser", "parser"),
        ]
        for row, (label, key) in enumerate(labels):
            ttk.Label(self.overview, text=label + ":", width=16).grid(row=row, column=0, sticky="nw", pady=4)
            var = tk.StringVar(value="-")
            self.summary_vars[key] = var
            ttk.Label(self.overview, textvariable=var, wraplength=820).grid(
                row=row, column=1, sticky="nw", pady=4
            )
        warning = (
            "Safety contract: every live write creates a timestamped sibling backup, refuses stale files, "
            "blocks while the game is running, writes atomically, and verifies the encrypted result."
        )
        ttk.Separator(self.overview).grid(row=len(labels), column=0, columnspan=2, sticky="ew", pady=14)
        ttk.Label(self.overview, text=warning, wraplength=900, style="Muted.TLabel").grid(
            row=len(labels) + 1, column=0, columnspan=2, sticky="w"
        )

    def _build_properties(self) -> None:
        self.properties_tab.rowconfigure(1, weight=1)
        self.properties_tab.columnconfigure(0, weight=1)
        row = ttk.Frame(self.properties_tab)
        row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(row, text="Filter:").pack(side="left")
        self.filter_var = tk.StringVar()
        entry = ttk.Entry(row, textvariable=self.filter_var, width=38)
        entry.pack(side="left", padx=6)
        entry.bind("<KeyRelease>", lambda _event: self._refresh_properties())
        ttk.Button(row, text="Edit selected", command=self.edit_selected_property).pack(side="left")

        columns = ("name", "type", "index", "value", "editable", "offset")
        self.property_tree = ttk.Treeview(self.properties_tab, columns=columns, show="headings")
        widths = {"name": 260, "type": 150, "index": 55, "value": 280, "editable": 70, "offset": 90}
        for name in columns:
            self.property_tree.heading(name, text=name.title())
            self.property_tree.column(name, width=widths[name], anchor="w")
        self.property_tree.grid(row=1, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(self.properties_tab, orient="vertical", command=self.property_tree.yview)
        scroll.grid(row=1, column=1, sticky="ns")
        self.property_tree.configure(yscrollcommand=scroll.set)
        self.property_tree.bind("<Double-1>", lambda _event: self.edit_selected_property())

    def _build_gameplay(self) -> None:
        ttk.Label(self.gameplay_tab, text="Schema-aware game editor", style="Title.TLabel").pack(anchor="w")
        self.gameplay_message = tk.StringVar(value="Open a save to inspect its schema.")
        ttk.Label(
            self.gameplay_tab,
            textvariable=self.gameplay_message,
            justify="left",
            wraplength=900,
        ).pack(anchor="w", pady=(8, 8))
        notebook = ttk.Notebook(self.gameplay_tab)
        notebook.pack(fill="both", expand=True)
        self.domain_trees: dict[str, ttk.Treeview] = {}
        for title in ("Trainer", "Party", "Storage", "Bag", "Progress"):
            frame = ttk.Frame(notebook, padding=6)
            frame.rowconfigure(0, weight=1)
            frame.columnconfigure(0, weight=1)
            notebook.add(frame, text=title)
            columns = ("owner", "field", "value", "rule", "editable", "path")
            tree = ttk.Treeview(frame, columns=columns, show="headings")
            settings = {
                "owner": ("Owner", 190),
                "field": ("Field", 180),
                "value": ("Value", 260),
                "rule": ("Rule", 130),
                "editable": ("Edit", 55),
                "path": ("Schema path", 310),
            }
            for column, (heading, width) in settings.items():
                tree.heading(column, text=heading)
                tree.column(column, width=width, anchor="w")
            tree.grid(row=0, column=0, sticky="nsew")
            scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            scroll.grid(row=0, column=1, sticky="ns")
            tree.configure(yscrollcommand=scroll.set)
            tree.bind("<Double-1>", lambda _event, current=tree: self._edit_domain_selected(current))
            ttk.Button(
                frame,
                text="Edit selected",
                command=lambda current=tree: self._edit_domain_selected(current),
            ).grid(row=1, column=0, sticky="w", pady=(6, 0))
            self.domain_trees[title] = tree

    def _build_backups(self) -> None:
        self.backups_tab.rowconfigure(1, weight=1)
        self.backups_tab.columnconfigure(0, weight=1)
        buttons = ttk.Frame(self.backups_tab)
        buttons.grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Button(buttons, text="Refresh", command=self._refresh_backups).pack(side="left")
        ttk.Button(buttons, text="Restore selected", command=self.restore_selected).pack(side="left", padx=6)
        self.backup_tree = ttk.Treeview(
            self.backups_tab, columns=("time", "size", "path"), show="headings"
        )
        for name, width in (("time", 180), ("size", 100), ("path", 700)):
            self.backup_tree.heading(name, text=name.title())
            self.backup_tree.column(name, width=width, anchor="w")
        self.backup_tree.grid(row=1, column=0, sticky="nsew")

    def _build_diagnostics(self) -> None:
        self.diagnostics_tab.rowconfigure(0, weight=1)
        self.diagnostics_tab.columnconfigure(0, weight=1)
        self.diagnostics = tk.Text(self.diagnostics_tab, wrap="word", font=("Consolas", 10))
        self.diagnostics.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(self.diagnostics_tab, orient="vertical", command=self.diagnostics.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.diagnostics.configure(yscrollcommand=scroll.set, state="disabled")

    def _build_status(self) -> None:
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w", padding=(8, 3)).pack(fill="x")

    def _open_default(self) -> None:
        saves = discover_saves()
        story_name = "859c7fd1524eb8d6726f1233820531b8.dat"
        choice = next((p for p in saves if p.name == story_name), saves[0] if saves else None)
        if choice:
            self.open_save(choice)
        else:
            self.status_var.set(f"No saves found in {default_save_dir()}")

    def _confirm_discard(self) -> bool:
        return not self.dirty or messagebox.askyesno(APP_TITLE, "Discard staged, unsaved changes?")

    def open_dialog(self) -> None:
        if not self._confirm_discard():
            return
        path = filedialog.askopenfilename(
            title="Open Gamma Emerald save",
            initialdir=default_save_dir(),
            filetypes=(("Gamma save", "*.dat"), ("All files", "*.*")),
        )
        if path:
            self.open_save(Path(path))

    def open_save(self, path: Path) -> None:
        try:
            self.loaded = load_save(path)
            self.working_gvas = self.loaded.container.payload
            self.dirty = False
            self._refresh_all()
            self.status_var.set(f"Loaded {path.name}; integrity checks passed")
        except (OSError, GammaEditorError) as exc:
            messagebox.showerror(APP_TITLE, str(exc))

    def reload(self) -> None:
        if self.loaded and self._confirm_discard():
            self.open_save(self.loaded.path)

    def _current_document(self):
        if self.working_gvas is None:
            return None
        return parse_gvas(self.working_gvas)

    def _refresh_all(self) -> None:
        if not self.loaded or self.working_gvas is None:
            return
        doc = self._current_document()
        assert doc is not None
        h = doc.header
        self.summary_vars["path"].set(str(self.loaded.path))
        self.summary_vars["slot"].set(self.loaded.container.slot_name)
        self.summary_vars["save_class"].set(h.save_game_class)
        self.summary_vars["engine"].set(f"{h.engine.major}.{h.engine.minor}.{h.engine.patch} ({h.engine.branch})")
        self.summary_vars["size"].set(f"{len(self.working_gvas):,} bytes")
        self.summary_vars["sha"].set(hashlib.sha256(self.working_gvas).hexdigest())
        parser_note = doc.property_error or f"{len(doc.properties)} tagged properties parsed"
        self.summary_vars["parser"].set(parser_note)
        self._refresh_properties()
        self._refresh_backups()
        self._refresh_gameplay(doc)
        self._refresh_diagnostics(doc)
        self._update_dirty_ui()

    def _refresh_properties(self) -> None:
        self.property_tree.delete(*self.property_tree.get_children())
        doc = self._current_document()
        if not doc:
            return
        needle = self.filter_var.get().strip().casefold()
        for index, prop in enumerate(doc.properties):
            haystack = f"{prop.name} {prop.type_name} {prop.value}".casefold()
            if needle and needle not in haystack:
                continue
            self.property_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    prop.path or prop.name,
                    prop.type_descriptor or prop.type_name,
                    prop.array_index,
                    repr(prop.value) if prop.value is not None else "<opaque>",
                    "yes" if prop.editable else "no",
                    f"0x{prop.value_offset:X}",
                ),
            )

    def _refresh_gameplay(self, doc) -> None:
        names = {p.name for p in doc.properties}
        expected = {"Party", "PlayerMoney", "PlayerItems", "CaughtPokemon", "SeenPokemon"}
        found = sorted(names & expected)
        if self.loaded and self.loaded.container.slot_name == "GEOptions":
            text = (
                "This is the GEOptions slot, not the story save. Start/continue a game and save once, then Reload.\n\n"
                "Expected story filename: 859c7fd1524eb8d6726f1233820531b8.dat\n"
                "The editor will never map Trainer/Party/Bag controls onto an unverified byte offset."
            )
        elif found:
            text = (
                "Detected gameplay fields: " + ", ".join(found) + ".\n\n"
                "Trainer, Party, Storage, Bag and Progress are mapped from the GE-1.0.0 story schema. "
                "Fields marked yes use fixed-size verified writes; variable-size arrays/enums remain read-only."
            )
        else:
            text = (
                "This save loaded and passed container validation, but its gameplay property schema is not "
                "recognized safely. Use Diagnostics and Export GVAS for analysis; no guessed writes are enabled."
            )
        self.gameplay_message.set(text)
        providers = {
            "Trainer": trainer_rows,
            "Party": party_rows,
            "Storage": storage_rows,
            "Bag": bag_rows,
            "Progress": progress_rows,
        }
        for title, tree in self.domain_trees.items():
            tree.delete(*tree.get_children())
            for index, row in enumerate(providers[title](doc)):
                tree.insert(
                    "",
                    "end",
                    iid=str(index),
                    values=(
                        row.owner,
                        row.field,
                        repr(row.value),
                        row.rule,
                        "yes" if row.editable else "no",
                        row.path,
                    ),
                )

    def _edit_domain_selected(self, tree: ttk.Treeview) -> None:
        selected = tree.selection()
        document = self._current_document()
        if not selected or not document:
            return
        values = tree.item(selected[0], "values")
        path = str(values[5])
        matches = [item for item in document.properties if item.path == path]
        if len(matches) != 1:
            messagebox.showerror(APP_TITLE, f"Schema path is no longer unique: {path}")
            return
        prop = matches[0]
        if not prop.editable:
            messagebox.showinfo(APP_TITLE, "This field is read-only because its serializer is not yet write-verified.")
            return
        raw = simpledialog.askstring(
            APP_TITLE,
            f"{path} ({prop.type_name})",
            initialvalue=str(prop.value),
        )
        if raw is None:
            return
        try:
            value = self._coerce_property_value(prop, raw)
            self.working_gvas = patch_domain_value(document, path, value)
            self.dirty = self.working_gvas != self.loaded.container.payload if self.loaded else True
            self._refresh_all()
        except (ValueError, GammaEditorError) as exc:
            messagebox.showerror(APP_TITLE, str(exc))

    def _refresh_diagnostics(self, doc) -> None:
        h = doc.header
        lines = [
            f"Container slot : {self.loaded.container.slot_name if self.loaded else '-'}",
            f"Save class     : {h.save_game_class}",
            f"GVAS version   : {h.save_game_version}",
            f"UE4 package    : {h.package_file_version_ue4}",
            f"UE5 package    : {h.package_file_version_ue5}",
            f"Engine         : {h.engine.major}.{h.engine.minor}.{h.engine.patch}",
            f"Header ext     : {h.header_extension.hex() or '<none>'}",
            f"Custom versions: {len(h.custom_versions)}",
            f"Body offset    : 0x{h.body_offset:X}",
            f"Properties     : {len(doc.properties)}",
            f"Parser note    : {doc.property_error or 'complete'}",
            "",
            "Unknown data is preserved byte-for-byte. A parser failure disables structured writes; it does not truncate data.",
        ]
        self.diagnostics.configure(state="normal")
        self.diagnostics.delete("1.0", "end")
        self.diagnostics.insert("1.0", "\n".join(lines))
        self.diagnostics.configure(state="disabled")

    def _refresh_backups(self) -> None:
        self.backup_tree.delete(*self.backup_tree.get_children())
        if not self.loaded:
            return
        for path in list_backups(self.loaded.path):
            stat = path.stat()
            self.backup_tree.insert(
                "", "end", iid=str(path), values=(
                    __import__("datetime").datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    f"{stat.st_size:,}",
                    str(path),
                )
            )

    def edit_selected_property(self) -> None:
        selected = self.property_tree.selection()
        doc = self._current_document()
        if not selected or not doc or self.working_gvas is None:
            return
        prop = doc.properties[int(selected[0])]
        if not prop.editable:
            messagebox.showinfo(APP_TITLE, "This value is opaque/read-only in the verified schema.")
            return
        raw = simpledialog.askstring(APP_TITLE, f"{prop.name} ({prop.type_name})", initialvalue=str(prop.value))
        if raw is None:
            return
        try:
            value = self._coerce_property_value(prop, raw)
            self.working_gvas = patch_scalar(doc, prop.path or prop.name, value)
            self.dirty = self.working_gvas != self.loaded.container.payload if self.loaded else True
            self._refresh_all()
        except (ValueError, GammaEditorError) as exc:
            messagebox.showerror(APP_TITLE, str(exc))

    @staticmethod
    def _coerce_property_value(prop, raw: str) -> object:
        if prop.type_name == "BoolProperty":
            lowered = raw.strip().lower()
            if lowered not in {"true", "false", "1", "0", "yes", "no"}:
                raise ValueError("Use true/false or 1/0.")
            return lowered in {"true", "1", "yes"}
        if "Float" in prop.type_name or "Double" in prop.type_name:
            return float(raw)
        if prop.type_name in {
            "Int8Property", "ByteProperty", "UInt8Property", "Int16Property", "UInt16Property",
            "IntProperty", "Int32Property", "UInt32Property", "Int64Property", "UInt64Property",
        }:
            return int(raw, 0)
        return raw

    def save(self) -> None:
        if not self.loaded or self.working_gvas is None or not self.dirty:
            return
        if not messagebox.askyesno(APP_TITLE, "Write the staged changes? A timestamped backup will be created first."):
            return
        try:
            backup = write_save(self.loaded, self.working_gvas)
            self.open_save(self.loaded.path)
            messagebox.showinfo(APP_TITLE, f"Saved and verified.\nBackup: {backup}")
        except (OSError, GammaEditorError) as exc:
            messagebox.showerror(APP_TITLE, str(exc))

    def export_gvas(self) -> None:
        if self.working_gvas is None:
            return
        path = filedialog.asksaveasfilename(
            title="Export inner GVAS", defaultextension=".gvas", filetypes=(("GVAS", "*.gvas"),)
        )
        if path:
            Path(path).write_bytes(self.working_gvas)
            self.status_var.set(f"Exported {path}")

    def import_gvas(self) -> None:
        if not self.loaded:
            return
        path = filedialog.askopenfilename(title="Stage inner GVAS", filetypes=(("GVAS", "*.gvas"), ("All", "*.*")))
        if not path:
            return
        try:
            payload = Path(path).read_bytes()
            doc = parse_gvas(payload)
            if doc.header.save_game_class != self.loaded.document.header.save_game_class:
                raise GammaEditorError("GVAS save class does not match the loaded slot.")
            self.working_gvas = payload
            self.dirty = payload != self.loaded.container.payload
            self._refresh_all()
            self.status_var.set("GVAS staged; live save is unchanged")
        except (OSError, GammaEditorError) as exc:
            messagebox.showerror(APP_TITLE, str(exc))

    def restore_selected(self) -> None:
        selected = self.backup_tree.selection()
        if not self.loaded or not selected:
            return
        backup = Path(selected[0])
        if not messagebox.askyesno(APP_TITLE, f"Restore this backup?\n\n{backup}"):
            return
        try:
            safety = restore_backup(self.loaded.path, backup)
            self.open_save(self.loaded.path)
            messagebox.showinfo(APP_TITLE, f"Backup restored. Pre-restore copy: {safety}")
        except (OSError, GammaEditorError) as exc:
            messagebox.showerror(APP_TITLE, str(exc))

    def _update_dirty_ui(self) -> None:
        self.save_button.configure(state="normal" if self.dirty else "disabled")
        marker = " *" if self.dirty else ""
        self.title(APP_TITLE + marker)

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


if __name__ == "__main__":
    main()
