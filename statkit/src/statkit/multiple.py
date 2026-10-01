"""Multiple-comparison corrections. Each returns adjusted p-values in input order."""
import numpy as np


def _check(pvals):
    p = np.asarray(pvals, dtype=float)
    if p.ndim != 1 or p.size == 0:
        raise ValueError("pvals must be a non-empty 1-D sequence")
    if np.any((p < 0) | (p > 1)) or np.any(np.isnan(p)):
        raise ValueError("p-values must lie in [0, 1]")
    return p


def bonferroni(pvals):
    """Bonferroni: multiply by the number of tests."""
    p = _check(pvals)
    return np.minimum(p * p.size, 1.0)


def holm(pvals):
    """Holm step-down (uniformly more powerful than Bonferroni)."""
    p = _check(pvals)
    m = p.size
    order = np.argsort(p)
    adj = np.maximum.accumulate((m - np.arange(m)) * p[order])
    out = np.empty(m)
    out[order] = np.minimum(adj, 1.0)
    return out


def benjamini_hochberg(pvals):
    """Benjamini-Hochberg FDR control (valid for independent / PRDS tests)."""
    p = _check(pvals)
    m = p.size
    order = np.argsort(p)[::-1]
    ranked = p[order] * m / (m - np.arange(m))
    adj = np.minimum.accumulate(ranked)
    out = np.empty(m)
    out[order] = np.minimum(adj, 1.0)
    return out
