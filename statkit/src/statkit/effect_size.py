"""Standardised mean-difference effect sizes."""
import math

import numpy as np

from ._util import as_sample


def cohens_d(a, b):
    """Cohen's d for two independent samples (pooled standard deviation)."""
    a, b = as_sample(a, "a"), as_sample(b, "b")
    na, nb = a.size, b.size
    pooled_var = ((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2)
    if pooled_var == 0:
        raise ValueError("pooled variance is zero; effect size is undefined")
    return float((a.mean() - b.mean()) / math.sqrt(pooled_var))


def hedges_g(a, b):
    """Hedges' g: Cohen's d with the small-sample bias correction."""
    a, b = np.asarray(a), np.asarray(b)
    df = a.size + b.size - 2
    correction = 1 - 3 / (4 * df - 1)
    return cohens_d(a, b) * correction
