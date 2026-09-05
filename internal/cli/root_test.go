package cli

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/avitamin/go-jiractl/internal/testenv"
)

func TestVersionForms(t *testing.T) {
	testenv.Isolate(t)
	for _, args := range [][]string{{"version"}, {"--version"}} {
		var stdout, stderr bytes.Buffer
		if code := Execute(args, &stdout, &stderr); code != 0 {
			t.Fatalf("exit %d: %s", code, stderr.String())
		}
		if got, want := stdout.String(), "jiractl dev\n"; got != want {
			t.Fatalf("stdout = %q, want %q", got, want)
		}
		if stderr.Len() != 0 {
			t.Fatalf("stderr = %q", stderr.String())
		}
	}
}

func TestErrorsOnlyOnStderr(t *testing.T) {
	dir := testenv.Isolate(t)
	bad := filepath.Join(dir, "bad.toml")
	if err := os.WriteFile(bad, []byte("profile = 'SYNTHETIC_SECRET_CANARY"), 0600); err != nil {
		t.Fatal(err)
	}
	for _, args := range [][]string{{"unknown"}, {"--pat", "SYNTHETIC_SECRET_CANARY"}, {"version", "extra"}, {"--config", filepath.Join(dir, "missing"), "version"}, {"--config", bad, "version"}, {"--config", bad, "--version"}, {"--config=", "version"}} {
		var stdout, stderr bytes.Buffer
		if code := Execute(args, &stdout, &stderr); code != 1 {
			t.Fatalf("%v exit = %d", args, code)
		}
		if stdout.Len() != 0 || stderr.Len() == 0 {
			t.Fatalf("stdout %q stderr %q", stdout.String(), stderr.String())
		}
		if strings.Contains(stderr.String(), "SYNTHETIC_SECRET_CANARY") {
			t.Fatal("configuration value leaked")
		}
	}
}

func TestIndependentRootsAndExplicitConfig(t *testing.T) {
	dir := testenv.Isolate(t)
	path := filepath.Join(dir, "first.toml")
	if err := os.WriteFile(path, []byte("profile = 'corp'\n"), 0600); err != nil {
		t.Fatal(err)
	}
	var first, second, stderr bytes.Buffer
	a, b := NewRoot(&first, &stderr), NewRoot(&second, &stderr)
	a.SetArgs([]string{"--config", path, "--profile", "corp", "version"})
	b.SetArgs([]string{"version"})
	if err := a.Execute(); err != nil {
		t.Fatal(err)
	}
	if b.PersistentFlags().Changed("config") || b.PersistentFlags().Changed("profile") {
		t.Fatal("flags leaked between roots")
	}
	t.Setenv("JIRACTL_CONFIG", filepath.Join(dir, "missing"))
	if err := b.Execute(); err != nil {
		t.Fatalf("JIRACTL_CONFIG must not select a file: %v", err)
	}
	if first.String() != "jiractl dev\n" || second.String() != "jiractl dev\n" {
		t.Fatalf("independent roots: first %q, second %q", first.String(), second.String())
	}
}
