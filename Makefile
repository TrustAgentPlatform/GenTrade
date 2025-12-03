
CURRENT_DIR := $(shell pwd)

PYTHON_VERSION := "3.11"
PYTHON_VERSION_OK := $(shell python -c "import sys; print(sys.version_info >= (3,11) and sys.version_info < (3,12))")

# Pylint configuration
PYLINT_ARGS = --rcfile=.pylintrc
PYLINT_VERSION = 4.0.4
PYLINT_INSTALLED := $(shell python -c "import pkg_resources; print('pylint' in {pkg.key for pkg in pkg_resources.working_set})" 2>/dev/null || echo "False")
PYLINT_VERSION_OK := $(shell python -c "import pylint; print(pylint.__version__ == '$(PYLINT_VERSION)')" 2>/dev/null || echo "False")

# Default target
all: lint

ensure-pylint:
	@if [ "$(PYLINT_INSTALLED)" = "False" ] || [ "$(PYLINT_VERSION_OK)" = "False" ]; then \
		echo "Installing/upgrading pylint to version $(PYLINT_VERSION)..."; \
		pip install pylint=="$(PYLINT_VERSION)"; \
	else \
		echo "✅ pylint $(PYLINT_VERSION) is already installed"; \
	fi

# Lint all Python files
lint: check-python ensure-pylint
	@echo "Running Pylint ..."
	@export PYTHONPATH=$(CURRENT_DIR)/src
	find . -type f -name "*.py" | xargs pylint $(PYLINT_ARGS)

# Lint specific file(s)
lint-file:
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make lint-file FILE=path/to/file.py"; \
		exit 1; \
	fi
	pip install pylint=="$(PYLINT_VERSION)"
	pylint $(PYLINT_ARGS) $(FILE)

# Check python version
check-python:
	@echo "Checking Python version..."
	@if [ "$(PYTHON_VERSION_OK)" = "True" ]; then \
		echo "✅ Python version is $(PYTHON_VERSION) (compatible)"; \
	else \
		echo "❌ Error: Python $(PYTHON_VERSION) is required (found $(shell python --version | cut -d' ' -f2))"; \
		exit 1; \
	fi

# Clean up
clean:
	@echo "Cleaning in: $(CURRENT_DIR)..."
	find $(CURRENT_DIR) -type d -name "__pycache__" -exec rm -rf {} +
	find $(CURRENT_DIR) -type f -name "*.pyc" -delete
	find $(CURRENT_DIR) -type f -name ".pylint-cache" -exec rm -rf {} +

.PHONY: all lint lint-file clean check-python ensure-pylint
