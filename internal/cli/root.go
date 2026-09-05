// Package cli defines the bootstrap command line.
package cli

import (
	"fmt"
	"io"

	"github.com/avitamin/go-jiractl/internal/buildinfo"
	"github.com/avitamin/go-jiractl/internal/config"
	"github.com/spf13/cobra"
)

// NewRoot creates a command tree and configuration registry for one invocation.
func NewRoot(stdout, stderr io.Writer) *cobra.Command {
	v := config.New()
	root := &cobra.Command{
		Use:           "jiractl",
		Short:         "Jira CLI bootstrap",
		SilenceErrors: true,
		SilenceUsage:  true,
		Args:          cobra.NoArgs,
	}
	root.SetOut(stdout)
	root.SetErr(stderr)
	root.CompletionOptions.DisableDefaultCmd = true
	root.PersistentFlags().String("config", "", "TOML configuration path")
	root.PersistentFlags().String("profile", "default", "Configuration profile")
	root.Flags().Bool("version", false, "Print version")
	// Flag existence is controlled here; retain errors to avoid hidden failures
	// if registration changes later.
	bindErr := v.BindPFlag("profile", root.PersistentFlags().Lookup("profile"))
	root.PersistentPreRunE = func(cmd *cobra.Command, args []string) error {
		if bindErr != nil {
			return bindErr
		}
		path, err := cmd.Flags().GetString("config")
		if err != nil {
			return err
		}
		if cmd.Flags().Changed("config") && path == "" {
			return fmt.Errorf("--config requires a non-empty path")
		}
		return config.Load(v, path)
	}
	printVersion := func(cmd *cobra.Command, args []string) error {
		_, err := fmt.Fprintf(cmd.OutOrStdout(), "jiractl %s\n", buildinfo.Version)
		return err
	}
	root.RunE = func(cmd *cobra.Command, args []string) error {
		version, err := cmd.Flags().GetBool("version")
		if err != nil {
			return err
		}
		if version {
			return printVersion(cmd, args)
		}
		return cmd.Help()
	}
	root.AddCommand(&cobra.Command{
		Use: "version", Short: "Print version", Args: cobra.NoArgs, RunE: printVersion,
	})
	return root
}

// Execute reports each error once on stderr and returns a process exit code.
func Execute(args []string, stdout, stderr io.Writer) int {
	root := NewRoot(stdout, stderr)
	root.SetArgs(args)
	if err := root.Execute(); err != nil {
		fmt.Fprintln(stderr, "Error:", err)
		return 1
	}
	return 0
}
