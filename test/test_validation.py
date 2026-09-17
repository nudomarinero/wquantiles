"""Tests for input validation and the behaviour changes introduced in 0.7."""
import numpy as np
import pytest

import wquantiles
from wquantiles import median, quantile, quantile_1D

DATA = np.array([0, 10, 20, 25, 30, 30, 35, 50.0])
WEIGHTS = np.array([0, 1, 0, 1, 2, 2, 2, 1.0])
# DATA repeats 30, and this library sums the weights of equal values, so the
# equivalences with numpy's unweighted quantiles need a fixture with no repeats.
DISTINCT = np.array([0, 10, 20, 25, 30, 35, 50.0])


# --- results that must not change ------------------------------------------

def test_results_unchanged_from_0_6_where_values_are_distinct():
    """Bit-for-bit agreement with 0.6 is guaranteed only where no value repeats
    and every weight is positive; that is where none of the 0.7 changes apply."""
    assert median(np.array([1.0, 2, 3]), np.array([100.0, 1, 1])) == 1.0198019801980198
    assert quantile_1D(DISTINCT, np.ones(7), 0.5) == 25.0


def test_tied_values_share_one_node():
    """DATA repeats 30. Dropping the zero weights and summing the tie leaves
    values [10, 25, 30, 35, 50] with weights [1, 1, 4, 2, 1], so Sn = [1, 2, 6,
    8, 9], Pn = (Sn - 0.5w)/9, and q=0.5 lands at 30 + 5/6.

    0.6 gave 30.0 here, treating the two 30s as separate nodes.
    """
    assert quantile_1D(DATA, WEIGHTS, 0.5) == pytest.approx(185 / 6)


@pytest.mark.skipif(
    tuple(int(p) for p in np.__version__.split(".")[:2]) < (1, 22),
    reason="np.quantile gained the `method` keyword in numpy 1.22",
)
def test_unit_weights_match_numpy_hazen():
    """With unit weights and distinct values this is numpy's Hyndman-Fan
    type 5. Compared approximately: numpy reaches the same number by a
    different route, so the two can disagree in the last bit."""
    qs = [0.05, 0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9]
    ours = [quantile_1D(DISTINCT, np.ones_like(DISTINCT), q) for q in qs]
    theirs = np.quantile(DISTINCT, qs, method="hazen")
    np.testing.assert_allclose(ours, theirs, rtol=1e-12, atol=1e-12)


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

def test_zero_dimensional_data_returns_the_value():
    """0.6 returned None, because the TypeError was built but never raised.

    numpy treats a scalar as a sample of one -- np.quantile(5.0, 0.5) is 5.0 --
    and so do we, rather than refusing an input with an obvious answer.
    """
    assert quantile(np.array(5.0), np.array(1.0), 0.5) == 5.0
    assert median(5.0, 1.0) == 5.0


def test_multidimensional_data_rejected_by_quantile_1D():
    with pytest.raises(TypeError, match="one dimensional"):
        quantile_1D(np.ones((2, 3)), np.ones(3), 0.5)


def test_multidimensional_weights_rejected():
    with pytest.raises(TypeError, match="weights must be a one dimensional"):
        quantile_1D(np.ones(6), np.ones((2, 3)), 0.5)


def test_mismatched_lengths_rejected():
    with pytest.raises(TypeError, match="must be the same"):
        quantile_1D(np.ones(4), np.ones(3), 0.5)


def test_empty_data_gives_nan_with_a_warning():
    """0.6 raised a bare IndexError from Sn[-1]."""
    with pytest.warns(RuntimeWarning, match="positive weight"):
        assert np.isnan(quantile_1D(np.array([]), np.array([]), 0.5))


# --- weight validation ------------------------------------------------------

def test_zero_sum_weights_give_nan_with_a_warning():
    """'No information, therefore undefined' is a legitimate answer, so the
    nan is kept -- but the caller is told, which 0.6 did not do."""
    with pytest.warns(RuntimeWarning, match="positive weight"):
        assert np.isnan(quantile_1D(DATA, np.zeros(8), 0.5))


def test_negative_weights_raise():
    """A negative weight pushes Pn outside [0, 1], so the curve being
    interpolated is no longer a cumulative distribution."""
    with pytest.raises(ValueError, match="must not be negative"):
        quantile_1D(np.array([1.0, 2, 3]), np.array([1.0, -5, 1]), 0.5)


@pytest.mark.parametrize("bad", [np.inf, -np.inf])
def test_infinite_weights_raise(bad):
    """The limit is not unique: for [1,2,3] with weights [1,W,1], W -> inf
    gives 1.5 at q=0.25 but 2.0 at q=0.5."""
    with pytest.raises(ValueError, match="must be finite"):
        quantile_1D(np.array([1.0, 2, 3]), np.array([1.0, bad, 1]), 0.5)


def test_nan_weight_propagates():
    assert np.isnan(quantile_1D(np.array([1.0, 2, 3]), np.array([1.0, np.nan, 1]), 0.5))


# --- zero weights are dropped, not left as interpolation nodes --------------

def test_zero_weight_point_is_not_returned():
    """0.6 returned 1.5 here: the zero-weight point stayed a node in the
    interpolation grid and could be handed back as the answer."""
    assert quantile_1D([1.0, 1.5, 3.0], [1.0, 0.0, 1.0], 0.5) == 2.0


@pytest.mark.parametrize("q", [0.1, 0.25, 0.5, 0.75, 0.9])
def test_zero_weights_equal_filtering_by_hand(q):
    data = np.array([1.0, 1.5, 2.0, 2.9, 3.0, 7.0])
    weights = np.array([1.0, 0.0, 2.0, 0.0, 1.0, 3.0])
    keep = weights > 0
    assert quantile_1D(data, weights, q) == quantile_1D(data[keep], weights[keep], q)


# --- masked arrays ----------------------------------------------------------

def test_masked_entries_are_dropped():
    """np.asarray strips the mask, so in 0.6 whatever sat under it leaked in."""
    m = np.ma.masked_array([1.0, 999.0, 3.0], mask=[0, 1, 0])
    assert quantile_1D(m, np.ones(3), 0.5) == 2.0
    assert quantile_1D(m, np.ones(3), 0.5) == np.ma.median(m)


def test_masked_weights_are_dropped():
    w = np.ma.masked_array([1.0, 1.0, 1.0], mask=[0, 1, 0])
    assert quantile_1D([1.0, 999.0, 3.0], w, 0.5) == 2.0


def test_fully_masked_gives_nan_with_a_warning():
    m = np.ma.masked_array([1.0, 2.0], mask=[1, 1])
    with pytest.warns(RuntimeWarning, match="positive weight"):
        assert np.isnan(quantile_1D(m, np.ones(2), 0.5))


def test_mask_survives_the_multidimensional_path():
    values = np.arange(12.0).reshape(3, 4)
    mask = np.zeros((3, 4), dtype=bool)
    mask[1, 2] = True
    result = quantile(np.ma.masked_array(values, mask=mask), np.ones(4), 0.5)
    expected = [quantile_1D(values[0], np.ones(4), 0.5),
                quantile_1D(np.delete(values[1], 2), np.ones(3), 0.5),
                quantile_1D(values[2], np.ones(4), 0.5)]
    np.testing.assert_array_equal(result, expected)


# --- NaN: propagate by default, omit on request -----------------------------

def test_nan_in_data_propagates():
    """0.6 returned 3.0, which is the '+inf carrying full weight' reading:
    argsort sends NaN to the end and it keeps its weight."""
    assert np.isnan(quantile_1D(np.array([1.0, np.nan, 3]), np.ones(3), 0.5))
    assert np.isnan(np.quantile(np.array([1.0, np.nan, 3]), 0.5))  # numpy agrees


def test_nanquantile_omits_nan():
    assert wquantiles.nanquantile([1.0, np.nan, 3.0], [1.0, 1.0, 1.0], 0.5) == 2.0
    assert wquantiles.nanmedian([1.0, np.nan, 3.0], [1.0, 1.0, 1.0]) == 2.0


def test_nanquantile_omits_nan_weights():
    assert wquantiles.nanquantile([1.0, 2.0, 3.0], [1.0, np.nan, 1.0], 0.5) == 2.0


@pytest.mark.parametrize("q", [0.1, 0.5, 0.9])
def test_nanquantile_equals_filtering_by_hand(q):
    data = np.array([1.0, np.nan, 2.0, 3.0, np.nan, 7.0])
    weights = np.array([1.0, 2.0, 2.0, 1.0, 1.0, 3.0])
    keep = ~np.isnan(data)
    assert wquantiles.nanquantile(data, weights, q) == quantile_1D(
        data[keep], weights[keep], q
    )


def test_all_nan_gives_nan_with_a_warning():
    with pytest.warns(RuntimeWarning, match="positive weight"):
        assert np.isnan(wquantiles.nanmedian([np.nan, np.nan], [1.0, 1.0]))


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
    """The reachable range is that of the data carrying weight: DATA[0] is 0
    but its weight is 0, so q=0 gives 10, not 0."""
    weighted = DATA[WEIGHTS > 0]
    assert quantile_1D(DATA, WEIGHTS, edge_q) in (weighted.min(), weighted.max())


# --- the deprecated `quantile=` keyword -------------------------------------

@pytest.mark.parametrize("func", [quantile_1D, quantile])
def test_quantile_keyword_still_works_but_warns(func):
    with pytest.warns(DeprecationWarning, match="use `q` instead"):
        result = func(DATA, WEIGHTS, quantile=0.5)
    assert result == pytest.approx(185 / 6)


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
    assert wquantiles.__all__ == [
        "quantile_1D", "quantile", "median", "nanquantile", "nanmedian",
    ]
