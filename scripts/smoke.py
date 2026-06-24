"""Import-and-solve smoke test shared by CI, cibuildwheel, and `make smoke`."""

from cybrentq import brentq

assert abs(brentq(lambda x: x * x - 2, 0, 2) - 2**0.5) < 1e-10
print("smoke ok")
