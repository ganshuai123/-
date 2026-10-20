# Commands and inputs

Run `python <skill-directory>/scripts/run.py <command> ...` using Python 3.10–3.12. The first call installs the pinned requirements in `~/.cache/codex-geoscience/envs`; it does not change the invoking Python installation. `GEOSCIENCE_CACHE` can select another cache directory. A later call can work offline when its environment and source files are already cached.

Every processing command requires `--out <new-or-empty-directory>`. Existing nonempty directories are refused. Figure commands produce both PNG and SVG. Each completed or failed run writes `run.json`, including source commits, input hashes where applicable, parameters, package versions, status, and artifact hashes. A failed run retains its error log rather than claiming success.

## Reproducible examples

```text
python <skill>/scripts/run.py doctor
python <skill>/scripts/run.py demo --out output/geoscience-demo
python <skill>/scripts/run.py demo --mode well-log --out output/well-example
```

The full demo exercises all five workflow categories and also executes the OCNG `numpy_1.ipynb` teaching notebook with its original assertions. Synthetic inputs are clearly named; the petroleum example uses the upstream teaching data. These are execution checks, not independent validation of a scientific model.

## Stereonet

```text
python <skill>/scripts/run.py stereonet --csv orientations.csv --out output/structures
```

Default CSV columns: `dip_direction,dip`. Values are degrees, azimuth 0–360 and dip 0–90. For right-hand-rule strike/dip, use `--azimuth strike --orientation rhr-strike`. Plain strike without a dip-direction convention is ambiguous; resolve it before running.

This calls geocouche's bundled APSG core and Schmidt equal-area, lower-hemisphere plotting. It exports input orientations and unit plane normals in north/east/down coordinates. Compatibility edits affect a cached copy only: Matplotlib warning class, canvas window-title manager, and NumPy's removed float alias. The original QGIS plugin GUI is not part of this headless adapter.

## Five-track well logs

```text
python <skill>/scripts/run.py well-log --csv well.csv --well ZK01 --units-json units.json --out output/ZK01
```

CSV columns: `well_name,depth,cal,gam,res,den,neu`. Select exactly one well by `--well`. All required samples must be finite, depths distinct, caliper positive, and resistivity positive. Sort order is handled by the adapter. Convert LAS data separately with an explicit curve-name and unit mapping.

Example `units.json`:

```json
{"depth":"m","cal":"inch","gam":"API","res":"ohm m","den":"g/cm3","neu":"fraction"}
```

The function is extracted at runtime from the pinned upstream notebook rather than republished here. The original caliper panel is normalized. Its fixed visual fills assume gamma in API, resistivity in ohm m, and density in g/cm3; other units require explicit conversion first. Fill colors/cutoffs do not classify productive reservoir intervals.

## CSV data analysis

```text
python <skill>/scripts/run.py analyze --csv observations.csv --x depth --ys temperature,conductivity --units-json units.json --out output/analysis
```

Outputs include numerical summaries, Pearson correlations, per-pair observation counts, and selected-variable plots. Missing values are excluded pairwise, with counts recorded; no imputation or unit conversion is performed. Units omitted from `units.json` are labelled unspecified. This adapter is newly written; the original OCNG tutorial can also run with `tutorial --out output/tutorial`.

## Petroleum spectral-gamma example

```text
python <skill>/scripts/run.py petroleum --out output/spectral-example
python <skill>/scripts/run.py petroleum --data-dir my-calibration-and-samples --out output/spectral-user-data
```

Runs the original `Spectral Gamma-ray Logging` notebook. By default it uses the upstream `k.mdb.csv`, `th.mdb.csv`, `u.mdb.csv`, `quest.mdb.csv`. The notebook assumes its original SPCH format, 1024 channels and 52 sample spectra; `--data-dir` supplies compatible files with those exact names. Inputs with another structure need separate adaptation.

The adapter changes explicit `/Users/...` input paths, removes `%matplotlib inline`, and saves figures headlessly. `executed.py` and `stdout.txt` preserve exactly what ran. `spectral_component_weights.csv` contains unconstrained least-squares weights, which may be negative. Neither the source notebook nor the adapter supplies a calibration that makes them physical U/Th/K concentrations. `fit_residuals.csv` reports residual RMSE in spectral counts. Forecasting, tomography, XRD, capillary and correlation notebooks are retained upstream for separately requested adaptation.

## Batch plots

```text
python <skill>/scripts/run.py batch-plot --input-dir csv-folder --x time --ys temperature --units-json units.json --out output/batch
```

Processes each top-level `*.csv` file with the selected schema into its own output folder. This is an independent implementation of the plotting use case: the pinned Geo-Plot- repository only has README.md and LICENSE. No original Geo-Plot GUI code is available to run.

## Upstream cache and provenance

`sources.lock.json` pins five source commits and SHA-256 hashes of every upstream source/data file used by these adapters. Sources are reused from a matching original download when available, otherwise fetched from the pinned GitHub archive. Files used for execution are checked against this lock. Third-party source code remains in the local cache with its original license files; it is not copied into this repository or relicensed by the adapters.
