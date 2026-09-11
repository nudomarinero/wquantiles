"""Tests for input validation and the behaviour changes introduced in 0.7."""
import numpy as np
import pytest

import wquantiles
from wquantiles import median, quantile, quantile_1D

DATA = np.array([0, 10, 20, 25, 30, 30, 35, 50.0])
WEIGHTS = np.array([0, 1, 0, 1, 2, 2, 2, 1.0])


# --- results that must not change ------------------------------------------

def test_results_unchanged_from_0_6():
    assert quantile_1D(DATA, WEIGHTS, 0.5) == 30.0
    assert quantile_1D(DATA, np.ones(8), 0.5) == 27.5
    assert median(np.array([1.0, 2, 3]), np.array([100.0, 1, 1])) == 1.0198019801980198


@pytest.mark.skipif(
    tuple(int(p) for p in np.__version__.split(".")[:2]) < (1, 22),
    reason="np.quantile gained the `method` keyword in numpy 1.22",
)
def test_unit_weights_match_numpy_hazen():
    """With unit weights this is exactly numpy's Hyndman-Fan type 5."""
    qs = [0.05, 0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9]
    ours = [quantile_1D(DATA, np.ones_like(DATA), q) for q in qs]
    theirs = np.quantile(DATA, qs, method="hazen")
    np.testing.assert_array_equal(ours, theirs)


def test_median_is_quantile_at_one_half():
    assert median(DATA, WEIGHTS) == quantile(DATA, WEIGHTS, 0.5)


# --- input coercion (issue #11) --------------------------------------------

@pytest.mark.parametrize("func", [quantile_1D, quantile])
def test_accepts_lists(func):
    assert func([1, 2, 3, 4, 5], [0.15, 0.1, 0.2, 0.3, 0.25], 0.5) == pytest.approx(3.6)


def test_median_accepts_lists():
    """The failure reported in issue #11."""
    assert median([1, 2, 3, 4, 5], [0.15, 0.1, 0.2, 0.3, 0.25]) == pytest.approx(3.6)


# --- shape validation -------------------------------------------------------

def test_zero_dimensional_data_raises():
    """Previously returned None: the TypeError was built but never raised."""
    with pytest.raises(TypeError, match="at least one dimension"):
        quantile(np.array(5.0), np.array(1.0), 0.5)


def test_multidimensional_data_rejected_by_quantile_1D():
    with pytest.raises(TypeError, match="one dimensional"):
        quantile_1D(np.ones((2, 3)), np.ones(3), 0.5)


def test_multidimensional_weights_rejected():
    with pytest.raises(TypeError, match="weights must be a one dimensional"):
        quantile_1D(np.ones(6), np.ones((2, 3)), 0.5)


def test_mismatched_lengths_rejected():
    with pytest.raises(TypeError, match="must be the same"):
        quantile_1D(np.ones(4), np.ones(3), 0.5)


def test_empty_data_rejected():
    with pytest.raises(ValueError, match="must not be empty"):
        quantile_1D(np.array([]), np.array([]), 0.5)


# --- weight validation ------------------------------------------------------

def test_zero_sum_weights_raise():
    """Previously returned nan."""
    with pytest.raises(ValueError, match="must not be zero"):
        quantile_1D(DATA, np.zeros(8), 0.5)


def test_negative_weights_raise():
    """Previously returned 2.0: Pn was non-monotonic and np.interp undefined."""
    with pytest.raises(ValueError, match="must not be negative"):
        quantile_1D(np.array([1.0, 2, 3]), np.array([1.0, -5, 1]), 0.5)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_non_finite_weights_raise(bad):
    """Previously returned nan."""
    with pytest.raises(ValueError, match="must all be finite"):
        quantile_1D(np.array([1.0, 2, 3]), np.array([1.0, bad, 1]), 0.5)


def test_zero_weights_are_allowed():
    """Zero is a legitimate weight; only an all-zero array is rejected."""
    assert quantile_1D(DATA, WEIGHTS, 0.5) == 30.0


# --- NaN in the data --------------------------------------------------------

def test_nan_in_data_propagates():
    """Previously returned 3.0. numpy's np.quantile returns nan here too."""
    assert np.isnan(quantile_1D(np.array([1.0, np.nan, 3]), np.ones(3), 0.5))


def test_invalid_weights_win_over_nan_data():
    with pytest.raises(ValueError):
        quantile_1D(np.array([1.0, np.nan, 3]), np.array([1.0, -1, 1]), 0.5)


# --- q validation -----------------------------------------------------------

@pytest.mark.parametrize("bad_q", [-0.1, 1.1])
def test_q_out_of_range_raises(bad_q):
    with pytest.raises(ValueError, match="between 0. and 1."):
        quantile_1D(DATA, WEIGHTS, bad_q)


@pytest.mark.parametrize("edge_q", [0.0, 1.0])
def test_q_at_the_edges_is_allowed(edge_q):
    assert quantile_1D(DATA, WEIGHTS, edge_q) in (DATA.min(), DATA.max())


# --- the deprecated `quantile=` keyword -------------------------------------

@pytest.mark.parametrize("func", [quantile_1D, quantile])
def test_quantile_keyword_still_works_but_warns(func):
    with pytest.warns(DeprecationWarning, match="use `q` instead"):
        result = func(DATA, WEIGHTS, quantile=0.5)
    assert result == 30.0


@pytest.mark.parametrize("func", [quantile_1D, quantile])
def test_passing_q_twice_raises(func):
    with pytest.raises(TypeError, match="passed twice"):
        func(DATA, WEIGHTS, 0.5, quantile=0.5)


@pytest.mark.parametrize("func", [quantile_1D, quantile])
def test_missing_q_raises(func):
    with pytest.raises(TypeError, match="missing a required argument"):
        func(DATA, WEIGHTS)


# --- module surface ---------------------------------------------------------

def test_version_matches_installed_metadata():
    from importlib.metadata import version

    assert wquantiles.__version__ == version("wquantiles")
    assert wquantiles.__version__ != "0.4"


def test_public_names():
    assert wquantiles.__all__ == ["quantile_1D", "quantile", "median"]
