# OriginPro CLI Plot Skill

一个面向 Codex 的 Origin/OriginPro 科研绘图 skill。它可以从表格、光谱、现有拟合曲线或 `.opju` 模板生成**可编辑 Origin 项目**，并进行保存后反读、来源哈希绑定和多格式导出检查。

图中文字中的科学指数会用 Origin 富文本保存为真正的上标。任务可直接写 `cm^-1`、`m^2` 或 `R^2`，交付的 OPJU、PDF、PNG 和 TIFF 不会留下可见的 `^`。

## 主要能力

- 40 条可执行绘图路线，覆盖 XPS、FTIR、UV–Vis、XRD、TGA/DSC、CV/LSV/EIS、误差棒、箱线图、小提琴图、热力图、ROC/PR、校准曲线和混淆矩阵等。
- 普通曲线与分峰曲线的默认样式，包括分峰渐变填充、反向 XPS 横轴和多曲线图例布局。
- 复用已有 `.opju` 的字体、图层、坐标与曲线格式，同时保留目标数据和实际峰数。
- 输出 OPJU、PNG、PDF、TIFF；保存后重新打开并检查字体、图层、曲线绑定、坐标、数据哈希和导出属性。
- 将用户确认的数据映射、来源文件和文件哈希绑定到交付记录，避免绘错文件或静默更换数据。

完整路线见 [`references/plot-routes.md`](references/plot-routes.md)。

## 运行条件

- Windows x64。
- 本机已安装并注册 Origin/OriginPro。上游完整验证基于 Origin 2024b；本集成也在 OriginPro 2025 SR1 上做过实际项目验证。
- Python 3.10–3.12。依赖可安装在 skill 内部的隔离环境，不需要修改系统 Python 或 PATH。

本项目不包含 OriginLab 软件，也不代表 OriginLab 官方产品。

## 安装

把整个 `originpro-cli-plot` 文件夹复制到 Codex 的 skills 目录，使最终路径类似：

```text
%CODEX_HOME%\skills\originpro-cli-plot\SKILL.md
```

如果没有设置 `CODEX_HOME`，Windows 常见位置是：

```text
%USERPROFILE%\.codex\skills\originpro-cli-plot\SKILL.md
```

然后在 skill 目录运行：

```powershell
python -X utf8 scripts\originpro_routes.py check-install
python -X utf8 scripts\originpro_routes.py doctor
```

如果 `doctor` 报告缺少 Python 依赖，可运行：

```powershell
python -X utf8 scripts\originpro_routes.py doctor --repair
```

该命令只在 skill 内创建隔离环境。它不会安装 Origin，也不会修改系统 PATH。

## 使用示例

安装后可在 Codex 中说：

```text
使用 $originpro-cli-plot 检查这份 XPS Excel，沿用提供的 OPJU 格式，输出可编辑 OPJU、PNG、PDF 和 TIFF。
```

对于新图，skill 会先检查工作表、列名、单位、缺失值、拟合列与误差列，再选择合适路线。对于真实科研数据，它会要求将实际数据映射与用户选择写入来源绑定记录，不会把样例数据当成用户确认。

## 包内容与隐私

分享包包含 skill 代码、测试、绘图模板、合成示例和固定版本的 EditaPlot 源码。以下内容已排除：

- 本机虚拟环境和绝对环境路径；
- Python/pytest 缓存；
- 用户 Excel、OPJU、图片和交付项目；
- API 密钥、GitHub 凭据及其他账号数据。

## 验证

发布包应满足：

```powershell
python <skill-creator-path>\scripts\quick_validate.py .
python -m pytest -q tests
python -X utf8 scripts\originpro_routes.py check-install
```

本次分享包的实际结果记录在 `SHARE_AUDIT.json`。

## 第三方组件与许可证

40 路线引擎来自 [hang-jin/editaplot](https://github.com/hang-jin/editaplot)，固定于提交 `4aa986f3f84da9cb2a2297159a8f20e42b7e527c`，按 Apache License 2.0 分发。完整许可证、NOTICE、来源哈希和本地兼容性修改说明保存在：

- `THIRD_PARTY_NOTICES.md`
- `vendor/editaplot/LICENSE`
- `vendor/editaplot/NOTICE`
- `vendor/editaplot/UPSTREAM.json`

当前分享包尚未为用户自行编写的集成层选择顶层开源许可证。公开发布前建议由维护者明确选择许可证；第三方 Apache-2.0 声明必须保留。
