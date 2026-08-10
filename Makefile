.PHONY: check lint test eval seed dev

check:
	py -3.13 scripts/bootstrap/validate_constitution.py

lint: check

test:
	py -3.13 -m unittest discover -s tests -p "test_*.py"

eval:
	py -3.13 scripts/eval/run_eval_smoke.py

seed:
	py -3.13 scripts/bootstrap/seed_placeholder.py

dev:
	docker compose up

