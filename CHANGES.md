0.7 (2026-09-17)
================

This release turns a number of silently wrong answers into either correct
answers or explicit errors. Read the breaking changes before upgrading.

### Breaking changes

- **Python 3.6, 3.7 and 3.8 are no longer supported.** The minimum is now
  Python 3.9. All three dropped releases are end-of-life; if you are on one of
  them, pin `wquantiles==0.6`.
- **A datum with zero weight is now dropped instead of remaining a node in the
  interpolation grid.** Up to 0.6 such a point could be returned as the answer
  despite carrying no probability mass: `quantile_1D([1, 1.5, 3], [1, 0, 1],
  0.5)` returned `1.5`, the zero-weight point itself, and now returns `2.0`.
  This is the only change that alters results for input that was always valid.
  It bites only when some weight is exactly zero, where roughly 20% of cases
  move; see the README for the reasoning.
- **The weights of equal values are now summed**, so each distinct value
  contributes one node carrying all of its mass. Up to 0.6 two equal values
  held two separate nodes, which meant the result was not a function of the
  weighted distribution at all: `quantile_1D([1,2,2,3], [1,5,0.5,1], 0.2)`
  returned `1.333`, but `2.000` if the two `2`s were swapped in the input.
  It now returns `1.308` either way, and `[1,2,2,3]` with unit weights agrees
  with `[1,2,3]` weighted `[1,2,1]`, as numpy's weighted `inverted_cdf` and
  statsmodels already did. The cost is that the numpy `hazen` equivalence now
  holds only for **distinct** values; see the README for why that is the right
  trade. Changes results only when values repeat: continuous data is untouched,
  around 40% of unit-weight cases on integer or binned data move.
- **Masked arrays are now honoured.** `np.asarray` discards the mask, so
  whatever sat underneath leaked into the result: for
  `np.ma.masked_array([1, 999, 3], mask=[0,1,0])` the median was `3.0`, where
  `np.ma.median` gives `2.0`. Masked entries — in the data or in the weights —
  are now dropped, and the answer is `2.0`.
- **`NaN` in the data or the weights now propagates**, as it does in
  `np.quantile`. `quantile_1D([1, nan, 3], [1,1,1], 0.5)` returned `3.0`,
  because `argsort` sends `NaN` to the end where it kept its full weight — the
  result was the "`NaN` is `+inf`" reading, not the "`NaN` is missing" one.
  Use the new `nanquantile` / `nanmedian` to drop it instead.
- **Negative weights now raise `ValueError`.** They push `Pn` outside `[0, 1]`,
  so the curve being interpolated is no longer a cumulative distribution.
- **Infinite weights now raise `ValueError`.** They previously returned `nan`
  from `inf/inf`. The limit is not unique: for `[1, 2, 3]` with weights
  `[1, W, 1]`, letting `W → ∞` gives `1.5` at q=0.25 but `2.0` at q=0.5.
- **`__version__` is now read from the installed package metadata.** It was
  hardcoded to `"0.4"` and had been wrong since the 0.5 release.
- **The `quantile` parameter is now called `q`.** Passing it positionally is
  unaffected. Passing it as `quantile=` still works but raises a
  `DeprecationWarning`, and the alias will be removed in a future release.

### Changed, where the old answer was defensible

These kept their old return value rather than becoming errors, because "no
information, therefore undefined" is a legitimate scientific answer that flows
through downstream array work. What changed is that the caller is now told.

- **Weights that sum to zero** still return `nan`, now with a `RuntimeWarning`.
- **Empty data** returns `nan` with a `RuntimeWarning`, where 0.6 raised a bare
  `IndexError` from `Sn[-1]`.
- **Zero-dimensional data** now returns the value itself, matching
  `np.quantile(5.0, 0.5) == 5.0`. It previously returned `None`, because the
  `TypeError` was constructed but never raised.

**Results for data with distinct values and all-positive weights, no mask and
no NaN are unchanged**, verified bit-exactly against 0.6 over ~54,000
comparisons spanning unit, random, integer and widely-scaled weights, every
quantile from 0 to 1, and integer dtypes.

### Fixed

- `quantile()` and `median()` now accept lists and other array-likes. They
  previously failed with `AttributeError: 'list' object has no attribute 'ndim'`
  while `quantile_1D()` accepted them, so the three entry points disagreed on
  what they took. (issue #11)
- Removed a `np.matrix` special case that could never help: skipping the
  `asarray` conversion for a matrix guaranteed `ndim == 2`, so the very next
  check rejected it.

### Added

- `nanquantile` and `nanmedian`, which treat `NaN` in the data or the weights
  as missing rather than propagating it, as `np.nanquantile` does.
- Type hints and a `py.typed` marker, so the package now ships as typed.
- `__all__`, declaring the public API. As a result `from wquantiles import *`
  no longer pulls in the `numpy` import as `np`.
- Docstrings and a README section stating which estimator is implemented — the
  quantile of the weighted empirical distribution, equal to numpy's
  `method="hazen"` (Hyndman-Fan type 5) under equal weights and distinct
  values — and how missing data and repeated values are handled.

### Other changes

- The project is now managed with [uv](https://docs.astral.sh/uv/) instead of
  Poetry, using PEP 621 metadata, a PEP 735 dev dependency group and the
  `uv_build` backend. `uv.lock` is committed.
- `wquantiles` and `weighted` are now package directories rather than
  single-file modules, as `uv_build` requires. **This does not change any
  import**: `import wquantiles`, `from wquantiles import quantile, median,
  quantile_1D` and `import weighted` all behave exactly as before.
- The sdist now contains the test suite, so downstream packagers can run it.
- Removed `tox.ini` and `.travis.yml`; travis-ci.org has been shut down. CI is
  now GitHub Actions, testing Python 3.9 to 3.14 against both numpy 1.x and
  numpy 2.x, on Linux, Windows and macOS, plus a job that installs the built
  wheel into a clean environment and runs the tests against it.
- The declared numpy floor moves from `>=1.18` to `>=1.19`. This removes
  nothing in practice: numpy 1.18 has no wheels for Python 3.9, so with the new
  `requires-python = ">=3.9"` it was unreachable from any supported
  interpreter.
- Removed `from __future__ import print_function`, dead in a Python 3 package.

0.6 (2021-05-26)
================

- Use Poetry to manage the project and its dependencies
- More robust call to pytest
- Update supported versions of Python (>=3.6 from this version on)
