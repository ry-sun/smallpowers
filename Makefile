PYTHON ?= python3

.PHONY: validate validate-release test

validate:
	$(PYTHON) scripts/validate_repo.py

validate-release:
	$(PYTHON) scripts/validate_repo.py --require-skill

test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests -p 'test_*.py'
