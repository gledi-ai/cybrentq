# cybrentq

A production-quality Cython implementation of Brent's root-finding method.
The algorithm is a faithful translation of the C routine in
`scipy/optimize/Zeros/brentq.c`: bisection guarded by inverse quadratic
interpolation, with a secant fallback and bisection used whenever an
interpolation step would not make adequate progress.

The public API mirrors the relevant subset of `scipy.optimize.brentq` and can
serve as a drop-in replacement in most code paths.

Requires **Python 3.10 or newer** and a working C compiler (used during
install to compile the Cython extension).

## Quick start

This project uses [`uv`](https://docs.astral.sh/uv/) for environment and
dependency management, with a `Makefile` wrapping the most common commands.

```bash
# Install uv if you don't have it:
#   curl -LsSf https://astral.sh/uv/install.sh | sh   (macOS / Linux)
#   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"   (Windows)

# Recommended: use the Makefile. PYTHON_VERSION=3.10 by default.
# The Cython extension is compiled during `make sync`.
make venv
make sync
```

The Makefile passes hardening flags the bare commands omit
(`--frozen --refresh --all-extras --all-groups --link-mode=copy`, plus
`--seed --prompt=cybrentq` on `venv`). Read the `Makefile` for the full
invocations.

If you want a minimal install without the Makefile:

```bash
uv venv --python 3.10       # create the venv
uv sync                     # install project + default groups, compile Cython
uv sync --group test        # add the test group only
uv sync --no-dev            # consumer-style install (no dev groups)
```

`uv sync` reads `pyproject.toml`, provisions a matching interpreter, builds
the C extension via the PEP 517 backend (setuptools + Cython), and writes
a `uv.lock`. Commit `uv.lock` for reproducible builds across machines.

### Editable iteration on the Cython source

`uv sync` installs the project into the managed venv. After editing
`_brentq.pyx`, re-run `uv sync --reinstall-package cybrentq` (or just
`uv sync` if you also bump the version) to force a recompile.

## Usage

```python
import math
from cybrentq import brentq

# Basic usage — finds sqrt(2)
root = brentq(lambda x: x * x - 2.0, 0.0, 2.0)

# Pass extra arguments via the args tuple
root = brentq(lambda x, target: x ** 3 - target, 0.0, 5.0, args=(27.0,))

# Diagnostics
root, info = brentq(lambda x: math.cos(x) - x, 0.0, 1.0, full_output=True)
print(info)
# RootResults(root=0.7390851332151607, iterations=8, function_calls=10,
#             converged=True, flag='converged')
```

### Signature

```python
brentq(
    f,                          # callable, f(x, *args) -> float
    a, b,                       # bracketing interval, f(a)*f(b) < 0
    args=(),                    # extra positional args forwarded to f
    xtol=2e-12,                 # absolute tolerance
    rtol=4*eps,                 # relative tolerance (>= 4 * machine eps)
    maxiter=100,                # iteration budget
    full_output=False,          # return RootResults alongside the root
    disp=True,                  # raise on non-convergence instead of returning a flag
) -> float | tuple[float, RootResults]
```

### Errors

| Condition | Behaviour |
|---|---|
| `f(a)` and `f(b)` have the same sign | `ValueError` |
| `xtol <= 0`, `rtol < 4*eps`, or `maxiter < 1` | `ValueError` |
| Iteration budget exhausted and `disp=True` | `ConvergenceError` |
| Iteration budget exhausted and `disp=False` | returns `(root, RootResults(converged=False))` |
| User-supplied `f` raises | exception propagates unchanged |

## Tests

```bash
make test                                   # all tests
make cov                                    # coverage run (see warning below)
make report                                 # print coverage report from last run

# Direct equivalents for `make test`:
uv run pytest                               # all tests
uv run pytest tests/test_basic.py           # just behaviour / error tests
uv run pytest tests/test_against_scipy.py   # head-to-head correctness vs scipy
uv run pytest tests/test_performance.py     # perf regression guard (CI-safe)
```

> **Note on `make cov`**: the target wipes `.c`/`.so` artifacts and
> reinstalls `cybrentq` with `CYTHON_TRACE=1` so that `coverage.py` (via
> the `Cython.Coverage` plugin) can report line coverage from `_brentq.pyx`.
> The traced build is significantly slower at runtime. **After running
> `make cov`, run `make sync` before `make bench`** — otherwise the
> traced extension will skew benchmark numbers.

The scipy-comparison suite asserts that:

- both implementations report `converged=True` on every problem,
- root estimates agree to within `1e-10` relative and absolute tolerance,
- iteration counts and function-call counts match exactly (Brent's method
  is deterministic, so any divergence flags a bug in our translation).

## Benchmarks

The benchmark suite compares this Cython `brentq` against
`scipy.optimize.brentq` and against
[`pymodab`](https://pypi.org/project/pymodab/) (a C implementation of the
Modified Anderson-Björck root-finding method) across nine problems.

```bash
make bench                                              # default config
make bench BENCH_ARGS="--n-calls 5000 --repeats 7"      # override args

# Direct equivalent:
uv run python benchmarks/bench_brentq.py --n-calls 5000 --repeats 7
```

Sample output (numbers depend on the machine, Python build, and library
versions):

```
problem                            scipy (µs)  cython (µs)   modab (µs)    cy/sc    mb/sc
-----------------------------------------------------------------------------------------
x^2 - 2 (cheap)                         8.374        0.518        2.665   16.16x    3.14x
x^3 - x - 2 (cheap)                     8.957        0.875        2.925   10.24x    3.06x
cos(x) - x                              7.978        0.782        2.718   10.20x    2.94x
exp(x) - 2                              9.862        0.981        2.950   10.05x    3.34x
sin(x), root at pi                      6.623        0.287        2.210   23.04x    3.00x
(x-1)^3 (flat)                          3.566        0.257        1.770   13.90x    2.02x
atan(1000*(x-0.5)) (steep)              3.692        0.341        1.864   10.82x    1.98x
poly degree 5                          13.879        2.010        4.445    6.90x    3.12x
expensive f (sum of 50 sines)          69.151       57.117       59.970    1.21x    1.15x
-----------------------------------------------------------------------------------------
cython vs scipy: gmean 9.24x  min 1.21x  max 23.04x
modab  vs scipy: gmean 2.52x  min 1.15x  max 3.34x
```

Columns: `cy/sc` is `scipy_time / cython_time` (Cython speedup over scipy);
`mb/sc` is `scipy_time / modab_time` (pymodab speedup over scipy). Higher is
better in both columns.

Before each timed problem the runner calls all three implementations and
asserts the roots agree to within `1e-9` — a benchmark with a silent
correctness regression is worse than one that doesn't run.

A few things to note when reading the numbers:

- Brent's method usually converges in 6–15 iterations, so most of the wall
  time of a single solve is spent **inside** `f`, not inside the algorithm.
  When `f` is expensive (the "sum of 50 sines" row), all implementations
  spend the vast majority of their time in `f` and look nearly identical.
- The Cython win is largest when `f` is cheap, because that is when the
  algorithm's own overhead matters most.
- pymodab's Modified Anderson-Björck typically uses fewer `f` evaluations
  than Brent — but each iteration carries pure-Python wrapper overhead
  here, so it lands between scipy and our Cython version.

## Building distributions

```bash
make build            # equivalent to: uv build
                      # produces sdist + wheel under dist/
```

## Make targets

`make help` lists every target with a short description.

| Target | Action |
|---|---|
| `venv` | Create the project venv via `uv venv` (`PYTHON_VERSION=3.10` by default) |
| `lock` | Resolve and write `uv.lock` (`uv lock --upgrade --refresh`) |
| `outdated` | Show outdated direct and transitive deps |
| `sync` | Sync the venv with `uv.lock` (all groups + extras) |
| `test` | Run the test suite without coverage |
| `cov` / `test/cov` | Recompile extension with `CYTHON_TRACE=1` and run under `coverage.py` (no pytest-cov). Run `make sync` afterward to restore the fast build. |
| `report` / `cov/report` | Print the coverage report from the last `make cov` |
| `bench` | Run the benchmark suite (override args via `BENCH_ARGS=…`) |
| `lint` / `lint/check` | Read-only `ruff check` |
| `lint/fix` | **Rewrites files** — `ruff check --fix` |
| `fmt` / `fmt/check` | Read-only `ruff format --check` |
| `fmt/fix` | **Rewrites files** — `ruff format` |
| `check` | `lint/check` + `fmt/check` (CI-safe) |
| `build` / `dist` | Build sdist + wheel into `dist/` |
| `clean` | Remove build artifacts and coverage data |

Bare `lint` and `fmt` are intentionally read-only; mutation requires the
explicit `/fix` variant so typos don't rewrite the tree.

## Linting and formatting

The project pins [ruff](https://docs.astral.sh/ruff/) (configuration in
`pyproject.toml` under `[tool.ruff]`). Enabled rule families:

| Code | Family |
|---|---|
| `E` / `W` | pycodestyle errors / warnings |
| `F` | pyflakes (unused imports, undefined names) |
| `I` | isort |
| `N` | pep8-naming |
| `UP` | pyupgrade |
| `C90` | mccabe complexity (`max-complexity = 10`) |
| `A` | flake8-builtins (shadowing) |
| `B` | flake8-bugbear |
| `PERF` | perflint |
| `PT` | flake8-pytest-style |
| `RUF` | ruff-native rules |
| `SIM` | flake8-simplify |
| `TRY` | tryceratops (exception hygiene) |

Ruff lints `.py` files only — `_brentq.pyx` is outside the ruff scope.

```bash
make check            # lint + format check, no mutations (use this in CI)
make lint/fix         # rewrites files: ruff check --fix
make fmt/fix          # rewrites files: ruff format
```

## Layout

```
src/cybrentq/
  _brentq.pyx           # the algorithm
  _brentq.pyi           # type stubs for IDEs / mypy
  __init__.py           # re-exports brentq, RootResults, ConvergenceError
  py.typed              # PEP 561 marker
tests/
  conftest.py           # shared fixture: 11 canonical root-finding problems
  test_basic.py         # behaviour, error paths, edge cases
  test_against_scipy.py # parity vs scipy
  test_performance.py   # perf regression guard
benchmarks/
  bench_brentq.py       # speed comparison vs scipy and pymodab
Makefile                # venv, sync, test, cov, bench, lint, fmt, build
pyproject.toml          # project metadata + ruff/coverage/pytest config
```

## License

MIT.
