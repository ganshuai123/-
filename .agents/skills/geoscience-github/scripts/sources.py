"""Fetch pinned upstream sources and verify the files used by the adapters."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import urllib.request
import zipfile

SKILL = Path(__file__).resolve().parents[1]
LOCK = json.loads((SKILL / "sources.lock.json").read_text(encoding="utf-8"))
CACHE = Path(os.environ.get("GEOSCIENCE_CACHE", Path.home() / ".cache" / "codex-geoscience"))


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(root: Path, spec: dict) -> bool:
    return all((root / name).is_file() and file_hash(root / name) == digest
               for name, digest in spec["files"].items())


def source(key: str) -> Path:
    spec = LOCK[key]
    destination = CACHE / "sources" / (key + "-" + spec["commit"][:12])
    if validate(destination, spec):
        return destination
    if destination.exists():
        raise ValueError(f"Source cache was modified: {destination}. Use a fresh GEOSCIENCE_CACHE to refetch.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    local_base = Path(os.environ.get("GEOSCIENCE_SOURCE_ROOT", Path.home() / "Downloads" / "geoscience-github-repos"))
    local_source = local_base / spec["download_directory"]
    with tempfile.TemporaryDirectory(prefix="source-", dir=destination.parent) as temporary:
        stage = Path(temporary) / "source"
        if validate(local_source, spec):
            shutil.copytree(local_source, stage)
        else:
            archive = Path(temporary) / "source.zip"
            url = f"https://codeload.github.com/{spec['repo']}/zip/{spec['commit']}"
            request = urllib.request.Request(url, headers={"User-Agent": "codex-geoscience"})
            with urllib.request.urlopen(request, timeout=60) as response, archive.open("wb") as output:
                shutil.copyfileobj(response, output)
            with zipfile.ZipFile(archive) as bundle:
                roots = {item.filename.split('/')[0] for item in bundle.infolist() if item.filename}
                if len(roots) != 1:
                    raise ValueError("Unexpected upstream archive structure")
                for item in bundle.infolist():
                    target = (Path(temporary) / item.filename).resolve()
                    if not target.is_relative_to(Path(temporary).resolve()):
                        raise ValueError("Unsafe archive path")
                    if (item.external_attr >> 16) & 0o170000 == 0o120000:
                        raise ValueError("Unexpected source symlink")
                bundle.extractall(temporary)
            shutil.copytree(Path(temporary) / next(iter(roots)), stage)
        if not validate(stage, spec):
            raise ValueError(f"Upstream source checksum mismatch: {key}")
        stage.rename(destination)
    return destination


def provenance(key: str) -> dict:
    spec = LOCK[key]
    return {"repo": spec["repo"], "commit": spec["commit"],
            "url": f"https://github.com/{spec['repo']}/tree/{spec['commit']}"}
