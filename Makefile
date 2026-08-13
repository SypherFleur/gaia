.PHONY: check lint test eval gaia seed dev

check:
	py -3.13 scripts/bootstrap/validate_constitution.py

lint: check

test:
	py -3.13 -m unittest discover -s tests -p "test_*.py"

eval:
	py -3.13 scripts/eval/run_eval_smoke.py

gaia:
	py -3.13 -m apps.cli.gaia

seed:
	py -3.13 scripts/bootstrap/seed_placeholder.py

dev:
	docker compose up
