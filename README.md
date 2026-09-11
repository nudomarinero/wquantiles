wquantiles
==========

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

The estimator is the **interpolated weighted percentile**. Each datum owns a
slab of probability whose width is proportional to its weight; the slab
midpoints give a weighted cumulative distribution, and the result is linearly
interpolated from it:

    Pn = (Sn - 0.5 * w) / Sn[-1]        with Sn the cumulative weights

With equal weights this is exactly numpy's `method="hazen"` (Hyndman–Fan
type 5).

It is **not** the discrete weighted median, which returns an actual element of
the data, and it is **not** what `np.quantile(..., weights=...)` computes:
numpy supports weights only with `method="inverted_cdf"`, which is discrete.
The two disagree on most inputs, so if you need the discrete definition, use
numpy.

Missing data, masks and zero weights
------------------------------------

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
such cases move. Results for data with all-positive weights are bit-identical
to 0.6, verified over ~28,000 comparisons. If you need the old numbers, pin
`wquantiles==0.6`.

A zero weight now means the same thing as a mask: this datum does not count.
