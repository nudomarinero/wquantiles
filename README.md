wquantiles
==========

[![Tests](https://github.com/nudomarinero/wquantiles/actions/workflows/tests.yml/badge.svg)](https://github.com/nudomarinero/wquantiles/actions/workflows/tests.yml)
[![DOI](https://zenodo.org/badge/doi/10.5281/zenodo.14952.svg)](http://dx.doi.org/10.5281/zenodo.14952)
[![Pypi](https://img.shields.io/pypi/v/wquantiles.svg)](https://pypi.python.org/pypi/wquantiles)

Weighted quantiles with Python, including weighted median.
This library is based on numpy, which is the only dependence.

The main methods are **quantile** and **median**. The input of
quantile is a numpy array (_data_), a numpy array of weights of one
dimension and the value of the quantile (between 0 and 1) to
compute. The weighting is applied along the last axis. The method
**median** is an alias to _quantile(data, weights, 0.5)_.

**nanquantile** and **nanmedian** are the same, but treat `NaN` as missing
data instead of propagating it, the way `np.nanquantile` does.

Which weighted quantile is this?
--------------------------------

The estimator is the quantile of the **weighted empirical distribution**. Each
distinct value owns a slab of probability whose width is proportional to its
total weight; the slab midpoints give a weighted cumulative distribution, and
the result is linearly interpolated from it:

    Pn = (Sn - 0.5 * w) / Sn[-1]        with Sn the cumulative weights

With equal weights **and no repeated values** this is numpy's `method="hazen"`
(Hyndman–Fan type 5).

The weights of equal values are summed, so the answer depends only on the
distribution and not on how it was written down: two entries of weight 1 at the
same value behave exactly like one entry of weight 2. numpy's unweighted
quantiles instead follow the order-statistic definition, which gives a repeated
value two separate plotting positions — the plotting-position family was derived
for continuous distributions, where ties have probability zero, so it has no
considered position on repeated values. This library takes the distributional
reading; see the note below.

It is **not** the discrete weighted median, which returns an actual element of
the data, and it is **not** what `np.quantile(..., weights=...)` computes:
numpy supports weights only with `method="inverted_cdf"`, which is discrete.
The two disagree on most inputs, so if you need the discrete definition, use
numpy.

Missing data, masks and zero weights
------------------------------------

- The weights of **equal values** are summed, so each distinct value
  contributes a single node carrying all of its mass.
- A datum whose weight is **zero** owns no probability mass, so it is dropped
  before interpolating.
- Entries masked out of a `numpy.ma.MaskedArray` are dropped as well, whether
  the mask is on the data or on the weights.
- `NaN` in the data or the weights **propagates**, as it does in
  `np.quantile`. Use `nanquantile` / `nanmedian` to drop it instead.
- If nothing is left to average over — empty input, all weights zero,
  everything masked — the result is `NaN` and a `RuntimeWarning` is raised.
- Negative weights raise `ValueError`: they push `Pn` outside `[0, 1]`, so the
  curve being interpolated stops being a cumulative distribution. Infinite
  weights raise too, because the limit is not unique — for data `[1, 2, 3]`
  with weights `[1, W, 1]`, letting `W → ∞` gives `1.5` at q=0.25 but `2.0` at
  q=0.5.

Behaviour change in 0.7: zero weights
-------------------------------------

**Up to and including 0.6, a datum with zero weight still acted as a node in
the interpolation grid, and could be returned as the answer even though it
counted for nothing.** For example:

```python
>>> quantile_1D([1, 1.5, 3], [1, 0, 1], 0.5)
1.5      # 0.6: the zero-weight point itself
2.0      # 0.7: that point is dropped first
```

In 0.6 the sorted values `[1, 1.5, 3]` gave `Pn = [0.25, 0.5, 0.75]`, and
interpolating at 0.5 landed exactly on `1.5` — a value carrying no weight at
all. From 0.7 such points are removed before the cumulative distribution is
built, so `[1, 3]` gives `Pn = [0.25, 0.75]` and the median is `2.0`.

This changes results **only when some weight is exactly zero**; roughly 20% of
such cases move.

A zero weight now means the same thing as a mask: this datum does not count.

Behaviour change in 0.7: repeated values
----------------------------------------

**Up to and including 0.6, two equal values carried two separate nodes**, so
the answer could depend on the order the caller happened to store them in:

```python
>>> quantile_1D([1, 2, 2, 3], [1, 5, 0.5, 1], 0.2)
1.333    # 0.6, as written
2.000    # 0.6, with the two 2s swapped
1.308    # 0.7, either way
```

The weights of equal values are now summed. The estimator is therefore a
function of the weighted distribution, which it was not before: `[1,2,2,3]`
with unit weights and `[1,2,3]` with weights `[1,2,1]` are the same sample
written two ways, and now give the same answer. `numpy`'s weighted
`inverted_cdf` and `statsmodels` both already behaved this way.

The cost is that the numpy `hazen` equivalence now holds only for **distinct**
values. That is the deliberate trade: `hazen` is defined on order statistics,
which split a tie across two plotting positions, but the plotting-position
family was derived for continuous distributions where ties cannot occur, so it
has no considered position on repeated values.

This changes results **only when values repeat**: continuous data is untouched,
while roughly 40% of unit-weight cases on integer or binned data move.

Results for data with **distinct values and all-positive weights** are
bit-identical to 0.6, verified over ~54,000 comparisons. If you need the old
numbers, pin `wquantiles==0.6`.
