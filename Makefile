GO ?= go
VERSION ?= dev

.PHONY: build test check hooks-test

hooks-test:
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s scripts -p 'test_*hook.py' -v

build:
	$(GO) build -ldflags '-X github.com/avitamin/go-jiractl/internal/buildinfo.Version=$(VERSION)' -o build/jiractl ./cmd/jiractl

test:
	$(GO) test ./...

check:
	$(MAKE) hooks-test
	@files="$$("$$($(GO) env GOROOT)/bin/gofmt" -l cmd internal)" && test -z "$$files" || { echo 'Run go fmt ./...'; exit 1; }
	$(GO) vet ./...
	$(GO) test ./...
	$(GO) test -race ./...
	$(GO) mod tidy -diff
	$(MAKE) build
