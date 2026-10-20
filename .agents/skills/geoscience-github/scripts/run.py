"""Portable, standard-library-only launcher; never changes the host Python install."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import venv

SKILL = Path(__file__).resolve().parents[1]


def cache_root() -> Path:
    return Path(os.environ.get("GEOSCIENCE_CACHE", Path.home() / ".cache" / "codex-geoscience"))


def main() -> int:
    if not (3, 10) <= sys.version_info[:2] <= (3, 12):
        raise SystemExit("Use Python 3.10, 3.11 or 3.12 for the tested legacy-code environment.")
    requirements = SKILL / "requirements.txt"
    digest = hashlib.sha256(requirements.read_bytes()).hexdigest()[:12]
    env = cache_root() / "envs" / (f"py{sys.version_info.major}{sys.version_info.minor}-" + digest)
    python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    marker = env / "ready.txt"
    if not marker.exists():
        print(f"Preparing isolated geoscience environment: {env}", file=sys.stderr, flush=True)
        venv.EnvBuilder(with_pip=True).create(env)
        subprocess.run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(requirements)], check=True, stdout=sys.stderr)
        marker.write_text(digest, encoding="utf-8")
    args = sys.argv[1:] or ["--help"]
    environment = os.environ.copy()
    environment.update(MPLBACKEND="Agg", PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    return subprocess.call([str(python), str(SKILL / "scripts" / "engine.py"), *args], env=environment)


if __name__ == "__main__":
    raise SystemExit(main())
