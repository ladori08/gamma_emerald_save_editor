from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .codec import decode_ges1, encode_ges1, validate_round_trip
from .errors import GammaEditorError
from .save_service import discover_saves, load_save, slot_filename


def _summary(path: Path) -> dict[str, object]:
    loaded = load_save(path)
    h = loaded.document.header
    return {
        "path": str(path),
        "slot_name": loaded.container.slot_name,
        "container_version": loaded.container.version,
        "plaintext_size": loaded.container.plaintext_size,
        "gvas_size": len(loaded.container.payload),
        "save_game_class": h.save_game_class,
        "engine": f"{h.engine.major}.{h.engine.minor}.{h.engine.patch}",
        "engine_branch": h.engine.branch,
        "package_version_ue4": h.package_file_version_ue4,
        "package_version_ue5": h.package_file_version_ue5,
        "custom_version_count": len(h.custom_versions),
        "parsed_property_count": len(loaded.document.properties),
        "property_parser_note": loaded.document.property_error,
        "sha256": loaded.source_sha256,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pokemon Gamma Emerald GES1/GVAS save tool")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("saves", help="List detected .ged/*.dat saves.")
    p_summary = sub.add_parser("summary", help="Validate and summarize a save.")
    p_summary.add_argument("save", type=Path)
    p_validate = sub.add_parser("validate", help="Run GES1 integrity and round-trip checks.")
    p_validate.add_argument("save", type=Path)
    p_properties = sub.add_parser("properties", help="List decoded UE property paths and values.")
    p_properties.add_argument("save", type=Path)
    p_properties.add_argument("--filter", default="", help="Case-insensitive path/type/value filter.")
    p_properties.add_argument("--top-level", action="store_true", help="Show only top-level properties.")
    p_properties.add_argument("--editable", action="store_true", help="Show only safely editable properties.")
    p_unpack = sub.add_parser("unpack", help="Export the inner GVAS payload.")
    p_unpack.add_argument("save", type=Path)
    p_unpack.add_argument("output", type=Path)
    p_pack = sub.add_parser("pack", help="Wrap a GVAS payload as a GES1 file (no live overwrite).")
    p_pack.add_argument("gvas", type=Path)
    p_pack.add_argument("output", type=Path)
    p_pack.add_argument("--slot", default="PokemonSaveSlot")
    p_name = sub.add_parser("slot-filename", help="Calculate the guarded filename for a slot.")
    p_name.add_argument("slot")
    p_name.add_argument("--user-index", type=int, default=0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "saves":
            for path in discover_saves():
                try:
                    item = _summary(path)
                    print(f"{path}\t{item['slot_name']}\t{item['save_game_class']}")
                except GammaEditorError as exc:
                    print(f"{path}\tINVALID\t{exc}")
            return 0
        if args.command == "summary":
            print(json.dumps(_summary(args.save), indent=2, ensure_ascii=False))
            return 0
        if args.command == "validate":
            validate_round_trip(args.save.read_bytes())
            print("OK: GES1 header, AES payload, SHA-1, GVAS marker and round-trip are valid.")
            return 0
        if args.command == "properties":
            document = load_save(args.save).document
            needle = args.filter.casefold()
            rows = []
            for prop in document.properties:
                if args.top_level and prop.depth != 0:
                    continue
                if args.editable and not prop.editable:
                    continue
                text = f"{prop.path} {prop.type_descriptor} {prop.value}".casefold()
                if needle and needle not in text:
                    continue
                rows.append(
                    {
                        "path": prop.path,
                        "type": prop.type_descriptor or prop.type_name,
                        "value": prop.value,
                        "editable": prop.editable,
                        "rule": "fixed-size/verified" if prop.editable else "read-only",
                    }
                )
            print(json.dumps(rows, indent=2, ensure_ascii=False))
            return 0
        if args.command == "unpack":
            args.output.write_bytes(decode_ges1(args.save.read_bytes()).payload)
            print(args.output)
            return 0
        if args.command == "pack":
            if args.output.exists():
                raise GammaEditorError("Output already exists; refusing to overwrite it.")
            args.output.write_bytes(encode_ges1(args.slot, args.gvas.read_bytes()))
            print(args.output)
            return 0
        if args.command == "slot-filename":
            print(slot_filename(args.slot, args.user_index))
            return 0
    except (OSError, GammaEditorError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
