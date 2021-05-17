# -*- coding: utf-8 -*-

"""An adapter for TensorBoard."""

import pathlib
import time
from typing import Any, Dict, Mapping, Optional, TYPE_CHECKING, Type

from .base import ResultTracker
from ..constants import PYKEEN_LOGS
from ..utils import flatten_dictionary

if TYPE_CHECKING:
    import torch.utils.tensorboard

__all__ = [
    'TensorBoardResultTracker',
]


class TensorBoardResultTracker(ResultTracker):
    """A tracker for TensorBoard."""

    #: The class that's used to instantiate a summarywriter
    summary_writer_cls: Type['torch.utils.tensorboard.SummaryWriter']

    def __init__(
        self,
        experiment_path: Optional[str] = None,
        experiment_name: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize result tracking via Tensorboard.

        :param experiment_path:
            The experiment path. A custom path at which the tensorboard logs will be saved.
        :param experiment_name:
            The name of the experiment, will be used as a sub directory name for the logging. If no default is given,
            the current time is used. If set, experiment_path is set, this argument has no effect.
        :param tags:
            The additional run details which are presented as tags to be logged
        """
        import torch.utils.tensorboard
        self.summary_writer_cls = torch.utils.tensorboard.SummaryWriter
        self.tags = tags

        if experiment_path is None:
            if experiment_name is None:
                experiment_name = time.strftime('%Y-%m-%d-%H-%M-%S')
            path = PYKEEN_LOGS.joinpath("tensorboard", experiment_name)
        elif isinstance(experiment_path, str):
            path = pathlib.Path(experiment_path)
        else:
            if experiment_name is None:
                experiment_name = time.strftime('%Y-%m-%d-%H-%M-%S')
            path = PYKEEN_LOGS.joinpath("tensorboard", experiment_name)
        self.path = path

        self.writer = self.summary_writer_cls(log_dir=self.path)

    def log_metrics(
        self,
        metrics: Mapping[str, float],
        step: Optional[int] = None,
        prefix: Optional[str] = None,
    ) -> None:  # noqa: D102
        metrics = flatten_dictionary(dictionary=metrics, prefix=prefix)
        for key, value in metrics.items():
            self.writer.add_scalar(tag=key, scalar_value=value, global_step=step)
        self.writer.flush()

    def log_params(self, params: Mapping[str, Any], prefix: Optional[str] = None) -> None:  # noqa: D102
        params = flatten_dictionary(dictionary=params, prefix=prefix)
        for key, value in params.items():
            self.writer.add_text(tag=str(key), text_string=str(value))
        self.writer.flush()

    def end_run(self) -> None:  # noqa: D102
        self.writer.flush()
        self.writer.close()
