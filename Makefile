.PHONY: test build publish clean

init:
	poetry install

test:
	tox --parallel auto

test-examples:
	pytest examples/

coverage:
	pytest --live --cov=snug --cov-report html --cov-report term

clean:
	find . | grep -E "(__pycache__|\.pyc|\.pyo$$)" | xargs rm -rf

format:
	black src tests
	isort src tests
