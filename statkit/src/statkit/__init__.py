"""statkit: reproducible statistics helpers."""
from .bootstrap import bootstrap_ci
from .effect_size import cohens_d, hedges_g
from .multiple import benjamini_hochberg, bonferroni, holm
from .permutation import permutation_test

__all__ = [
    "bootstrap_ci", "cohens_d", "hedges_g", "permutation_test",
    "bonferroni", "holm", "benjamini_hochberg",
]
__version__ = "0.1.0"
