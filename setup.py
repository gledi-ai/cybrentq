import os
import sys

from setuptools import Extension, setup

try:
    from Cython.Build import cythonize
except ImportError as exc:  # pragma: no cover - build-time error
    raise SystemExit("Cython is required to build cybrentq. Install it with `pip install cython`.") from exc


# Reasonable optimisation defaults. We deliberately avoid -ffast-math because
# it relaxes IEEE-754 semantics that root finding relies on.
if sys.platform == "win32":
    extra_compile_args = ["/O2"]
else:
    extra_compile_args = ["-O3", "-fno-strict-aliasing"]

# Coverage-traced build. Set CYTHON_TRACE=1 in the environment to compile
# the extension with line-tracing enabled so coverage.py + the
# Cython.Coverage plugin can collect coverage from the .pyx source.
# Trace builds carry significant runtime overhead, so this is opt-in.
trace_enabled = bool(int(os.environ.get("CYTHON_TRACE", "0") or "0"))

compiler_directives = {
    "boundscheck": False,
    "wraparound": False,
    "cdivision": True,
    "initializedcheck": False,
    "embedsignature": True,
    "linetrace": trace_enabled,
    "binding": trace_enabled,
}

define_macros = [("CYTHON_TRACE_NOGIL", "1")] if trace_enabled else []

extensions = [
    Extension(
        name="cybrentq._brentq",
        sources=["src/cybrentq/_brentq.pyx"],
        extra_compile_args=extra_compile_args,
        define_macros=define_macros,
    )
]

setup(
    ext_modules=cythonize(
        extensions,
        language_level=3,
        compiler_directives=compiler_directives,
        annotate=bool(os.environ.get("CYTHON_ANNOTATE")),
    ),
)
