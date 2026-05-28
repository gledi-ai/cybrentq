"""Cython implementation of Brent's root-finding algorithm.

Public API mirrors the parts of ``scipy.optimize.brentq`` that most users
need so it can be used as a drop-in replacement in many cases.
"""

from ._brentq import ConvergenceError, RootResults, brentq

__all__ = ["ConvergenceError", "RootResults", "brentq"]
__version__ = "0.1.0"
