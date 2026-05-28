"""Parity tests against ``scipy.optimize.brentq``.

We treat scipy as the reference implementation. For each problem in the
shared fixture set we require:

* both implementations report converged=True,
* roots agree to within ``rtol*|root| + xtol`` (the algorithm's own
  bracket), with some slack to absorb the fact that the two
  implementations may pick different points inside the final bracket,
* iteration counts agree exactly (the algorithm is deterministic, so any
  divergence is a sign of a subtle bug in our translation).
"""

from __future__ import annotations

import math

import pytest

scipy_optimize = pytest.importorskip("scipy.optimize")

from cybrentq import brentq as cy_brentq  # noqa: E402

scipy_brentq = scipy_optimize.brentq


# Tolerance for comparing the two roots: both should land in the same
# converged bracket so this is a loose but meaningful upper bound.
_AGREEMENT_RTOL = 1e-10
_AGREEMENT_ATOL = 1e-10


def _both(f, a, b, **kw):
    cy_root, cy_info = cy_brentq(f, a, b, full_output=True, **kw)
    sp_root, sp_info = scipy_brentq(f, a, b, full_output=True, **kw)
    return cy_root, cy_info, sp_root, sp_info


class TestRootAgreement:
    def test_roots_match_scipy(self, problem):
        name, f, a, b, _expected = problem
        cy_root, cy_info, sp_root, sp_info = _both(f, a, b)

        assert cy_info.converged, name
        assert sp_info.converged, name
        assert math.isclose(cy_root, sp_root, rel_tol=_AGREEMENT_RTOL, abs_tol=_AGREEMENT_ATOL), (
            f"{name}: cy={cy_root!r} vs scipy={sp_root!r}"
        )

    def test_residuals_match_scipy(self, problem):
        name, f, a, b, _expected = problem
        cy_root, _, sp_root, _ = _both(f, a, b)
        # Residuals should be the same order of magnitude.
        cy_res, sp_res = abs(f(cy_root)), abs(f(sp_root))
        if sp_res == 0.0:
            assert cy_res < 1e-10, name
        else:
            # Two orders of magnitude is a generous bound; in practice the
            # residuals are usually within a factor of 2.
            ratio = cy_res / sp_res if sp_res > 0 else 1.0
            assert 1e-2 < ratio < 1e2 or cy_res < 1e-10, f"{name}: cy_res={cy_res!r}, sp_res={sp_res!r}"


class TestIterationParity:
    """Brent's method is deterministic, so iteration counts should match."""

    def test_iteration_count_matches_scipy(self, problem):
        name, f, a, b, _expected = problem
        _, cy_info, _, sp_info = _both(f, a, b)
        assert cy_info.iterations == sp_info.iterations, f"{name}: cy={cy_info.iterations}, scipy={sp_info.iterations}"

    def test_function_call_count_matches_scipy(self, problem):
        name, f, a, b, _expected = problem
        _, cy_info, _, sp_info = _both(f, a, b)
        assert cy_info.function_calls == sp_info.function_calls, (
            f"{name}: cy={cy_info.function_calls}, scipy={sp_info.function_calls}"
        )


class TestArgsParity:
    def test_args_behave_like_scipy(self):
        def f(x, target):
            return x**3 - target

        cy_root = cy_brentq(f, 0.0, 5.0, args=(27.0,))
        sp_root = scipy_brentq(f, 0.0, 5.0, args=(27.0,))
        assert math.isclose(cy_root, sp_root, rel_tol=1e-12, abs_tol=1e-12)
        assert math.isclose(cy_root, 3.0, rel_tol=1e-10, abs_tol=1e-10)


class TestErrorParity:
    def test_same_sign_error_in_both(self):
        def f(x):
            return x * x + 1.0

        with pytest.raises(ValueError, match="signs"):
            cy_brentq(f, -1.0, 1.0)
        with pytest.raises(ValueError, match="signs"):
            scipy_brentq(f, -1.0, 1.0)


@pytest.mark.parametrize(
    "n",
    [2, 3, 5, 7, 10, 25],
    ids=lambda n: f"x^{n} - 2",
)
class TestPowerFunctions:
    """Sweep across x**n - 2 for several n values."""

    def test_match_scipy(self, n):
        def f(x):
            return x**n - 2.0

        cy_root = cy_brentq(f, 0.0, 2.0)
        sp_root = scipy_brentq(f, 0.0, 2.0)
        assert math.isclose(cy_root, sp_root, rel_tol=1e-12, abs_tol=1e-12)


@pytest.mark.parametrize("seed", list(range(20)))
def test_random_linear_roots_match_scipy(seed):
    """Linear functions a*x + b across many random parameter draws."""
    import random

    rng = random.Random(seed)
    slope = rng.uniform(-10.0, 10.0)
    while abs(slope) < 0.1:
        slope = rng.uniform(-10.0, 10.0)
    target = rng.uniform(-50.0, 50.0)

    def f(x):
        return slope * x - target

    expected = target / slope
    pad = abs(expected) + 1.0
    a, b = expected - pad, expected + pad

    cy_root = cy_brentq(f, a, b)
    sp_root = scipy_brentq(f, a, b)
    assert math.isclose(cy_root, sp_root, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(cy_root, expected, rel_tol=1e-10, abs_tol=1e-10)
