import numpy as np
import pytest

from statkit import (benjamini_hochberg, bonferroni, bootstrap_ci, cohens_d, hedges_g, holm,
                     permutation_test)
from statkit.cli import main


def test_cohens_d_known_value():
    a, b = [2, 4, 6, 8], [1, 3, 5, 7]
    # equal variances (sd = sqrt(20/3)), mean difference 1
    assert cohens_d(a, b) == pytest.approx(1 / np.sqrt(20 / 3))


def test_cohens_d_sign_and_antisymmetry():
    a, b = [5, 6, 7, 8], [1, 2, 3, 4]
    assert cohens_d(a, b) > 0
    assert cohens_d(a, b) == pytest.approx(-cohens_d(b, a))


def test_hedges_g_smaller_than_d():
    a, b = [5, 6, 7, 8], [1, 2, 3, 5]
    assert abs(hedges_g(a, b)) < abs(cohens_d(a, b))


def test_zero_variance_rejected():
    with pytest.raises(ValueError):
        cohens_d([1, 1, 1], [1, 1, 1])


def test_bootstrap_reproducible_and_covers_mean():
    rng = np.random.default_rng(1)
    x = rng.normal(10, 2, 200)
    r1 = bootstrap_ci(x, seed=7, n_boot=2000)
    r2 = bootstrap_ci(x, seed=7, n_boot=2000)
    assert r1 == r2
    est, lo, hi = r1
    assert lo < est < hi
    assert lo < 10 < hi


def test_bootstrap_validation():
    with pytest.raises(ValueError):
        bootstrap_ci([1, 2, 3], alpha=1.5)
    with pytest.raises(ValueError):
        bootstrap_ci([1.0, float("nan")])


def test_permutation_detects_difference():
    rng = np.random.default_rng(0)
    a, b = rng.normal(0, 1, 40), rng.normal(2, 1, 40)
    _, p = permutation_test(a, b, n_perm=2000, seed=3)
    assert p < 0.01


def test_permutation_null_not_significant_and_never_zero():
    rng = np.random.default_rng(0)
    a, b = rng.normal(0, 1, 40), rng.normal(0, 1, 40)
    _, p = permutation_test(a, b, n_perm=2000, seed=3)
    assert 0.05 < p <= 1
    _, p0 = permutation_test([100, 101, 102], [0, 1, 2], n_perm=500, seed=1)
    assert p0 > 0


def test_bonferroni_and_holm():
    p = [0.01, 0.04, 0.03]
    assert bonferroni(p) == pytest.approx([0.03, 0.12, 0.09])
    assert holm(p) == pytest.approx([0.03, 0.06, 0.06])


def test_benjamini_hochberg_known_example():
    p = [0.01, 0.04, 0.03, 0.005]
    assert benjamini_hochberg(p) == pytest.approx([0.02, 0.04, 0.04, 0.02])


@pytest.mark.parametrize("fn", [bonferroni, holm, benjamini_hochberg])
def test_corrections_bounds_and_validation(fn):
    out = fn([0.5, 0.9, 0.99])
    assert np.all(out <= 1) and np.all(out >= 0)
    with pytest.raises(ValueError):
        fn([0.5, 1.2])
    with pytest.raises(ValueError):
        fn([])


def test_cli(tmp_path, capsys):
    for name, vals in (("a.csv", [1, 2, 3, 4, 5]), ("b.csv", [6, 7, 8, 9, 10])):
        (tmp_path / name).write_text("score\n" + "\n".join(map(str, vals)) + "\n")
    main([str(tmp_path / "a.csv"), str(tmp_path / "b.csv"), "--column", "score",
          "--n-boot", "200"])
    out = capsys.readouterr().out
    assert '"mean_difference": -5.0' in out
