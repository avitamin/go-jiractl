package main

import (
	"bytes"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"testing"

	"github.com/avitamin/go-jiractl/internal/testenv"
)

func TestLinkedVersion(t *testing.T) {
	// Build with the original Go environment; isolate only the CLI under test.
	buildEnv := os.Environ()
	dir := testenv.Isolate(t)
	name := "jiractl-test-binary"
	if runtime.GOOS == "windows" {
		name += ".exe"
	}
	binary := filepath.Join(dir, name)
	build := exec.Command("go", "build", "-ldflags", "-X github.com/avitamin/go-jiractl/internal/buildinfo.Version=1.2.3-test", "-o", binary, ".")
	build.Env = buildEnv
	if output, err := build.CombinedOutput(); err != nil {
		t.Fatalf("build: %v\n%s", err, output)
	}
	for _, arg := range []string{"version", "--version"} {
		cmd := exec.Command(binary, arg)
		var stderr bytes.Buffer
		cmd.Stderr = &stderr
		stdout, err := cmd.Output()
		if err != nil {
			t.Fatalf("%s: %v: %s", arg, err, stderr.String())
		}
		if string(stdout) != "jiractl 1.2.3-test\n" || stderr.Len() != 0 {
			t.Fatalf("stdout=%q stderr=%q", stdout, stderr.String())
		}
	}
}
