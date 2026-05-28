"""Performance regression test.

This is *not* a benchmark — its job is to catch catastrophic perf
regressions. We require our implementation to be within a generous
factor of scipy on a small set of representative problems. The exact
threshold is tuned to be wide enough that ordinary CI noise doesn't
flake the test but tight enough that "we accidentally added a global
import in the hot path" would be caught.

For real performance measurements, run ``python benchmarks/bench_brentq.py``.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable

import pytest

scipy_optimize = pytest.importorskip("scipy.optimize")

from cybrentq import brentq as cy_brentq  # noqa: E402

scipy_brentq = scipy_optimize.brentq


PROBLEMS: list[tuple[str, Callable[[float], float], float, float]] = [
    ("x^2 - 2", lambda x: x * x - 2.0, 0.0, 2.0),
    ("cos(x) - x", lambda x: math.cos(x) - x, 0.0, 1.0),
    ("(x-1)^3", lambda x: (x - 1.0) ** 3, 0.0, 2.0),
]

# Allow ourselves to be up to this factor slower than scipy. scipy's brentq
# is a hand-written C routine, so being within ~3x while supporting the
# same Python-callable API is reasonable.
MAX_SLOWDOWN = 4.0


def _time_calls(fn, problem, n_calls: int, repeats: int) -> float:
    f, a, b = problem
    # Warm up.
    for _ in range(5):
        fn(f, a, b)
    best = float("inf")
    for _ in range(repeats):
        t0 = time.perf_counter_ns()
        for _ in range(n_calls):
            fn(f, a, b)
        elapsed = time.perf_counter_ns() - t0
        if elapsed < best:
            best = elapsed
    return best


@pytest.mark.parametrize("problem", PROBLEMS, ids=lambda p: p[0])
def test_not_dramatically_slower_than_scipy(problem):
    name, f, a, b = problem
    cy_time = _time_calls(cy_brentq, (f, a, b), n_calls=1000, repeats=3)
    sp_time = _time_calls(scipy_brentq, (f, a, b), n_calls=1000, repeats=3)
    ratio = cy_time / sp_time
    assert ratio <= MAX_SLOWDOWN, (
        f"{name}: cython implementation is {ratio:.2f}x slower than scipy "
        f"(threshold {MAX_SLOWDOWN}x). cy={cy_time / 1e6:.2f}ms, "
        f"sp={sp_time / 1e6:.2f}ms"
    )
