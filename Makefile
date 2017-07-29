.PHONY: docs test

init:
	pip install -r requirements/dev.txt

docs:
	make -C docs/ html

test:
	pytest

coverage:
	pytest --cov=snug --cov-report html --cov-report term --cov-branch

publish:
	rm -fr build dist .egg snug.egg-info
	python setup.py sdist bdist_wheel
	twine upload dist/*
