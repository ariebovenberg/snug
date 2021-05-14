.PHONY: docs test build publish clean

init:
	poetry install

docs:
	@touch docs/api.rst  # ensure api docs always rebuilt
	make -C docs/ html

test:
	tox --parallel auto

test-examples:
	pytest examples/

coverage:
	pytest --live --cov=snug --cov-report html --cov-report term

clean:
	make -C docs/ clean
	find . | grep -E "(__pycache__|\.pyc|\.pyo$$)" | xargs rm -rf

format:
	black src tests
	isort src tests
