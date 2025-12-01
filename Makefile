# Makefile for Pylint with suggestion-mode support

# Default target
all: lint

# Pylint configuration
PYLINT = pylint
PYLINT_ARGS = --rcfile=.pylintrc
PYLINT_VERSION = pylint==4.0.4


# Lint all Python files with suggestion-mode support
lint:
	pip install $(PYLINT_VERSION)
	@echo "Running Pylint with suggestion-mode support..."
	find . -type f -name "*.py" | xargs $(PYLINT) $(PYLINT_ARGS)

# Lint specific file(s)
lint-file:
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make lint-file FILE=path/to/file.py"; \
		exit 1; \
	fi
	pip install $(PYLINT_VERSION)
	$(PYLINT) $(PYLINT_ARGS) $(FILE)


# Clean up (optional)
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

.PHONY: all lint lint-file clean
