.PHONY: lint test test-cov build-binary brew-bump

lint:
	ruff check src tests
	python -m mypy src

test:
	python -m pytest

test-cov:
	python -m pytest --cov=s3peek --cov-report=term-missing --cov-report=html

build-binary:
	pip install pyinstaller
	pyinstaller --onefile --name s3peek src/s3peek/cli.py

brew-bump:
	@echo "Update Formula/s3peek.rb with new version and SHA256"
