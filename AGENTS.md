# AGENTS.md

## The project

`wquantiles` computes **weighted quantiles**, including the weighted median, of
numpy arrays. numpy is the only runtime dependency.

- `wquantiles.py` — the whole library. Three public functions:
  - `quantile_1D(data, weights, quantile)` — the actual algorithm, 1-D only.
  - `quantile(data, weights, quantile)` — dispatcher; weights apply along the last axis.
  - `median(data, weights)` — alias for `quantile(data, weights, 0.5)`.
- `weighted.py` — deprecated import shim kept for pre-0.4 users; emits a
  `DeprecationWarning` and re-exports `wquantiles`.
- `test/test_weighted.py` — the test suite (pytest). `conftest.py` at the repo
  root exists only so `test/` can import the top-level modules.

### The definition it implements

The estimator is the **interpolated weighted percentile**: the data are sorted,
a weighted cumulative distribution `Pn = (Sn - 0.5*w) / Sn[-1]` is built, and
the result is linearly interpolated from it. With unit weights this is exactly
numpy's `method="hazen"` (Hyndman–Fan type 5).

This matters: it is **not** the discrete weighted median, and it is **not** what
`np.quantile(..., weights=...)` computes — numpy only supports weights with
`method="inverted_cdf"`, which is discrete and returns an actual data value.
The two disagree on most inputs. Historical confusion about this is the subject
of issue #4. Any change to the estimator's definition is a breaking change and
needs to be called out explicitly.

## Working agreements

### 1. Never commit to `master`

`master` is the release branch: it only moves when a release is cut, by a pull
request from `develop`. Do not commit, amend, rebase, or otherwise write to it
directly. If you find yourself on `master` with changes to make, stop and create
a branch first.

### 2. All work happens on a feature branch, merged by pull request

`develop` is the integration branch. Branch off `develop` using a
`type/short-description` name (`fix/`, `feat/`, `perf/`, `docs/`, `test/`,
`ci/`, `build/`, `chore/`). One coherent change per branch. Merge back into
`develop` through a pull request, never by pushing the branch's commits to
`develop` or `master` directly.

    feature branch --PR--> develop --PR at release time--> master

## Backwards compatibility

This library has been on PyPI since 2014 and is used in published work, so
compatibility is taken seriously.

Any change that alters the value returned for an input that previously returned
a value, or that turns a working call into an error, is **breaking**. It must be:

1. labelled `BREAKING:` in the commit message and the pull request description,
2. recorded under a `### Breaking changes` heading in `CHANGES.md`, and
3. given a deprecation period where one is feasible.

Turning a *silently wrong* answer into an exception is still breaking, and still
gets an entry — but it does not need a deprecation period, since no caller can
have been depending on the wrong value meaningfully.

Changes that only turn an error into a working call (accepting list input, say)
are not breaking.

## Conventions

- `pyproject.toml` is the authoritative source for the supported Python and
  numpy floors.
- numpy-style docstrings, as in the existing code.
- Run the tests with `uv run pytest` once the uv migration has landed; until
  then, `python -m pytest` from the repo root.
- `PLAN.md` holds the current roadmap and the state of each phase. Keep it
  updated as phases complete.
