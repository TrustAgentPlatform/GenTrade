
CURRENT_DIR := $(shell pwd)

# Pylint configuration
PYLINT_ARGS = --rcfile=.pylintrc
PYLINT_VERSION = pylint==4.0.4

REQUIRED_PYTHON_VERSION := "3.11"
PYTHON_VERSION_OK := $(shell python -c "import sys; print(sys.version_info >= (3,11) and sys.version_info < (3,12))")

# Default target
all: lint

# Lint all Python files
lint:
	pip install $(PYLINT_VERSION)
	@echo "Running Pylint ..."
	find . -type f -name "*.py" | xargs pylint $(PYLINT_ARGS)

# Lint specific file(s)
lint-file:
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make lint-file FILE=path/to/file.py"; \
		exit 1; \
	fi
	pip install $(PYLINT_VERSION)
	pylint $(PYLINT_ARGS) $(FILE)

# Check python version
check-python:
	@echo "Checking Python version..."
	@if [ "$(PYTHON_VERSION_OK)" = "True" ]; then \
		echo "✅ Python version is $(REQUIRED_PYTHON_VERSION) (compatible)"; \
	else \
		echo "❌ Error: Python $(REQUIRED_PYTHON_VERSION) is required (found $(shell python --version | cut -d' ' -f2))"; \
		exit 1; \
	fi

# Clean up
clean:
	@echo "Cleaning in: $(CURRENT_DIR)..."
	find $(CURRENT_DIR) -type d -name "__pycache__" -exec rm -rf {} +
	find $(CURRENT_DIR) -type f -name "*.pyc" -delete
	find $(CURRENT_DIR) -type f -name ".pylint-cache" -exec rm -rf {} +

.PHONY: all lint lint-file clean check-python
