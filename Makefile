.PHONY: docs test

docs:
	make -C docs/ html

test:
	pytest

coverage:
	pytest --cov=snug --cov-report html --cov-report term

publish:
	rm -fr build dist .egg snug.egg-info
	python setup.py sdist bdist_wheel
	twine upload dist/*
