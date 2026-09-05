package config

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"

	"github.com/avitamin/go-jiractl/internal/testenv"
	"github.com/spf13/pflag"
)

func writeConfig(t *testing.T, path, content string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0600); err != nil {
		t.Fatal(err)
	}
}

func TestConfigSources(t *testing.T) {
	for _, tc := range []struct {
		name, content              string
		explicit, missing, wantErr bool
	}{
		{name: "missing default", missing: true},
		{name: "platform TOML", content: "profile = 'corp'\n"},
		{name: "explicit TOML", explicit: true, content: "profile = 'corp'\n"},
		{name: "missing explicit", explicit: true, missing: true, wantErr: true},
		{name: "malformed default", content: "profile = [", wantErr: true},
		{name: "malformed explicit", explicit: true, content: "profile = [", wantErr: true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			dir := testenv.Isolate(t)
			platformDir, err := os.UserConfigDir()
			if err != nil {
				t.Fatal(err)
			}
			path := filepath.Join(platformDir, "jiractl", "config.toml")
			explicitPath := ""
			v := New()
			if tc.explicit {
				path = filepath.Join(dir, "explicit.conf")
				explicitPath = path
			}
			if !tc.missing {
				writeConfig(t, path, tc.content)
			}
			err = Load(v, explicitPath)
			if (err != nil) != tc.wantErr {
				t.Fatalf("Load() = %v, want error %v", err, tc.wantErr)
			}
			if tc.wantErr {
				return
			}
			want := "corp"
			if tc.missing {
				want = "default"
			}
			if got := v.GetString("profile"); got != want {
				t.Fatalf("profile = %q, want %q", got, want)
			}
		})
	}
}

func TestPrecedenceAndNestedEnvironment(t *testing.T) {
	dir := testenv.Isolate(t)
	path := filepath.Join(dir, "config.toml")
	writeConfig(t, path, "profile = 'file'\n[profiles.default]\nbase_url = 'https://file.invalid'\n")
	v := New()
	flags := pflag.NewFlagSet("test", pflag.ContinueOnError)
	flags.String("profile", "default", "")
	if err := v.BindPFlags(flags); err != nil {
		t.Fatal(err)
	}
	t.Setenv("JIRACTL_CONFIG", filepath.Join(dir, "ignored.toml"))
	if err := Load(v, path); err != nil {
		t.Fatal(err)
	}
	if got := v.GetString("profile"); got != "file" {
		t.Fatalf("file precedence: %q", got)
	}
	t.Setenv("JIRACTL_PROFILE", "env")
	t.Setenv("JIRACTL_PROFILES_DEFAULT_BASE_URL", "https://env.invalid")
	if got := v.GetString("profile"); got != "env" {
		t.Fatalf("env precedence: %q", got)
	}
	if got := v.GetString("profiles.default.base_url"); got != "https://env.invalid" {
		t.Fatalf("nested env: %q", got)
	}
	if err := flags.Set("profile", "flag"); err != nil {
		t.Fatal(err)
	}
	if got := v.GetString("profile"); got != "flag" {
		t.Fatalf("flag precedence: %q", got)
	}
	other := filepath.Join(dir, "other.toml")
	writeConfig(t, other, "profile = 'other'\nsource = 'explicit'\n")
	if err := Load(v, other); err != nil {
		t.Fatal(err)
	}
	if got := v.GetString("profile"); got != "flag" {
		t.Fatalf("flag lost on load: %q", got)
	}
	if got := v.GetString("source"); got != "explicit" {
		t.Fatalf("--config did not override JIRACTL_CONFIG: %q", got)
	}
	if got := v.Get("profiles.default.base_url"); got != "https://env.invalid" {
		t.Fatalf("nested env lost: %v", got)
	}
}

func TestInstancesAreIndependent(t *testing.T) {
	dir := testenv.Isolate(t)
	v1, v2 := New(), New()
	path := filepath.Join(dir, "first.toml")
	writeConfig(t, path, "profile = 'first'\n")
	if err := Load(v1, path); err != nil {
		t.Fatal(err)
	}
	if err := Load(v2, ""); err != nil {
		t.Fatal(err)
	}
	if v1.GetString("profile") != "first" || v2.GetString("profile") != "default" {
		t.Fatal("configuration leaked between instances")
	}
}

func TestRejectInlineCredentials(t *testing.T) {
	dir := testenv.Isolate(t)
	for _, content := range []string{
		"pat = 'SYNTHETIC_CANARY'",
		"[profiles.default]\njira_pat = 'SYNTHETIC_CANARY'",
		"[profiles.default]\nbearer_token = 'SYNTHETIC_CANARY'",
		"[profiles.default]\npersonal_access_token = 'SYNTHETIC_CANARY'",
		"[[profiles.default.providers]]\nAuthorization = 'SYNTHETIC_CANARY'",
	} {
		path := filepath.Join(dir, "credential.toml")
		writeConfig(t, path, content)
		v := New()
		if err := Load(v, path); err == nil || err.Error() != "inline credentials are not supported in configuration" {
			t.Fatalf("expected safe credential rejection, got %v", err)
		}
		if len(v.AllSettings()) != 1 {
			t.Fatal("rejected config was stored in registry")
		}
	}
}

func TestNoWorkingDirectoryOrDotenvDiscovery(t *testing.T) {
	dir := testenv.Isolate(t)
	writeConfig(t, filepath.Join(dir, "config.toml"), "profile = 'cwd'\n")
	writeConfig(t, filepath.Join(dir, ".env"), "JIRACTL_PROFILE=dotenv\n")
	t.Chdir(dir)
	t.Setenv("JIRACTL_CONFIG", filepath.Join(dir, "config.toml"))
	v := New()
	if err := Load(v, ""); err != nil {
		t.Fatal(err)
	}
	if got := v.GetString("profile"); got != "default" {
		t.Fatalf("unexpected discovery: %q", got)
	}
}

func TestUserConfigDirFailure(t *testing.T) {
	if runtime.GOOS != "linux" {
		t.Skip("Linux directory discovery")
	}
	testenv.Isolate(t)
	t.Setenv("XDG_CONFIG_HOME", "")
	t.Setenv("HOME", "")
	if err := Load(New(), ""); err == nil {
		t.Fatal("expected directory discovery error")
	}
}
