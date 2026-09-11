0.7 (unreleased)
================

This release turns a number of silently wrong answers into either correct
answers or explicit errors. Read the breaking changes before upgrading.

### Breaking changes

- **Python 3.6, 3.7 and 3.8 are no longer supported.** The minimum is now
  Python 3.9. All three dropped releases are end-of-life; if you are on one of
  them, pin `wquantiles==0.6`.
- **Invalid weights now raise `ValueError` instead of returning a number.**
  Weights that sum to zero previously returned `nan`; negative weights
  previously returned a meaningless value (`quantile_1D([1,2,3], [1,-5,1], 0.5)`
  returned `2.0`, because a negative weight makes the cumulative distribution
  non-monotonic and `np.interp` undefined); `NaN` or infinite weights previously
  returned `nan`. All four now raise.
- **`NaN` in `data` now propagates.** `quantile_1D([1, nan, 3], [1,1,1], 0.5)`
  previously returned `3.0` and now returns `nan`, matching `np.quantile`.
- **Zero-dimensional `data` now raises `TypeError`.** It previously returned
  `None`: the exception was constructed but never raised.
- **Empty `data` now raises `ValueError`** instead of `IndexError`.
- **`__version__` is now read from the installed package metadata.** It was
  hardcoded to `"0.4"` and had been wrong since the 0.5 release.
- **The `quantile` parameter is now called `q`.** Passing it positionally is
  unaffected. Passing it as `quantile=` still works but raises a
  `DeprecationWarning`, and the alias will be removed in a future release.

None of these were given a deprecation period except the parameter rename,
because in each of the other cases the previous return value was wrong and no
caller can have depended on it meaningfully.

**Results for valid inputs are unchanged.** This was verified bit-exactly
against 0.6 over ~37,000 comparisons spanning unit, random, integer, zero-valued
and widely-scaled weights, all quantiles from 0 to 1, one- and multi-dimensional
input, and integer dtypes.

### Fixed

- `quantile()` and `median()` now accept lists and other array-likes. They
  previously failed with `AttributeError: 'list' object has no attribute 'ndim'`
  while `quantile_1D()` accepted them, so the three entry points disagreed on
  what they took. (issue #11)
- Removed a `np.matrix` special case that could never help: skipping the
  `asarray` conversion for a matrix guaranteed `ndim == 2`, so the very next
  check rejected it.

### Added

- Type hints and a `py.typed` marker, so the package now ships as typed.
- `__all__`, declaring `quantile_1D`, `quantile` and `median` as the public API.
  As a result `from wquantiles import *` no longer pulls in the `numpy` import
  as `np`.
- Docstrings now state which estimator is implemented — the interpolated
  weighted percentile, equal to numpy's `method="hazen"` (Hyndman-Fan type 5)
  under unit weights — and document what each function raises.

### Other changes

- The project is now managed with [uv](https://docs.astral.sh/uv/) instead of
  Poetry, using PEP 621 metadata, a PEP 735 dev dependency group and the
  `uv_build` backend. `uv.lock` is committed.
- `wquantiles` and `weighted` are now package directories rather than
  single-file modules, as `uv_build` requires. **This does not change any
  import**: `import wquantiles`, `from wquantiles import quantile, median,
  quantile_1D` and `import weighted` all behave exactly as before.
- The sdist now contains the test suite, so downstream packagers can run it.
- Removed `tox.ini` and `.travis.yml`; travis-ci.org has been shut down and CI
  moves to GitHub Actions.
- Removed `from __future__ import print_function`, dead in a Python 3 package.

0.6 (2021-05-26)
================

- Use Poetry to manage the project and its dependencies
- More robust call to pytest
- Update supported versions of Python (>=3.6 from this version on)
