"""Cython implementation of Brent's root-finding algorithm.

Public API mirrors the parts of ``scipy.optimize.brentq`` that most users
need so it can be used as a drop-in replacement in many cases.
"""

from ._brentq import ConvergenceError, RootResults, brentq

try:
    from ._version import __version__
except ImportError:  # pragma: no cover - source tree without a build
    __version__ = "0.0.0+unknown"

__all__ = ["ConvergenceError", "RootResults", "__version__", "brentq"]
