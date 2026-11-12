# 泪之地牢 · TEARS OF THE DUNGEON

一个用 **Python + pygame** 写的俯视角 roguelike 射击游戏，玩法参考《以撒的结合》：随机生成的房间地牢、眼泪射击、多种敌人 AI、道具强化、Boss 房、6 层推进、随机种子复现与本地存档。

> ⚠️ **当前状态：未完成**。代码可运行、62 个单元测试全绿、3 秒冒烟约 60 FPS，但 **AI 像素素材尚未生成**（画面目前是程序化几何替身），且**没有做完整流程试玩与平衡性调优**。
> 接手开发者 / AI 请先读 **[HANDOFF.md](HANDOFF.md)**，那里有完整的未完成事项、架构约定和踩坑记录。

---

## 快速开始

环境：Windows / Python 3.13 / pygame 2.6.1 / Pillow。

```bash
cd isaac_like
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
./.venv/Scripts/python.exe main.py
```

> 本机装了多个 Python，裸 `pip` 和 `python` 可能指向不同版本，**请统一用 `.venv/Scripts/python.exe -m pip`**。

## 操作

| 按键 | 作用 |
| --- | --- |
| `W A S D` | 移动 |
| `方向键` | 四向射击（默认模式） |
| `鼠标左键` | 朝鼠标方向射击（切到鼠标模式后） |
| `Tab` | 切换「WASD+方向键」/「WASD+鼠标瞄准」 |
| `E` / `空格` | 交互（开宝箱、拾取道具、进门） |
| `Q` | 使用炸弹 |
| `Esc` / `P` | 暂停 |
| `Enter` | 确认 |
| `R` | 用同一种子重开 |
| `T` | 返回标题 |
| `F1` | 调试信息 |
| `Backspace` | 标题页输入种子时删除字符 |

**玩法**：进入房间 → 清光敌人自动开门 → 走进门切换房间 → 找宝箱/道具房拿强化 → 打完该层 Boss 进入下一层 → 通关第 6 层即胜利。血量归零则本局结束，最高纪录写在 `saves/save.json`（本地文件，不入库）。

## 命令行参数

| 参数 | 说明 |
| --- | --- |
| `--seed DEMO-1` | 指定种子，复现同一局地牢 |
| `--mode keyboard` / `--mode mouse` | 指定输入模式 |
| `--no-assets` | 强制不用图片素材，全部几何占位 |
| `--headless` | 无窗口（SDL dummy 驱动，CI / 长稳测试用） |
| `--smoke --seconds 3` | 冒烟测试：自动驾驶、定时退出、自动截图 |
| `--shot PATH` | 指定冒烟截图路径 |
| `--stats` | 打印 FPS 统计 |

## 测试

```bash
./.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py" -v
./.venv/Scripts/python.exe main.py --smoke --seconds 3 --seed SMOKE-1 --stats
```

覆盖：随机数复现、地牢连通性、存档往返与损坏恢复、道具属性、碰撞伤害与掉落、素材管线、状态机结算，共 62 例。另有 100 种子 × 6 层 = 600 个地牢的批量断言（命令见 HANDOFF.md 第 6 节）。

## 目录结构

| 目录 | 内容 |
| --- | --- |
| `main.py` / `settings.py` | 入口、全部常量与状态枚举 |
| `core/` | 主循环、状态机、输入、事件总线、确定性随机、碰撞、存档、素材加载 |
| `entities/` | 玩家、6 种敌人、Boss、眼泪、掉落物、门、障碍物 |
| `world/` | 地牢生成、楼层、房间模板、小地图 |
| `items/` | 属性系统、20 个道具定义与效果 |
| `ui/` | 绘制门面、中文字体、HUD、各状态界面 |
| `tools/make_sprites.py` | 像素素材后处理管线（AI 原图 → 去背 → 切格 → sprite sheet + manifest） |
| `assets/` | `raw/`（AI 原图，目前为空）、`sprites/`（当前为程序化兜底图）、`manifest.json` |
| `tests/` | 7 个测试模块 |
| `screenshots/smoke.png` | 冒烟截图（几何占位时期） |

## 美术素材说明

原计划用 AI 生成 26 张透明底像素图。`tools/make_sprites.py` 已实现完整管线：把原图放进 `assets/raw/<名字>.png`，重跑脚本即可增量替换对应 sprite；**即使一张原图都没有，也会生成完整的程序化替身与 manifest，游戏不会因缺图崩溃**。文件名清单与生成要求见 [HANDOFF.md 第 4 节](HANDOFF.md)。

```bash
./.venv/Scripts/python.exe tools/make_sprites.py
./.venv/Scripts/python.exe tools/make_sprites.py --validate
```

## 许可

未指定 LICENSE。代码为学习用途，玩法参考《以撒的结合》，未使用其任何原始素材。
