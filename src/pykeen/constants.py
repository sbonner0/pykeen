"""Constants for PyKEEN."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pystow
import torch

from .typing import (
    COLUMN_HEAD,
    COLUMN_RELATION,
    COLUMN_TAIL,
    LABEL_HEAD,
    LABEL_RELATION,
    LABEL_TAIL,
    Target,
    TargetColumn,
    TargetHint,
)

__all__ = [
    "PYKEEN_HOME",
    "PYKEEN_DATASETS",
    "PYKEEN_DATASETS_MODULE",
    "PYKEEN_BENCHMARKS",
    "PYKEEN_EXPERIMENTS",
    "PYKEEN_CHECKPOINTS",
    "PYKEEN_LOGS",
    "AGGREGATIONS",
]

#: A manager around the PyKEEN data folder. It defaults to ``~/.data/pykeen``.
#  This can be overridden with the envvar ``PYKEEN_HOME``.
#: For more information, see https://github.com/cthoyt/pystow
PYKEEN_MODULE: pystow.Module = pystow.module("pykeen")
#: A path representing the PyKEEN data folder
PYKEEN_HOME: Path = PYKEEN_MODULE.base
#: A subdirectory of the PyKEEN data folder for datasets, defaults to ``~/.data/pykeen/datasets``
PYKEEN_DATASETS: Path = PYKEEN_MODULE.join("datasets")
PYKEEN_DATASETS_MODULE: pystow.Module = PYKEEN_MODULE.module("datasets")
#: A subdirectory of the PyKEEN data folder for benchmarks, defaults to ``~/.data/pykeen/benchmarks``
PYKEEN_BENCHMARKS: Path = PYKEEN_MODULE.join("benchmarks")
#: A subdirectory of the PyKEEN data folder for experiments, defaults to ``~/.data/pykeen/experiments``
PYKEEN_EXPERIMENTS: Path = PYKEEN_MODULE.join("experiments")
#: A subdirectory of the PyKEEN data folder for checkpoints, defaults to ``~/.data/pykeen/checkpoints``
PYKEEN_CHECKPOINTS: Path = PYKEEN_MODULE.join("checkpoints")
#: A subdirectory for PyKEEN logs
PYKEEN_LOGS: Path = PYKEEN_MODULE.join("logs")

PYKEEN_DEFAULT_CHECKPOINT = "PyKEEN_just_saved_my_day.pt"

DEFAULT_DROPOUT_HPO_RANGE = dict(type=float, low=0.0, high=0.5, q=0.1)
#: We define the embedding dimensions as a multiple of 16 because it is computational beneficial (on a GPU)
#: see: https://docs.nvidia.com/deeplearning/performance/index.html#optimizing-performance
DEFAULT_EMBEDDING_HPO_EMBEDDING_DIM_RANGE = dict(type=int, low=16, high=256, q=16)

USER_DEFINED_CODE = "<user defined>"

AGGREGATIONS = {func.__name__: func for func in [torch.sum, torch.max, torch.mean, torch.logsumexp]}

# TODO: extend to relation, cf. https://github.com/pykeen/pykeen/pull/728
# SIDES: Tuple[Target, ...] = (LABEL_HEAD, LABEL_TAIL)
TARGET_TO_INDEX: Mapping[Target, TargetColumn] = {
    LABEL_HEAD: COLUMN_HEAD,
    LABEL_RELATION: COLUMN_RELATION,
    LABEL_TAIL: COLUMN_TAIL,
}

COLUMN_LABELS: tuple[Target, Target, Target] = (LABEL_HEAD, LABEL_RELATION, LABEL_TAIL)
TARGET_TO_KEY_LABELS = {target: [c for c in COLUMN_LABELS if c != target] for target in COLUMN_LABELS}
TARGET_TO_KEYS = {target: [TARGET_TO_INDEX[c] for c in cs] for target, cs in TARGET_TO_KEY_LABELS.items()}


def get_target_column(target: TargetHint = None) -> TargetColumn:
    """Normalize target choice to column."""
    if target is None:
        return COLUMN_TAIL
    if isinstance(target, str):
        return TARGET_TO_INDEX[target]
    return target
