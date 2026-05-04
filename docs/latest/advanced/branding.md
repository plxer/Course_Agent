# 品牌自定义

系统支持自定义 Logo、组织名称、标题、副标题、功能卡片和版权信息。

## 配置方法

复制模板文件：

```bash
cp src/config/static/info.template.yaml src/config/static/info.local.yaml
```

编辑 `src/config/static/info.local.yaml`：

<<< @/../src/config/static/info.template.yaml

## 环境变量配置

如需指定自定义配置文件路径，在 `.env` 中设置：

```bash
BRAND_FILE_PATH=src/config/static/info.local.yaml
```

兼容旧环境变量 `YUXI_BRAND_FILE_PATH`，但新配置建议使用 `BRAND_FILE_PATH`。

## 样式定制

系统配色主要保存在 `web/src/assets/css/base.css` 中：

- 替换 `--main-*` 相关变量即可改变配色。
- 支持主题色、辅助色等完整定制。
- 前端热重载环境下保存后即可预览。

`web/src/stores/theme.js` 中也包含主题相关配置，可按需调整 `colorPrimary`。
