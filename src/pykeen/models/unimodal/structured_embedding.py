# -*- coding: utf-8 -*-

"""Implementation of structured model (SE)."""

import functools
from typing import Optional

import numpy as np
from torch import nn
from torch.nn import functional

from .. import SingleVectorEmbeddingModel
from ...losses import Loss
from ...nn.init import xavier_uniform_
from ...nn.modules import StructuredEmbeddingInteractionFunction
from ...regularizers import Regularizer
from ...triples import TriplesFactory
from ...typing import DeviceHint
from ...utils import compose

__all__ = [
    'StructuredEmbedding',
]


class StructuredEmbedding(SingleVectorEmbeddingModel):
    r"""An implementation of the Structured Embedding (SE) published by [bordes2011]_.

    SE applies role- and relation-specific projection matrices
    $\textbf{M}_{r}^{h}, \textbf{M}_{r}^{t} \in \mathbb{R}^{d \times d}$ to the head and tail
    entities' embeddings before computing their differences. Then, the $l_p$ norm is applied
    and the result is negated such that smaller differences are considered better.

    .. math::

        f(h, r, t) = - \|\textbf{M}_{r}^{h} \textbf{e}_h  - \textbf{M}_{r}^{t} \textbf{e}_t\|_p

    By employing different projections for the embeddings of the head and tail entities, SE explicitly differentiates
    the role of an entity as either the subject or object.
    """

    #: The default strategy for optimizing the model's hyper-parameters
    hpo_default = dict(
        embedding_dim=dict(type=int, low=50, high=350, q=25),
        scoring_fct_norm=dict(type=int, low=1, high=2),
    )

    def __init__(
        self,
        triples_factory: TriplesFactory,
        embedding_dim: int = 50,
        automatic_memory_optimization: Optional[bool] = None,
        scoring_fct_norm: int = 1,
        loss: Optional[Loss] = None,
        preferred_device: DeviceHint = None,
        random_seed: Optional[int] = None,
        regularizer: Optional[Regularizer] = None,
    ) -> None:
        r"""Initialize SE.

        :param embedding_dim: The entity embedding dimension $d$. Is usually $d \in [50, 300]$.
        :param scoring_fct_norm: The $l_p$ norm. Usually 1 for SE.
        """
        # Embeddings
        init_bound = 6 / np.sqrt(embedding_dim)
        # Initialise relation embeddings to unit length
        initializer = compose(
            functools.partial(nn.init.uniform_, a=-init_bound, b=+init_bound),
            functional.normalize,
        )
        super().__init__(
            triples_factory=triples_factory,
            interaction_function=StructuredEmbeddingInteractionFunction(
                p=scoring_fct_norm,
                power_norm=False,
            ),
            embedding_dim=embedding_dim,
            relation_dim=2 * embedding_dim ** 2,  # head and tail projection matrices
            automatic_memory_optimization=automatic_memory_optimization,
            loss=loss,
            preferred_device=preferred_device,
            random_seed=random_seed,
            regularizer=regularizer,
            entity_initializer=xavier_uniform_,
            entity_constrainer=functional.normalize,
            relation_initializer=initializer,
        )
