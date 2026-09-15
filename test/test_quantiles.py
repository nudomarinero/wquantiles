"""Core behaviour of the weighted quantile functions."""
import warnings

import numpy as np
import pytest

from wquantiles import median, quantile, quantile_1D

NUMPY_HAS_METHOD = tuple(int(p) for p in np.__version__.split(".")[:2]) >= (1, 22)

# Sorted and unsorted spellings of the same weighted sample.
SORTED = np.array([0, 10, 20, 25, 30, 30, 35, 50.0])
SORTED_W = np.array([0, 1, 0, 1, 2, 2, 2, 1.0])
UNSORTED = np.array([30, 25, 0, 50, 30, 20, 35, 10.0])
UNSORTED_W = np.array([2, 1, 0, 1, 2, 0, 2, 1.0])


@pytest.mark.parametrize("data, weights", [(SORTED, SORTED_W), (UNSORTED, UNSORTED_W)])
def test_weighted_median(data, weights):
    assert quantile_1D(data, weights, 0.5) == 30


@pytest.mark.parametrize("data", [SORTED, UNSORTED])
def test_unit_weights_reproduce_the_plain_median(data):
    assert quantile_1D(data, np.ones_like(data), 0.5) == np.median(data)


@pytest.mark.skipif(not NUMPY_HAS_METHOD, reason="numpy < 1.22 has no `method=`")
@pytest.mark.parametrize("q", [0.05, 0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9])
def test_unit_weights_match_numpy_hazen(q):
    """The anchor for the whole library: with equal weights this is exactly
    numpy's Hyndman-Fan type 5."""
    assert quantile_1D(SORTED, np.ones_like(SORTED), q) == np.quantile(
        SORTED, q, method="hazen"
    )


def test_median_is_an_alias():
    assert median(SORTED, SORTED_W) == quantile(SORTED, SORTED_W, 0.5)


def test_one_dimensional_input_dispatches_to_quantile_1D():
    assert quantile(SORTED, SORTED_W, 0.3) == quantile_1D(SORTED, SORTED_W, 0.3)


@pytest.mark.parametrize("shape", [(4, 5), (3, 4, 5), (2, 3, 4, 5)])
@pytest.mark.parametrize("q", [0.25, 0.5, 0.75])
def test_weights_are_applied_along_the_last_axis(shape, q):
    """`quantile` must be `quantile_1D` applied to each row of the last axis.

    The expectation is derived rather than hardcoded: the previous version of
    this test carried a 5x5x5 block of magic numbers with no derivation, so
    there was no way to tell a real regression from a stale constant.
    """
    rng = np.random.default_rng(20260916)
    data = rng.normal(size=shape) * 100
    weights = rng.random(shape[-1]) + 0.01

    result = quantile(data, weights, q)
    assert result.shape == shape[:-1]

    flat = data.reshape(-1, shape[-1])
    expected = np.array([quantile_1D(row, weights, q) for row in flat])
    np.testing.assert_array_equal(result, expected.reshape(shape[:-1]))


def test_multidimensional_regression_anchor():
    """An expectation worked out by hand, so a change in the maths cannot slip
    past the test above, which derives its own expectation from the code.

    Each row is four consecutive integers with weights [1, 2, 3, 4]:

        Sn = [1, 3, 6, 10]
        Pn = (Sn - 0.5w) / 10 = [0.05, 0.2, 0.45, 0.8]

    q=0.5 falls between (0.45, x+2) and (0.8, x+3), so the result is
    x + 2 + 0.05/0.35 = x + 15/7, with x the first value of the row.
    """
    data = np.arange(24.0).reshape(2, 3, 4)
    weights = np.array([1.0, 2.0, 3.0, 4.0])
    expected = (15 / 7 + 4 * np.arange(6.0)).reshape(2, 3)
    np.testing.assert_allclose(quantile(data, weights, 0.5), expected)


class TestDeprecatedModule:
    def test_importing_weighted_warns(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            import weighted  # noqa: F401

            assert len(caught) == 1
            assert issubclass(caught[-1].category, DeprecationWarning)
            assert "deprecated" in str(caught[-1].message)

    def test_weighted_re_exports_the_public_api(self):
        import weighted

        assert weighted.quantile_1D(SORTED, SORTED_W, 0.5) == 30
        assert weighted.median(SORTED, SORTED_W) == 30
