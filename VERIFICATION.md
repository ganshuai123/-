# Verification

Verified on 2026-10-20, Windows, Python 3.12.14.

- The skill's first-call launcher created an isolated environment; package imports and `doctor` succeeded.
- Six runnable examples succeeded: geocouche/APSG stereonet, original five-track well-log function, CSV analysis, original OCNG NumPy teaching notebook, original spectral-gamma notebook, and independently implemented batch plots.
- Seven end-to-end tests passed. They check nonempty PNG/SVG outputs, known horizontal/vertical plane normals, equivalence of right-hand-rule strike and dip-direction inputs, pairwise missing-data counts, spectral weights and RMSE against an independently parsed least-squares calculation, rejection of negative resistivity, and preservation of existing outputs.
- A clean source-cache test fetched the pinned well-log archive from GitHub and verified its source SHA-256, without relying on the original local download.
- The system skill validator accepted the source and installed skill. The local installer verified all installed file hashes.
- A contact sheet of representative outputs was visually checked; labels, axes and five-track layout were inspected. Spectral coefficients are labelled as uncalibrated component weights.

The demo seed is `20261020`. The installed direct requirements are pinned in the skill's `requirements.txt`. Each execution records its actual package versions, source commits and file hashes in `run.json`. Generated data, figures, logs and virtual environments are excluded from Git.

To reproduce, run:

```text
python .agents/skills/geoscience-github/scripts/run.py demo --out output/check
```

For the test suite, use the isolated Python executable reported by `doctor`:

```text
<isolated-python> -X utf8 -m unittest discover -s tests -v
```

These checks establish execution and the listed numerical/data-handling properties. They do not establish calibrated geochemical concentrations, geothermal resource estimates, or performance of the other upstream petroleum notebooks.
