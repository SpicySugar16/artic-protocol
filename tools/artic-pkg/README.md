# artic-pkg — Artic Protocol .amod Packaging Tool

A CLI tool for building, validating, inspecting, and extracting `.amod` module packages per [Artic Protocol SPEC Section 10](SPEC.md#10-模块打包格式module-package-format).

## Quick Start

```bash
# Validate a module directory
./tools/artic-pkg/artic-pkg validate examples/packaging/emotion-detect-v1.0.0/

# Build an .amod package
./tools/artic-pkg/artic-pkg build examples/packaging/emotion-detect-v1.0.0/
# → emotion-detect-v1.0.0.amod

# Inspect a built package
./tools/artic-pkg/artic-pkg info emotion-detect-v1.0.0.amod

# Extract a package
./tools/artic-pkg/artic-pkg extract emotion-detect-v1.0.0.amod ./extracted/
```

## Commands

| Command | Description |
|---------|-------------|
| `build <dir>` | Validate + build `.amod` package from module directory |
| `validate <dir>` | Check `manifest.toml` and directory structure against SPEC |
| `info <file.amod>` | Show package metadata (module ID, version, services, etc.) |
| `extract <file.amod> [dir]` | Extract package to directory |

## Validation Checks

The `validate` (and `build`) command checks:

- All required `[module]` fields present (`id`, `name`, `version`, `language`, `entry`, `description`)
- Module ID matches `^[a-z][a-z0-9_.-]+$`
- Version is valid SemVer
- Language is in the recognised list
- Entry file exists
- `[module.author]` has all required fields
- `[module.declare]` handler names match known events
- `module/` directory exists
- `min_protocol_version` is a valid format

## Install

No installation required — the tool runs with Python 3 stdlib (no dependencies).

For system-wide use, symlink or copy:

```bash
sudo cp tools/artic-pkg/artic-pkg /usr/local/bin/
```
