# 导航网格与视觉定位资源

本仓库供 nav-grid-editor 和 ok-end-field 使用。根目录的 `*.grid.npz`、
`levels.json`、`links.json` 是导航数据；`localization/` 是独立的视觉定位资源。

## 取得完整资源

WebP、旧 PNG 和网格通过 Git LFS 保存，必须下载实际内容，不能把 LFS 指针当图片。

```powershell
git clone https://github.com/luqing233/nav-grid-data.git
git -C nav-grid-data lfs pull
```

ok-end-field 源码中的获取方式：

```powershell
git submodule update --init assets/nav-grid-data
git -C assets/nav-grid-data lfs pull
```

子模块固定到主项目记录的提交，不会自动追踪本仓库最新 master。
发布流程应先取该提交的 LFS 实体，再展开为普通文件随 assets 分发。
`AliceJump/ok-end-field-x-anylabeling-asset` 是另一份截图模板仓库；
截至本次核查，其工作流没有从本仓库同步导航或定位资源。

## 视觉定位资源

```text
localization/
  manifest.json                  文件长度、SHA-256、坐标约定与来源
  maps/<map>/4/<map>_4.webp        base01 / map01 / map02 原分辨率基础图
  maps/<map>/4/<map>_4_mapping.json
  layers/catalog.json            官方分层元数据（schema_version=1）
  layers/<map>/<level>/<tier>.webp
```

与 ok-end-field 的 `CalibratedMapStore` 直接兼容：将“视觉地图资源目录”设为
`assets/nav-grid-data/localization/maps`。分层目录从该路径的同级 `layers/` 读取。
包内为 3 张基础图及标定、69 张分层图（map01=22、map02=47）。
发行图为原分辨率彩色 WebP Q90（Pillow quality=90、method=4），楼层图保留原 alpha，
不转灰度、不压平透明背景、不做降采样。RGB 有损压缩，alpha 逐像素保留；尺寸、
标定控制点、仿射矩阵和 bounds 不变。72 张图片共 17,406,888 字节，定位资源含元数据共 17,500,255 字节。
manifest/catalog 指向实际文件，旧 PNG 仍兼容读取；消费端须使用已支持彩色 WebP 的版本。
`dataset.json` 结构及 schema_version=1 不变，记录新定位清单的大小与 SHA-256。
本次图片更新保留远端最新导航网格、links 和 levels 原字节。

基础图 `matrix` 将 `[u,v,1]` 变换为世界 `[X,Z]`，`inverse_matrix` 反向变换。
分层原图使用官方 bounds：

```text
X = west + u * (east - west) / width
Z = north - v * (north - south) / height
```

分层无需另存 `_mapping.json`。消费者若缩放图片，必须同步变换像素标定；
ok-end-field 的 `layer_calibration` 已处理重采样的像素中心约定。
`map_category=independent` 的图保留在目录内，须保持独立场景身份，
不能根据归档 map_name 把局部坐标与大地图合并；当前消费者只匹配 `layered`。

目录保留 `missing_logic_ids`：`scene_map01_lv007_layer_tips_6` 暂缺资源。
不得删除该标记或把不完整比较宣称为唯一楼层。层声明不代表已经有对应导航网格。
视觉只提供 X/Z；没有真实高度时 Y 应保持缺失，网格 origin 的 Y=0 只是格式占位。
图像不能区分重叠层时须保持 tier 未知，不能按高度区间中心或入口距离伪造层身份。

## 导航数据契约

- `cells[z,x]` 为二维 uint8：0 未知、1 可走、2 阻挡；格式为 `okef-nav-grid` v2。
- 主图 `<map>_<zoom>.grid.npz`；分层 `<map>__<tier>_<zoom>.grid.npz`。
- 世界坐标最小角为 `origin`；格子大小为 `cell_size`；主图磁盘 tier 为空串，API 为 `__main__`。
- `floor_regions` 中矩形和可选 cells 都是世界坐标，含真实 Y 区间；cells 非空时先判逐格 X/Z，再判外框和高度，均为闭区间。
- `levels.json` 是层声明索引，包含没有网格的层；不能仅扫描网格文件代替它。
- 跨层只走 `links.json` 的显式边。端点 rect 是世界坐标，空 zoom 按查询 zoom 解析。
- links 读取兼容 v1/v2/v3；v3 可选端点 y_min/y_max 成对出现，缺失就是未知。
  两端未同时给高度时不得从 floor_regions 猜落差。

## 完整性检查

从仓库根目录运行（仅用 Python 标准库，无需解码整张大图）：

```powershell
uv run --no-project python scripts/verify_localization.py
```

检查覆盖文件 SHA-256、字节数、WebP/PNG 尺寸、标定矩阵互逆、目录引用、独立场景分类和缺失层声明。
此检查验证资源完整性，不代表实际游戏截图上的识别精度或楼层覆盖完整。
