# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: initializedcheck=False
# cython: embedsignature=True
"""
Cython implementation of Brent's root finding method.

The algorithm follows the same logic as SciPy's C implementation in
``scipy/optimize/Zeros/brentq.c``: a hybrid of bisection, the secant method,
and inverse quadratic interpolation, with bisection used as a guaranteed
fallback whenever interpolation steps would not make adequate progress.
"""

from libc.math cimport fabs

# 4 * machine epsilon for IEEE-754 double precision. Matches SciPy.
cdef double _EPS = 2.220446049250313e-16
cdef double _RTOL_MIN = 4.0 * _EPS


cdef class RootResults:
    """Result object returned when ``full_output=True``.

    Mirrors the relevant fields of ``scipy.optimize.RootResults`` so it can be
    used interchangeably in most code paths.
    """
    cdef public double root
    cdef public Py_ssize_t iterations
    cdef public Py_ssize_t function_calls
    cdef public bint converged
    cdef public str flag

    def __cinit__(self, double root, Py_ssize_t iterations,
                  Py_ssize_t function_calls, bint converged, str flag):
        self.root = root
        self.iterations = iterations
        self.function_calls = function_calls
        self.converged = converged
        self.flag = flag

    def __repr__(self):
        return (
            f"RootResults(root={self.root!r}, iterations={self.iterations}, "
            f"function_calls={self.function_calls}, "
            f"converged={self.converged}, flag={self.flag!r})"
        )


class ConvergenceError(RuntimeError):
    """Raised when brentq fails to converge within ``maxiter`` iterations."""


cdef inline double _dmin(double a, double b) noexcept nogil:
    return a if a < b else b


cdef inline bint _opposite_sign(double a, double b) noexcept nogil:
    # Equivalent to (a * b) < 0 but immune to underflow / overflow.
    return (a > 0.0 and b < 0.0) or (a < 0.0 and b > 0.0)


cdef inline double _call(object f, double x, tuple args, bint no_args) except? -1.0:
    # Fast path for the no-args case (by far the most common); falls back to
    # tuple unpacking when extra arguments are required.
    if no_args:
        return <double> f(x)
    return <double> f(x, *args)


def brentq(f, double a, double b, tuple args=(),
           double xtol=2e-12, double rtol=_RTOL_MIN,
           Py_ssize_t maxiter=100, bint full_output=False, bint disp=True):
    """Find a root of ``f`` in the bracketing interval ``[a, b]``.

    Parameters
    ----------
    f : callable
        A continuous scalar function. ``f(a)`` and ``f(b)`` must have opposite
        signs (the function must bracket the root).
    a, b : float
        Endpoints of the bracketing interval.
    args : tuple, optional
        Extra positional arguments forwarded to ``f``.
    xtol : float, optional
        Absolute tolerance for the computed root. Must be positive.
    rtol : float, optional
        Relative tolerance for the computed root. Must be at least
        ``4 * eps`` (≈ 8.88e-16).
    maxiter : int, optional
        Maximum number of iterations. Must be at least 1.
    full_output : bool, optional
        When ``True``, return ``(root, RootResults)``; otherwise just ``root``.
    disp : bool, optional
        When ``True``, raise :class:`ConvergenceError` on failure to converge.
        When ``False``, the result is returned with ``converged=False``.

    Returns
    -------
    root : float
        The estimated root.
    info : RootResults, optional
        Convergence diagnostics. Only returned when ``full_output=True``.

    Raises
    ------
    ValueError
        If ``xtol`` is non-positive, ``rtol`` is below the machine-imposed
        minimum, ``maxiter < 1``, or ``f(a)`` and ``f(b)`` have the same sign.
    ConvergenceError
        If ``maxiter`` iterations are exhausted and ``disp=True``.
    """
    if xtol <= 0.0:
        raise ValueError(f"xtol must be positive, got {xtol!r}")
    if rtol < _RTOL_MIN:
        raise ValueError(
            f"rtol must be at least {_RTOL_MIN!r} (4 * machine eps), got {rtol!r}"
        )
    if maxiter < 1:
        raise ValueError(f"maxiter must be >= 1, got {maxiter}")

    cdef:
        bint no_args = (len(args) == 0)
        double xpre = a
        double xcur = b
        double xblk = 0.0
        double fpre, fcur, fblk = 0.0
        double spre = 0.0, scur = 0.0
        double sbis, stry, dpre, dblk, delta
        double tmp
        Py_ssize_t i
        Py_ssize_t funcalls = 0

    fpre = _call(f, xpre, args, no_args)
    funcalls += 1
    if fpre == 0.0:
        return _finalize(xpre, 0, funcalls, True, "converged", full_output)

    fcur = _call(f, xcur, args, no_args)
    funcalls += 1
    if fcur == 0.0:
        return _finalize(xcur, 0, funcalls, True, "converged", full_output)

    if not _opposite_sign(fpre, fcur):
        raise ValueError(
            f"f(a) and f(b) must have opposite signs, got "
            f"f({a!r})={fpre!r}, f({b!r})={fcur!r}"
        )

    for i in range(maxiter):
        # If fpre and fcur straddle zero, the contrapoint moves to xpre.
        if _opposite_sign(fpre, fcur):
            xblk = xpre
            fblk = fpre
            spre = xcur - xpre
            scur = spre

        # Ensure xcur is the better approximation (|fcur| <= |fblk|).
        if fabs(fblk) < fabs(fcur):
            xpre = xcur
            xcur = xblk
            xblk = xpre

            fpre = fcur
            fcur = fblk
            fblk = fpre

        delta = (xtol + rtol * fabs(xcur)) * 0.5
        sbis = (xblk - xcur) * 0.5

        # Convergence test.
        if fcur == 0.0 or fabs(sbis) < delta:
            return _finalize(xcur, i + 1, funcalls, True, "converged", full_output)

        # Decide between an interpolation step or bisection.
        if fabs(spre) > delta and fabs(fcur) < fabs(fpre):
            if xpre == xblk:
                # Secant step.
                stry = -fcur * (xcur - xpre) / (fcur - fpre)
            else:
                # Inverse quadratic interpolation step.
                dpre = (fpre - fcur) / (xpre - xcur)
                dblk = (fblk - fcur) / (xblk - xcur)
                stry = (
                    -fcur * (fblk * dblk - fpre * dpre)
                    / (dblk * dpre * (fblk - fpre))
                )

            # Accept the interpolated step only if it is short enough.
            if 2.0 * fabs(stry) < _dmin(fabs(spre), 3.0 * fabs(sbis) - delta):
                spre = scur
                scur = stry
            else:
                # Step is too aggressive; fall back to bisection.
                spre = sbis
                scur = sbis
        else:
            # Bisection step.
            spre = sbis
            scur = sbis

        xpre = xcur
        fpre = fcur
        if fabs(scur) > delta:
            xcur = xcur + scur
        else:
            xcur = xcur + (delta if sbis > 0.0 else -delta)

        fcur = _call(f, xcur, args, no_args)
        funcalls += 1

    # Iteration budget exhausted.
    if disp:
        raise ConvergenceError(
            f"Failed to converge after {maxiter} iterations; "
            f"current estimate: {xcur!r}"
        )
    return _finalize(xcur, maxiter, funcalls, False, "convergence error", full_output)


cdef _finalize(double root, Py_ssize_t iterations, Py_ssize_t function_calls,
               bint converged, str flag, bint full_output):
    if not full_output:
        return root
    return root, RootResults(root, iterations, function_calls, converged, flag)
