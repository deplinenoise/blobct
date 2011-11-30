
.PHONY: test

test:
	python -m unittest discover

testcov:
	rm -rf .coverage htmlcov
	coverage run run_all_tests.py
	coverage html
