.PHONY: docs test

docs:
	make -C docs/ html

test:
	pytest

coverage:
	pytest --cov=snug --cov-report html --cov-report term

publish:
	python setup.py sdist bdist_wheel
	twine upload dist/*
	rm -fr build dist .egg snug.egg-info
