"""PyKEEN internal "nn" module."""

from class_resolver import ClassResolver

from . import init
from .combination import (
    Combination,
    ComplexSeparatedCombination,
    ConcatAggregationCombination,
    ConcatCombination,
    ConcatProjectionCombination,
    GatedCombination,
)
from .message_passing import RGCNRepresentation
from .meta import FeatureEnrichedEmbedding, MLPTransformedRepresentation
from .modules import (
    AutoSFInteraction,
    BoxEInteraction,
    ComplExInteraction,
    ConvEInteraction,
    ConvKBInteraction,
    CPInteraction,
    CrossEInteraction,
    DistMAInteraction,
    DistMultInteraction,
    ERMLPEInteraction,
    ERMLPInteraction,
    HolEInteraction,
    Interaction,
    KG2EInteraction,
    LineaREInteraction,
    MonotonicAffineTransformationInteraction,
    MultiLinearTuckerInteraction,
    MuREInteraction,
    NTNInteraction,
    PairREInteraction,
    ProjEInteraction,
    QuatEInteraction,
    RESCALInteraction,
    RotatEInteraction,
    SEInteraction,
    SimplEInteraction,
    TorusEInteraction,
    TransDInteraction,
    TransEInteraction,
    TransFInteraction,
    TransformerInteraction,
    TransHInteraction,
    TransRInteraction,
    TripleREInteraction,
    TuckERInteraction,
    UMInteraction,
    interaction_resolver,
)
from .node_piece import NodePieceRepresentation, TokenizationRepresentation, tokenizer_resolver
from .pyg import (
    FeaturizedMessagePassingRepresentation,
    SimpleMessagePassingRepresentation,
    TypedMessagePassingRepresentation,
)
from .representation import (
    BackfillRepresentation,
    BiomedicalCURIERepresentation,
    CachedTextRepresentation,
    CombinedRepresentation,
    Embedding,
    EmbeddingBagRepresentation,
    LowRankRepresentation,
    MultiBackfillRepresentation,
    Partition,
    PartitionRepresentation,
    Representation,
    SingleCompGCNRepresentation,
    SubsetRepresentation,
    TensorTrainRepresentation,
    TextRepresentation,
    TransformedRepresentation,
    WikidataTextRepresentation,
)
from .vision import VisualRepresentation, WikidataVisualRepresentation

__all__ = [
    # REPRESENTATION
    # base
    "Representation",
    # concrete
    "Embedding",
    "FeaturizedMessagePassingRepresentation",
    "LowRankRepresentation",
    "NodePieceRepresentation",
    "PartitionRepresentation",
    "Partition",
    "EmbeddingBagRepresentation",
    "MultiBackfillRepresentation",
    "BackfillRepresentation",
    "RGCNRepresentation",
    "SimpleMessagePassingRepresentation",
    "SingleCompGCNRepresentation",
    "SubsetRepresentation",
    "TokenizationRepresentation",
    "TypedMessagePassingRepresentation",
    "FeaturizedMessagePassingRepresentation",
    "FeatureEnrichedEmbedding",
    "CombinedRepresentation",
    "TensorTrainRepresentation",
    "TextRepresentation",
    "TransformedRepresentation",
    "WikidataTextRepresentation",
    "BiomedicalCURIERepresentation",
    "VisualRepresentation",
    "WikidataVisualRepresentation",
    "MLPTransformedRepresentation",
    "tokenizer_resolver",
    "representation_resolver",
    # INITIALIZER
    "init",
    # INTERACTIONS
    "Interaction",
    # Adapter classes
    "MonotonicAffineTransformationInteraction",
    # Concrete Classes
    "AutoSFInteraction",
    "BoxEInteraction",
    "ComplExInteraction",
    "ConvEInteraction",
    "ConvKBInteraction",
    "CPInteraction",
    "CrossEInteraction",
    "DistMAInteraction",
    "DistMultInteraction",
    "ERMLPEInteraction",
    "ERMLPInteraction",
    "HolEInteraction",
    "KG2EInteraction",
    "LineaREInteraction",
    "MultiLinearTuckerInteraction",
    "MuREInteraction",
    "NTNInteraction",
    "PairREInteraction",
    "ProjEInteraction",
    "QuatEInteraction",
    "RESCALInteraction",
    "RotatEInteraction",
    "SEInteraction",
    "SimplEInteraction",
    "TorusEInteraction",
    "TransDInteraction",
    "TransEInteraction",
    "TransFInteraction",
    "TransformerInteraction",
    "TransHInteraction",
    "TransRInteraction",
    "TripleREInteraction",
    "TuckERInteraction",
    "UMInteraction",
    "interaction_resolver",
    # combinations
    "Combination",
    "ComplexSeparatedCombination",
    "ConcatAggregationCombination",
    "ConcatCombination",
    "ConcatProjectionCombination",
    "GatedCombination",
]

#: A resolver for representations
representation_resolver: ClassResolver[Representation] = ClassResolver.from_subclasses(
    base=Representation,
    default=Embedding,
    skip={
        CachedTextRepresentation,
    },
)
