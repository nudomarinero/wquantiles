# wquantiles — modernisation plan

Status of the repository at the time this plan was written (2026-09-11):
version 0.6 on PyPI, last release 2021-05-26, 55 stars, 13 forks, no CI running
the tests, and `develop` 5 commits behind `master`.

Each phase below is one branch and one pull request. Phases are ordered so that
each one lands on a tree the previous phase left green. Work through them in
order; do not start a phase before its predecessor is merged.

## Branching

A two-tier flow, per `AGENTS.md`:

    feature branch --PR--> develop --PR at release time--> master

Every phase branch is cut from `develop` and merged back into `develop`.
`master` moves twice in this plan: at the 0.7 release (end of Phase 2) and at
the 1.0 release (Phase 9). `origin/develop` was 5 commits behind `master` when
this plan was written and has been fast-forwarded to match.

Legend: **[ ]** not started · **[~]** in progress · **[x]** merged

---

## Phase 0 — Ground rules · `chore/agents-and-plan` · **[x]**

Establish how the work is done before doing any of it.

- Add `AGENTS.md`: what the project is, which estimator it implements, the two
  `master` rules, and the backwards-compatibility policy.
- Add this `PLAN.md`.
- Fast-forward `develop` to `master` and adopt the two-tier flow above.
  *Decided:* `develop` is kept and resynced rather than deleted.

**Breaking changes:** none. No library code is touched.

---

## Phase 1 — Migrate to uv · `build/migrate-to-uv` · **[x]**

*Deviation from the original ordering, deliberately:* this was last on the
earlier list, but every subsequent phase runs its tests and its CI matrix through
the packaging tooling, so replacing Poetry first means it is done once rather
than reworked at each step.

- Replace `[tool.poetry]` metadata with PEP 621 `[project]` metadata.
- Switch the build backend from `poetry-core` to `uv_build`. *Decided:*
  `uv_build` over `hatchling`, to keep the toolchain to one tool.
- **Convert both modules to package directories.** `uv_build` requires every
  shipped module to be a directory containing an `__init__.py`; it cannot ship a
  bare `.py` file at the project root. Verified: with `wquantiles.py` at the root
  it fails with *"Expected a Python module at: wquantiles/__init__.py"*. So
  `wquantiles.py` → `wquantiles/__init__.py` and `weighted.py` →
  `weighted/__init__.py`. Imports are unchanged for users, and the package now
  installs as `site-packages/wquantiles/` rather than a loose `.py` file — the
  layout behind the confusion in issues #1 and #3. It also gives `py.typed` a
  home in Phase 2.
- Declare dev dependencies as a PEP 735 dependency group rather than the
  deprecated `[tool.poetry.dev-dependencies]`.
- Commit `uv.lock`.
- Raise the floors: `requires-python = ">=3.9"`, `pytest` to a current release.
  Leave `numpy>=1.18` alone for now — Phase 3 will pin down what is actually
  testable.
- Delete `tox.ini` (its `whitelist_externals` is tox-3 syntax and its envlist
  stops at py39) and `.travis.yml` (travis-ci.org is shut down). uv's Python
  management plus the Phase 3 CI matrix replaces both.
- Delete `conftest.py`. It existed only so `test/` could import the top-level
  modules via a `sys.path` hack; under uv the package is installed into the
  environment and the tests import it properly.
- Ship the test suite and `CHANGES.md` in the sdist so downstream packagers can
  run the tests.
- **Verify by building an sdist and a wheel and inspecting their contents**, then
  installing the wheel into a clean environment and running the sdist's tests
  against it — a packaging regression here is exactly the failure reported in
  issue #1.

**Breaking changes:**

- `BREAKING:` **Python 3.6, 3.7 and 3.8 are no longer supported.** All three are
  end-of-life. Users on them can pin `wquantiles==0.6`.

No deprecation period: the runtimes concerned are themselves unsupported.

The module-to-package conversion is **not** breaking: `import wquantiles`,
`from wquantiles import quantile, median, quantile_1D` and `import weighted`
(with its `DeprecationWarning`) all behave exactly as before. Verified against a
wheel installed in a clean environment.

---

## Phase 2 — Correctness pass · `fix/correctness` · **[~]** *(code done; release pending)*

The behaviour changes here are the substance of the next release. Every one of
them replaces a silently wrong answer with either a correct one or an exception.

The behaviour changes here are the substance of the next release. They were
reviewed case by case, asking of each old output: was it an *artifact of the
implementation*, or a *defensible answer under some reading of the data*? The
two get different treatment.

### Artifacts — no reading of the data makes them right

| Issue | Now | After |
|---|---|---|
| Dead `raise` | 0-d input returns `None`; the `TypeError` is built and discarded | returns the value, as `np.quantile(5.0, 0.5)` does |
| No coercion in `quantile()` | `median([1,2,3],[1,1,1])` → `AttributeError: 'list' object has no attribute 'ndim'` (issue #11) | lists accepted, as `quantile_1D` already did |
| Wrong `__version__` | `"0.4"` while the package is 0.6 | read from package metadata |
| Inverted `np.matrix` guard | skipping `asarray` guarantees `ndim == 2`, so the next check rejects it — the branch can never help | deleted |
| `NaN` in data | `[1,nan,3]` → `3.0`. `argsort` sends `NaN` last where it keeps its weight, so this is the "`NaN` is `+inf`" reading, not "`NaN` is missing" — masking gives `2.0` | propagates `nan`; `nanquantile`/`nanmedian` drop it |
| Infinite weight | `nan`, from `inf/inf` | `ValueError` — the limit is not unique: `[1,2,3]` with `[1,W,1]` tends to `1.5` at q=0.25 but `2.0` at q=0.5 |
| Negative weight | `[1,-5,1]` → `2.0`. `Pn` usually stays monotonic but leaves `[0,1]`, so it is no longer a cumulative probability | `ValueError` |
| Masked arrays | `np.asarray` strips the mask, so `masked_array([1,999,3], mask=[0,1,0])` gives `3.0` where `np.ma.median` gives `2.0` | masked entries dropped, in data or weights |
| Zero-weight points | remain nodes in the interpolation grid and can be returned as the answer: `[1,1.5,3]` with `[1,0,1]` → `1.5`, a point carrying no mass | dropped before interpolating |

### Defensible old behaviour — value kept, caller now told

"No information, therefore undefined" is a legitimate scientific answer, and a
`nan` flows through downstream array work where an exception would kill it.

| Issue | Now | After |
|---|---|---|
| Zero-sum weights | `nan`, silently | `nan` with a `RuntimeWarning` |
| Empty data | bare `IndexError` from `Sn[-1]` | `nan` with a `RuntimeWarning` |

### Also in scope

Rename the `quantile` parameter to `q` (it shadows the function of the same
name, and `q` matches `np.quantile`), keeping `quantile=` as a deprecated
keyword. Drop `from __future__ import print_function`. Add type hints, a
`py.typed` marker, `__all__`, and docstrings stating the estimator.

Add targeted tests for every behaviour change (`test/test_validation.py`). The
broader test restructuring stays in Phase 4, but behaviour changes cannot ship
untested.

### Breaking changes

- `BREAKING:` **zero-weight points are dropped.** The only change that alters
  results for input that was always valid — ~20% of cases containing a zero
  weight move, including 2 of the 25 cells in the existing 3-D test. Explained
  in the README, as agreed.
- `BREAKING:` masked arrays are honoured, changing results for anyone who was
  passing them.
- `BREAKING:` `NaN` in data or weights propagates instead of being treated as
  `+inf`.
- `BREAKING:` negative and infinite weights raise `ValueError`.
- `BREAKING:` zero-sum weights and empty data now warn.
- `BREAKING:` 0-d data returns its value instead of `None`.
- `BREAKING:` `__version__` corrected from `"0.4"`.
- `BREAKING:` the `quantile` parameter is renamed `q`; the old keyword warns.

Only the parameter rename gets a deprecation period.

**Verification.** Results for data with all-positive weights, no mask and no
NaN are bit-identical to 0.6: ~28,000 comparisons across unit, random, integer
and widely-scaled weights, every quantile from 0 to 1, one- and
multi-dimensional input, and integer dtypes — zero mismatches. Separately
confirmed that dropping zero weights, honouring masks, and `nanquantile` each
give exactly the same answer as filtering the array by hand beforehand.

**Release:** cut **0.7** at the end of this phase — merge `develop` into
`master` by pull request and tag `v0.7.0` on `master`.

---

## Phase 3 — Real CI · `ci/github-actions` · **[ ]**

Nothing currently runs the test suite. `.github/workflows/` holds only
`codeql-analysis.yml`, and the README's build badge points at travis-ci.org,
which is shut down — the repository advertises a build status that does not exist.

- GitHub Actions workflow, `uv`-driven, matrix over Python 3.9–3.13 **crossed
  with numpy 1.x and numpy 2.x**. The 1.x/2.x axis is the one that matters here:
  it is what proves the compatibility claim the README will make in Phase 5.
- Run on push and pull request, and make it a required check on both
  `develop` and `master`.
- Replace the dead Travis badge in the README with the Actions badge.
- Add a coverage report.
- Decide whether to keep `codeql-analysis.yml` — it is close to pointless for a
  90-line pure-numpy module with no I/O.

**Breaking changes:** none.

---

## Phase 4 — Tests worth having · `test/coverage-and-properties` · **[ ]**

Five tests pass today, but `test_median` asserts only on `np.median` — every
assertion in it is about numpy, not about this library. It contributes nothing
and should go.

- Delete `test_median`.
- Cover every error path added in Phase 2, plus `median()` itself, list input,
  2-D input, and both branches of the `quantile()` dispatcher.
- Replace the hardcoded 5×5×5 expected array — the current magic numbers have no
  derivation and are untraceable if anything changes — with a seeded generator
  and a derived expectation.
- Add property-based tests (Hypothesis). The invariants worth asserting:
  - the result lies in `[min(data), max(data)]`;
  - with equal weights the result equals `np.quantile(data, q, method="hazen")`;
  - scaling every weight by a positive constant changes nothing;
  - duplicating a data point equals doubling its weight;
  - the result is monotonic non-decreasing in `q`.
- Consider moving from `unittest` classes to plain pytest functions.

**Breaking changes:** none.

---

## Phase 5 — README and the visual explanation · `docs/readme-and-visual` · **[ ]**

The highest-value documentation change is not a diagram: it is **stating which
estimator this library implements**. Issue #4 and the follow-up on it are the
same confusion twice, and the README currently never defines the estimator at all.

- A "Which weighted quantile is this?" section: the interpolated weighted
  percentile; equal to numpy's `hazen` / Hyndman–Fan type 5 under unit weights.
- A "How this relates to `numpy.quantile`" section carrying this table, and
  saying plainly when to reach for each:

  | data / weights | q | `wquantiles` | `np.quantile(..., method="inverted_cdf")` |
  |---|---|---|---|
  | `[1,2,3]` / `[100,1,1]` | 0.50 | 1.0198 | 1.0 |
  | `[1,2,3]` / `[100,1,1]` | 0.75 | 1.5248 | 1.0 |
  | `[0,10,20,25,30,30,35,50]` / `[0,1,0,1,2,2,2,1]` | 0.25 | 27.50 | 30.0 |
  | `[0,10,20,25,30,30,35,50]` / `[0,1,0,1,2,2,2,1]` | 0.75 | 34.375 | 35.0 |
  | same data / all ones | 0.50 | 27.50 | 25.0 |

- A worked example using the `[1,2,3]` / `[100,1,1]` case from issue #4 —
  a good teaching example precisely because the answer surprises people.
- **The visual.** The figure that actually explains the algorithm is the
  weighted ECDF staircase:
  - x-axis sorted data, y-axis cumulative probability;
  - each point a step whose *rise is proportional to its weight*, so weight
    becomes visually obvious as "how much of the vertical axis this point owns";
  - the `Pn` points marked at the *midpoint of each riser* — that is the
    `-0.5*w` term, the least obvious line in the code, made self-evident;
  - the segments joining those midpoints: the interpolation;
  - a line at y = 0.5 meeting the curve, dropping to the x-axis: the median.

  A second panel overlays the discrete `inverted_cdf` step function on the same
  data, showing the two answers differ. That panel *is* the answer to issue #4.

  Deliverables: a committed matplotlib script under `docs/` so the figure is
  regenerable, the SVG it produces, and — recommended — an interactive version
  where the weights can be dragged and the median tracks them.

- Fix the stale Zenodo/PyPI badges while in here.

**Breaking changes:** none.

---

## Phase 6 — Accept an array of quantiles · `feat/array-quantiles` · **[ ]**

Merges the only upstream-worthy fork change. `ysong-astro/wquantiles @ e1e52f7`
is the sole fork with a commit of its own worth taking (the other twelve are
either unmodified or superseded — `seatme`'s four 2015 commits move `__version__`
out of a `setup.py` that no longer exists). Credit it in the commit trailer.

```diff
-    if ((quantile > 1.) or (quantile < 0.)):
+    if np.any(quantile > 1.) or np.any(quantile < 0.):
```

`np.interp` already accepts a vector `x`, so this guard is the only thing
blocking array input. Today:

```
quantile_1D(d, w, np.array([0.25, 0.5, 0.75]))
  -> ValueError: The truth value of an array with more than one element is ambiguous
```

Extend it to `quantile()` as well, where the multi-dimensional reshape needs
adjusting for the extra output axis, and settle the output shape convention —
follow `np.quantile`, which puts the quantile axis first.

**Breaking changes:** none. This turns an exception into a working call.

---

## Phase 7 — Vectorise, and add `axis=` · `perf/vectorise-axis` · **[ ]**

Closes the oldest TODO in the file (`wquantiles.py:76`). `np.apply_along_axis`
at `wquantiles.py:85` is slow: on a `(200, 200, 50)` array it takes **639 ms**.
A vectorised `argsort` / `take_along_axis` / `cumsum` implementation produces
matching results in **164 ms** — **~3.9× faster** — and makes an `axis=`
parameter fall out almost for free. A working prototype exists.

- Vectorise `quantile()` over the reduction axis.
- Add `axis=-1`, defaulting to current behaviour.
- **Assert bit-exact equality with the 0.7 results, not approximate equality.**
  If the float results differ at all, that is a breaking change and has to be
  reported as one rather than waved through as rounding.
- Preserve the existing weights-length validation through the new broadcasting
  path.

**Breaking changes:** `axis=` is additive and defaults to today's behaviour, so
none are expected — but this phase has the highest risk of an unintended one.
The bit-exactness check above is what catches it.

---

## Phase 8 — Sphinx docs · `docs/sphinx-cleanup` · **[ ]**

`docs/` is stale and the build is broken:

- `docs/weighted.rst` autodocs the **deprecated** `weighted` module rather than
  `wquantiles`;
- `docs/setup.rst` autodocs a `setup` module that no longer exists — Poetry
  removed it — so the build errors;
- `conf.py` says `version = '0.2'`, `copyright = u'2014, Author'`,
  `html_theme = 'default'`;
- nothing is published anywhere: no Read the Docs, no GitHub Pages.

**Open decision:** fix it or retire it. For a three-function module, a good
README may serve users better than a Sphinx site that nobody visits. If it is
kept, it needs to build in CI and publish to Read the Docs or Pages, and it
should host the Phase 5 visual. If it is retired, delete `docs/` and fold
everything into the README.

**Breaking changes:** none.

---

## Phase 9 — Release 1.0 · `chore/release-1.0` · **[ ]**

Once Phases 2–8 are merged the library has a stated definition, real CI, a real
test suite, `axis=` support and array `q`. That is a 1.0.

- **Remove `weighted.py`.** It has emitted a `DeprecationWarning` since 2017
  (PR #5) and the rename landed in 0.4. `BREAKING:` — but with an eight-year
  deprecation period behind it, and it is the one change in this plan that
  genuinely warrants the major version bump.
- Also decide whether to keep the `quantile=` keyword alias from Phase 2 or
  drop it here.
- Update the Zenodo DOI for the new release.
- Merge `develop` into `master` by pull request, tag `v1.0.0` on `master`.
- Publish to PyPI with `uv publish`.

**Breaking changes:**

- `BREAKING:` `import weighted` no longer works. Use `import wquantiles`.
- Possibly `BREAKING:` removal of the `quantile=` keyword alias, if that is the
  decision.

---

## Summary of every breaking change in this plan

| Phase | Change | Deprecation period |
|---|---|---|
| 1 | Python 3.6 / 3.7 / 3.8 dropped | none — all end-of-life |
| 2 | Zero-weight points dropped (**changes valid results**) | none — documented in the README |
| 2 | Masked arrays honoured | none — previous result used masked values |
| 2 | Negative and infinite weights raise `ValueError` | none — previous result was wrong |
| 2 | `NaN` in data or weights propagates as `nan` | none — previous result was the `+inf` reading |
| 2 | Zero-sum weights and empty data warn | none — value unchanged |
| 2 | 0-d data returns its value instead of `None` | none — previously returned `None` |
| 2 | `__version__` corrected from `"0.4"` | none — previously wrong |
| 2 | `quantile` parameter renamed to `q` | keyword alias kept through 0.x |
| 9 | `weighted.py` removed | deprecated since 2017 |
| 9 | `quantile=` keyword alias removed (if chosen) | one minor release |

Everything else in the plan is additive or internal.
