"""Behavioural and error-handling tests for ``brentq``."""

from __future__ import annotations

import math

import pytest

from cybrentq import ConvergenceError, RootResults, brentq


class TestBasicConvergence:
    def test_finds_root_of_canonical_problem(self, problem):
        name, f, a, b, expected = problem
        root = brentq(f, a, b)
        # Tolerance is intentionally a bit loose so the very-flat (x-1)^3
        # problem doesn't fail on the absolute-error check; the residual
        # check below is the real correctness test.
        assert math.isclose(root, expected, rel_tol=1e-6, abs_tol=1e-6), name
        assert abs(f(root)) < 1e-8, name

    def test_default_tolerances_are_tight(self):
        root = brentq(lambda x: x * x - 2.0, 0.0, 2.0)
        assert abs(root - math.sqrt(2.0)) < 1e-12

    def test_returns_python_float(self):
        root = brentq(lambda x: x - 1.0, 0.0, 2.0)
        assert type(root) is float


class TestFullOutput:
    def test_full_output_returns_root_results(self):
        root, info = brentq(lambda x: x * x - 2.0, 0.0, 2.0, full_output=True)
        assert isinstance(info, RootResults)
        assert info.root == root
        assert info.converged is True
        assert info.flag == "converged"
        assert info.iterations >= 1
        assert info.function_calls >= 2  # f(a) and f(b) at minimum

    def test_iteration_and_call_counts_are_consistent(self):
        calls = 0

        def f(x):
            nonlocal calls
            calls += 1
            return x**3 - x - 2.0

        _, info = brentq(f, 1.0, 2.0, full_output=True)
        assert info.function_calls == calls


class TestExactRootAtEndpoint:
    def test_root_exactly_at_a(self):
        root, info = brentq(lambda x: x, 0.0, 1.0, full_output=True)
        assert root == 0.0
        assert info.iterations == 0
        assert info.function_calls == 1

    def test_root_exactly_at_b(self):
        root, info = brentq(lambda x: x - 1.0, 0.0, 1.0, full_output=True)
        assert root == 1.0
        assert info.iterations == 0
        # 2 calls: f(a) checked first, then f(b) which equals zero.
        assert info.function_calls == 2


class TestArgsPassing:
    def test_args_forwarded_to_function(self):
        def f(x, target, scale):
            return scale * (x - target)

        root = brentq(f, -10.0, 10.0, args=(3.5, 2.0))
        assert math.isclose(root, 3.5, abs_tol=1e-12)

    def test_empty_args_default(self):
        root = brentq(lambda x: x - 7.0, 0.0, 100.0)
        assert math.isclose(root, 7.0, abs_tol=1e-12)


class TestInputValidation:
    def test_same_sign_raises(self):
        with pytest.raises(ValueError, match="opposite signs"):
            brentq(lambda x: x * x + 1.0, -1.0, 1.0)

    def test_non_positive_xtol_raises(self):
        with pytest.raises(ValueError, match="xtol"):
            brentq(lambda x: x, -1.0, 1.0, xtol=0.0)
        with pytest.raises(ValueError, match="xtol"):
            brentq(lambda x: x, -1.0, 1.0, xtol=-1e-10)

    def test_too_small_rtol_raises(self):
        with pytest.raises(ValueError, match="rtol"):
            brentq(lambda x: x, -1.0, 1.0, rtol=1e-20)

    def test_zero_maxiter_raises(self):
        with pytest.raises(ValueError, match="maxiter"):
            brentq(lambda x: x, -1.0, 1.0, maxiter=0)


class TestConvergenceFailure:
    def test_disp_true_raises_on_maxiter(self):
        with pytest.raises(ConvergenceError):
            brentq(lambda x: x * x - 2.0, 0.0, 2.0, maxiter=1, disp=True)

    def test_disp_false_returns_non_converged_result(self):
        root, info = brentq(
            lambda x: x * x - 2.0,
            0.0,
            2.0,
            maxiter=1,
            disp=False,
            full_output=True,
        )
        assert info.converged is False
        assert info.flag == "convergence error"
        assert math.isfinite(root)


class TestExceptionPropagation:
    def test_user_function_exception_propagates(self):
        sentinel = RuntimeError("user code blew up")

        def f(x):
            raise sentinel

        with pytest.raises(RuntimeError) as exc_info:
            brentq(f, 0.0, 1.0)
        assert exc_info.value is sentinel


class TestSwappedBracket:
    """The algorithm should be agnostic to whether a < b or a > b."""

    def test_reversed_bracket(self):
        root = brentq(lambda x: x * x - 2.0, 2.0, 0.0)
        assert math.isclose(root, math.sqrt(2.0), abs_tol=1e-12)
