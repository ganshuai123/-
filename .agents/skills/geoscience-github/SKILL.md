---
name: geoscience-github
description: Run the user's GitHub geoscience tools for stereonets, five-track well logs, CSV analysis, batch scientific plots, and supplied petrophysics examples. Use for requests mentioning geocouche, OCNG 669, DS well logs, Pertoleum Geology Projects, or Geo-Plot.
---

# Geoscience GitHub tools

Run the portable entry point `scripts/run.py` in this skill directory with a local Python 3.10–3.12 interpreter. It provisions an isolated environment outside the repository on first use; subsequent calls reuse it. On this Windows host, the bundled interpreter can be located under `~/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`. Do not install dependencies into that bundled environment.

Start with `python <skill>/scripts/run.py doctor` if runtime status is uncertain. Read [the command reference](references/commands.md) for inputs, supported tasks, and examples. Use `--help` for exact arguments. Resolve the skill's actual directory; do not assume the current working directory is the skill directory.

Choose the matching command:

- `stereonet`: dip-direction/dip or right-hand-rule strike/dip CSV, using geocouche's bundled APSG computation and plotting core, with recorded compatibility patches. Its QGIS GUI is outside this command.
- `well-log`: plot a real CSV with the original upstream `plot_well` function; require the documented column mapping and user-confirmed units. Its caliper panel is normalized, not a physical borehole-diameter axis.
- `analyze`: numerical CSV summaries, correlations with pair counts, and selected-variable plots. This is new adapter code supporting the OCNG tutorial workflow.
- `petroleum`: run the upstream spectral-gamma notebook with bundled or explicitly supplied calibration/sample files. Export fitted component weights; do not describe them as calibrated U/Th/K concentrations or radiogenic heat production.
- `batch-plot`: independently implemented CSV batch plots. Geo-Plot's original repository contains no executable source; never attribute this implementation to that author.
- `demo`: reproducible synthetic examples plus original upstream teaching examples. Keep demo labels and distinguish these from the user's research data.

Write outputs into the user's requested directory, or a new task-specific output directory. Commands require an empty destination to preserve prior results. Link or preview resulting PNG/SVG files and report the generated `run.json` provenance. Do not silently convert units, invent missing inputs, or present successful execution as validation of a scientific interpretation.

For unsupported upstream notebooks, read their source and data requirements before adapting them. The ready-to-run petrophysics command covers the spectral-gamma example; it does not claim the entire upstream repository is automated. Forecasting, tomography, and other notebooks need separate adaptation and validation.
