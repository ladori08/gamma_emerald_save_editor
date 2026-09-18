# Item Mod Builder (experimental)

Version 0.19.2 expands the local template-based mod pipeline for the installed GE-1.0.0 Windows
build. It creates a real cooked `ItemData` asset and patch pak; writing an arbitrary Bag name alone
cannot create an item.

## Supported wizard archetypes

The wizard exposes 41 selected behavior/visual templates across 11 groups:

| Archetype | Templates / editable behavior |
| --- | --- |
| HP Restore | Potion, Super Potion, Full Restore; flat/percentage healing where serialized |
| Status Heal | Antidote, Awakening, Burn Heal, Ice Heal, Paralyze Heal, Full Heal |
| Revive | Revive behavior |
| PP Restore | Ether behavior |
| Vitamin | HP Up plus five stat templates; selectable runtime stat enum and EV gain amount |
| Rare Candy | Rare Candy behavior |
| Evolution / Utility | Water Stone and Everstone; experimental identity clone |
| Held Item | Seven shipped templates; selected numeric/type fields where serialized |
| Berry | Four shipped templates; HP/threshold fields where serialized |
| TM | TM01 visual template with any of the 99 verified shipped move assets |
| Poké Ball | Nine shipped visual/Blueprint dependency sets; Ball enum/rate where serialized |

Every item also has an internal asset name, display/Bag name, description, high-range Item ID, buy
price and sell price. Every one of the 11 groups has separate `Visual template` and `Behavior
template` selectors. They must come from the same category: the behavior donor keeps the safe native
`ItemType`, flags and effect data, while the visual donor supplies its cooked icon references. For a
Poké Ball, the visual copy also includes actor, sprite, flipbook, VFX and SFX references. A category
with one verified donor still shows both selectors, but naturally has only one choice.

### Compatible multiple effects

Held Items expose six independently editable native modifiers in addition to the selected core
behavior: Attack, Defense, Sp. Atk, Sp. Def and Speed multipliers plus end-of-turn HP recovery. For
example, select `Leftovers` behavior, `Light Ball` visuals, then set Attack and Sp. Atk to `2` and HP
per turn to `6.25`; the built asset retains Leftovers behavior and serializes all three modifiers.
The `Effects` box lists every non-neutral modifier before building.

This is deliberately not an unrestricted behavior stack. GE-1.0.0 stores one `ItemType` and one
`HeldItemEffect` enum per ItemData. Vitamins likewise have one target stat, TMs one move and Balls one
Ball behavior enum. Combining unrelated behaviors such as Revive + Ball or two core held-effect enums
would need new Blueprint/C++ runtime logic, so the editor rejects cross-category visual/behavior pairs
and does not claim those combinations work.

## Custom Item IDs

GE-1.0.0 stores `ItemID` as a signed 32-bit integer, so a literal string such as `Custom-1` cannot be
written into that property. The editor instead reserves a recognizable numeric namespace whose base
value is the big-endian `CSTM` FourCC. It displays each generated value as `CSTM-000001`,
`CSTM-000002`, and so on, while showing the exact numeric value stored by Gamma beside it.

The next sequence is persisted under `%LOCALAPPDATA%\GammaEmeraldSaveEditor` and is reserved when the
wizard opens or `Next CSTM ID` is pressed. Gaps are harmless and preferable to accidentally reusing
an old custom-item identity. Manual numeric IDs remain possible for advanced use.

## Vitamin limits

The EV gain dropdown contains every positive divisor of 252 plus `10`, Gamma's shipped Vitamin
default. Reverse engineering the build-matched native `CalculateVitaminGain` implementation confirms
that a Vitamin applies the smallest of the configured amount, the remaining room to 100 EV in the
selected stat, and the remaining room to 510 total EV. Therefore choices such as 126 or 252 are valid
serialized values but a single use still cannot push that stat above 100 through Vitamin behavior.
The separate Pokemon editor may store up to 252 per stat; that is a different path.

### Optional runtime Vitamin rules

v0.16.0 adds a separate `Vitamin runtime rules` panel. It hooks GE-1.0.0's native
`CalculateVitaminGain` result at runtime, so Vitamin use can match the editor's broader EV model:

- per-stat cap: vanilla `100` or full `252`;
- total cap: vanilla `510` or `Unlimited`;
- scope: only numeric IDs in the editor's `CSTM` namespace, or all Vitamins including vanilla ones.

The default is `252 / 510 / Custom CSTM Vitamins only`. This lets a custom Vitamin reach 252 in one
stat while retaining the normal competitive total and leaving shipped Vitamins untouched. Selecting
`Unlimited` permits a total above 510; selecting `All Vitamins` changes the behavior of shipped
Vitamins too.

This feature does not add an EV button to the Pokemon editor and does not change direct EV editing.
It changes what happens when a Vitamin is consumed during gameplay. The custom item `.pak` supplies
the item and its configured `EVBoostAmount`; the runtime rule supplies the cap policy. Install both
when testing a custom Vitamin.

The runtime installer copies a build-matched local UE4SS loader beside Gamma's executable and writes
an ownership/hash manifest. It refuses an existing unmanaged `dwmapi.dll` or `ue4ss` directory rather
than merging with somebody else's mods. Update and uninstall require the owned files to retain their
recorded hashes; an unexpected user mod blocks deletion. Fully close Gamma before install, update or
uninstall. `Uninstall runtime rules` removes only the editor-owned loader and returns Vitamin behavior
to Gamma's native 100-per-stat/510-total clamp.

## Player-facing Effects summary

The inline `Effects` sentence describes what the current item does in gameplay language. It updates
from the display name and editable fields instead of repeating raw property names. For example,
Silk Scarf with `Normal` and `1.2` reads: `When held, Silk Scarf raises the power of Normal-type
moves by 20%.` Changing either field immediately changes the sentence. Healing items, status cures,
Vitamins, held items, Berries, TMs and Balls have equivalent trigger-and-effect wording.

The muted line below is intentionally separate: it identifies the cloned cooked template and marks
experimental runtime paths. It is implementation/risk information, not the item effect.

TM creation is useful even though the move itself is selected from an existing list: GE-1.0.0 ships
99 verified move Blueprints but only 26 concrete TM items. A clone can therefore make an item that
teaches an existing move such as one outside that TM set. It cannot create a new move or edit move
power, type, accuracy, animation or effects; that would require separate cooked Blueprint assets.

This does not synthesize new C++ or Blueprint logic. Status conditions, Revive, Ether, Rare Candy,
Evolution items and several held-item effects intentionally inherit their complete shipped behavior.
Key/story items are excluded because cloning their identity does not safely create new quest logic.

## Ball scope

GE-1.0.0 ships nine complete Ball ItemData/Blueprint dependency sets: Poké, Great, Ultra, Premier,
Luxury, Repeat, Timer, Cherish and Shimmer. The wizard can clone any of those visuals. Templates that
serialize `PokeballType` can select all 17 runtime enum values, including Master, Safari, Net, Dive,
Nest, Dusk, Heal and Quick; those eight do not have their own cooked art/Blueprint sets in this build,
so they reuse the selected shipped visual and remain experimental.

The supplied `Cobblemon Anime Poké ball SFX Pack v1.1 MC1.21.1.zip` contains 33 Minecraft `.ogg`
sources plus `pack.mcmeta`/`pack.png` (SHA-256
`5A1C4FDFEC5F1CD5E2C0F8E00956203F57A6AF47F1897D76A52C36387BA4721A`). It contains no license file.
The attached PNG and those OGGs cannot be referenced directly by a cooked Gamma asset: they first
need permission to redistribute, import into an Unreal 5.6 project, and cooking into compatible
Texture/Sprite/SoundWave packages. The editor therefore does not bundle or inject them. Current Ball
mods reuse Gamma's already-cooked visuals and sounds.

## Required local components

Open `Item Mod Builder` and press `Refresh`. Every row must be `OK`:

- Gamma Emerald Shipping executable and unchanged base pak;
- local .NET runtime;
- UAssetAPI-based item writer helper;
- repak V11 writer;
- build-matched GE-1.0.0 `.usmap`;
- the locally extracted directory containing all 41 supported ItemData template pairs (the current
  workspace extraction contains all 86 shipped pairs for audit coverage).

The research/build workspace already contains these ignored local components. They are not published
with the source repository. Alternate locations can be supplied with:

```powershell
$env:GAMMA_EMERALD_GAME_DIR = "D:\path\to\gamma-emerald-ea-windows"
$env:GAMMA_EMERALD_MOD_TOOLS = "D:\path\to\local-tool-assets"
```

Never mix mappings or cooked templates from another Gamma build. A package may serialize cleanly
and still crash at runtime.

## Build and install workflow

The builder content scrolls vertically when it is taller than the available window. Use the visible
scrollbar, mouse wheel or trackpad while the pointer is over the builder. The title and category tab
remain in place, and the behavior fields, Effects panel and build buttons can all be reached at the
editor's 1080 × 680 minimum size.

1. Fully close Pokémon Gamma Emerald.
2. Open `Item Mod Builder`; confirm every environment row is `OK`.
3. Select a category, its cooked visual template, then its core behavior template.
4. Keep the generated CSTM Item ID, or enter a different unique numeric ID of at least 100000.
5. Set the display name, description, prices and the template-specific fields that appear.
6. Use `Build .pak...` for a standalone one-item output; this is the only action that asks for an
   export folder. Use `Build + Install...` to add the item directly to the guarded installed editor
   pack. It builds in disposable staging, then cleans that staging automatically. Existing custom
   items are rebuilt into the installed pack and preserved.
7. Reload/open the save in the editor, then add the custom item from its generated Bag pocket. Held
   items and Berries also become available in the Pokémon Held Item selector.
8. Use `Save + Backup`, launch the game, and test the checklist below on a disposable slot/copy.

The output includes a `.pak` and `<pak>.gamma-editor.json`. Gamma currently recognizes the tested
patch only as `PokemonEmerald-Windows_0_P.pak`, so the editor manages one installed **pack**. That
pack may contain multiple custom items; its format-2 manifest records every item needed to rebuild
it. Existing format-1 single-item manifests are upgraded automatically on the next addition.

## Replacement and uninstall safety

- Unknown patch files and editor patches whose SHA-256 changed are never overwritten or removed.
- Adding an item backs up the existing editor-owned pak and manifest, then atomically replaces them
  with a rebuilt pack containing both the old items and the new item.
- Installation verifies a temporary sibling and atomically replaces the owned target.
- The base `PokemonEmerald-Windows.pak` is never opened for writing.
- Adding another item does not require removing existing items from the loaded save because their
  assets remain in the rebuilt pack. Uninstall is blocked if the loaded Bag, Party, or any loaded
  Storage box still references any item in the pack; remove those references and use
  `Save + Backup` first.
- The editor cannot inspect every other save automatically; clean custom items out of other saves
  before removing or sharing the patch.

## Editing or removing an installed custom item

The `Installed custom items` selector is backed by the owned pack's format-2 manifest. Select an
item and press `Edit selected` to restore its category, Visual, Behavior, description, prices and
effect fields into the wizard. While editing, Item ID, internal asset name, display/Bag name and
category are locked. Those four values form its save-facing identity and pocket placement; changing
them could orphan an existing Bag or held-item reference.

Change the unlocked fields and press `Update + Install`. The editor replaces that item at the same
position, rebuilds every item in the cumulative pack, verifies the new pak and backs up the previous
pak/manifest before atomic replacement. It does not ask for an output folder, and old manual exports
in `CustomItemBuild` cannot cause a filename collision. `New Item` exits edit mode and restores the fresh-item form.
`Build .pak...` while editing creates a standalone proof only; it does not update the installed pack.

`Remove selected` scans the currently loaded Bag, Party and every loaded Storage box. A reference
blocks removal until it is cleared and saved with `Save + Backup`. If other items remain, the editor
rebuilds a pack containing them; removing the last item performs the normal guarded full uninstall.
Other save files are not scanned automatically, so remove the item from those saves before deleting
it from the pack.

## Runtime proof and remaining acceptance work

Automated tests and real cooked-asset builds cover the writer and pak layout. A v0.18.0 non-installed
proof pack contains one generated asset for every supported category (11 items / 22 cooked files).
A separate parsed proof retained Leftovers as `HeldItemEffect`, copied Light Ball's icon and serialized
all five stat multipliers plus end-of-turn healing. A read-only headless
runtime probe confirmed that ItemDataManager discovers representative custom Vitamin, Ball and TM
assets and reads their new IDs plus template-specific stat/Ball/rate/move fields. The probe patch and
loader were removed afterward, and the base pak hash remained unchanged.

That discovery proof does not prove every effect during gameplay. Test each new archetype:

1. Load the edited save; verify no Fatal Error or new-game reset.
2. Check the correct Bag pocket, name, description, inherited icon and quantity.
3. Exercise the actual behavior: use/hold/teach/throw as appropriate.
4. For a Ball, test successful capture, breakout, battle end, caught-Pokémon summary and PC deposit.
5. For a TM or held item, test battle entry/exit and the affected calculation.
6. Make a normal in-game save, close, reload, and re-check the item and affected Pokémon.
7. Reopen the save in the editor and run normal validation.

If runtime behavior fails, close the game, preserve its crash log, restore the latest pre-edit save
backup if needed, and uninstall the editor-owned patch after removing references. See
`SAVE_RUNTIME_DIAGNOSTICS.md` for the read-only triage workflow.
