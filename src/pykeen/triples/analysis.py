"""Analysis utilities for (mapped) triples."""
import enum
import hashlib
import itertools as itt
import logging
from collections import defaultdict
from typing import Collection, DefaultDict, Iterable, Mapping, NamedTuple, Optional, Set, Tuple

import numpy
import pandas as pd
import torch
from tqdm.auto import tqdm

from pykeen.typing import MappedTriples

logger = logging.getLogger(__name__)

__all__ = [
    "relation_cardinality_types",
    "CardinalityTypeEnum",
    "relation_pattern_types",
    "PatternTypeEnum",
]


class CardinalityTypeEnum(str, enum.Enum):
    """An enum for cardinality types."""

    one_to_one = "one-to-one"
    one_to_many = "one-to-many"
    many_to_one = "many-to-one"
    many_to_many = "many-to-many"


class PatternTypeEnum(str, enum.Enum):
    """An enum for pattern types."""

    # unary
    symmetry = "symmetry"
    anti_symmetry = "anti-symmetry"

    # binary
    inversion = "inversion"

    # ternary
    composition = "composition"


class PatternMatch(NamedTuple):
    """A pattern match tuple of relation_id, pattern_type, support, and confidence."""

    relation_id: int
    pattern_type: str
    support: int
    confidence: float


def composition_candidates(
    mapped_triples: Iterable[Tuple[int, int, int]],
) -> Collection[Tuple[int, int]]:
    r"""Pre-filtering relation pair candidates for composition pattern.

    Determines all relation pairs $(r, r')$ with at least one entity $e$ such that

    .. math ::

        \{(h, r, e), (e, r', t)\} \subseteq \mathcal{T}

    :param mapped_triples:
        An iterable over ID-based triples. Only consumed once.

    :return:
        A set of relation pairs.
    """
    # index triples
    # incoming relations per entity
    ins: DefaultDict[int, Set[int]] = defaultdict(set)
    # outgoing relations per entity
    outs: DefaultDict[int, Set[int]] = defaultdict(set)
    for h, r, t in mapped_triples:
        outs[h].add(r)
        ins[t].add(r)

    # return candidates
    return {
        (r1, r2)
        for e, r1s in ins.items()
        for r1, r2 in itt.product(r1s, outs[e])
    }


def iter_unary_patterns(
    pairs: Mapping[int, Set[Tuple[int, int]]],
) -> Iterable[PatternMatch]:
    r"""
    Yield unary patterns from pre-indexed triples.

    =============  ===============================
    Pattern        Equation
    =============  ===============================
    Symmetry       $r(x, y) \implies r(y, x)$
    Anti-Symmetry  $r(x, y) \implies \neg r(y, x)$
    =============  ===============================

    :param pairs:
        A mapping from relations to the set of entity pairs.

    :yields: A pattern match tuple of relation_id, pattern_type, support, and confidence.
    """
    logger.debug("Evaluating unary patterns: {symmetry, anti-symmetry}")
    for r, ht in pairs.items():
        support = len(ht)
        rev_ht = {(t, h) for h, t in ht}
        confidence = len(ht.intersection(rev_ht)) / support
        yield PatternMatch(r, PatternTypeEnum.symmetry, support, confidence)
        confidence = len(ht.difference(rev_ht)) / support
        yield PatternMatch(r, PatternTypeEnum.anti_symmetry, support, 1 - confidence)


def iter_binary_patterns(
    pairs: Mapping[int, Set[Tuple[int, int]]],
) -> Iterable[PatternMatch]:
    r"""
    Yield binary patterns from pre-indexed triples.

    =========  ===========================
    Pattern    Equation
    =========  ===========================
    Inversion  $r'(x, y) \implies r(y, x)$
    =========  ===========================

    :param pairs:
        A mapping from relations to the set of entity pairs.

    :yields: A pattern match tuple of relation_id, pattern_type, support, and confidence.
    """
    logger.debug("Evaluating binary patterns: {inversion}")
    for (_r1, ht1), (r, ht2) in itt.combinations(pairs.items(), r=2):
        support = len(ht1)
        confidence = len(ht1.intersection(ht2)) / support
        yield PatternMatch(r, PatternTypeEnum.inversion, support, confidence)


def iter_ternary_patterns(
    mapped_triples: Collection[Tuple[int, int, int]],
    pairs: Mapping[int, Set[Tuple[int, int]]],
) -> Iterable[PatternMatch]:
    r"""
    Yield ternary patterns from pre-indexed triples.

    ===========  ===========================================
    Pattern      Equation
    ===========  ===========================================
    Composition  $r'(x, y) \land r''(y, z) \implies r(x, z)$
    ===========  ===========================================

    :param mapped_triples:
        A collection of ID-based triples.
    :param pairs:
        A mapping from relations to the set of entity pairs.

    :yields: A pattern match tuple of relation_id, pattern_type, support, and confidence.
    """
    logger.debug("Evaluating ternary patterns: {composition}")
    # composition r1(x, y) & r2(y, z) => r(x, z)
    # indexing triples for fast join r1 & r2
    adj: DefaultDict[int, DefaultDict[int, Set[int]]] = defaultdict(lambda: defaultdict(set))
    for h, r, t in mapped_triples:
        adj[r][h].add(t)
    # actual evaluation of the pattern
    for r1, r2 in tqdm(
        composition_candidates(mapped_triples),
        desc="Checking ternary patterns",
        unit="pattern",
        unit_scale=True,
    ):
        lhs = {
            (x, z)
            for x, y in pairs[r1]
            for z in adj[r2]
        }
        support = len(lhs)
        # skip empty support
        # TODO: Can this happen after pre-filtering?
        if not support:
            continue
        for r, ht in pairs.items():
            confidence = len(lhs.intersection(ht)) / support
            yield PatternMatch(r, PatternTypeEnum.composition, support, confidence)


def iter_patterns(
    mapped_triples: Collection[Tuple[int, int, int]],
) -> Iterable[PatternMatch]:
    """Iterate over unary, binary, and ternary patterns.

    :param mapped_triples:
        A collection of ID-based triples.

    :yields: Patterns from :func:`iter_unary_patterns`, func:`iter_binary_patterns`, and :func:`iter_ternary_patterns`.
    """
    # indexing triples for fast lookup of entity pair sets
    pairs: DefaultDict[int, Set[Tuple[int, int]]] = defaultdict(set)
    for h, r, t in mapped_triples:
        pairs[r].add((h, t))

    yield from iter_unary_patterns(pairs=pairs)
    yield from iter_binary_patterns(pairs=pairs)
    yield from iter_ternary_patterns(mapped_triples, pairs=pairs)


def triple_set_hash(
    mapped_triples: Collection[Tuple[int, int, int]],
) -> str:
    """
    Compute an order-invariant hash value for a set of triples given as list of triples.

    :param mapped_triples:
        The ID-based triples.

    :return:
        The hash digest as hex-value string.
    """
    # sort first, for triple order invariance
    return hashlib.sha512("".join(map(str, sorted(mapped_triples))).encode("utf8")).hexdigest()


def _is_injective_mapping(
    df: pd.DataFrame,
    source: str,
    target: str,
) -> Tuple[int, float]:
    """
    (Soft-)Determine whether there is an injective mapping from source to target.

    :param df:
        The dataframe.
    :param source:
        The source column.
    :param target:
        The target column.

    :return:
        The number of unique source values, and the relative frequency of unique target per source.
    """
    grouped = df.groupby(by=source)
    support = len(grouped)
    n_unique = grouped.agg({target: "nunique"})[target]
    conf = (n_unique <= 1).mean()
    return support, conf


def iter_relation_cardinality_types(
    mapped_triples: Collection[Tuple[int, int, int]],
) -> Iterable[PatternMatch]:
    """Iterate over relation-cardinality types.

    :param mapped_triples:
        A collection of ID-based triples.

    :yields: A pattern match tuple of relation_id, pattern_type, support, and confidence.
    """
    df = pd.DataFrame(data=mapped_triples, columns=["h", "r", "t"])
    for relation, group in df.groupby(by="r"):
        n_unique_heads, head_injective_conf = _is_injective_mapping(df=group, source="h", target="t")
        n_unique_tails, tail_injective_conf = _is_injective_mapping(df=group, source="t", target="h")
        # TODO: what is the support?
        support = n_unique_heads + n_unique_tails
        yield PatternMatch(relation, CardinalityTypeEnum.one_to_one, support, head_injective_conf * tail_injective_conf)
        yield PatternMatch(
            relation,
            CardinalityTypeEnum.one_to_many,
            support,
            (1 - head_injective_conf) * tail_injective_conf,
        )
        yield PatternMatch(
            relation,
            CardinalityTypeEnum.many_to_one,
            support,
            head_injective_conf * (1 - tail_injective_conf),
        )
        yield PatternMatch(
            relation,
            CardinalityTypeEnum.many_to_many,
            support,
            (1 - head_injective_conf) * (1 - tail_injective_conf),
        )


def _get_skyline(
    xs: Iterable[Tuple[int, float]],
) -> Iterable[Tuple[int, float]]:
    """Calculate 2-D skyline."""
    # cf. https://stackoverflow.com/questions/19059878/dominant-set-of-points-in-on
    largest_y = float("-inf")
    # sort decreasingly. i dominates j for all j > i in x-dimension
    for x_i, y_i in sorted(xs, reverse=True):
        # if it is also dominated by any y, it is not part of the skyline
        if y_i > largest_y:
            yield x_i, y_i
            largest_y = y_i


def skyline(data_stream: Iterable[PatternMatch]) -> Iterable[PatternMatch]:
    """
    Keep only those entries which are in the support-confidence skyline.

    A pair $(s, c)$ dominates $(s', c')$ if $s > s'$ and $c > c'$. The skyline contains those entries which are not
    dominated by any other entry.

    :param data_stream:
        The stream of data, comprising tuples (relation_id, pattern-type, support, confidence).

    :yields: An entry from the support-confidence skyline.
    """
    # group by (relation id, pattern type)
    data: DefaultDict[Tuple[int, str], Set[Tuple[int, float]]] = defaultdict(set)
    for tup in data_stream:
        data[tup[:2]].add(tup[2:])
    # for each group, yield from skyline
    for (r_id, pat), values in data.items():
        for supp, conf in _get_skyline(values):
            yield PatternMatch(r_id, pat, supp, conf)


def get_id_counts(
    id_tensor: torch.LongTensor,
    num_ids: Optional[int] = None,
) -> numpy.ndarray:
    """Create a dense tensor of ID counts.

    :param id_tensor:
        The tensor of IDs.
    :param num_ids:
        The number of IDs.

    :return: shape: (num_ids,)
         The counts for each individual ID from {0, 1, ..., num_ids-1}.
    """
    unique, counts = id_tensor.unique(return_counts=True)
    if num_ids is None:
        num_ids = unique.max().item() + 1
    total_counts = numpy.zeros(shape=(num_ids,), dtype=numpy.int64)
    total_counts[unique.numpy()] = counts.numpy()
    return total_counts


def get_relation_counts(
    mapped_triples: MappedTriples,
) -> pd.DataFrame:
    """
    Create a dataframe of relation frequency.

    :param mapped_triples: shape: (num_triples, 3)
        The mapped triples.

    :return:
        A dataframe with columns ( relation_id | count )
    """
    unique, counts = mapped_triples[:, 1].unique(return_counts=True)
    return pd.DataFrame(data=dict(relation_id=unique.numpy(), count=counts.numpy()))


def relation_pattern_types(
    mapped_triples: Collection[Tuple[int, int, int]],
) -> pd.DataFrame:
    r"""
    Categorize relations based on patterns from RotatE [sun2019]_.

    The relation classifications are based upon checking whether the corresponding rules hold with sufficient support
    and confidence. By default, we do not require a minimum support, however, a relatively high confidence.

    The following four non-exclusive classes for relations are considered:

    - symmetry
    - anti-symmetry
    - inversion
    - composition

    This method generally follows the terminology of association rule mining. The patterns are expressed as

    .. math ::

        X_1 \land \cdot \land X_k \implies Y

    where $X_i$ is of the form $r_i(h_i, t_i)$, and some of the $h_i / t_i$ might re-occur in other atoms.
    The *support* of a pattern is the number of distinct instantiations of all variables for the left hand side.
    The *confidence* is the proportion of these instantiations where the right-hand side is also true.
    """
    # determine patterns from triples
    base = iter_patterns(mapped_triples=mapped_triples)

    # drop zero-confidence
    base = (
        pattern
        for pattern in base
        if pattern.confidence > 0
    )

    # keep only skyline
    base = skyline(base)

    # create data frame
    return pd.DataFrame(
        data=list(base),
        columns=["relation_id", "pattern", "support", "confidence"],
    ).sort_values(by=["pattern", "relation_id", "confidence", "support"])


def relation_cardinality_types(
    mapped_triples: Collection[Tuple[int, int, int]],
) -> pd.DataFrame:
    r"""
    Determine the relation cardinality types.

    The possible types are given in relation_cardinality_types.

    .. note ::
        In the current implementation, we have by definition

        .. math ::
            1 = \sum_{type} conf(relation, type)

    .. note ::
       These relation types are also mentioned in [wang2014]_. However, the paper does not provide any details on
       their definition, nor is any code provided. Thus, their exact procedure is unknown and may not coincide with this
       implementation.

    :param mapped_triples:
        The ID-based triples.

    :return:
        A dataframe with columns ( relation_id | relation_type )
    """
    # iterate relation types
    base = iter_relation_cardinality_types(mapped_triples=mapped_triples)

    # drop zero-confidence
    base = (
        pattern
        for pattern in base
        if pattern.confidence > 0
    )

    # keep only skyline
    # does not make much sense, since there is always exactly one entry per (relation, pattern) pair
    # base = skyline(base)

    # create data frame
    return pd.DataFrame(
        data=base,
        columns=["relation_id", "relation_type", "support", "confidence"],
    )
