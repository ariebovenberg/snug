.PHONY: docs test

init:
	pip install -r requirements.txt

docs:
	make -C docs/ html

test:
	detox

test-examples:
	pytest examples/

coverage:
	pytest --cov=snug --cov-report html --cov-report term --cov-branch --cov-fail-under 100

publish: clean
	rm -rf build dist .egg snug.egg-info
	python setup.py sdist bdist_wheel
	twine upload dist/*

clean:
	find . | grep -E "(__pycache__|\.pyc|\.pyo$$)" | xargs rm -rf
	python setup.py clean --all
