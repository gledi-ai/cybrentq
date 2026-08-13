from collections.abc import Callable
from typing import Any, Literal, overload

class RootResults:
    root: float
    iterations: int
    function_calls: int
    converged: bool
    flag: str
    def __init__(
        self,
        root: float,
        iterations: int,
        function_calls: int,
        converged: bool,
        flag: str,
    ) -> None: ...

class ConvergenceError(RuntimeError): ...

@overload
def brentq(
    f: Callable[..., float],
    a: float,
    b: float,
    args: tuple[Any, ...] = ...,
    xtol: float = ...,
    rtol: float = ...,
    maxiter: int = ...,
    full_output: Literal[False] = False,
    disp: bool = ...,
) -> float: ...
@overload
def brentq(
    f: Callable[..., float],
    a: float,
    b: float,
    args: tuple[Any, ...] = ...,
    xtol: float = ...,
    rtol: float = ...,
    maxiter: int = ...,
    *,
    full_output: Literal[True],
    disp: bool = ...,
) -> tuple[float, RootResults]: ...
