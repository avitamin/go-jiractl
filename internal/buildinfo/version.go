// Package buildinfo holds release metadata injected at link time.
package buildinfo

// Version is overridden with -ldflags '-X github.com/avitamin/go-jiractl/internal/buildinfo.Version=...'.
var Version = "dev"
