# HANDOFF — 给接手 AI 的交接说明

> 本文件是**交接文档**，不是给用户看的教程。请接手者先完整读完本文件，再动代码。
> 最后更新：2026-11-12。用户因时间不足主动中止开发，要求把当前进度上传 GitHub 并留下未完成事项。
> 阅读对象：下一个接手本仓库的 AI / 开发者。用户使用中文、偏好简洁指令与表格化说明。

---

## 0. 一句话现状

**代码可运行、可测试，但项目没有做完。**

- 约 5000 行 Python（47 个 `.py`），多模块工程，核心玩法闭环已打通。
- `62` 个单元测试全绿；真实窗口 3 秒冒烟通过（约 60 FPS，180 逻辑步）。
- 100 个种子 × 6 层 = 600 个地牢全部连通且同种子完全复现。
- **最大的缺口：AI 像素素材一张都没生成**（`assets/raw/` 为空），当前画面是程序化几何替身。
- **第二大缺口：没有做过端到端全流程试玩**（6 层通关、Boss 战、道具组合、死亡结算均未人工或脚本化验证），平衡性完全没调。

请**不要**把"测试全绿"误读成"游戏完成"。

---

## 1. 用户原始需求与已拍板的决策（不要重新问用户）

原始需求：「下载个 pygame 库，看看能不能通过 Python 生成个类似以撒的游戏，不限时间」。

| 项目 | 用户已确认的选择 | 当前落实情况 |
| --- | --- | --- |
| 完成度 | 完整可玩版（随机地牢、多敌人、眼泪射击、道具、Boss、多层、结算） | 代码层面已实现，未经实玩验证 |
| 美术 | **AI 生成像素图片素材**（不是纯几何绘制） | ❌ 未落实：0/26 张，仅留了完整管线与降级方案 |
| 代码形式 | 多模块工程 + requirements.txt + README | ✅ 已落实，README 本次补齐 |
| 附加功能 | 随机种子与存档 | ✅ 已落实（单元级验证） |
| 附加功能 | 中文教程与关键逻辑中文注释 | ✅ 注释已有，README 本次补齐 |
| 通关层数 | **6 层** | ✅ `settings.MAX_FLOOR = 6` |
| 操作 | **双模式可切换**：WASD+方向键 / WASD+鼠标瞄准 | ✅ `core/input.py` + `Tab` 切换，标题页有提示 |
| 安装方式 | 工程内 `.venv` 隔离 | ✅ 已建（**不上传**，需本地重建） |
| 未选（不用做） | 音效/BGM、手柄支持 | 未做，但架构未堵死 |
| 素材预算 | 用户接受完整 25–30 张（约 125–300 积分） | 未消耗，尚未生成 |

其他用户偏好：不喜欢画面闪烁（已用双缓冲 + 固定步长）；代码修改遵循最小改动；本次明确允许中文注释。

---

## 2. 环境与运行（接手第一步）

| 项 | 值 |
| --- | --- |
| 系统 | Windows 11，交互式桌面，可弹 pygame 窗口 |
| Python | 3.13.14（64 位） |
| pygame | 2.6.1（SDL 2.28.4，官方 cp313 wheel） |
| Pillow | 11.3.0 |
| 逻辑分辨率 / 窗口 | 480×288 / 960×576（`SCALE=2`） |

**重建环境（本机有 6 个 Python，`pip` 裸命令指向 3.11，会装错地方！统一用 venv 内的解释器）：**

```bash
cd isaac_like
python -m venv .venv
./.venv/Scripts/python.exe -m pip install --upgrade pip
./.venv/Scripts/python.exe -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

**常用命令：**

| 命令 | 用途 |
| --- | --- |
| `./.venv/Scripts/python.exe main.py` | 正常游玩，标题页可输入种子 |
| `... main.py --seed DEMO-1` | 指定种子直接开局 |
| `... main.py --smoke --seconds 3 --seed SMOKE-1 --stats` | 真实窗口冒烟 + 自动截图 |
| `... main.py --headless --smoke --seconds 60 --stats` | 无窗口长稳测试（自动驾驶） |
| `... main.py --no-assets` | 强制几何占位，用于排查素材问题 |
| `... main.py --mode mouse` | 强制鼠标瞄准模式 |
| `./.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py" -v` | 62 个单元测试 |
| `./.venv/Scripts/python.exe tools/make_sprites.py` | 重建 sprite sheet |
| `./.venv/Scripts/python.exe tools/make_sprites.py --validate` | 只校验现有产物 |

**本机已知环境坑：**
- Windows schannel 证书吊销检查失败（`CRYPT_E_NO_REVOCATION_CHECK`），`curl` / `git` 直连 GitHub 会报 SSL 错误。git 用 `git -c http.schannelCheckRevoke=false ...` 规避；PowerShell 的 `Invoke-RestMethod` 正常。这是本机问题，不是项目问题。
- `assets/raw/` 是空目录，靠 `.gitkeep` 保留；`saves/` 与 `.venv/` 被 `.gitignore` 忽略。

---

## 3. 已完成内容（文件 → 职责）

| 目录 | 文件 | 职责 |
| --- | --- | --- |
| 根 | `main.py` | 入口、argparse、pygame 初始化（`SDL_AUDIODRIVER=dummy`）、开窗 |
| 根 | `settings.py` | 全部常量、调色板、`State` 状态枚举、枚举型配置 |
| 根 | `requirements.txt` | pygame==2.6.1、Pillow |
| `core/` | `loop.py` | 固定步长累加器（`STEP=1/60`）、整帧缩放、FPS 统计、截图、退出 |
| | `game.py` | 状态机、碰撞分发、事件注册、楼层推进、结算（约 578 行，最核心） |
| | `vec2.py` / `collision.py` | 向量、圆-圆 / 圆-矩形碰撞 |
| | `rng.py` | 基于 sha256 派生的确定性随机 + `fork`，禁止污染全局 `random` |
| | `events.py` / `context.py` | 事件总线常量、依赖注入容器（bus / rng / painter / seed） |
| | `input.py` | 双输入模式、`Tab` 切换、确定性自动驾驶（冒烟用） |
| | `save.py` | JSON 存档：原子写、版本迁移、损坏时备份并重建 |
| | `assets.py` / `sprite_sheet.py` | 素材加载、`convert_alpha`、缓存、缺图返回 `None` |
| `entities/` | `base.py` | `Entity` 基类、`Group` 分组、生命/无敌帧 |
| | `player.py` / `tear.py` | 玩家、眼泪（射程衰减、尺寸随伤害） |
| | `enemies.py` | 6 种敌人 AI：fly / chaser / hopper / shooter / splitter / orbiter |
| | `boss.py` | Boss 分阶段攻击 |
| | `door.py` / `prop.py` / `pickup.py` | 门、障碍/基座/火焰、心/币/钥匙/炸弹掉落 |
| `world/` | `dungeon.py` | 地牢生成（连通性、房间类型、Boss 房距离约束、`signature()` 复现） |
| | `floor.py` / `room.py` | 楼层容器、房间实体管理与清房开门 |
| | `room_templates.py` | ASCII 房间模板网格 |
| | `minimap.py` | 小地图 |
| `items/` | `stats.py` / `item_defs.py` / `effects.py` | 属性结构、20 个道具定义、道具效果应用 |
| `ui/` | `painter.py` / `fonts.py` / `hud.py` / `screens.py` | 绘制门面（缺图降级几何）、中文字体、HUD、各状态界面 |
| `tools/` | `make_sprites.py` | AI 原图 → 去背 → 统一色板 → 切格 → sprite sheet + manifest |
| `tests/` | 7 个 `test_*.py` | RNG / 地牢 / 存档 / 道具 / 战斗 / 素材 / 状态机，共 62 例 |
| `assets/` | `sprites/*.png`、`manifest.json`、`sheets.json` | **程序化兜底生成的** 5 张 sheet、44 个 sprite key |

**已验证的边界：**
- 3 秒真实窗口冒烟：182 帧 / 180 逻辑步 / 平均 60.6 FPS，截图 `screenshots/smoke.png`。
- 600 个地牢：全部连通、Boss 房度为 1、Boss 距起点 ≥3、同种子 `signature()` 完全一致。
- 存档：往返、损坏 JSON 恢复、非对象根节点恢复（测试里有对应日志输出，属正常）。

---

## 4. 未完成事项（按优先级，接手请从这里开始）

### P0-1　AI 像素素材：0/26 张，用户明确选的方案尚未落地

- `assets/raw/` **为空**；`sprites/*.png` 全部是 `tools/make_sprites.py` 里的 `make_placeholder()` 几何替身。
- `RAW_SPECS`（`tools/make_sprites.py` 第 52–79 行）定义了 **26 个原图文件名**与处理方式：
  - `single`（一图一 sprite）：6 种敌人、2 个 Boss 姿态、2 种眼泪、4 种掉落、岩石/火焰/基座、门饰、地砖等。
  - `pose`：`player.png` 一张派生 4 个朝向。
  - `grid4`：`items_1.png` ~ `items_5.png`，每张 2×2 切 4 个道具图标，共覆盖 20 个道具。
- 生成要求（原设计）：**透明背景直出**、统一像素风与统一色板、单主体居中、避免抗锯齿糊边；本环境的 `ImageGen` 支持透明底与参考图风格继承（比"洋红底抠图"更省事），管线里仍保留 `clean_background()` 兜底去背。
- 成本提醒：约 26 张 × 5–10 积分 ≈ 130–260 积分，**生成前须再次向用户确认**。
- 落地步骤：`assets/raw/<名字>.png` 放图 → `python tools/make_sprites.py` → `--validate` → 跑一遍冒烟截图肉眼对比。管线是增量的：任何一张失败只影响对应 sprite，不会让游戏崩。
- **已知小缺口**：`RAW_SPECS` 末尾是 `floor_decor.png` / `decor.png`，原先规划的 `items_6.png` 被替换掉了。当前 20 个道具恰好被 `items_1~5` 覆盖，所以暂时无影响；但**若后续新增道具超过 20 个，需补 `items_6.png` 之类的网格入口**，否则新增图标只能吃占位图。

### P0-2　从未做过完整流程试玩 / 通关验证

- 只跑过 3 秒冒烟和单元测试。**没有**验证过：6 层连续推进、Boss 击杀触发通关、死亡结算、宝箱/商店/道具房实际交互、道具叠加后的数值、清房开门的真实手感。
- 建议补两类自动化：
  1. **长稳测试**：`main.py --headless --smoke --seconds 600 --stats`，断言无异常、FPS 不明显下滑、内存不涨。
  2. **脚本化通关测试**：直接构造 `Game`，循环 `advance_floor()` 到第 6 层、清空 Boss 房敌人、断言 `State.WIN`；死亡路径同理断言 `State.DEAD`。目前 `tests/test_game.py` 只覆盖到胜负结算写存档，没有走完整链路。
- 之后仍需人工试玩至少一局，确认手感与可读性。

### P0-3　平衡性完全没调

- 数值散落在 `settings.py`（基础属性）、`items/item_defs.py`（20 个道具）、`entities/enemies.py`（`hp_scale` / `speed_scale`）、`world/floor.py`（楼层难度）、`world/room.py`（刷怪量）。
- 敌人伤害、道具强度、掉落率、Boss 血量都是首次拍脑袋赋值，未做难度曲线验证。

### P1-4　视觉复核未做

- `screenshots/smoke.png` 是**几何占位时期**的截图，画面元素齐全但墙/地板对比弱；之后调过一次 `COL_WALL*` 与墙体纹理，**没有再截图确认**。
- 接上 AI 素材后必须重新截图，检查 `Painter` 的 sprite 尺寸、锚点、透明边、朝向翻转是否对得上。

### P1-5　存档只做了单元级验证

- `core/save.py` 的往返 / 损坏恢复 / 版本迁移有测试，但**跨会话的最高纪录、解锁进度、输入模式持久化**没有在真实游玩流程里验证。
- `saves/` 被忽略（不上传），接手者本地首次运行会自动生成 `save.json`。

### P1-6　README 操作文案需人工核对

- 本次补的 `README.md` 按 `core/input.py` 与 `ui/screens.py` 写的键位，未逐条实按验证。

### P2-7　未选功能与工程化收尾

- 音效/BGM、`pygame.joystick` 手柄支持：用户没选，架构上 `core/input.py` 可扩展；注意 `main.py` 里把 `SDL_AUDIODRIVER` 设成了 `dummy`，要加音效必须先去掉。
- 没有 CI 配置、没有 LICENSE、没有 PyInstaller 打包、没有 CHANGELOG。
- 没有性能剖析（大量实体同屏时）；中文渲染依赖本机字体，`ui/fonts.py` 有兜底但未在缺字体机器上验证。

---

## 5. 架构约定（改代码前必读，破坏约定会让 62 个测试挂）

| 约定 | 说明 |
| --- | --- |
| 固定步长 | `core/loop.py` 用累加器按 `STEP=1/60` 更新逻辑，渲染整帧 `pygame.transform.scale` 到窗口；`pygame.DOUBLEBUF`，不要改成可变 dt |
| 确定性 | 所有随机必须走 `core/rng.RNG`（sha256 派生 + `fork`），**禁止 `import random` 直接取全局随机**；`RNG(seed)` 保证同种子同结果；另有 `visual_rng = RNG(seed + "|visual")` 隔离视觉抖动，避免影响逻辑 |
| 事件总线 | 实体不互相直接引用，统一 `ctx.bus.emit(...)`；`core/game.py` 注册 handler。这是避免循环 import 的关键 |
| 依赖注入 | `core/context.py` 的 `Context(bus, rng, painter, seed)` 传给每个实体的 `update(ctx)` |
| 分组碰撞 | `entities/base.py` 的 `Group` 决定友军/敌军子弹归属，碰撞在 `core/game.py` 统一分发 |
| 素材降级 | `AssetBank.get()` 返回 `None` 时 `Painter` 画几何图形。**任何素材缺失都不允许抛异常**，这是本项目最重要的容错契约 |
| 状态机 | `settings.State`：`TITLE / PLAYING / PAUSED / ITEM_SELECT / DEAD / WIN`；切换逻辑集中在 `core/game.py` |
| 存档 | JSON、原子写、含 `version`；损坏时备份并重建，绝不因存档坏而打不开游戏 |
| 冒烟输入 | `--smoke` 打开 `autopilot`，此时 `InputState.poll()` 会**屏蔽所有真实按键注入**。写 `Game` 级测试时记得把 `autopilot` 关掉（见 `tests/test_game.py`） |

---

## 6. 测试与验收命令

```bash
# 单元与逻辑
./.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py" -v     # 62 例
./.venv/Scripts/python.exe -m compileall -q .

# 地牢批量断言（100 种子 × 6 层，之前通过）
./.venv/Scripts/python.exe -c "
from core.rng import RNG
from world.dungeon import Dungeon, build_adj, bfs_dist
from settings import MAX_FLOOR
for i in range(100):
    for f in range(1, MAX_FLOOR + 1):
        s = 'SEED-%d' % i
        a, b = Dungeon(f, RNG(s)), Dungeon(f, RNG(s))
        assert a.signature() == b.signature()
        adj = build_adj(a.cells, a.links)
        assert len(bfs_dist(adj, a.start_pos)) == len(a.cells)
        assert len(adj[a.boss_pos]) == 1
print('OK 600 dungeons')
"

# 渲染冒烟（会弹窗 3 秒并写 screenshots/smoke.png）
./.venv/Scripts/python.exe main.py --smoke --seconds 3 --seed SMOKE-1 --stats
```

验收标准：测试全绿 + 冒烟截图能看到房间地板/四面墙/门/玩家/HUD 心形血量/中文文字/右上角小地图，且不是纯色或黑屏。

---

## 7. 已修 Bug 与踩过的坑（不要重复踩）

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 冒烟启动时 `Tear` 初始化报错 | 子类定义了同名只读属性 `radius` / `friendly` / `color`，挡住基类赋值 | 改为普通字段，见 `entities/tear.py` |
| 敌人刷不出来 / 卡在障碍里 | `world/room.py` 把模板里的敌人生成点 `'e'` 也建成了 `Prop` 障碍物 | 生成点跳过建障碍 |
| Game 测试里注入的按键无效 | `--smoke` 的 autopilot 屏蔽了注入 | 测试构造 `Game` 时关掉 autopilot |
| `pip install` 装完 import 不到 | 机器 6 个 Python，裸 `pip` → 3.11、`python` → 3.13 | 统一 `.venv/Scripts/python.exe -m pip` |
| curl / git 连 GitHub SSL 报错 | Windows schannel 吊销检查 | `git -c http.schannelCheckRevoke=false` |

---

## 8. 建议接手顺序

1. 克隆 → 按第 2 节重建 `.venv` → 跑 62 测试 + 3 秒冒烟 → 看 `screenshots/smoke.png`，确认基线。
2. 先补 **P0-2 脚本化通关/长稳测试**，把"能不能真的打完 6 层"这件事钉死，再谈其它。
3. 向用户确认积分后做 **P0-1 AI 素材**（26 张），重跑 `make_sprites.py`，截图对比，修 `Painter` 锚点问题。
4. 人工试玩一局 → 调 **P0-3 平衡性**。
5. 收尾：README 键位核对、LICENSE、CI、可选音效/手柄。

---

## 9. 安全与仓库约定

- 用户提供的 GitHub Personal Access Token 曾以明文出现在对话里，**必须提醒用户尽快在 GitHub Settings 中撤销并轮换**。本仓库的任何文件、`.git/config`、remote URL 都不含该凭据（推送时才通过临时 HTTP header 传入）。
- `.venv/`、`saves/`、`__pycache__/`、临时截图一律不入库；`screenshots/smoke.png` 作为验收证据保留。
- 默认分支 `main`；提交前请确认没有把本地存档、素材原图临时文件或任何密钥 `git add` 进去。
