.PHONY: docs test

docs:
	make -C docs/ html

test:
	pytest

coverage:
	pytest --cov=snug --cov-report html --cov-report term
