"""Load and validate the pipeline configuration.

A single YAML file (``config/config.yaml``) parameterises every stage. We wrap
it in a small dataclass-backed loader so that (a) paths are resolved relative to
the project root, (b) output directories are created on demand, and (c) the
random seed is applied consistently for reproducibility.
"""
from __future__ import annotations

import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

import numpy as np
import yaml

# Project root = two levels up from this file (src/ale_meta/config.py).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"


@dataclass
class Config:
    """Typed, path-aware wrapper around the YAML configuration."""

    raw: Dict[str, Any] = field(default_factory=dict)
    root: Path = PROJECT_ROOT

    # -- convenient accessors ------------------------------------------------
    def __getitem__(self, key: str) -> Any:
        return self.raw[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.raw.get(key, default)

    def path(self, key: str) -> Path:
        """Resolve a configured path (under ``paths:``) to an absolute Path,
        creating the directory if it does not yet exist."""
        rel = self.raw["paths"][key]
        p = (self.root / rel).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def seed(self) -> int:
        return int(self.raw.get("project", {}).get("random_seed", 42))

    def apply_seed(self) -> None:
        """Seed all RNGs the pipeline touches for reproducibility."""
        random.seed(self.seed)
        np.random.seed(self.seed)
        os.environ["PYTHONHASHSEED"] = str(self.seed)


def load_config(path: str | os.PathLike | None = None) -> Config:
    """Read the YAML config, validate a few invariants, seed RNGs, return it."""
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {cfg_path}")

    with open(cfg_path, "r") as fh:
        raw = yaml.safe_load(fh)

    _validate(raw)
    cfg = Config(raw=raw)
    cfg.apply_seed()
    return cfg


def _validate(raw: Dict[str, Any]) -> None:
    """Fail fast on obvious misconfiguration."""
    for section in ("project", "paths", "databases", "curation", "ale"):
        if section not in raw:
            raise ValueError(f"Config missing required section: '{section}'")

    ale = raw["ale"]
    if not (0 < ale["cluster_forming_p"] < 1):
        raise ValueError("ale.cluster_forming_p must be in (0, 1)")
    if not (0 < ale["fwe_cluster_p"] < 1):
        raise ValueError("ale.fwe_cluster_p must be in (0, 1)")
    # 500+ is a reasonable exploratory null; publication needs >=5000 (documented
    # in config). Anything below 100 is meaningless, so guard that hard floor.
    if ale["n_iters"] < 100:
        raise ValueError("ale.n_iters must be >= 100 (>=5000 for publication)")

    if not any(db.get("enabled") for db in raw["databases"].values()):
        raise ValueError("At least one database must be enabled")
