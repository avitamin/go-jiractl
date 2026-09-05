// Package testenv provides shared environment isolation for repository tests.
package testenv

import (
	"os"
	"testing"
)

// Isolate redirects platform configuration directories and clears CLI overrides.
// Environment changes are restored by testing; the unique directory is retained
// for inspection per repository deletion policy. Do not use in parallel tests.
func Isolate(t testing.TB) string {
	t.Helper()
	dir, err := os.MkdirTemp("", "jiractl-test-")
	if err != nil {
		t.Fatal(err)
	}
	t.Setenv("XDG_CONFIG_HOME", dir)
	t.Setenv("HOME", dir)
	t.Setenv("AppData", dir)
	t.Setenv("JIRACTL_CONFIG", "")
	t.Setenv("JIRACTL_PROFILE", "")
	return dir
}
