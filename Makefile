.PHONY: lint test coverage

lint:
	python -m pylint check_sar_perf.py
test:
	python -m unittest test_check_sar_perf.py
coverage:
	python -m coverage run -m unittest test_check_sar_perf.py
	python -m coverage report -m --include check_sar_perf.py
