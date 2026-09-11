Unreleased
==========

### Breaking changes

- **Python 3.6, 3.7 and 3.8 are no longer supported.** The minimum is now
  Python 3.9. All three dropped releases are end-of-life; if you are on one of
  them, pin `wquantiles==0.6`.

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

0.6 (2021-05-26)
================

- Use Poetry to manage the project and its dependencies
- More robust call to pytest
- Update supported versions of Python (>=3.6 from this version on)
