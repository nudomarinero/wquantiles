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

## Phase 2 — Correctness pass · `fix/correctness` · **[x]**

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

**Release:** **0.7** was released on 2026-09-17, after Phase 4 rather than at
the end of this phase — Phases 3 and 4 changed enough (real CI, and the
tie-summing fix the property tests uncovered) that shipping before them would
have released untested and since-superseded behaviour. See Phase 4a.

---

## Phase 3 — Real CI · `ci/github-actions` · **[x]**

Nothing currently runs the test suite. `.github/workflows/` holds only
`codeql-analysis.yml`, and the README's build badge points at travis-ci.org,
which is shut down — the repository advertises a build status that does not exist.

- `.github/workflows/tests.yml`, `uv`-driven. Ten test jobs:
  - Python 3.9 – 3.14 on Linux with current numpy;
  - Python 3.9 with **numpy 1.19.5**, the oldest combination that can exist;
  - Python 3.12 with **numpy 1.x**, the axis that proves the compatibility
    claim the README makes;
  - Python 3.12 on Windows and macOS. Windows earns its slot because integer
    arrays defaulted to int32 there and the tests cover integer dtypes.
  Verified locally before committing: all six Python versions pass, and numpy
  back to 1.19.5 passes (with the hazen test correctly skipping below 1.22,
  where `np.quantile` gained `method=`).
- A `coverage` job, gated at 100%. The module is at 100% of 87 statements.
- A `package` job that builds both artefacts, runs `twine check`, and performs
  the **round trip**: install the wheel into a clean environment and run the
  sdist's own tests against it. Issue #1 was a packaging failure, so this is
  proved rather than assumed. Verified locally.
- Correct the numpy floor from `>=1.18` to `>=1.19`. numpy 1.18 has no wheels
  for Python 3.9, so with `requires-python = ">=3.9"` it was unreachable from
  any supported interpreter — the declared floor could never have been used.
- Modernise `codeql-analysis.yml`: it pinned `github/codeql-action@v1`, which
  GitHub retired, and `actions/checkout@v2`. *Decided:* keep it rather than
  delete it, since it was added deliberately in the most recent commit on
  `master`; it now runs on `develop` too.
- Add the Actions badge to the README. The Travis badge was already removed in
  Phase 2, when travis-ci.org turned out to be shut down.

- An `all-green` job that gathers the other three. Matrix jobs are reported
  under their rendered names (`py3.9 · numpy latest · ubuntu-latest`), so
  requiring them individually would mean editing the protection rule every time
  the matrix changes. **`All green` is the one check to require.**

**Manual follow-up for the maintainer:** making this a required check is a
branch-protection setting in the GitHub UI, not something a workflow file can
declare, and GitHub only offers a check name for selection after it has seen
that check run at least once. So the order is: push the branch, let the
workflow run once, then add the rule requiring `All green` on `master` and
`develop`.

**Breaking changes:** none.

---

## Phase 4 — Tests worth having · `test/coverage-and-properties` · **[x]**

Coverage was already at 100% after Phase 2, so this phase is not about reaching
unreached lines. It is about what coverage cannot see.

- Delete `test_median`: every assertion in it was about `np.median`, so it
  tested numpy rather than this library.
- `test/test_weighted.py` becomes `test/test_quantiles.py`, pytest functions
  rather than `unittest` classes.
- Replace the hardcoded 5×5×5 expected array, whose magic numbers had no
  derivation and could not be told apart from a stale constant. Two tests take
  its place: one derives its expectation by applying `quantile_1D` to each row,
  which is precisely the dispatcher's contract, over several shapes; the other
  is an anchor worked out by hand with the derivation written out, so a change
  in the maths cannot slip past a test that derives its own expectation from
  the code.
- Property-based tests with Hypothesis (`test/test_properties.py`). **Every
  candidate property was checked over several thousand random cases before
  being asserted**, and two of the five originally planned did not survive.
  - *Hold:* result within `[min, max]`; q=0 and q=1 give the extremes;
    non-decreasing in `q`; scaling every weight by a positive constant changes
    nothing; equal weights equal `np.quantile(..., method="hazen")`; zero
    weights, masks and `nanquantile` each equal removing the points; `median`
    agrees with `quantile` at 0.5; input order does not matter **for distinct
    values**.
  - *Does not hold:* **duplicating a point is not the same as doubling its
    weight.** The duplicate spreads its mass over two interpolation nodes,
    whereas the doubled weight puts one node at the midpoint: `[1,2,2,3]` with
    unit weights gives `1.5` at q=0.25, where `[1,2,3]` with `[1,2,1]` gives
    `1.333`.
  - *Does not hold:* **input order does not matter when values tie.** See below.

  Both failures are recorded as strict `xfail`s rather than quietly dropped, so
  they will speak up if the behaviour ever changes.

Result: 82 passed, 2 xfailed, coverage still 100%.

**Breaking changes:** none in this phase.

### Found by the property tests: ties with unequal weights — **fixed**

`quantile_1D` is not a function of the multiset of `(value, weight)` pairs.
When two values are exactly equal but carry different weights, `argsort`
decides which weight lands on which tied position, and the answer moves:

    data [1, 2, 2, 3], weights [1, 5, 0.5, 1]
      as given             q=0.2 -> 1.333
      the two 2s swapped   q=0.2 -> 2.000

26% of cases with tied values and unequal weights are order-dependent this way.
Continuous data essentially never ties; integer-valued or binned scientific
data ties constantly.

Three ways out, measured:

| | matches `np.quantile(hazen)` at unit weights | order-invariant | changes tied results |
|---|---|---|---|
| leave as is | **100%** | no — 26% of cases | — |
| sum the weights of tied values | 57% ✗ | yes | 69% |
| sort ties by weight | **100%** | **yes** | 26% |

Summing tied weights is what statsmodels does, but it would **break the hazen
equivalence the README now states as the library's definition**: with unit
weights and ties it stops matching numpy. Sorting ties by weight is a stable
tie-break — it makes the sort order a function of the data rather than of the
caller's array order, keeps the numpy equivalence exactly, and leaves the
repo's own 1-D fixture unchanged, since that tie carries equal weights.

*Decided:* **sum the weights of tied values**, implemented in this phase and
released in 0.7.

The measurement above made the case for sorting ties by weight, on the strength
of keeping the numpy `hazen` equivalence at 100%. That reasoning was wrong, for
two reasons found on closer inspection:

1. **`hazen`'s tie behaviour is not a considered position.** Hyndman-Fan type 5
   is defined on order statistics, which include repeats, so numpy is faithful
   to the definition — but the plotting-position family is derived from the
   distribution of `F(X_(i))` for iid draws from a *continuous* `F`, where ties
   have probability zero. The definition is silent on repeated values; the
   order-statistic formula simply produces something when handed them.
2. **Sorting ties by weight fixes the symptom, not the defect.** It removes the
   order-dependence while leaving the estimator not a function of the weighted
   distribution: duplicating a point still would not equal doubling its weight.

Summing tied weights makes every verified property hold, including the two that
previously failed, and makes `wquantiles` agree with itself — `[1,2,3]` weighted
`[1,2,1]` and `[1,2,2,3]` with unit weights are the same sample written two
ways, and numpy's weighted `inverted_cdf` and statsmodels already gave identical
answers for them where this library did not.

The price is one clause in the README: the `hazen` equivalence now holds for
equal weights **and distinct values**. Results for distinct values with
all-positive weights remain bit-identical to 0.6 (~54,000 comparisons).

- `BREAKING:` the weights of equal values are summed. Continuous data is
  untouched; around 40% of unit-weight cases on integer or binned data move.
  The repo's own 1-D fixture moves from `30.0` to `30 + 5/6`.

---

## Phase 4a — Release 0.7 · `chore/release-0.7` · **[~]**

- Date the `0.7` heading in `CHANGES.md`.
- Refresh the stale dates the release would otherwise ship:
  - `LICENSE` still said `2014-2021`, last touched for 0.6;
  - `docs/conf.py` claimed `version = '0.2'` and `copyright = u'2014, Author'`,
    both untouched since `sphinx-quickstart` in 2014. The version is now read
    from the installed package metadata so it cannot drift again, and the
    author is a real name in all seven places that said `u'Author'`.
- Merge `develop` into `master` by pull request and tag the release.

**Tag name:** `v0.7`, not `v0.7.0`. The repository's existing tags are `v0.3`
and `v0.6`, and PyPI carries 0.3, 0.4, 0.5 and 0.6 — two components throughout.
The plan previously said `v0.7.0`, which would have broken that convention.

**Publishing to PyPI is the maintainer's step**, with `uv publish`; it needs
credentials this session does not have. The last upload was 0.6 on 2021-05-26.

**Breaking changes:** none of its own. This is where the seven breaking changes
of Phases 1–4 reach users; `CHANGES.md` leads with them.

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
- Merge `develop` into `master` by pull request, tag `v1.0` on `master`
  (two components, matching `v0.3`, `v0.6` and `v0.7`).
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
| 2 | Tied values have their weights summed (**changes valid results**) | none — documented in the README |
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
