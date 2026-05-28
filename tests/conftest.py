"""Shared test fixtures and the canonical set of root-finding problems.

Each problem is a tuple ``(name, f, a, b, expected_root)``. They cover a
range of behaviours: smooth polynomials, transcendentals, functions with
flat regions near the root, roots near the endpoints, and roots that scipy
itself uses in its test suite.
"""

from __future__ import annotations

import math

import pytest


def _f_quadratic(x: float) -> float:
    return x * x - 2.0


def _f_cubic(x: float) -> float:
    return x**3 - x - 2.0


def _f_cos_minus_x(x: float) -> float:
    return math.cos(x) - x


def _f_sin(x: float) -> float:
    return math.sin(x)


def _f_log(x: float) -> float:
    return math.log(x)


def _f_exp_minus_2(x: float) -> float:
    return math.exp(x) - 2.0


def _f_flat(x: float) -> float:
    # Very flat near the root; stresses the interpolation step.
    return (x - 1.0) ** 3


def _f_steep(x: float) -> float:
    # Steep around the root.
    return math.atan(1000.0 * (x - 0.5))


def _f_high_degree(x: float) -> float:
    # Wilkinson-ish polynomial with a root at 5.
    return (x - 5.0) * (x - 1.0) * (x + 2.0)


def _f_root_near_left(x: float) -> float:
    return x - 1.0 + 1e-10


def _f_root_near_right(x: float) -> float:
    return x - 1.0 + 1e-10  # same function, different bracket below


PROBLEMS = [
    ("x^2 - 2", _f_quadratic, 0.0, 2.0, math.sqrt(2.0)),
    ("x^3 - x - 2", _f_cubic, 1.0, 2.0, 1.5213797068045676),
    ("cos(x) - x", _f_cos_minus_x, 0.0, 1.0, 0.7390851332151607),
    ("sin(x), root at pi", _f_sin, 3.0, 4.0, math.pi),
    ("log(x), root at 1", _f_log, 0.5, 2.0, 1.0),
    ("exp(x) - 2", _f_exp_minus_2, 0.0, 2.0, math.log(2.0)),
    ("(x-1)^3 flat root", _f_flat, 0.0, 2.0, 1.0),
    ("atan(1000(x-0.5))", _f_steep, 0.0, 1.0, 0.5),
    ("cubic with root at 5", _f_high_degree, 3.0, 10.0, 5.0),
    ("root near left endpoint", _f_root_near_left, 1.0 - 1e-10, 5.0, 1.0 - 1e-10),
    ("root near right endpoint", _f_root_near_right, -5.0, 1.0 - 1e-10 + 1e-15, 1.0 - 1e-10),
]


@pytest.fixture(params=PROBLEMS, ids=lambda p: p[0])
def problem(request):
    """Yields one canonical test problem at a time."""
    return request.param
