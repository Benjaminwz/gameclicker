import numpy as np


def as_sample(x, name="sample", min_size=2):
    """Convert input to a 1-D float array and validate it."""
    arr = np.asarray(x, dtype=float)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if arr.size < min_size:
        raise ValueError(f"{name} needs at least {min_size} observations")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains NaN or infinite values")
    return arr
