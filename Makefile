# Makefile

pypi:
	rm -rf dist/ build/ py_scrapi.egg-info/
	python3 -m build
	python3 -m twine upload dist/*

wheel:
	pip wheel . -w dist

format:
	black py_scrapi --line-length 79

lint:
	cd py_scrapi && python -m pylint py_scrapi
