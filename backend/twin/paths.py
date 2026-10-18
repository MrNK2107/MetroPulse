"""Filesystem layout for the India Twin data directory."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class TwinPaths:
    root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", Path(self.root))

    @property
    def manual(self) -> Path:
        return self.root / "manual"

    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def published(self) -> Path:
        return self.root / "published"

    @property
    def seed(self) -> Path:
        return self.root / "seed"

    @property
    def current_file(self) -> Path:
        return self.published / "CURRENT.json"

    def places_dir(self, boundary_version: str) -> Path:
        return self.published / "places" / boundary_version

    def dataset_dir(self, source_id: str, dataset_version: str) -> Path:
        return self.published / "datasets" / source_id / dataset_version

    @classmethod
    def default(cls) -> "TwinPaths":
        env = os.environ.get("TWIN_DATA_DIR")
        return cls(Path(env) if env else _REPO_ROOT / "data" / "twin")
