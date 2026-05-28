"""Benchmark ``cybrentq.brentq`` against ``scipy.optimize.brentq``.

Run with ``python benchmarks/bench_brentq.py``. Pass ``--repeats`` to
control the number of timing repeats per problem.

For each problem we:

  1. Warm up both implementations a few times (lets the CPU caches settle
     and avoids the first-call import / JIT-ish costs from skewing
     results).
  2. Time ``N`` solves in a tight loop using ``time.perf_counter_ns``.
  3. Repeat ``--repeats`` times and report the **minimum** elapsed time.
     The minimum is the standard choice for micro-benchmarks because the
     noise floor is one-sided (the OS can only slow you down).
  4. Confirm that both implementations actually agree on the root for
     each problem before timing it.

The benchmark deliberately includes a mix of trivial functions (where
algorithmic overhead dominates and our Cython version should shine) and
moderately expensive functions (where Python call overhead from ``f``
dominates and both implementations should look similar).
"""

from __future__ import annotations

import argparse
import math
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass

from pymodab import find_root as modab_find_root
from scipy.optimize import brentq as scipy_brentq

from cybrentq import brentq as cy_brentq

Problem = tuple[str, Callable[[float], float], float, float]

PROBLEMS: list[Problem] = [
    ("x^2 - 2 (cheap)", lambda x: x * x - 2.0, 0.0, 2.0),
    ("x^3 - x - 2 (cheap)", lambda x: x**3 - x - 2.0, 1.0, 2.0),
    ("cos(x) - x", lambda x: math.cos(x) - x, 0.0, 1.0),
    ("exp(x) - 2", lambda x: math.exp(x) - 2.0, 0.0, 2.0),
    ("sin(x), root at pi", math.sin, 3.0, 4.0),
    ("(x-1)^3 (flat)", lambda x: (x - 1.0) ** 3, 0.0, 2.0),
    ("atan(1000*(x-0.5)) (steep)", lambda x: math.atan(1000.0 * (x - 0.5)), 0.0, 1.0),
    ("poly degree 5", lambda x: x**5 - 3.0 * x**3 + x - 1.0, 0.0, 2.0),
    (
        "expensive f (sum of 50 sines)",
        lambda x: sum(math.sin(k * x) / k for k in range(1, 51)) - 0.5,
        0.5,
        3.0,
    ),
]


@dataclass
class Timing:
    name: str
    impl: str
    n_calls: int
    repeats: int
    times_ns: list[int]

    @property
    def best_ns(self) -> int:
        return min(self.times_ns)

    @property
    def per_call_ns(self) -> float:
        return self.best_ns / self.n_calls

    @property
    def stdev_ns(self) -> float:
        return statistics.stdev(self.times_ns) if len(self.times_ns) > 1 else 0.0


def _bench(impl, name: str, impl_label: str, f, a: float, b: float, n_calls: int, repeats: int, warmup: int) -> Timing:
    # Warm up.
    for _ in range(warmup):
        impl(f, a, b)

    times_ns: list[int] = []
    for _ in range(repeats):
        t0 = time.perf_counter_ns()
        for _ in range(n_calls):
            impl(f, a, b)
        t1 = time.perf_counter_ns()
        times_ns.append(t1 - t0)
    return Timing(name=name, impl=impl_label, n_calls=n_calls, repeats=repeats, times_ns=times_ns)


def _verify_agreement(f, a: float, b: float, name: str) -> None:
    cy = cy_brentq(f, a, b)
    sp = scipy_brentq(f, a, b)
    mb = modab_find_root(f, a, b)
    if not math.isclose(cy, sp, rel_tol=1e-9, abs_tol=1e-9):
        raise AssertionError(f"{name}: cy/scipy disagree (cy={cy!r}, scipy={sp!r})")
    if not math.isclose(mb, sp, rel_tol=1e-9, abs_tol=1e-9):
        raise AssertionError(f"{name}: modab/scipy disagree (modab={mb!r}, scipy={sp!r})")


def run(n_calls: int, repeats: int, warmup: int) -> None:
    print(
        f"Benchmarking cybrentq vs scipy.optimize.brentq "
        f"(N={n_calls} solves/repeat, {repeats} repeats, "
        f"{warmup} warmup solves)\n"
    )
    header = f"{'problem':<32} {'scipy (µs)':>12} {'cython (µs)':>12} {'modab (µs)':>12} {'cy/sc':>8} {'mb/sc':>8}"
    print(header)
    print("-" * len(header))

    cy_speedups: list[float] = []
    mb_speedups: list[float] = []
    for name, f, a, b in PROBLEMS:
        _verify_agreement(f, a, b, name)

        sp = _bench(scipy_brentq, name, "scipy", f, a, b, n_calls, repeats, warmup)
        cy = _bench(cy_brentq, name, "cython", f, a, b, n_calls, repeats, warmup)
        mb = _bench(modab_find_root, name, "modab", f, a, b, n_calls, repeats, warmup)

        sp_per = sp.per_call_ns / 1000.0
        cy_per = cy.per_call_ns / 1000.0
        mb_per = mb.per_call_ns / 1000.0
        cy_speedup = sp.best_ns / cy.best_ns
        mb_speedup = sp.best_ns / mb.best_ns
        cy_speedups.append(cy_speedup)
        mb_speedups.append(mb_speedup)
        print(f"{name:<32} {sp_per:>12.3f} {cy_per:>12.3f} {mb_per:>12.3f} {cy_speedup:>7.2f}x {mb_speedup:>7.2f}x")

    print("-" * len(header))

    def _summary(label: str, speedups: list[float]) -> None:
        if not speedups:
            return
        gmean = math.exp(sum(math.log(s) for s in speedups) / len(speedups))
        print(f"{label}: gmean {gmean:.2f}x  min {min(speedups):.2f}x  max {max(speedups):.2f}x")

    _summary("cython vs scipy", cy_speedups)
    _summary("modab  vs scipy", mb_speedups)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-calls", type=int, default=2000, help="solves per timed batch (default: 2000)")
    parser.add_argument("--repeats", type=int, default=5, help="how many timed batches to run (default: 5)")
    parser.add_argument("--warmup", type=int, default=10, help="warmup solves before timing (default: 10)")
    args = parser.parse_args()
    run(n_calls=args.n_calls, repeats=args.repeats, warmup=args.warmup)


if __name__ == "__main__":
    main()
