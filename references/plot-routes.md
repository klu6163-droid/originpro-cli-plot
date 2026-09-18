# 40 条 Origin 绘图路线

来源：[EditaPlot 固定版本](https://github.com/hang-jin/editaplot/tree/4aa986f3f84da9cb2a2297159a8f20e42b7e527c)；Apache-2.0。

这 40 个公开路线及其数据模板、示例和执行器均随本 Skill 收录。XPS 的两个内部执行器不另算路线；ROC 与 PR 共用 diagnostic_curve。

运行 `python scripts/originpro_routes.py catalog` 查看清单；`catalog --json` 查看机器可读输入要求。源表数值、科学处理与模板选择仍需按本 Skill 确认。

状态区分：代码已集成；上游声称已验证的基线为 Origin 2024b；本机是否可运行以本次 doctor、origin-smoke、四格式导出和对象反读为准。目录中的 upstream_support_level 不是本机验收结果。

| 路线 ID | 图形 | 最少输入 |
|---|---|---|
| `xps` | XPS | 结合能或动能列；至少一个强度/计数列 |
| `eis` | EIS 阻抗谱 | Nyquist：Z 实部 + Z 虚部；或 Bode：频率 + 阻抗模/相位 |
| `trajectory3d` | 三维多条件 Nyquist 轨迹 | Zreal（数值）；真实第三变量与单位（数值）；-Zimag（数值）；Series（组名） |
| `density_ridgeline3d` | 三维双轮廓密度曲线与基线焦点 | Condition ID（条件标识）；Condition Position（带单位数值）；Density X（带单位数值）；Solid Density（非负数值）；Dashed Density（非负数值）；Focal X（每组仅一行非空） |
| `cv` | CV 循环伏安曲线 | 电位或电压列；一个或多个电流系列 |
| `lsv` | LSV 线性扫描伏安曲线 | 电位或电压列；一个或多个电流系列 |
| `xas` | XAS 吸收谱 | 能量列；一个或多个吸收信号列 |
| `pl` | PL 与 TRPL 光致发光谱 | Wavelength 或 Time；一个或多个 PL 数值系列 |
| `xps_compare` | XPS 多谱线对比 | Binding Energy/结合能列；至少两个独立实测 Intensity/Counts 数值系列 |
| `uv_vis` | UV–Vis 吸收/透射与 Tauc 插图 | Wavelength；一个或多个 Absorbance/Transmittance 系列 |
| `ftir` | FTIR / IR 红外光谱 | Wavenumber/波数列；一个或多个 Absorbance/Transmittance 数值系列 |
| `nmr` | NMR 核磁共振谱 | Chemical Shift/化学位移列；一个或多个 Intensity/强度数值系列 |
| `dsc` | DSC 差示扫描量热 | Temperature/温度列；一个或多个 Heat Flow/热流数值系列 |
| `xrd` | XRD 衍射图谱 | 普通图谱：2θ 衍射角列 + 一个或多个强度列；精修图：X/2θ + Obs/实测 + Calc/计算 |
| `bar` | 柱状图（可选误差） | 类别列；一个或多个数值系列 |
| `horizontal_bar` | 横向分组条形图 | 一列类别；一个或多个数值系列 |
| `stacked_bar` | 堆叠柱状图 | 一列类别；至少两个非负数值组成列 |
| `percent_stacked_bar` | 百分比堆叠柱状图 | 一列类别；至少两个非负数值组成列 |
| `pie` | 二维饼图 | 一列类别；恰好一个非负数值列 |
| `sankey` | 桑基流向图 | 来源 Source；目标 Target；正数权重 Value |
| `trend` | 多系列趋势折线图 | 连续 X 列；一个或多个数值系列 |
| `radar` | 多指标雷达图 | 指标列；至少两个非负数值系列 |
| `circular_network` | 环形有向加权网络图 | Panel；Source；Target；Weight |
| `heatmap` | 自适应矩阵热力图 | 一列行类别；至少两个数值系列 |
| `scatter` | 通用散点图 | 一个数值 X 列；一个或多个数值 Y 列 |
| `line_error` | 带误差折线图 | 一个数值 X 列；一个或多个中心值列；每个中心值的配对误差列 |
| `grouped_box` | 分组箱线与原始点图 | 至少四个数值列，列名写成 Category \| Group |
| `raw_summary` | 原始点汇总图 | 一个或多个原始数值列 |
| `violin` | 小提琴分布图 | 一个或多个原始数值列，每列至少 5 个观测 |
| `histogram` | 直方分布图 | 一个或多个原始数值列，每列至少 5 个观测 |
| `forest` | 森林效应图 | Label；Estimate；CI Low；CI High |
| `bubble` | 气泡关系图 | 一个数值 X；一个数值 Y；一个正值 Size |
| `diagnostic_curve` | 医学诊断 ROC / PR 曲线 | ROC：FPR + 一个或多个 TPR；PR：Recall + 一个或多个 Precision |
| `calibration_curve` | 医学模型校准曲线 | Predicted probability；Observed fraction；Bin count |
| `confusion_matrix` | 医学分类混淆矩阵 | 第一列 Actual class；后续每列一个 Predicted class 的计数或已给比例 |
| `bland_altman` | Bland–Altman 一致性图 | Mean；Difference；Bias；Lower LoA；Upper LoA |
| `decision_curve` | 医学决策曲线分析 | Threshold；一个或多个模型 Net benefit；Treat all；Treat none |
| `paired_trajectory` | 配对与纵向轨迹图 | 一个数值 Time/Visit/Condition index；每个 Subject 一列数值 |
| `raincloud` | Raincloud 原始分布图 | 一个或多个原始数值列，每列至少 5 个观测 |
| `shap_summary` | 预计算 SHAP 汇总图 | Feature；SHAP value；Feature value |

## 各路线的输入与限制

这里给出注册清单中的输入要求；遇到歧义时读取 [完整数据合同](editaplot/data-contracts.md) 的对应段落。

### xps — XPS

通用 XPS 扫描与拟合数据自动识别、预览和 Origin 可编辑绘图

- 必需：结合能或动能列；至少一个强度/计数列
- 可选：背景；拟合包络；任意数量 component peaks；残差
- 布局：宽表
- [合成示例](../vendor/editaplot/runtime/templates/xps/../xps_adaptive/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/xps/runner.py)。
- 不会修改原始文件或补造峰列
- 能量轴方向和 Y 轴规则由识别到的 profile 决定

### eis — EIS 阻抗谱

自动识别 Nyquist 或 Bode 列角色并生成可编辑 Origin 图

- 必需：Nyquist：Z 实部 + Z 虚部；或 Bode：频率 + 阻抗模/相位
- 可选：多个样品系列
- 布局：宽表
- [合成示例](../vendor/editaplot/runtime/templates/eis/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/eis/runner.py)。
- 不会自动进行等效电路拟合
- 频率对数轴要求全部频率为正

### trajectory3d — 三维多条件 Nyquist 轨迹

从具有科学含义的 X/Y/Z/Series 长表生成可编辑的 Origin 三维多条件阻抗轨迹

- 必需：Zreal（数值）；真实第三变量与单位（数值）；-Zimag（数值）；Series（组名）
- 可选：无
- 布局：长表；每行一个 XYZ 点；Series 标识 1–6 条轨迹
- [合成示例](../vendor/editaplot/runtime/templates/trajectory3d/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/trajectory3d/runner.py)。
- 第三轴不能是装饰性序号；列名必须同时给出科学含义和单位。
- 不拟合、不计算等效电路、不添加电阻标注，也不修改源文件。
- 角色证据不完整时必须人工确认；缺少第三轴单位时拒绝绘图。

### density_ridgeline3d — 三维双轮廓密度曲线与基线焦点

用同一行的实线/虚线预计算密度比较 2–6 个真实有序条件，并在基线标出用户提供的焦点位置

- 必需：Condition ID（条件标识）；Condition Position（带单位数值）；Density X（带单位数值）；Solid Density（非负数值）；Dashed Density（非负数值）；Focal X（每组仅一行非空）
- 可选：无
- 布局：mixed-wide；每行一个横轴位置；同一行同时提供 Solid Density 与 Dashed Density
- [合成示例](../vendor/editaplot/runtime/templates/density_ridgeline3d/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/density_ridgeline3d/runner.py)。
- Density X 和 Condition Position 的表头必须同时写明科学含义与单位；条件轴必须是真实实验变量，不能使用装饰性序号。
- Year、年份、年度可作为日历条件轴，单位按 year 处理；其他条件轴仍需在表头明确单位。
- 六个冻结角色键为 condition_id、condition_position、density_x、density_solid、density_dashed、focal_x。
- 仅支持 2–6 个 Condition ID；每个 ID 必须唯一对应一个 Condition Position，每组至少 5 个完整横轴点。
- Density X 在每组源顺序中严格单调且所有组方向一致；Condition Position 按 Condition ID 首次出现顺序严格递增。
- Focal X 在每组必须恰好一行非空并落在该组 Density X 范围内；它只是在 Z=0 基线上的定位点，不代表软件计算的峰值或交点。
- Threshold X、阈值点、峰值或交点列不自动等同于 Focal X，必须先由用户确认其基线定位语义。
- 本路线已通过真实 Origin OPJU、PNG/PDF/TIF、对象反读与人工视觉验收；仍不得把焦点解释为软件计算结果。

### cv — CV 循环伏安曲线

保留原始扫描顺序的通用 CV 单循环或多循环绘图

- 必需：电位或电压列；一个或多个电流系列
- 可选：无
- 布局：宽表
- [合成示例](../vendor/editaplot/runtime/templates/cv/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/cv/runner.py)。
- 严格保留原始扫描顺序
- 不自动做峰积分或基线处理

### lsv — LSV 线性扫描伏安曲线

通用电位—电流或电流密度 LSV 绘图

- 必需：电位或电压列；一个或多个电流系列
- 可选：无
- 布局：宽表
- [合成示例](../vendor/editaplot/runtime/templates/lsv/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/lsv/runner.py)。
- 不自动计算 onset、Tafel slope 或极限电流

### xas — XAS 吸收谱

不自动归一化或拟合的通用 XAS 能量—吸收信号绘图

- 必需：能量列；一个或多个吸收信号列
- 可选：无
- 布局：宽表
- [合成示例](../vendor/editaplot/runtime/templates/xas/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/xas/runner.py)。
- 不自动归一化、扣背景、求导或拟合

### pl — PL 与 TRPL 光致发光谱

绘制稳态、多条件 PL 发射光谱或用户预处理的 TRPL 衰减与拟合曲线

- 必需：Wavelength 或 Time；一个或多个 PL 数值系列
- 可选：与测量列同名并以 Fit/拟合结尾的用户拟合列
- 布局：宽表；稳态多条件系列按源列顺序保留
- [合成示例](../vendor/editaplot/runtime/templates/pl/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/pl/runner.py)。
- 不自动归一化、平滑、拟合或计算寿命。
- TRPL 对数轴要求所有显示值为正。
- 拟合列按去掉 Fit/拟合后的名称与测量列配对。
- 波长加多条强度列但没有明确 PL/发射语义时，必须让用户确认，不能与 UV–Vis 自动混淆。
- 温度、时间或处理条件的顺序来自源列顺序，不从数值大小重新排序。

### xps_compare — XPS 多谱线对比

绘制共享结合能轴上的两条或更多独立实测 XPS 谱线，默认直接叠加且不把拟合列误当作样品谱线

- 必需：Binding Energy/结合能列；至少两个独立实测 Intensity/Counts 数值系列
- 可选：无
- 布局：宽表；第一条物理 X 列加两条或更多独立实测谱线
- [合成示例](../vendor/editaplot/runtime/templates/xps_compare/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/xps_compare/runner.py)。
- 默认直接叠加源谱线；只有用户明确确认后才能采用纵向显示偏移。
- 结合能按 XPS 惯例由高到低显示，但源表数值和顺序保持不变。
- Background、Envelope/Fit、Residual、Component/Peak 等列属于拟合语义，不由本模板自动当作独立实测谱线。
- 不自动归一化、扣背景、平滑、拟合、分峰、识别谱区或指认化学态。

### uv_vis — UV–Vis 吸收/透射与 Tauc 插图

绘制单样品或多样品 UV–Vis 吸收/透射光谱，并在输入完整时增加用户预计算的可编辑 Tauc 插图

- 必需：Wavelength；一个或多个 Absorbance/Transmittance 系列
- 可选：Photon energy；Tauc value；Tauc fit；Band gap
- 布局：宽表；多光谱系列按源列顺序保留；可选插图列允许列尾空白
- [合成示例](../vendor/editaplot/runtime/templates/uv_vis/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/uv_vis/runner.py)。
- 不从波长静默计算光子能量，不选择 Tauc 指数，不拟合，不求 Eg。
- 只有 Photon energy 与 Tauc value 同时存在时才创建插图。
- Band gap 若存在必须为一个重复常数或单个非空显式值。
- 不嵌入参考论文的样品照片、箭头或文字；这些元素可在后期排版中添加。
- 波长加未知数值系列但没有 Absorbance/Transmittance 语义时，必须让用户确认。

### ftir — FTIR / IR 红外光谱

绘制单样品、多样品或有序条件下的 FTIR / IR 吸收与透射光谱，不自动平滑、校正或指认峰位

- 必需：Wavenumber/波数列；一个或多个 Absorbance/Transmittance 数值系列
- 可选：无
- 布局：宽表
- [合成示例](../vendor/editaplot/runtime/templates/ftir/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/ftir/runner.py)。
- 波数按红外光谱惯例由大到小显示，源表顺序和数值保持不变。
- 不自动做基线校正、平滑、归一化、峰识别、峰指认或峰面积计算。
- 多谱线默认直接叠加；只有用户明确确认后才能增加显示偏移。

### nmr — NMR 核磁共振谱

绘制一个或多个用户预处理完成的 NMR 强度谱，不自动做相位、基线、积分或峰指认

- 必需：Chemical Shift/化学位移列；一个或多个 Intensity/强度数值系列
- 可选：无
- 布局：宽表
- [合成示例](../vendor/editaplot/runtime/templates/nmr/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/nmr/runner.py)。
- 化学位移按 NMR 惯例由大到小显示，核种只在源表明确给出时保留。
- 不自动做相位校正、基线校正、积分、峰识别、峰归属或定量。
- 多谱线默认直接叠加；只有用户明确确认后才能增加显示偏移。

### dsc — DSC 差示扫描量热

绘制一个或多个用户提供的 DSC 热流曲线，不自动翻转热流方向或识别热转变

- 必需：Temperature/温度列；一个或多个 Heat Flow/热流数值系列
- 可选：无
- 布局：宽表
- [合成示例](../vendor/editaplot/runtime/templates/dsc/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/dsc/runner.py)。
- 吸热或放热向上/向下的约定必须由用户确认，软件不根据曲线形状猜测或静默翻转。
- 不自动识别、拟合或标注 Tg、Tm、Tc、焓变、起始温度或峰温。
- 多曲线默认直接叠加；只有用户明确确认后才能增加显示偏移。

### xrd — XRD 衍射图谱

自动识别普通 XRD 与 GSAS-II 精修数据，区分实测、计算、背景、差值、物相刻线和非绘图控制列

- 必需：普通图谱：2θ 衍射角列 + 一个或多个强度列；精修图：X/2θ + Obs/实测 + Calc/计算
- 可选：Bkg/背景；Diff/差值；具有明确物相名称的 Phase 刻线列；weight、Q、Used、diff/sigma、Axis-limits 等辅助或控制列
- 布局：普通 XRD 宽表；GSAS-II Powder CSV；GSAS-II Publication CSV
- [合成示例](../vendor/editaplot/runtime/templates/xrd/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/xrd/runner.py)。
- 不根据曲线形状自动添加材料峰位、物相名称或精修结论
- 未识别的数值列必须先确认用途，默认不会画成曲线
- GSAS-II Publication 的 Diff 保留其原始显示偏移，不会再次偏移
- 辅助和控制列保留在映射与 Origin 工作簿中，但不会误画成数据系列
- 原始 CSV/TXT/XLS/XLSX 始终只读

### bar — 柱状图（可选误差）

通用分组柱状图，支持 SD、SE、SEM 或自定义误差列

- 必需：类别列；一个或多个数值系列
- 可选：与系列同名的 SD/SE/SEM/误差列
- 布局：宽表
- [合成示例](../vendor/editaplot/runtime/templates/bar/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/bar/runner.py)。
- 不从重复观测自动计算均值或误差。
- 误差必须非负，且其统计含义会显示在识别摘要中。

### horizontal_bar — 横向分组条形图

适合类别名称较长的一个或多个数值系列比较

- 必需：一列类别；一个或多个数值系列
- 可选：与系列同名的 SD/SE/SEM/误差列
- 布局：宽表
- [合成示例](../vendor/editaplot/runtime/templates/horizontal_bar/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/horizontal_bar/runner.py)。
- 系列数会自动影响组内宽度、同族颜色与图例。
- 不从重复观测自动计算均值或误差。

### stacked_bar — 堆叠柱状图

比较各类别的绝对总量及其多个非负组成部分

- 必需：一列类别；至少两个非负数值组成列
- 可选：一个显式总量 SD/SE/SEM/误差列
- 布局：宽表
- [合成示例](../vendor/editaplot/runtime/templates/stacked_bar/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/stacked_bar/runner.py)。
- 每行的柱高是原始组成值之和。
- 不接受负值，也不把绝对量自动换算为百分比。
- 误差棒仅在源文件明确提供总量误差时显示，不合成分量误差。

### percent_stacked_bar — 百分比堆叠柱状图

将每个类别的非负组成值仅在显示层归一化为 100%

- 必需：一列类别；至少两个非负数值组成列
- 可选：无
- 布局：宽表
- [合成示例](../vendor/editaplot/runtime/templates/percent_stacked_bar/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/percent_stacked_bar/runner.py)。
- 每行总和必须大于零。
- 百分比换算只发生在预览和 Origin helper columns，源文件保持不变。

### pie — 二维饼图

用于少量类别构成比例的平面二维饼图

- 必需：一列类别；恰好一个非负数值列
- 可选：无
- 布局：两列长表
- [合成示例](../vendor/editaplot/runtime/templates/pie/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/pie/runner.py)。
- 推荐不超过 8 个扇区；过多类别应优先选择条形图。
- 只使用二维饼图，不生成 3D 爆炸效果。

### sankey — 桑基流向图

用来源、目标和正权重展示节点之间的定量流向

- 必需：来源 Source；目标 Target；正数权重 Value
- 可选：无
- 布局：三列长表
- [合成示例](../vendor/editaplot/runtime/templates/sankey/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/sankey/runner.py)。
- 每行是一条有向连接，权重必须大于零。
- 当前不接受自连接；高密度网络会提示人工检查标签可读性。

### trend — 多系列趋势折线图

按连续自变量比较一个或多个趋势系列，自动适配画幅和系列密度

- 必需：连续 X 列；一个或多个数值系列
- 可选：无
- 布局：宽表
- [合成示例](../vendor/editaplot/runtime/templates/trend/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/trend/runner.py)。
- 行顺序保持源文件顺序，不擅自平滑、补点或计算统计量。
- 系列过多时会提示人工确认，画幅会随系列数自动扩展。

### radar — 多指标雷达图

比较两个或多个对象在至少三个非负指标上的轮廓

- 必需：指标列；至少两个非负数值系列
- 可选：无
- 布局：宽表；每行一个指标，每个数值列一个对象
- [合成示例](../vendor/editaplot/runtime/templates/radar/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/radar/runner.py)。
- 至少需要三个指标和两个对象；不接受负值。
- 建议先把不同单位的指标规范化到可比较尺度，程序不会擅自归一化原数据。

### circular_network — 环形有向加权网络图

用环形节点、方向箭头、权重线宽和正负语义比较一个或多个面板中的有向关系

- 必需：Panel；Source；Target；Weight
- 可选：Sign；SourceGroup；TargetGroup；EdgeLabel
- 布局：有向边长表；每行一条边；支持 1–4 个面板
- [合成示例](../vendor/editaplot/runtime/templates/circular_network/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/circular_network/runner.py)。
- Weight 必须是大于零的有限数；正负关系由可选 Sign 单独提供，不能把负权重当作线宽。
- 不接受自连接或同一面板内重复的 Source→Target；节点组在所有行中必须保持一致。
- 最多支持 4 个节点组；单面板超过 12 条边时保留 EdgeLabel 源文字但默认不在图中显示。
- 本路线已经通过 Origin 2024b 的 OPJU、PNG、PDF、TIF、对象反读和人工视觉验收。

### heatmap — 自适应矩阵热力图

将类别 × 系列宽表转换为可编辑 Origin 矩阵热力图；小矩阵标注数值，高密度矩阵稀疏显示标签

- 必需：一列行类别；至少两个数值系列
- 可选：无
- 布局：宽表；行是类别，数值列是热力图列
- [合成示例](../vendor/editaplot/runtime/templates/heatmap/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/heatmap/runner.py)。
- 小矩阵自动显示单元格数值；高密度矩阵关闭单元格文字以避免重叠。
- 同时包含正负值时自动使用以零为中心的发散色阶；源表不被改写。

### scatter — 通用散点图

一个数值 X 与一个或多个观测系列的通用散点图

- 必需：一个数值 X 列；一个或多个数值 Y 列
- 可选：无
- 布局：宽表
- [合成示例](../vendor/editaplot/runtime/templates/scatter/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/scatter/runner.py)。
- 不自动拟合回归线、删除离群点或计算相关系数。
- 点数增加时只调整显示密度，正式 Origin 仍使用全部数据。

### line_error — 带误差折线图

自动配对 SD、SE、SEM 或自定义误差列的折线图

- 必需：一个数值 X 列；一个或多个中心值列；每个中心值的配对误差列
- 可选：无
- 布局：宽表
- [合成示例](../vendor/editaplot/runtime/templates/line_error/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/line_error/runner.py)。
- 不从重复观测计算均值或误差。
- 自定义误差必须由用户确认统计含义。

### grouped_box — 分组箱线与原始点图

从 Category | Group 宽表原始观测生成分组箱体、原始点和样本量标签

- 必需：至少四个数值列，列名写成 Category | Group
- 可选：无
- 布局：宽表；每列是一组原始观测，允许列尾缺失
- [合成示例](../vendor/editaplot/runtime/templates/grouped_box/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/grouped_box/runner.py)。
- 每列至少五个有限观测。
- Origin 从原始值计算箱体统计并叠加全部原始点；不会修改源表。
- n 由非空观测数计数；不静默计算显著性或添加星号。

### raw_summary — 原始点汇总图

多组原始观测点与中心线的通用证据图

- 必需：一个或多个原始数值列
- 可选：无
- 布局：宽表，每个数值列代表一组
- [合成示例](../vendor/editaplot/runtime/templates/raw_summary/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/raw_summary/runner.py)。
- 不自动删除异常值，不修改原始观测。
- 中心线由 Origin 官方统计图对象计算并保持可编辑。

### violin — 小提琴分布图

使用原始观测展示多个组的分布形状和四分位结构

- 必需：一个或多个原始数值列，每列至少 5 个观测
- 可选：无
- 布局：宽表，每个数值列代表一组
- [合成示例](../vendor/editaplot/runtime/templates/violin/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/violin/runner.py)。
- 密度由 Origin 官方 Violin/Box 统计图对象生成。
- 不把小样本伪装成稳定分布；样本太少时改用原始点图。

### histogram — 直方分布图

基于原始连续数值的可编辑 Origin 直方分布图

- 必需：一个或多个原始数值列，每列至少 5 个观测
- 可选：无
- 布局：宽表
- [合成示例](../vendor/editaplot/runtime/templates/histogram/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/histogram/runner.py)。
- bin 规则冻结到计划和 Origin 反读报告，不静默拟合分布曲线。
- 多列叠加容易遮挡，缺少明确意图时需要人工确认。

### forest — 森林效应图

使用显式点估计和区间上下限绘制可编辑森林图

- 必需：Label；Estimate；CI Low；CI High
- 可选：Reference，非空值必须相同
- 布局：每行一个对象
- [合成示例](../vendor/editaplot/runtime/templates/forest/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/forest/runner.py)。
- 软件不计算 CI；上下限必须由输入明确提供。
- Reference 缺失时不自动假设零或一。

### bubble — 气泡关系图

以 X、Y 和显式正值 Size 同时表达位置与规模

- 必需：一个数值 X；一个数值 Y；一个正值 Size
- 可选：无
- 布局：X/Y/Size 三列
- [合成示例](../vendor/editaplot/runtime/templates/bubble/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/bubble/runner.py)。
- Size 必须为正；缩放规则和原始范围写入计划与反读报告。
- 不把颜色同时编码为第四变量，避免难以解释的默认多重编码。

### diagnostic_curve — 医学诊断 ROC / PR 曲线

使用用户提供的经验坐标绘制 ROC 或 Precision-Recall 曲线

- 必需：ROC：FPR + 一个或多个 TPR；PR：Recall + 一个或多个 Precision
- 可选：PR 模式需要一列恒定 Prevalence；AUC/AUPRC/CI 只作为用户提供的说明
- 布局：宽表，每个模型一列
- [合成示例](../vendor/editaplot/runtime/templates/diagnostic_curve/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/diagnostic_curve/runner.py)。
- 不从标签和预测分数静默计算曲线、AUC、CI 或 DeLong 检验。
- ROC 使用 0–1 方形数据区和机会参考线；PR 使用显式患病率基线。
- 示例库同时提供 ROC 与 PR 两种规范文件。

### calibration_curve — 医学模型校准曲线

使用用户提供的分箱预测概率、观察比例和样本数绘制校准证据图

- 必需：Predicted probability；Observed fraction；Bin count
- 可选：无
- 布局：一行一个预计算概率箱
- [合成示例](../vendor/editaplot/runtime/templates/calibration_curve/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/calibration_curve/runner.py)。
- 所有概率必须位于 0–1，Bin count 必须非负且至少一个大于 0。
- 不计算校准斜率、截距、Brier score、置信区间或平滑曲线。
- 底部分布条是工作簿 helper column，仅用于显示，原始数据保持不变。

### confusion_matrix — 医学分类混淆矩阵

绘制保留实际类与预测类语义的可编辑 Origin 混淆矩阵

- 必需：第一列 Actual class；后续每列一个 Predicted class 的计数或已给比例
- 可选：无
- 布局：宽矩阵
- [合成示例](../vendor/editaplot/runtime/templates/confusion_matrix/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/confusion_matrix/runner.py)。
- 不静默进行行归一化、列归一化或百分比转换。
- Actual class 保持为行，Predicted class 保持为列。

### bland_altman — Bland–Altman 一致性图

使用显式配对均值、差值、偏倚和一致性限绘制医学测量一致性图

- 必需：Mean；Difference；Bias；Lower LoA；Upper LoA
- 可选：无
- 布局：每行一个明确配对病例，三条参考值列重复同一个输入值
- [合成示例](../vendor/editaplot/runtime/templates/bland_altman/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/bland_altman/runner.py)。
- V1 不从 Method A/Method B 静默计算统计量。
- 不根据行号猜配对，不计算比例偏倚或 LoA 的置信区间。

### decision_curve — 医学决策曲线分析

使用用户提供的阈值概率和净获益序列绘制决策曲线

- 必需：Threshold；一个或多个模型 Net benefit；Treat all；Treat none
- 可选：无
- 布局：宽表，每条曲线一列
- [合成示例](../vendor/editaplot/runtime/templates/decision_curve/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/decision_curve/runner.py)。
- 阈值必须位于 0–1。
- 不从标签、预测概率或患病率静默计算净获益。
- Treat all 与 Treat none 使用中性灰，模型使用同一医学蓝青色族。

### paired_trajectory — 配对与纵向轨迹图

用宽表中的稳定受试者列绘制配对或纵向轨迹

- 必需：一个数值 Time/Visit/Condition index；每个 Subject 一列数值
- 可选：无
- 布局：宽表；列名是稳定 Subject ID
- [合成示例](../vendor/editaplot/runtime/templates/paired_trajectory/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/paired_trajectory/runner.py)。
- 不根据行号猜 Subject，不插值，不补不存在的时间点。
- V1 使用数值或有序索引作为 X；文本长表将在后续 profile 支持。

### raincloud — Raincloud 原始分布图

使用半小提琴、全部原始点与均值 ± 1 SD 展示医学 AI 分布

- 必需：一个或多个原始数值列，每列至少 5 个观测
- 可选：无
- 布局：宽表，每个数值列代表一组
- [合成示例](../vendor/editaplot/runtime/templates/raincloud/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/raincloud/runner.py)。
- Origin 使用已隔离验证的 Box_HalfViolin 官方主题。
- 密度、原始点和均值 ± 1 SD 都是显示对象；源 CSV/XLSX 保持不变。
- 不静默删除异常值，也不把小样本伪装成稳定密度。

### shap_summary — 预计算 SHAP 汇总图

可编辑展示外部预计算的 SHAP 蜂群、Mean |SHAP| 与可选分组贡献

- 必需：Feature；SHAP value；Feature value
- 可选：Sample ID；Feature Order；Mean absolute SHAP；Feature Group；Group contribution (%)
- 布局：长表，每行是一个样本-特征观测
- [合成示例](../vendor/editaplot/runtime/templates/shap_summary/example_standard.csv)；[执行器](../vendor/editaplot/runtime/templates/shap_summary/runner.py)。
- 每个特征至少 3 个完整观测，至少 2 个不同特征。
- Feature value 仅在每个特征内部归一化为颜色；原 SHAP 横坐标保持不变。
- 未提供 Mean absolute SHAP 时，可从用户给出的逐行 SHAP 值计算 mean(abs(SHAP))，但必须在元素清单中明确并由用户确认。
- 提供 Feature Group 后，可生成分组贡献面板；未提供百分比时，按组汇总 Mean |SHAP| 后归一到 100%，同样需要确认。
- 不训练模型、不运行 SHAP、不补造模型输出、不静默重排特征。
