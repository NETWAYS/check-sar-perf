PHONY: lint test coverage

lint:
	python -m pylint check_sar_perf.py
test:
	python -m unittest discover -v
coverage:
	python -m coverage run -m unittest discover
	python -m coverage report -m --include check_sar_perf.py
