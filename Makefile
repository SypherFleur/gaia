.PHONY: check lint test eval gaia seed dev

# Override with `make PYTHON=py\ -3.13 test` on Windows, or set GAIA_PYTHON.
PYTHON ?= $(if $(GAIA_PYTHON),$(GAIA_PYTHON),python3)

check:
	$(PYTHON) scripts/bootstrap/validate_constitution.py

lint: check

test:
	$(PYTHON) -m unittest discover -s tests -p "test_*.py"

eval:
	$(PYTHON) scripts/eval/run_eval_smoke.py

gaia:
	$(PYTHON) -m apps.cli.gaia

seed:
	$(PYTHON) -m apps.cli.gaia seed demo

dev:
	$(PYTHON) -m apps.cli.gaia dev
