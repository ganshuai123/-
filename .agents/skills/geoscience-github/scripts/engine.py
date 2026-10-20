"""Headless adapters for the five geoscience workflows."""
from __future__ import annotations

import argparse
import ast
import contextlib
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import traceback

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd

from sources import CACHE, LOCK, file_hash, provenance, source

plt.rcParams.update({"svg.fonttype": "none", "figure.max_open_warning": 40})
available_fonts = {font.name for font in font_manager.fontManager.ttflist}
plt.rcParams["font.family"] = [name for name in ("DejaVu Sans", "Microsoft YaHei", "SimHei", "Noto Sans CJK SC") if name in available_fonts]
SEED = 20261020
SPECTRAL = "Spectral Gamma-ray Logging/Petrophysics task a - Spectral gamma log.ipynb"


def save_figure(fig, output: Path, name: str) -> None:
    for extension in ("png", "svg"):
        fig.savefig(output / f"{name}.{extension}", dpi=160, bbox_inches="tight")


def numeric(frame: pd.DataFrame, columns: list[str], missing: bool = False) -> pd.DataFrame:
    absent = set(columns) - set(frame.columns)
    if absent:
        raise ValueError(f"Missing CSV columns: {sorted(absent)}")
    values = frame[columns].apply(pd.to_numeric, errors="raise")
    if np.isinf(values.to_numpy(dtype=float)).any():
        raise ValueError("Infinite numeric values are unsupported")
    if not missing and values.isna().any().any():
        raise ValueError("Required numeric values contain missing data")
    return values


def units(args) -> dict:
    if not args.units_json:
        return {}
    result = json.loads(Path(args.units_json).read_text(encoding="utf-8-sig"))
    if not isinstance(result, dict) or any(not isinstance(k, str) or not isinstance(v, str) or not v.strip() for k, v in result.items()):
        raise ValueError("Units JSON must map column names to nonempty unit strings")
    return result


def read_csv(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path, encoding="utf-8-sig")
    if frame.empty:
        raise ValueError("CSV has no data rows")
    return frame


def patched_apsg():
    upstream = source("geocouche")
    target = CACHE / "patched" / ("apsg-" + LOCK["geocouche"]["commit"][:12] + "-v1")
    patches = ["Matplotlib warning class rename", "canvas window-title moved to manager", "NumPy float alias replaced by builtin float"]
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(upstream / "apsg", target / "apsg")
        plotting = target / "apsg" / "plotting.py"
        text = plotting.read_text(encoding="utf-8")
        text = text.replace("import matplotlib.cbook as mcb", "import matplotlib.cbook as mcb\nfrom matplotlib import MatplotlibDeprecationWarning")
        text = text.replace("mcb.mplDeprecation", "MatplotlibDeprecationWarning")
        text = text.replace("self.fig.canvas.set_window_title(", "self.fig.canvas.manager.set_window_title(")
        plotting.write_text(text, encoding="utf-8")
        core = target / "apsg" / "core.py"
        core.write_text(core.read_text(encoding="utf-8").replace("dtype=np.float)", "dtype=float)"), encoding="utf-8")
    sys.path.insert(0, str(target))
    import apsg
    apsg.core.settings["notation"] = "dd"
    return apsg, patches


def stereonet(args, output: Path) -> dict:
    frame = numeric(read_csv(args.csv), [args.azimuth, args.dip])
    azimuth = frame[args.azimuth].to_numpy(float)
    dip = frame[args.dip].to_numpy(float)
    if (azimuth < 0).any() or (azimuth > 360).any() or (dip < 0).any() or (dip > 90).any():
        raise ValueError("Azimuth must be 0–360 degrees and dip 0–90 degrees")
    if args.orientation == "rhr-strike":
        azimuth = (azimuth + 90) % 360
    apsg, patches = patched_apsg()
    net = apsg.StereoNet(figsize=(7, 7), grid=True, title=args.title)
    normals = []
    for direction, inclination in zip(azimuth, dip):
        foliation = apsg.Fol(float(direction), float(inclination))
        normals.append(np.asarray(foliation))
        net.plane(foliation, color="#2e6c91", lw=0.8, alpha=0.65)
        net.pole(foliation, color="#a53632", marker="o", ms=3)
    save_figure(net.fig, output, "stereonet")
    pd.DataFrame(normals, columns=["north", "east", "down"]).to_csv(output / "unit_plane_normals.csv", index=False)
    pd.DataFrame({"dip_direction_deg": azimuth % 360, "dip_deg": dip}).to_csv(output / "orientations_used.csv", index=False)
    return {"upstream": provenance("geocouche"), "compatibility_patches": patches,
            "input": str(Path(args.csv).resolve()), "input_sha256": file_hash(Path(args.csv)), "rows": len(frame),
            "projection": "Schmidt equal-area, lower hemisphere", "input_convention": args.orientation,
            "normal_coordinates": "north, east, down; axial plane normals"}


def well_log(args, output: Path) -> dict:
    frame = read_csv(args.csv)
    columns = ["depth", "cal", "gam", "res", "den", "neu"]
    if "well_name" not in frame:
        raise ValueError("CSV needs a well_name column")
    if args.well not in set(frame.well_name.astype(str)):
        raise ValueError(f"Well not present: {args.well}")
    frame = frame[frame.well_name.astype(str) == args.well].copy()
    frame["well_name"] = frame.well_name.astype(str)
    frame[columns] = numeric(frame, columns)
    frame = frame.sort_values("depth")
    if len(frame) < 2 or frame.depth.duplicated().any():
        raise ValueError("Need at least two distinct depth samples for the selected well")
    if (frame.res <= 0).any() or (frame.cal <= 0).any():
        raise ValueError("Resistivity and caliper must be positive")
    declared = units(args)
    if set(columns) - set(declared):
        raise ValueError("Supply --units-json declaring depth, cal, gam, res, den and neu units; no units are inferred")
    expected_units = {"gam": {"api"}, "res": {"ohm m", "ohm·m"}, "den": {"g/cm3", "g/cm^3"}}
    if any(declared[name].lower() not in allowed for name, allowed in expected_units.items()):
        raise ValueError("Upstream fixed visual fills require gam in API, res in ohm m, den in g/cm3. Convert other units explicitly first.")
    notebook = source("well-logs") / "Plot Well Logs_v1.ipynb"
    cells = json.loads(notebook.read_text(encoding="utf-8"))["cells"]
    functions = [node for cell in cells if cell["cell_type"] == "code"
                 for node in ast.parse("".join(cell["source"]).replace("%matplotlib inline", "")).body
                 if isinstance(node, ast.FunctionDef) and node.name == "plot_well"]
    if len(functions) != 1:
        raise ValueError("Upstream plot_well definition changed")
    namespace = {"np": np, "pd": pd, "plt": plt}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(notebook), "exec"), namespace)
    namespace["plot_well"](frame, args.well)
    fig = plt.gcf()
    for axis, name in zip(fig.axes[:5], ["cal", "gam", "res", "den", "neu"]):
        axis.set_xlabel("Caliper (normalized)" if name == "cal" else f"{name} [{declared[name]}]")
    fig.axes[0].set_title("")
    fig.texts[1].set_text(f"Depth [{declared['depth']}]")
    save_figure(fig, output, "well_logs")
    frame.to_csv(output / "data_used.csv", index=False)
    return {"upstream": provenance("well-logs"), "function": "plot_well", "input_sha256": file_hash(Path(args.csv)),
            "well": args.well, "rows": len(frame), "units": declared,
            "notes": ["Upstream caliper panel is normalized", "Upstream fills use fixed visual cutoffs; they are not reservoir classifications"]}


def analyze(args, output: Path) -> dict:
    frame = read_csv(args.csv)
    ys = [name.strip() for name in args.ys.split(',') if name.strip()]
    if not ys or args.x in ys or len(set(ys)) != len(ys):
        raise ValueError("Choose distinct y columns, different from x")
    values = numeric(frame, [args.x, *ys], missing=True)
    declared = units(args)
    summary = values.describe().T
    summary["missing"] = values.isna().sum()
    summary["unit"] = [declared.get(name, "unspecified") for name in summary.index]
    summary.to_csv(output / "summary.csv", encoding="utf-8-sig")
    values.corr(min_periods=2).to_csv(output / "pearson_correlations.csv")
    observed = values.notna().astype(int)
    (observed.T @ observed).to_csv(output / "correlation_pair_counts.csv")
    fig, axes = plt.subplots(len(ys), 1, figsize=(9, 3.2 * len(ys)), squeeze=False)
    valid_counts = {}
    for ax, column in zip(axes[:, 0], ys):
        pairs = values[[args.x, column]].dropna().sort_values(args.x)
        if len(pairs) < 2:
            raise ValueError(f"Fewer than two complete x/y pairs for {column}")
        valid_counts[column] = len(pairs)
        ax.plot(pairs[args.x], pairs[column], ".-", color="#2e6c91", lw=0.8, ms=3)
        ax.set(xlabel=f"{args.x} [{declared.get(args.x, 'unit unspecified')}]",
               ylabel=f"{column} [{declared.get(column, 'unit unspecified')}]")
        ax.grid(alpha=0.25)
    fig.suptitle(args.title)
    fig.tight_layout()
    save_figure(fig, output, "analysis")
    return {"implementation": "New CSV analysis adapter for the OCNG tutorial workflow", "reference": provenance("ocng"),
            "input": str(Path(args.csv).resolve()), "input_sha256": file_hash(Path(args.csv)), "rows": len(frame),
            "units": declared, "plotted_complete_pairs": valid_counts, "missing_policy": "Pairwise complete observations; no imputation"}


class RebaseInputs(ast.NodeTransformer):
    def __init__(self, directory: Path):
        self.directory = directory
        self.changes = {}

    def visit_Constant(self, node):
        if isinstance(node.value, str) and node.value.startswith("/Users/"):
            replacement = self.directory / Path(node.value).name
            if not replacement.is_file():
                raise ValueError(f"Required upstream input is absent: {replacement}")
            self.changes[node.value] = str(replacement)
            return ast.copy_location(ast.Constant(str(replacement)), node)
        return node


def notebook_run(key: str, relative_path: str, output: Path, data_dir=None, figure_hook=None) -> tuple[dict, dict]:
    upstream = source(key)
    notebook = upstream / relative_path
    namespace = {"__name__": "__main__"}
    np.random.seed(SEED)
    random.seed(SEED)
    transformer = RebaseInputs(Path(data_dir).resolve() if data_dir else notebook.parent)
    executed, count = [], 0
    original_show = plt.show
    plt.show = lambda *args, **kwargs: None
    try:
        with (output / "stdout.txt").open("w", encoding="utf-8") as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            for index, cell in enumerate(json.loads(notebook.read_text(encoding="utf-8"))["cells"]):
                if cell["cell_type"] != "code":
                    continue
                text = "".join(cell["source"]).replace("%matplotlib inline", "")
                tree = ast.fix_missing_locations(transformer.visit(ast.parse(text)))
                executed.append(f"# original notebook cell {index}\n" + ast.unparse(tree))
                (output / "executed.py").write_text("\n\n".join(executed), encoding="utf-8")
                exec(compile(tree, f"{notebook}:cell{index}", "exec"), namespace)
                count += 1
        for number, figure_number in enumerate(plt.get_fignums(), start=1):
            figure = plt.figure(figure_number)
            if figure_hook:
                figure_hook(number, figure)
            save_figure(figure, output, f"figure_{number:02}")
    finally:
        plt.show = original_show
    return {"upstream": provenance(key), "notebook": relative_path, "code_cells_executed": count,
            "notebook_sha256": file_hash(notebook), "path_replacements": transformer.changes,
            "seed": SEED, "adaptations": ["Removed the matplotlib inline magic", "Rebased explicit upstream /Users/ data paths", "Saved figures using the Agg backend"]}, namespace


def tutorial(args, output: Path) -> dict:
    detail, namespace = notebook_run("ocng", "numpy_1.ipynb", output)
    detail["original_assertions"] = "Executed without suppression"
    return detail


def petroleum(args, output: Path) -> dict:
    def correct_labels(number, figure):
        axis = figure.axes[0]
        if number == 1:
            axis.set(xlabel="Channel", ylabel="ln(counts)", title="Calibration spectra and sample 33")
            for line, name in zip(axis.lines, ("K calibration", "Th calibration", "U calibration", "Sample 33")):
                line.set_label(name)
            axis.legend()
        elif number == 2:
            axis.set(xlabel="Sample index", ylabel="Spectral component weight (uncalibrated)", title="Spectral least-squares fit")
    detail, namespace = notebook_run("petroleum", SPECTRAL, output, args.data_dir, correct_labels)
    coefficients = namespace["Conc_n"]
    pd.DataFrame(coefficients, columns=["K_weight", "Th_weight", "U_weight"]).to_csv(output / "spectral_component_weights.csv", index=False)
    spectrum, samples = namespace["Spectrum"].T, namespace["Q_array"].T
    predicted = spectrum @ coefficients.T
    residual = samples - predicted
    pd.DataFrame({"sample": np.arange(1, samples.shape[1] + 1),
                  "rmse_counts": np.sqrt(np.mean(residual ** 2, axis=0))}).to_csv(output / "fit_residuals.csv", index=False)
    detail.update(rows=int(coefficients.shape[0]), channels=int(samples.shape[0]),
                  output_meaning="Unconstrained least-squares spectral component weights. No physical concentration calibration is provided.")
    detail["adaptations"].append("Labelled spectral axes as natural log counts and uncalibrated component weights")
    return detail


def batch(args, output: Path) -> dict:
    inputs = sorted(Path(args.input_dir).resolve().glob("*.csv"))
    if not inputs:
        raise ValueError("No CSV files in input directory")
    results = []
    for csv in inputs:
        child = output / csv.stem
        child.mkdir()
        parameters = argparse.Namespace(csv=str(csv), x=args.x, ys=args.ys, units_json=args.units_json, title=args.title)
        detail = analyze(parameters, child)
        (child / "analysis.json").write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")
        plt.close("all")
        results.append({"input": str(csv), "input_sha256": file_hash(csv), "output": str(child)})
    return {"implementation": "Independent replacement; original Geo-Plot repository has no executable source", "reference": provenance("geo-plot"), "files": results}


def demo(args, output: Path) -> dict:
    inputs = output / "synthetic_inputs"
    inputs.mkdir()
    rng = np.random.default_rng(SEED)
    pd.DataFrame({"dip_direction": [0, 45, 90, 135, 200, 260], "dip": [0, 25, 90, 60, 40, 70]}).to_csv(inputs / "orientations.csv", index=False)
    n = 101
    pd.DataFrame({"well_name": ["SYNTHETIC-DEMO"] * n, "depth": np.arange(1000, 1101),
                  "cal": 8 + rng.uniform(-0.05, 0.05, n), "gam": rng.uniform(5, 120, n),
                  "res": rng.uniform(1, 180, n), "den": rng.uniform(2.1, 2.7, n), "neu": rng.uniform(0.05, 0.35, n)}).to_csv(inputs / "well.csv", index=False)
    declared = {"depth": "m", "cal": "inch", "gam": "API", "res": "ohm m", "den": "g/cm3", "neu": "fraction"}
    (inputs / "units.json").write_text(json.dumps(declared), encoding="utf-8")
    (inputs / "batch-units.json").write_text(json.dumps({"time_s": "s", "signal": "arbitrary unit"}), encoding="utf-8")
    batch_input = inputs / "batch"
    batch_input.mkdir()
    for offset in (0, 1):
        pd.DataFrame({"time_s": np.linspace(0, 10, n), "signal": np.sin(np.linspace(0, 10, n)) + offset}).to_csv(batch_input / f"synthetic_{offset}.csv", index=False)
    commands = {
        "stereonet": ["stereonet", "--csv", str(inputs / "orientations.csv"), "--title", "SYNTHETIC structural example"],
        "well-log": ["well-log", "--csv", str(inputs / "well.csv"), "--well", "SYNTHETIC-DEMO", "--units-json", str(inputs / "units.json")],
        "analyze": ["analyze", "--csv", str(inputs / "well.csv"), "--x", "depth", "--ys", "gam,res", "--units-json", str(inputs / "units.json"), "--title", "SYNTHETIC CSV example"],
        "tutorial": ["tutorial"],
        "petroleum": ["petroleum"],
        "batch-plot": ["batch-plot", "--input-dir", str(batch_input), "--x", "time_s", "--ys", "signal", "--units-json", str(inputs / "batch-units.json"), "--title", "SYNTHETIC batch example"],
    }
    selected = commands if args.mode == "all" else {args.mode: commands[args.mode]}
    results = []
    for name, command in selected.items():
        result = subprocess.run([sys.executable, __file__, *command, "--out", str(output / name)], capture_output=True, text=True, encoding="utf-8")
        (output / f"{name}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        results.append({"mode": name, "passed": result.returncode == 0})
        if result.returncode:
            raise RuntimeError(f"Demo failed: {name}; see {output / (name + '.log')}")
    return {"dataset_kind": "Synthetic demonstrations and upstream teaching datasets; not Hunan field measurements", "seed": SEED, "results": results}


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    for command in ("stereonet", "well-log", "analyze", "petroleum", "batch-plot", "tutorial", "demo"):
        child = commands.add_parser(command)
        child.add_argument("--out", required=True, help="New or empty output directory")
        if command in ("stereonet", "well-log", "analyze"):
            child.add_argument("--csv", required=True)
        if command == "stereonet":
            child.add_argument("--azimuth", default="dip_direction")
            child.add_argument("--dip", default="dip")
            child.add_argument("--orientation", choices=["dip-direction", "rhr-strike"], default="dip-direction")
            child.add_argument("--title", default="Structural orientations")
        if command == "well-log":
            child.add_argument("--well", required=True)
        if command in ("well-log", "analyze", "batch-plot"):
            child.add_argument("--units-json")
        if command in ("analyze", "batch-plot"):
            child.add_argument("--x", required=True)
            child.add_argument("--ys", required=True, help="Comma-separated numeric column names")
            child.add_argument("--title", default="CSV analysis")
        if command == "batch-plot":
            child.add_argument("--input-dir", required=True)
        if command == "petroleum":
            child.add_argument("--data-dir", help="Directory containing k.mdb.csv, th.mdb.csv, u.mdb.csv, quest.mdb.csv")
        if command == "demo":
            child.add_argument("--mode", choices=["all", "stereonet", "well-log", "analyze", "tutorial", "petroleum", "batch-plot"], default="all")
    return result


def main() -> int:
    args = parser().parse_args()
    if args.command == "doctor":
        print(json.dumps({"python": sys.executable, "python_version": sys.version,
                          "cache": str(CACHE), "versions": {name: importlib.metadata.version(name) for name in ("numpy", "pandas", "matplotlib", "scipy", "seaborn", "openpyxl")},
                          "source_commits": {key: spec["commit"] for key, spec in LOCK.items()}}, indent=2))
        return 0
    output = Path(args.out).resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"Output must be empty to protect previous results: {output}")
    output.mkdir(parents=True, exist_ok=True)
    record = {"command": args.command, "parameters": vars(args), "started_utc": datetime.now(timezone.utc).isoformat(),
              "python": sys.version, "packages": {name: importlib.metadata.version(name) for name in ("numpy", "pandas", "matplotlib", "scipy")}}
    try:
        record.update({"status": "success", "details": {"stereonet": stereonet, "well-log": well_log, "analyze": analyze,
                       "petroleum": petroleum, "batch-plot": batch, "tutorial": tutorial, "demo": demo}[args.command](args, output)})
        return_code = 0
    except Exception as error:
        record.update(status="failed", error=f"{type(error).__name__}: {error}")
        (output / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        return_code = 1
    finally:
        plt.close("all")
    record["completed_utc"] = datetime.now(timezone.utc).isoformat()
    record["artifacts"] = {str(path.relative_to(output)): file_hash(path) for path in sorted(output.rglob('*')) if path.is_file()}
    (output / "run.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": record["status"], "output": str(output), "error": record.get("error")}, ensure_ascii=False))
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
