# Geoscience & Petroleum Research Resources

This repository collects useful GitHub projects related to geology, petroleum geology, scientific analysis, and plotting.

## 在 Codex 中直接调用

本仓库提供可执行的技能 **`geoscience-github`**：构造地质赤平投影、五道测井曲线、CSV 数据分析、能谱伽马教学示例和批量绘图。技能位于 [`.agents/skills/geoscience-github`](.agents/skills/geoscience-github)，在此仓库内工作时可直接发现，也可安装为个人技能。

首次安装需 Python 3.10–3.12 和网络：

```powershell
git clone https://github.com/ganshuai123/-.git geoscience-tools
cd geoscience-tools
python scripts/install_local.py
python .agents/skills/geoscience-github/scripts/run.py doctor
```

随后在 Codex 输入：

```text
$geoscience-github 运行完整示例，把结果保存到 output/geoscience-demo
$geoscience-github 用我的测井 CSV 绘制五道曲线，并保留单位和运行记录
$geoscience-github 根据我的倾向、倾角 CSV 绘制赤平投影
```

也可直接运行：

```powershell
python .agents/skills/geoscience-github/scripts/run.py demo --out output/geoscience-demo
```

依赖安装在用户缓存中的独立虚拟环境；上游代码按固定提交下载并验证所用文件的 SHA-256。图件同时输出 PNG 和 SVG，每次运行生成 `run.json`。已有非空输出目录会被保留。

输入格式、单位、支持范围及命令见[使用说明](.agents/skills/geoscience-github/references/commands.md)。`geocouche` 调用其计算和绘图核心；原 QGIS 插件界面需 QGIS 环境。`Geo-Plot-` 当前没有程序源码，本仓库的批量绘图为独立补写。石油地质仓库已封装能谱伽马示例，其余笔记本需要按任务另行适配。

## Recommended repositories

### 1. geocouche
- URL: https://github.com/mauroalberti/geocouche
- Description: Structural geological plotting and analysis, including stereonets and geologic orientation data.
- Use case: Structural geology, fault/joint analysis, stereographic plots.

### 2. Data-Analysis-Using-Python-OCNG_669_Geosciences
- URL: https://github.com/kaushikmanikonda/Data-Analysis-Using-Python-OCNG_669_Geosciences
- Description: Python for geosciences with NumPy, Matplotlib, Pandas, and data visualization.
- Use case: Geoscience data analysis and scientific plotting.

### 3. DS_python-well-logs-plot
- URL: https://github.com/taiwofawumi/DS_python-well-logs-plot
- Description: Python functions for plotting geological well logs.
- Use case: Well log visualization and petroleum geology plotting.

### 4. Pertoleum-Geology-Projects
- URL: https://github.com/aleksandrbogdanovmsu/Pertoleum-Geology-Projects
- Description: Petroleum geology projects focused on well log analysis and petrophysical workflows in Python.
- Use case: Petroleum geology analysis and research projects.

### 5. Geo-Plot-
- URL: https://github.com/aysha-anjala/Geo-Plot-
- Description: Simple plotting tool for geo-related data with a Python GUI workflow.
- Use case: Quick geological data plotting and visualization.

## Notes

These repositories are useful for:
- scientific plotting
- geology and petroleum geology analysis
- well log visualization
- structural geology research
- Python-based geoscience workflows

## Quick selection for research

If you need a short list to start with:
- Structural geology: geocouche
- Data analysis / scientific plotting: Data-Analysis-Using-Python-OCNG_669_Geosciences
- Well logs: DS_python-well-logs-plot
- Petroleum geology research: Pertoleum-Geology-Projects
- Fast plotting: Geo-Plot-
