# Them item cho Pokemon Gamma Emerald: gioi han va quy trinh an toan

Tai lieu nay ap dung cho ban game dang cai dat `GE-1.0.0` va Gamma Emerald Save Editor v0.13.2.

## Ket luan ngan

Save editor **co the tao them mot dong inventory**, nhung **khong the tu tao mot item that ma game
chua dong goi**.

Trong save, moi dong Bag chi co ba truong ma editor da xac minh:

- `ItemName`: ten noi bo dung de game tim item.
- `ItemID`: hien cac dong da xac minh dung gia tri `0`.
- `Quantity`: so luong.

Ten, icon, pocket, mo ta, gia tri su dung va hieu ung cua item nam trong cac Unreal `ItemData`/
Blueprint da duoc cook vao game. Neu chi ghi `Master Ball` vao `ItemName`, save van co the parse binh
thuong nhung runtime khong co asset de resolve. Ket qua co the la dong trong/Unknown, item bien mat,
khong dung duoc, hoac Fatal Error. Vi vay editor khong mo che do ghi ten raw trong UI.

## Ket qua audit ban game hien tai

`Manifest_UFSFiles_Win64.txt` cua ban cai dat liet ke dung **86** concrete ItemData:

| Pocket | So item co ItemData |
|---|---:|
| Items | 35 |
| Pokeballs | 9 |
| TMs | 26 |
| Berries | 4 |
| Key Items | 12 |
| Tong | 86 |

Editor da bao phu 86/86 item nay.

Executable co enum cho 8 Ball nua: Dive, Dusk, Heal, Master, Nest, Net, Quick va Safari Ball. Tuy
nhien build nay khong co `DA_*` ItemData va khong co concrete Ball Blueprint tuong ung. Chung chi la
ten enum con sot lai, khong phai item runtime hoan chinh.

Bon asset co Blueprint nhung chua co registered ItemData la Alternative Amulet, Rotten Leftovers,
Shiny Ping va Fire Stone. Blueprint rieng le khong du de bien chung thanh mot dong Bag hop le.

## Ba truong hop khac nhau

### 1. Item da co san trong game

Day la truong hop editor dang ho tro. Vao tab Bag, chon `+ Add Item`, pocket, item va quantity. Moi
thay doi chi duoc stage; dong game roi dung `Save + Backup` de ghi an toan.

### 2. Item duoc author them trong ban update sau

Co the ho tro tu editor sau khi xac minh ban update co:

1. Concrete `Content/Items/.../DA_<Item>.uasset`.
2. `ItemName` va `EItemCategory` that ben trong DataAsset.
3. Blueprint/effect can thiet doi voi Ball, medicine, evolution item hoac Key Item co hanh vi.
4. Icon/UI reference hop le.

Sau do chi can bo sung ten noi bo + pocket da xac minh vao catalog cua editor. Khong can thay doi
dinh dang save neu schema Bag van la ba truong hien tai.

### 3. Tu tao mot item game chua co

Day la **game modding**, khong con la save editing. Mot mod hoan chinh toi thieu phai:

1. Duoc cook bang Unreal Engine/phien ban va class schema tuong thich voi game.
2. Tao ItemData, icon/UI va effect/Blueprint.
3. Dang ky asset de runtime/Asset Manager tim thay.
4. Voi Ball, tao logic bat Pokemon va mapping `EPokeballType` phu hop.
5. Dong goi thanh mod pak load sau pak goc va test tren mot save copy.
6. Cuoi cung moi them `ItemName` do vao catalog editor.

Chi clone/doi ten mot `.uasset` hoac ghi ten vao save la chua du. Pak goc hien cung duoc ma hoa, nen
khong nen sua de len file game goc; neu nghien cuu mod, dung overlay pak tach rieng va giu ban cai dat
sach de rollback.

## Checklist xac minh mot item moi

Dung mot save test rieng, khong dung save chinh.

1. Xac nhan game da dong va backup ca Story/Quest/Berry/Options lien quan.
2. Xac nhan DataAsset + Blueprint/effect + icon deu ton tai trong **chinh build dang test**.
3. Ghi mot item, quantity `1`; khong batch nhieu item chua test.
4. Mo game, vao Bag va kiem tra ten, icon, pocket, description.
5. Test cac hanh vi phu hop: use, give/hold, remove, sell/toss, hoac throw trong battle.
6. Save trong game, thoat, mo lai game va mo lai editor.
7. Chay validation va kiem tra crash log. Neu item mat, thanh Unknown, khong dung duoc hoac crash,
   restore backup ngay va coi candidate la unsupported.

Mot item chi nen duoc dua vao dropdown chinh thuc sau khi qua het vong test tren. Parser/serializer
round-trip thanh cong **khong** phai bang chung runtime item hoat dong.

## Huong phat trien hop ly cho editor

- Them bo detect thay doi cua `Manifest_UFSFiles_Win64.txt` khi game update, de bao co ItemData moi.
- Import catalog extension co schema ro rang (`name`, `pocket`, asset evidence), nhung chi bat writer
  sau khi user xac nhan item da duoc runtime-test.
- Danh dau item custom/experimental va khong cho no tron lan voi 86 item verified.
- Khong cung cap hop nhap `ItemName` tuy y mac dinh, vi no rat de tao save parse-duoc nhung game-crash.

Voi ban GE-1.0.0 hien tai, cach an toan la giu dropdown o 86 item. Neu author phat hanh build moi
hoac co mot mod pak item hoan chinh, catalog editor co the mo rong ma khong can reverse engineer lai
toan bo save format.
