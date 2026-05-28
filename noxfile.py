"""Local multi-version test runner.

Run pytest against every supported Python version:

    uvx nox                  # default session, every supported Python
    uvx nox -s tests-3.12    # single version
    uvx nox -- -k brentq     # forward args to pytest
"""

from __future__ import annotations

# We are running nox via `uvx nox`, so we can be sure that the nox package is available in the environment.
import nox  # type: ignore[import]

nox.options.default_venv_backend = "uv"
nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ["tests"]

PYTHON_VERSIONS = ["3.10", "3.11", "3.12", "3.13", "3.14"]


@nox.session(python=PYTHON_VERSIONS)
def tests(session: nox.Session) -> None:
    """Install cybrentq + the test group via `uv sync` and run pytest."""
    session.run_install(
        "uv",
        "sync",
        "--frozen",
        "--group",
        "test",
        env={"UV_PROJECT_ENVIRONMENT": session.virtualenv.location},
        external=True,
    )
    session.run("pytest", *session.posargs)
