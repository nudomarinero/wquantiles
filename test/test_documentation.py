"""Checks that the numbers quoted in the README and drawn in the committed
figure are still the ones the library produces.

Documentation goes stale silently; these fail loudly instead. If one of them
breaks after a deliberate change, update the prose and run

    uv run --group docs python docs/make_figure.py
"""
import numpy as np
import pytest

from wquantiles import median, quantile, quantile_1D

# The sample used in the README's quick start and in both panels of the figure.
FIGURE_DATA = np.array([1.0, 2.0, 3.0, 5.0, 8.0])
FIGURE_WEIGHTS = np.array([1.0, 3.0, 1.0, 4.0, 2.0])

NUMPY_HAS_WEIGHTS = int(np.__version__.split(".")[0]) >= 2
NUMPY_HAS_METHOD = tuple(int(p) for p in np.__version__.split(".")[:2]) >= (1, 22)


def test_quick_start():
    assert median(FIGURE_DATA, FIGURE_WEIGHTS) == 3.8
    assert quantile(FIGURE_DATA, FIGURE_WEIGHTS, 0.25) == 2.125


def test_figure_annotations():
    """The left panel is labelled "weighted median = 3.8"."""
    assert quantile_1D(FIGURE_DATA, FIGURE_WEIGHTS, 0.5) == 3.8


@pytest.mark.skipif(not NUMPY_HAS_WEIGHTS, reason="np.quantile gained weights in numpy 2.0")
def test_figure_discrete_comparison():
    """The right panel puts numpy's discrete answer at 5."""
    assert np.quantile(FIGURE_DATA, 0.5, weights=FIGURE_WEIGHTS,
                       method="inverted_cdf") == 5.0


@pytest.mark.skipif(not NUMPY_HAS_WEIGHTS, reason="np.quantile gained weights in numpy 2.0")
@pytest.mark.parametrize("data, weights, q, ours, theirs", [
    ([1, 2, 3], [100, 1, 1], 0.50, 1.0198019801980198, 1),
    ([1, 2, 3], [100, 1, 1], 0.75, 1.5247524752475248, 1),
    ([1, 2, 3, 5, 8], [1, 3, 1, 4, 2], 0.50, 3.8, 5),
    ([1, 2, 3, 5, 8], [1, 3, 1, 4, 2], 0.75, 6.25, 5),
    ([10, 25, 30, 35, 50], [1, 1, 4, 2, 1], 0.25, 26.5, 30),
])
def test_comparison_table(data, weights, q, ours, theirs):
    """Every row of the README's `numpy.quantile` comparison table."""
    data, weights = np.array(data, float), np.array(weights, float)
    assert quantile_1D(data, weights, q) == pytest.approx(ours)
    assert np.quantile(data, q, weights=weights, method="inverted_cdf") == theirs


def test_issue_4_example():
    """The README explains why this is not 1.0."""
    assert median(np.array([1, 2, 3]), np.array([100, 1, 1])) == 1.0198019801980198


def test_behaviour_change_examples():
    """The two 0.7 behaviour-change sections."""
    assert quantile_1D([1, 2, 2, 3], [1, 5, 0.5, 1], 0.2) == pytest.approx(1.308, abs=5e-4)
    assert quantile_1D([1, 1.5, 3], [1, 0, 1], 0.5) == 2.0


@pytest.mark.skipif(not NUMPY_HAS_METHOD, reason="numpy < 1.22 has no `method=`")
def test_hazen_equivalence_claim():
    """The README says: equal weights and no repeats give numpy's hazen."""
    distinct = np.array([0, 10, 20, 25, 30, 35, 50.0])
    for q in (0.1, 0.25, 0.5, 0.75, 0.9):
        assert quantile_1D(distinct, np.ones_like(distinct), q) == pytest.approx(
            np.quantile(distinct, q, method="hazen"), rel=1e-12, abs=1e-12
        )
