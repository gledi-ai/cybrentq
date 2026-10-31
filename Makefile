.DEFAULT_GOAL := help

.PHONY: help venv lock outdated sync test cov test/cov report cov/report bench smoke build dist clean \
        lint lint/fix lint/check fmt fmt/fix fmt/check typecheck check

BENCH_ARGS ?=

PYTHON_VERSION ?= 3.11
GROUP ?= dev

help:  ## Show this help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_\/-][a-zA-Z0-9_\/ -]*:.*?## / {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

venv:  ## Create the project virtualenv via uv (PYTHON_VERSION=3.11).
	uv venv --seed --link-mode=copy --prompt=cybrentq --python $(PYTHON_VERSION)

lock:  ## Resolve and write uv.lock (WARNING: upgrades all dependencies and rewrites uv.lock).
	uv lock --upgrade --resolution=highest --refresh

outdated:  ## Show outdated direct and transitive dependencies.
	uv tree --locked --outdated

sync:  ## Sync the venv with uv.lock (All groups and extras).
	uv sync --locked --all-extras --all-groups --link-mode=copy --refresh

test:  ## Run the test suite without coverage.
	uv run --locked pytest --verbose

cov test/cov:  ## Recompile extension with line-tracing and run coverage (uses coverage.py, not pytest-cov).
	find src -name '*.c' -delete
	find src -name '*.so' -delete
	CYTHON_TRACE=1 uv sync --locked --all-groups --link-mode=copy --reinstall-package cybrentq
	uv run --locked coverage erase
	uv run --locked coverage run -m pytest --verbose

report cov/report:  ## Print the coverage report from the last test-cov run.
	uv run --locked coverage report

bench:  ## Run the benchmark suite (override args via BENCH_ARGS).
	uv run --locked python benchmarks/bench_brentq.py $(BENCH_ARGS)

smoke:  ## Run the import-and-solve smoke test against the installed package.
	uv run --locked python scripts/smoke.py

lint lint/check:  ## Run ruff linter in check-only mode.
	uv run --locked ruff check .

lint/fix:  ## WARNING: rewrites files on disk. Runs ruff linter with --fix.
	uv run --locked ruff check --fix .

fmt fmt/check:  ## Run ruff formatter in check-only mode.
	uv run --locked ruff format --check .

fmt/fix:  ## WARNING: rewrites files on disk. Runs ruff formatter in place.
	uv run --locked ruff format .

typecheck:  ## Run the pyrefly type checker over the project.
	uv run --locked pyrefly check

check: lint/check fmt/check typecheck  ## Run lint/check, fmt/check and typecheck.

build dist:  ## Build the sdist and wheel into dist/.
	uv build --clear

clean:  ## Remove build artifacts and coverage data.
	rm -rf build dist *.egg-info src/*.egg-info .coverage coverage.xml htmlcov
	find src -name '*.c' -delete
	find src -name '*.so' -delete
	find . -type d -name __pycache__ -exec rm -rf {} +
