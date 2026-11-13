# 导航网格与定位瓦片 v3

本仓库供 nav-grid-editor 和 ok-end-field 使用。`dataset.json` 统一登记导航网格、层声明、跨层连接和视觉资源；`localization/manifest.json` 使用定位瓦片 v3。

## 下载

WebP 与 NPZ 使用 Git LFS，必须取得实体文件：

```powershell
git clone https://github.com/luqing233/nav-grid-data.git
git -C nav-grid-data lfs pull
```

在消费项目中运行 `git submodule update --init assets/nav-grid-data`，再运行 `git -C assets/nav-grid-data lfs pull`。子模块使用项目固定的提交，不会自动跟随本仓库 master。

## 定位资源

本版本将旧整图 PNG 替换为有完整索引的 WebP 瓦片，包含 3 张主图、69 张楼层图、粗搜缩图和楼层排序图。索引记录完整逻辑尺寸、标定和裁切位置；消费者按需解码局部块。

- `full`：保留完整块；楼层 alpha 为零的像素按零 BGR 处理。
- `roi`：无损保存非零 BGR 外接矩形，按 `roi` 还原位置，其他像素补零。
- `zero`：明确声明整个逻辑块为零；缺失文件或索引记录不等于零块。

坐标沿用原标定，像素中心使用整数坐标，左上原点、列向右、行向下。本次修复保留所有非全透明楼层块的完整载荷，alpha 不按 BGR ROI 裁剪；不透明黑色及部分透明度均参与当前层与压暗主图的合成。全黑但非透明的 `full` 块允许空 BGR ROI；楼层 `zero` 只表示全透明。

格式契约见 [Editor v3 文档](https://github.com/luqing233/nav-grid-editor/blob/master/docs/localization-tiles-v3.md)。消费端需支持 v3；ok-end-field 的对应适配在 [PR #678](https://github.com/AliceJump/ok-end-field/pull/678)。旧版仅支持整图 PNG 的消费者不能直接加载此版本。

## 导航约定

- `cells[z,x]` 是二维 uint8：0 未知、1 可走、2 阻挡；格式为 `okef-nav-grid` v2。
- 主图文件为 `<map>_<zoom>.grid.npz`，楼层为 `<map>__<tier>_<zoom>.grid.npz`。
- `origin` 为世界坐标最小角，`cell_size` 为格长；主图磁盘 tier 为空串，Editor API 使用 `__main__`。
- `levels.json` 包含无网格的层声明；不能仅扫描 NPZ 代替完整层索引。
- 跨层仅使用 `links.json` 显式连接，遵守方向；没有连接就不能推断可以跨层。
- `floor_regions` 的矩形与 cells 是世界坐标，包含真实 Y 区间；cells 非空时先判逐格 X/Z，再判外框和高度，均为闭区间。
- links v3 端点可选 `y_min/y_max` 必须成对出现；未提供的高度保持未知。
- 视觉仅提供 X/Z；网格 origin 中 Y=0 是格式占位，不能代替角色高度。独立场景不与归档主图合并坐标空间。

新增 `scene_map02_lv004_layer_tips_1` 网格包含 1574 个已标注格，未知格保持未知。缺失楼层 `scene_map01_lv007_layer_tips_6` 继续保留缺项声明，不补图或伪造楼层身份。

## 生成与验证

通过 Editor 的 `export-dataset --format tiled-v3` 从已保存素材和网格生成。`validation.json` 保存冻结输入的文件摘要、精匹配 BGR 逐像素核对结果、搜索资源核验和缺项原因；`alpha_repair` 记录本次楼层 alpha 恢复及全量核验结果。这些检查不是实机识别精度保证。

在 Editor 仓库中，针对独立导出目录运行：

```powershell
uv run --locked python -c "from nav_grid_editor.services.maps.dataset_tiled_export import verify_tiled_release; verify_tiled_release('output/nav-grid-release')"
```

在支持 v3 的 ok-end-field 中，对实际安装的资源运行：

```powershell
uv run --locked python scripts/nav/verify_localization.py --root assets/nav-grid-data/localization
```

旧 `scripts/verify_localization.py` 只理解 PNG 整图，已移除。生产端验证覆盖完整发布目录、导航注册与连接，消费端验证覆盖定位清单、资源摘要、标定和稀疏块语义。不要用仅支持旧格式的检查器验证 v3。
