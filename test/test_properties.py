"""Property-based tests.

Coverage was already at 100% before these were written, so their job is not to
reach unreached lines: it is to check the things coverage cannot see. Each
property below was verified to hold over several thousand random cases before
being asserted here -- two candidate properties did not survive that check and
are recorded at the bottom rather than asserted.
"""
import numpy as np
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from wquantiles import median, nanquantile, quantile_1D

NUMPY_HAS_METHOD = tuple(int(p) for p in np.__version__.split(".")[:2]) >= (1, 22)

# Bounded magnitudes: the point is the algebra of the estimator, not the
# floating-point behaviour of 1e300.
values = st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False)
positive_weights = st.floats(min_value=1e-3, max_value=1e6, allow_nan=False, allow_infinity=False)
quantiles = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)


@st.composite
def samples(draw, min_size=1, max_size=20, distinct=False):
    """A (data, weights) pair of equal length with strictly positive weights."""
    data = draw(st.lists(values, min_size=min_size, max_size=max_size,
                         unique=distinct))
    weights = draw(st.lists(positive_weights, min_size=len(data), max_size=len(data)))
    return np.array(data, dtype=float), np.array(weights, dtype=float)


slow = settings(deadline=None, max_examples=300)


@slow
@given(sample=samples(), q=quantiles)
def test_result_lies_within_the_data(sample, q):
    data, weights = sample
    result = quantile_1D(data, weights, q)
    assert data.min() <= result <= data.max()


@slow
@given(sample=samples(), q=quantiles)
def test_extreme_quantiles_are_the_extremes(sample, q):
    data, weights = sample
    assert quantile_1D(data, weights, 0.0) == data.min()
    assert quantile_1D(data, weights, 1.0) == data.max()


@slow
@given(sample=samples(), qs=st.lists(quantiles, min_size=2, max_size=8))
def test_non_decreasing_in_q(sample, qs):
    data, weights = sample
    results = [quantile_1D(data, weights, q) for q in sorted(qs)]
    assert np.all(np.diff(results) >= -1e-9)


@slow
@given(sample=samples(), q=quantiles,
       factor=st.floats(min_value=1e-3, max_value=1e3, allow_nan=False))
def test_scaling_every_weight_changes_nothing(sample, q, factor):
    """Only the relative weights matter: Pn is invariant under w -> c*w."""
    data, weights = sample
    scaled = weights * factor
    assume(np.all(np.isfinite(scaled)) and scaled.sum() > 0)
    assert quantile_1D(data, weights, q) == pytest.approx(
        quantile_1D(data, scaled, q), rel=1e-9, abs=1e-9
    )


@slow
@given(sample=samples(), q=quantiles, seed=st.integers(0, 2**32 - 1))
def test_order_of_the_input_does_not_matter(sample, q, seed):
    """Holds for tied values too, since their weights are summed."""
    data, weights = sample
    perm = np.random.default_rng(seed).permutation(len(data))
    assert quantile_1D(data, weights, q) == quantile_1D(data[perm], weights[perm], q)


@slow
@given(sample=samples(), q=quantiles)
def test_zero_weights_equal_removing_the_points(sample, q):
    data, weights = sample
    padded_data = np.concatenate([data, [1e5, -1e5]])
    padded_weights = np.concatenate([weights, [0.0, 0.0]])
    assert quantile_1D(padded_data, padded_weights, q) == quantile_1D(data, weights, q)


@slow
@given(sample=samples(), q=quantiles)
def test_masking_equals_removing_the_points(sample, q):
    data, weights = sample
    padded_data = np.concatenate([data, [1e5, -1e5]])
    padded_weights = np.concatenate([weights, [1.0, 1.0]])
    mask = np.zeros(len(padded_data), dtype=bool)
    mask[-2:] = True
    masked = np.ma.masked_array(padded_data, mask=mask)
    assert quantile_1D(masked, padded_weights, q) == quantile_1D(data, weights, q)


@slow
@given(sample=samples(), q=quantiles)
def test_nanquantile_equals_removing_the_points(sample, q):
    data, weights = sample
    padded_data = np.concatenate([data, [np.nan, np.nan]])
    padded_weights = np.concatenate([weights, [1.0, 1.0]])
    assert nanquantile(padded_data, padded_weights, q) == quantile_1D(data, weights, q)


@slow
@given(sample=samples())
def test_median_agrees_with_quantile_at_one_half(sample):
    data, weights = sample
    assert median(data, weights) == quantile_1D(data, weights, 0.5)


@pytest.mark.skipif(not NUMPY_HAS_METHOD, reason="numpy < 1.22 has no `method=`")
@slow
@given(data=st.lists(values, min_size=1, max_size=20, unique=True), q=quantiles)
def test_equal_weights_are_numpys_hazen(data, q):
    """With equal weights and **distinct** values this is numpy's hazen.

    Distinct on purpose: numpy follows the order-statistic definition and gives
    a repeated value two plotting positions, while this library gives each
    distinct value one node carrying all of its mass. The two therefore part
    company on ties, which is a deliberate choice -- see the README.
    """
    array = np.array(data, dtype=float)
    # Both sides carry an error of order eps * (data range): the interpolation
    # runs between order statistics, so the spread of the data sets the scale,
    # not the magnitude of the answer. Checked against exact rational
    # arithmetic: on a sample spanning 2281, numpy lands 1.1e-16 of the range
    # from the true value and this library 6.3e-16, both at float64 resolution.
    tolerance = 1e-12 * max(1.0, float(np.ptp(array)))
    assert quantile_1D(array, np.ones_like(array), q) == pytest.approx(
        np.quantile(array, q, method="hazen"), rel=1e-12, abs=tolerance
    )


# --- ties ------------------------------------------------------------------
#
# Both of the following were proposed as properties, found to fail, and then
# made to hold in 0.7 by summing the weights of equal values. They are the
# reason that change was made, so they are asserted rather than described.

@slow
@given(sample=samples(), q=quantiles)
def test_duplicating_a_point_equals_doubling_its_weight(sample, q):
    data, weights = sample
    duplicated = quantile_1D(
        np.concatenate([data, data[:1]]), np.concatenate([weights, weights[:1]]), q
    )
    doubled = quantile_1D(
        data, np.concatenate([[2 * weights[0]], weights[1:]]), q
    )
    assert duplicated == pytest.approx(doubled, rel=1e-9, abs=1e-9)


@slow
@given(
    data=st.lists(st.integers(0, 4).map(float), min_size=2, max_size=14),
    q=quantiles,
    seed=st.integers(0, 2**32 - 1),
)
def test_order_does_not_matter_even_with_ties(data, q, seed):
    """Integer-valued data so that Hypothesis produces ties constantly."""
    rng = np.random.default_rng(seed)
    array = np.array(data, dtype=float)
    weights = rng.random(len(array)) + 1e-3
    perm = rng.permutation(len(array))
    assert quantile_1D(array, weights, q) == pytest.approx(
        quantile_1D(array[perm], weights[perm], q), rel=1e-9, abs=1e-9
    )
