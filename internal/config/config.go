// Package config loads the explicitly selected or platform configuration file.
package config

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/pelletier/go-toml/v2"
	"github.com/spf13/viper"
)

// New returns an isolated configuration registry. It never reads credentials.
func New() *viper.Viper {
	v := viper.New()
	v.SetDefault("profile", "default")
	v.SetEnvPrefix("JIRACTL")
	v.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))
	v.AutomaticEnv()
	return v
}

// Load reads only TOML. A missing platform default is allowed; an explicitly
// selected file must exist. Neither environment nor cwd selects the path.
func Load(v *viper.Viper, path string) error {
	explicit := path != ""
	if !explicit {
		dir, err := os.UserConfigDir()
		if err != nil {
			return fmt.Errorf("locate config directory: %w", err)
		}
		path = filepath.Join(dir, "jiractl", "config.toml")
	}
	f, err := os.Open(path)
	if err != nil {
		if !explicit && errors.Is(err, os.ErrNotExist) {
			return nil
		}
		return fmt.Errorf("open config: %w", err)
	}
	defer f.Close()
	var values map[string]any
	if err := toml.NewDecoder(f).Decode(&values); err != nil {
		// Parser diagnostics can include configuration values. Do not echo them.
		return errors.New("invalid TOML configuration")
	}
	if containsCredential(values) {
		return errors.New("inline credentials are not supported in configuration")
	}
	return v.MergeConfigMap(values)
}

// Reject literal credential fields at any depth. A future pat_env field names
// an environment variable, not its value, and is deliberately allowed.
func containsCredential(value any) bool {
	switch value := value.(type) {
	case map[string]any:
		for key, item := range value {
			key = strings.ToLower(strings.ReplaceAll(key, "-", "_"))
			if strings.HasSuffix(key, "_pat") || strings.HasSuffix(key, "_token") || strings.HasSuffix(key, "_secret") {
				return true
			}
			switch key {
			case "pat", "token", "secret", "api_key", "password", "authorization":
				return true
			}
			if containsCredential(item) {
				return true
			}
		}
	case []any:
		for _, item := range value {
			if containsCredential(item) {
				return true
			}
		}
	}
	return false
}
