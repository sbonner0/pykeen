"""Instance creation utilities."""

import pathlib
from collections.abc import Callable, Sequence
from typing import TextIO

import numpy as np
import pandas
import torch
from class_resolver import FunctionResolver

from ..typing import LabeledTriples, LongTensor, MappedTriples

__all__ = [
    "compute_compressed_adjacency_list",
    "load_triples",
    "get_entities",
    "get_relations",
    "tensor_to_df",
    "max_value",
    "get_num_ids",
]

TRIPLES_DF_COLUMNS = ("head_id", "head_label", "relation_id", "relation_label", "tail_id", "tail_label")

Importer = Callable[[str], LabeledTriples]

#: Functions for specifying exotic resources with a given prefix
PREFIX_IMPORTER_RESOLVER: FunctionResolver[[str], LabeledTriples] = FunctionResolver.from_entrypoint(
    "pykeen.triples.prefix_importer"
)

#: Functions for specifying exotic resources based on their file extension
EXTENSION_IMPORTER_RESOLVER: FunctionResolver[[str], LabeledTriples] = FunctionResolver.from_entrypoint(
    "pykeen.triples.extension_importer"
)


def load_triples(
    path: str | pathlib.Path | TextIO,
    delimiter: str = "\t",
    encoding: str | None = None,
    column_remapping: Sequence[int] | None = None,
) -> LabeledTriples:
    """Load triples saved as tab separated values.

    :param path: The key for the data to be loaded. Typically, this will be a file path ending in ``.tsv`` that points
        to a file with three columns - the head, relation, and tail. This can also be used to invoke PyKEEN data
        importer entrypoints (see below).
    :param delimiter: The delimiter between the columns in the file
    :param encoding: The encoding for the file. Defaults to utf-8.
    :param column_remapping: A remapping if the three columns do not follow the order head-relation-tail. For example,
        if the order is head-tail-relation, pass ``(0, 2, 1)``

    :returns: A numpy array representing "labeled" triples.

    :raises ValueError: if a column remapping was passed, but it was not a length 3 sequence

    Besides TSV handling, PyKEEN does not come with any importers pre-installed. A few can be found at:

    - :mod:`pybel.io.pykeen`
    - :mod:`bio2bel.io.pykeen`
    """
    if isinstance(path, str | pathlib.Path):
        path = str(path)
        for extension, handler in EXTENSION_IMPORTER_RESOLVER.lookup_dict.items():
            if path.endswith(f".{extension}"):
                return handler(path)

        for prefix, handler in PREFIX_IMPORTER_RESOLVER.lookup_dict.items():
            if path.startswith(f"{prefix}:"):
                return handler(path[len(f"{prefix}:") :])

    if encoding is None:
        encoding = "utf-8"
    if column_remapping is not None:
        if len(column_remapping) != 3:
            raise ValueError("remapping must have length of three")
    df = pandas.read_csv(
        path,
        sep=delimiter,
        encoding=encoding,
        dtype=str,
        header=None,
        usecols=column_remapping,
        keep_default_na=False,
    )
    if column_remapping is not None:
        df = df[[df.columns[c] for c in column_remapping]]
    return df.to_numpy()


def get_entities(triples: LongTensor) -> set[int]:
    """Get all entities from the triples."""
    return set(triples[:, [0, 2]].flatten().tolist())


def get_relations(triples: LongTensor) -> set[int]:
    """Get all relations from the triples."""
    return set(triples[:, 1].tolist())


def tensor_to_df(
    tensor: LongTensor,
    **kwargs: torch.Tensor | np.ndarray | Sequence,
) -> pandas.DataFrame:
    """Take a tensor of triples and make a pandas dataframe with labels.

    :param tensor: shape: (n, 3) The triples, ID-based and in format (head_id, relation_id, tail_id).
    :param kwargs: Any additional number of columns. Each column needs to be of shape (n,). Reserved column names:
        {"head_id", "head_label", "relation_id", "relation_label", "tail_id", "tail_label"}.

    :returns: A dataframe with n rows, and 3 + len(kwargs) columns.

    :raises ValueError: If a reserved column name appears in kwargs.
    """
    # Input validation
    additional_columns = set(kwargs.keys())
    forbidden = additional_columns.intersection(TRIPLES_DF_COLUMNS)
    if len(forbidden) > 0:
        raise ValueError(
            f"The key-words for additional arguments must not be in {TRIPLES_DF_COLUMNS}, but {forbidden} were used.",
        )

    # convert to numpy
    tensor = tensor.cpu().numpy()
    data = dict(zip(["head_id", "relation_id", "tail_id"], tensor.T, strict=False))

    # Additional columns
    for key, values in kwargs.items():
        # convert PyTorch tensors to numpy
        if isinstance(values, torch.Tensor):
            values = values.cpu().numpy()
        data[key] = values

    # convert to dataframe
    rv = pandas.DataFrame(data=data)

    # Re-order columns
    columns = list(TRIPLES_DF_COLUMNS[::2]) + sorted(set(rv.columns).difference(TRIPLES_DF_COLUMNS))
    return rv.loc[:, columns]


def compute_compressed_adjacency_list(
    mapped_triples: MappedTriples,
    num_entities: int | None = None,
) -> tuple[LongTensor, LongTensor, LongTensor]:
    """Compute compressed undirected adjacency list representation for efficient sampling.

    The compressed adjacency list format is inspired by CSR sparse matrix format.

    :param mapped_triples: the ID-based triples
    :param num_entities: the number of entities.

    :returns: a tuple `(degrees, offsets, compressed_adj_lists)` where

            - degrees: shape: `(num_entities,)`
            - offsets: shape: `(num_entities,)`
            - compressed_adj_list: shape: `(2 * num_triples, 2)`

        with

        .. code-block::

            adj_list[i] = compressed_adj_list[offsets[i]:offsets[i+1]]
    """
    num_entities = num_entities or mapped_triples[:, [0, 2]].max().item() + 1
    num_triples = mapped_triples.shape[0]
    adj_lists: list[list[tuple[int, float]]] = [[] for _ in range(num_entities)]
    for i, (s, _, o) in enumerate(mapped_triples):
        adj_lists[s].append((i, o.item()))
        adj_lists[o].append((i, s.item()))
    degrees = torch.tensor([len(a) for a in adj_lists], dtype=torch.long)
    assert torch.sum(degrees) == 2 * num_triples

    offset = torch.empty(num_entities, dtype=torch.long)
    offset[0] = 0
    offset[1:] = torch.cumsum(degrees, dim=0)[:-1]
    compressed_adj_lists = torch.cat([torch.as_tensor(adj_list, dtype=torch.long) for adj_list in adj_lists], dim=0)
    return degrees, offset, compressed_adj_lists


def max_value(x: LongTensor) -> int | None:
    """Return the maximum value, or None if the tensor is empty."""
    if x.numel():
        return x.max().item()
    return None


def get_num_ids(x: LongTensor) -> int:
    """Return the number of ids values."""
    max_id = max_value(x)
    if max_id is None:
        return 0
    return max_id + 1
