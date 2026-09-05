# Item Mod Wizard cho Gamma Emerald - bao cao kha thi

Ngay audit: 2026-09-05. Target: Gamma Emerald EA 1.13.1 / project `PokemonEmerald`, Unreal
Engine 5.6.

## Ket luan

Co the them mot tab **Item Mod Builder**, nhung no khong the chi sua save. Tab nay phai dieu phoi
mot pipeline mod Unreal gom:

1. Tao hoac clone cooked ItemData va cac asset phu thuoc.
2. Tao metadata/registry ma runtime dung de tim asset.
3. Dong goi thanh patch pak rieng.
4. Cai/go patch pak voi game da dong va co rollback.
5. Sau khi game nhan item, them `ItemName` vao Bag/save.

Kha thi nhat la lam theo tung phase. Mount, schema, override-priority va new-asset discovery proofs
deu da pass. v0.14.0 vi vay trien khai MVP hep: clone Potion thanh HP-restoring ItemData moi, pack,
install/uninstall co ownership guard, roi expose item da install trong Bag editor.

Huong dan su dung va gioi han hien tai: [ITEM_MOD_BUILDER.md](ITEM_MOD_BUILDER.md).

## Vi sao Icarus lam de hon

Icarus Mod Manager khong tu bien mot form thanh Blueprint. Pipeline chinh cua no patch cac JSON
DataTable trong `Data.pak`: co the add/alter/remove row theo ten, merge lai voi data cua ban game moi
roi repack. Manager cung chap nhan cooked `.uasset`, nhung tai lieu cua chinh project yeu cau modder
cai dung Unreal version, tao project C++ dung ten `Icarus`, cook content, sau do dung UnrealPak.

Nguon:

- [Icarus Mod Manager - Creating Mods](https://github.com/CrystalFerrai/IcarusModManager/blob/main/docs/creating_mods.md)
- [Icarus Software / Mod Editor](https://github.com/Jimk72/Icarus_Software)

Gamma hien khong ship mot Item DataTable JSON tuong duong. Moi item la mot `ItemData` `.uasset/.uexp`
da cook, con Ball co them Blueprint, sprite/flipbook, particle va sound references.

## Bang chung local cua Gamma

- Chi co mot base pak: `PokemonEmerald-Windows.pak`, khoang 1.64 GB.
- Pak dung format V11 va encrypted index/data.
- Khong co `.sig`, `.utoc` hoac `.ucas` ben canh base pak.
- Project descriptor ben trong pak khai bao Engine `5.6`, runtime module `PokemonEmerald`, editor
  module `PokemonEmeraldEditor` va runtime module `GESaveGuard`.
- Ban cai dat khong kem Unreal Editor/UnrealPak, C++ source headers, `.usmap` hay Shipping PDB. Mot
  `.usmap` build-matched sau do da duoc sinh cuc bo bang UE4SS va duoc giu trong runtime assets ignored.
- `DA_Potion`, `DA_UltraBall` va `BP_Pokeball_UltraBall` deu la unversioned cooked packages.
  Khong co mapping thi ItemData chi la `RawExport`; voi `.usmap` vua sinh, UAssetAPI parse duoc Potion
  va Ultra Ball thanh `NormalExport` va cho phep clone/write/round-trip.
- `DA_UltraBall` tham chieu rieng den Ball Blueprint, UI icon, world sprite/flipbook, release
  particle va sound. Mot Ball moi vi vay khong phai chi la mot record ten + catch rate.
- Da tao va doc lai thanh cong mot V11 `_P.pak` vo hai voi mount point `../../../` va dung internal
  path `PokemonEmerald/Content/Mods/...`.
- Runtime mount proof pass khi pak duoc dat ten `PokemonEmerald-Windows_0_P.pak`: trong luc Shipping
  process song, Windows khong the mo exclusive ca base pak lan probe pak, chung minh engine da mo/giu
  patch. Ten tuy y `GammaEditorMountProbe_P.pak` bi bo qua, nen convention ten la bat buoc voi build nay.
- Probe chi chua text marker, khong override asset/save. Headless process sau do duoc tat, patch va
  build temp duoc xoa; base pak van giu size/timestamp goc va hash SHA-256
  `2DB705FA9ABCB415C7D73772FF7A8584C021B703D745BDA70D209DD3ABE1CA10`.

Theo tai lieu Unreal, cooked content phai duoc cook truoc khi runtime dung; patch pak duoc mount cung
base pak va suffix `_p.pak` cho patch priority. Day la bang chung engine-level, chua phai bang chung
Gamma runtime da chap nhan mod:

- [Packaging Unreal projects](https://dev.epicgames.com/documentation/en-us/unreal-engine/packaging-your-project)
- [Cooking and chunking](https://dev.epicgames.com/documentation/en-us/unreal-engine/cooking-content-and-creating-chunks-in-unreal-engine)
- [Creating Unreal patches](https://dev.epicgames.com/documentation/en-us/unreal-engine/how-to-create-a-patch-in-unreal-engine)

## Cac muc ho tro co the dat duoc

| Muc | Chuc nang | Danh gia |
|---|---|---|
| A | Override thong so/anh cua mot item da co, cung asset path | Kha thi nhat; khong can discover asset moi |
| B | Clone item moi nhung tai su dung effect/Blueprint da co | Co the, sau khi co schema + registry proof |
| C | Tao Ball moi tu Ball template va enum da co | Co the nghien cuu; can test parent Blueprint/native branch |
| D | Tao effect/Blueprint hoan toan moi tu form | Khong nen hua; can UE project/devkit va Blueprint compilation |
| E | Viet native C++ gameplay class moi | Ngoai pham vi save editor; can loader/plugin hoac game source |

## Cap nhat proof va implementation v0.14.0

- UE4SS developer dumper sinh thanh cong `.usmap` va `.jmap` cho dung GE-1.0.0/UE 5.6 build.
- Mapping khoi phuc native `ItemData` gom 72 properties va `ItemDataManager.ItemDataPaths = /Game/Items/`.
- Same-path Potion override trong patch pak duoc runtime doc voi `BuyPrice` da doi, chung minh patch
  priority, khong chi container mount.
- New `DA_GammaEditorProbe` duoc `ItemDataManager` auto-discover truoc ca explicit LoadAsset; Item ID va
  price moi deu doc dung. Khong can sua `AssetRegistry.bin` cho ItemData dat dung `/Game/Items/`.
- Probe/loader deu duoc go sau test, khong save nao bi ghi, base pak van giu SHA-256
  `2DB705FA9ABCB415C7D73772FF7A8584C021B703D745BDA70D209DD3ABE1CA10`.
- v0.14.0 them tab Item Mod Builder va chi expose cac Potion-derived field da runtime-proven. Ball,
  TM, Berry, held item, custom icon/Blueprint/native behavior van bi chan cho den khi co proof rieng.

MVP nen bat dau o muc A, sau do B. Muc D chi nen mo bang cach launch mot companion Unreal project,
khong nen co gang tu serialize bytecode Blueprint bang Python.

## Cac trang trong wizard de xuat

### 1. Environment Check

- Fingerprint executable, base pak, manifest va engine 5.6.
- Kiem tra game dang chay.
- Kiem tra mount proof, schema mapping va packer version.
- Hien ro `Supported`, `Experimental` hoac `Blocked`.

### 2. Base Template

- Chon Potion/Berry/Held Item/Key Item/TM/Ball lam template.
- Wizard chi hien cac field da map tu template do.
- Khong cho doi sang behavior khac neu dependency set chua xac minh.

### 3. Identity and Bag

- Package path va object name noi bo.
- `ItemName` dung trong save.
- Display name, description/localization key.
- Category/pocket, price, stack/unique flags, give/toss/sell/use permissions.

Ten field o tren la requirement logic; ten property Unreal chinh xac van phai lay tu schema mapping.

### 4. Visuals

- Import icon PNG va cook thanh texture/sprite dung format.
- Chon lai asset co san neu khong co Unreal cooker.
- Preview references va bao missing dependency.

### 5. Behavior

- MVP: chon effect/Blueprint da co va chi sua cac numeric property da xac minh.
- Ball: ball actor, enum type, catch behavior, sprites/flipbooks, VFX va SFX.
- Custom Blueprint: mo companion UE 5.6 project; editor chinh chi import ket qua da cook.

### 6. Validate and Build

- Kiem tra object/path collision, unversioned schema, imports, dependency closure va Asset Registry.
- Build ra staging directory truoc.
- Pack thanh `<ModName>_P.pak`; khong sua base pak.
- Liet ke semantic diff va SHA-256 cua output.

### 7. Install, Test, Rollback

- Chi cai khi game da dong.
- Backup/move patch cu, atomic install, mot-click uninstall.
- Dung save test rieng; sau mount proof moi cho add item vao Bag.
- Test open Bag, icon/text, use/give/sell/toss/battle, in-game save va reload.

## Cac milestone bat buoc truoc khi code full tab

### Milestone 0 - Mount proof (PASS)

Probe marker-only da duoc runtime mo khi dung ten `PokemonEmerald-Windows_0_P.pak`; ten pak tuy y bi
bo qua. Probe da duoc go sach. Buoc sau se can mot override hinh anh vo hai de chung minh asset
priority, nhung kha nang mount patch container khong con la gia thuyet.

### Milestone 1 - Schema/registry proof (PASS)

`.usmap` build-matched, clone-and-round-trip, same-path override va new-ItemData discovery deu pass.
`ItemDataManager` auto-discover package moi trong `/Game/Items/`; registry patch khong can cho proof nay.
Vong game UI/use/save/reload cua item do user tao van la acceptance test tiep theo.

## Quyet dinh hien tai

Nen xay Item Mod Builder, nhung theo thu tu:

1. Read-only `Environment Check` + manifest/version detector. **Da implement.**
2. Controlled mount probe. **Da pass container mount.**
3. Mapping/registry extractor va verifier. **Da pass.**
4. MVP override existing item. **Runtime proof da pass.**
5. Template-based new item dung existing behavior. **v0.15.0 exposes 41 selected templates across
   11 archetypes; representative Vitamin/Ball/TM manager discovery is proven.**
6. Tich hop `Add to test save`. **Da expose item installed trong Bag tab; runtime acceptance pending.**

Khong nen mo rong thanh form "tat ca 72 field" ngay luc nay. Moi archetype phai co template/dependency
proof rieng de tranh tao cooked asset parse duoc nhung runtime-invalid.
