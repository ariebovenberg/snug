.PHONY: docs test

docs:
	make -C docs/ html

test:
	pytest

coverage:
	pytest --cov=omgorm
