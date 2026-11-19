# nav-grid-data

`navigation/` 是导航业务的唯一运行根，包含网格、层声明、跨层连接、视觉定位载荷、
预编译竞争资源和根发布标记。请完整下载并解压整个仓库；只复制其中一部分不构成
可用数据包。

```text
navigation/
├── dataset.json
├── *.grid.npz
├── levels.json
├── links.json
├── validation.json
├── prepared-package.json
├── schemas/
└── localization/
    ├── manifest.json
    ├── maps/
    ├── layers/
    ├── objects/
    └── prepared/
```

`dataset.json`、`localization/manifest.json` 和
`localization/prepared/manifest.json` 由 `prepared-package.json` 与 `READY`
互相绑定。prepared 直接复用 localization 中的楼层排序图，不复制第二份图片。
运行端只读取这些静态资源，不会在首次定位时编译派生图片。

完整验证、来源摘要及缺项见 `navigation/validation.json`。WebP 和 NPZ 使用
Git LFS；发布或更新数据前必须取得实体文件，不能提交 LFS 指针文本。
