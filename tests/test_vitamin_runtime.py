from __future__ import annotations

import json
from pathlib import Path

import pytest

from gamma_editor import vitamin_runtime
from gamma_editor.mod_builder import ModBuilderError
from gamma_editor.vitamin_runtime import (
    VitaminRuntimeConfig,
    VitaminRuntimeEnvironment,
    install_vitamin_runtime,
    installed_vitamin_runtime_config,
    render_vitamin_runtime_lua,
    uninstall_vitamin_runtime,
)


def fake_environment(tmp_path: Path) -> VitaminRuntimeEnvironment:
    game_bin = tmp_path / "game" / "PokemonEmerald" / "Binaries" / "Win64"
    game_bin.mkdir(parents=True)
    game_executable = game_bin / "PokemonEmerald-Win64-Shipping.exe"
    game_executable.write_bytes(b"game")
    source = tmp_path / "source"
    source.mkdir()
    loader = source / "dwmapi.dll"
    loader.write_bytes(b"loader")
    ue4ss = source / "ue4ss"
    ue4ss.mkdir()
    (ue4ss / "UE4SS.dll").write_bytes(b"runtime")
    (ue4ss / "LICENSE").write_text("MIT", encoding="utf-8")
    (ue4ss / "UE4SS-settings.ini").write_text("UseCache = 1\n", encoding="utf-8")
    for directory in vitamin_runtime._SOURCE_DIRECTORIES:
        path = ue4ss / directory
        path.mkdir()
        (path / "fixture.txt").write_text(directory, encoding="utf-8")
    mods = ue4ss / "Mods"
    (mods / "shared").mkdir(parents=True)
    (mods / "shared" / "fixture.lua").write_text("return {}", encoding="utf-8")
    (mods / "DisabledFixture" / "Scripts").mkdir(parents=True)
    (mods / "DisabledFixture" / "Scripts" / "main.lua").write_text("print('disabled')", encoding="utf-8")
    (mods / "mods.txt").write_text("DisabledFixture : 1\n", encoding="utf-8")
    return VitaminRuntimeEnvironment(game_executable, loader, ue4ss)


def test_lua_runtime_rule_renders_verified_hook_order_and_scope() -> None:
    custom = render_vitamin_runtime_lua(VitaminRuntimeConfig(252, None, "custom"))
    assert "local STAT_CAP = 252" in custom
    assert "local TOTAL_CAP = nil" in custom
    assert "local APPLY_TO_ALL_VITAMINS = false" in custom
    assert "function(_context, return_param, item_param, pokemon_param)" in custom
    assert "return_param:set(gain)" in custom
    all_vitamins = render_vitamin_runtime_lua(VitaminRuntimeConfig(100, 510, "all"))
    assert "local STAT_CAP = 100" in all_vitamins
    assert "local TOTAL_CAP = 510" in all_vitamins
    assert "local APPLY_TO_ALL_VITAMINS = true" in all_vitamins


def test_runtime_config_rejects_unverified_rules() -> None:
    with pytest.raises(ModBuilderError, match="stat cap"):
        VitaminRuntimeConfig(999, 510, "custom").validated()
    with pytest.raises(ModBuilderError, match="total cap"):
        VitaminRuntimeConfig(252, 999, "custom").validated()
    with pytest.raises(ModBuilderError, match="scope"):
        VitaminRuntimeConfig(252, 510, "unknown").validated()


def test_runtime_install_update_and_owned_uninstall(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    environment = fake_environment(tmp_path)
    monkeypatch.setattr(vitamin_runtime, "is_game_running", lambda: False)
    installed_path = install_vitamin_runtime(VitaminRuntimeConfig(252, 510, "custom"), environment)
    assert installed_path.is_file()
    assert environment.loader_target.read_bytes() == b"loader"  # type: ignore[union-attr]
    assert "UseCache = 0" in (environment.ue4ss_target / "UE4SS-settings.ini").read_text(encoding="utf-8")  # type: ignore[operator]
    assert installed_vitamin_runtime_config(environment) == VitaminRuntimeConfig(252, 510, "custom")
    manifest = json.loads(environment.manifest_target.read_text(encoding="utf-8"))  # type: ignore[union-attr]
    assert manifest["product"] == vitamin_runtime.RUNTIME_PRODUCT
    assert "UE4SS.log" not in manifest["managed_files"]

    install_vitamin_runtime(VitaminRuntimeConfig(252, None, "all"), environment)
    assert installed_vitamin_runtime_config(environment) == VitaminRuntimeConfig(252, None, "all")
    (environment.ue4ss_target / "UE4SS.log").write_text("generated", encoding="utf-8")  # type: ignore[operator]
    uninstall_vitamin_runtime(environment)
    assert not environment.loader_target.exists()  # type: ignore[union-attr]
    assert not environment.ue4ss_target.exists()  # type: ignore[union-attr]
    assert not environment.manifest_target.exists()  # type: ignore[union-attr]
    assert not list(environment.game_bin.glob("*.gamma-editor-removing-*"))  # type: ignore[union-attr]


def test_runtime_refuses_unmanaged_loader_and_user_mod_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = fake_environment(tmp_path)
    monkeypatch.setattr(vitamin_runtime, "is_game_running", lambda: False)
    environment.loader_target.write_bytes(b"foreign")  # type: ignore[union-attr]
    with pytest.raises(ModBuilderError, match="unmanaged"):
        install_vitamin_runtime(VitaminRuntimeConfig(), environment)
    environment.loader_target.unlink()  # type: ignore[union-attr]

    install_vitamin_runtime(VitaminRuntimeConfig(), environment)
    user_mod = environment.ue4ss_target / "Mods" / "UserMod" / "main.lua"  # type: ignore[operator]
    user_mod.parent.mkdir(parents=True)
    user_mod.write_text("print('user')", encoding="utf-8")
    with pytest.raises(ModBuilderError, match="Unmanaged file"):
        uninstall_vitamin_runtime(environment)
    assert user_mod.exists()
