PYTHON ?= python

.PHONY: test-backend

test-backend:
	"$(PYTHON)" -m pytest -q
