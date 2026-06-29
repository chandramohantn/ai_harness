BOOTSTRAP_PYTHON ?= python3
VENV_DIR := .venv
PYTHON := $(VENV_DIR)/bin/python
PACKAGE := src
PYTEST := $(PYTHON) -m pytest
PYTEST_ARGS := tests
PIP := $(PYTHON) -m pip

.PHONY: help all build install-dev compile test coverage run clean

help:
	@printf "%s\n" \
		"Available targets:" \
		"  make install-dev          Create .venv and install test dependencies" \
		"  make compile              Compile Python sources under $(PACKAGE)" \
		"  make build                Alias for compile" \
		"  make test                 Run pytest with terminal coverage report" \
		"  make coverage             Run pytest and generate terminal/html/xml coverage reports" \
		"  make run                  Run the default package demo" \
		"  make run TASK_FILE=path   Run a task payload from a JSON file" \
		"  make clean                Remove Python cache artifacts" \
		"  make all                  Compile and test"

all: compile test

build: compile

$(PYTHON):
	$(BOOTSTRAP_PYTHON) -m venv $(VENV_DIR)

$(VENV_DIR)/.deps-installed: $(PYTHON) requirements-dev.txt
	$(PIP) install -r requirements-dev.txt
	touch $(VENV_DIR)/.deps-installed

install-dev: $(VENV_DIR)/.deps-installed

compile: $(PYTHON)
	$(PYTHON) -m compileall $(PACKAGE)

test: $(VENV_DIR)/.deps-installed
	$(PYTEST) $(PYTEST_ARGS) --cov=$(PACKAGE) --cov-report=term-missing

coverage: $(VENV_DIR)/.deps-installed
	$(PYTEST) $(PYTEST_ARGS) --cov=$(PACKAGE) --cov-report=term-missing --cov-report=html:coverage_html --cov-report=xml:coverage.xml

run: $(PYTHON)
	@if [ -n "$(TASK_FILE)" ]; then \
		$(PYTHON) -m $(PACKAGE) "$(TASK_FILE)"; \
	else \
		$(PYTHON) -m $(PACKAGE); \
	fi

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage coverage_html coverage.xml .pytest_cache
