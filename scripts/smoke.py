"""Import-and-solve smoke test shared by CI, cibuildwheel, and `make smoke`."""

from cybrentq import brentq


def _f(x: float) -> float:
    return x * x - 2.0


assert abs(brentq(_f, 0, 2) - 2**0.5) < 1e-10
print("smoke ok")
