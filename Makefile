# riscv-xray Makefile

PYTHON   ?= python3
PIP      ?= pip3
PYTEST   ?= pytest

.PHONY: plugin install setup test clean check all

all: setup

## Build the QEMU TCG plugin (.so)
plugin:
	$(MAKE) -C plugin

## Install the Python package in editable mode
install:
	$(PIP) install -e .

## Full setup: build plugin + install package
setup: plugin install
	@echo ""
	@echo "riscv-xray is ready. Run: riscv-xray check"

## Run tests
test:
	$(PYTEST) tests/ -v

## Verify dependencies
check:
	riscv-xray check

## Clean build artifacts
clean:
	rm -f plugin/xray_plugin.so
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .pytest_cache/
