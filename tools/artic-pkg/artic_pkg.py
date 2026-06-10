#!/usr/bin/env python3
"""
artic-pkg — Artic Protocol .amod package tool

Build, validate, inspect, and extract .amod module packages per Artic Protocol SPEC Section 10.

Usage:
  artic-pkg build <module-dir>          Build .amod from module directory
  artic-pkg validate <module-dir>       Validate manifest.toml and directory structure
  artic-pkg info <file.amod>            Show info about an existing .amod package
  artic-pkg extract <file.amod> [dir]   Extract an .amod package
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path


# ── Manifest validation ────────────────────────────────────

REQUIRED_MODULE_FIELDS = ["id", "name", "version", "language", "entry", "description"]

REQUIRED_AUTHOR_FIELDS = ["name", "email", "url"]

REQUIRED_DECLARE_FIELDS = {"provides": list}

KNOWN_HANDLERS = ["startup", "shutdown", "on_message", "on_response"]

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

MODULE_ID_RE = re.compile(r"^[a-z][a-z0-9_.-]+$")

LANGUAGES = {"python", "rust", "go", "typescript", "javascript", "ruby", "java", "kotlin", "csharp", "c", "cpp", "zig", "lua", "elixir"}


def validate_manifest(path: Path) -> list[str]:
    """Validate manifest.toml against SPEC section 10 requirements.
    Returns a list of error messages (empty = valid).
    """
    errors: list[str] = []

    if not path.exists():
        return [f"manifest.toml not found at {path}"]

    text = path.read_text(encoding="utf-8")

    # ── Parse TOML manually (avoid toml dependency) ──────
    sections: dict[str, dict[str, object]] = {}
    current_section = ""
    current_keys: dict[str, object] = {}

    for line in text.splitlines():
        line_stripped = line.strip()
        # Skip empty and comments
        if not line_stripped or line_stripped.startswith("#"):
            continue
        # Section header
        sec_match = re.match(r"^\[([a-zA-Z0-9_.]+)\]$", line_stripped)
        if sec_match:
            if current_section:
                sections[current_section] = current_keys
            current_section = sec_match.group(1)
            current_keys = {}
            continue
        # Key = value
        kv_match = re.match(r'^([a-zA-Z0-9_]+)\s*=\s*(.+)$', line_stripped)
        if kv_match and current_section:
            key = kv_match.group(1)
            val = kv_match.group(2)
            # Basic TOML-like parsing
            if val.startswith("[") and val.endswith("]"):
                # Array: ["a", "b", "c"]
                items = re.findall(r'"([^"]*)"', val)
                current_keys[key] = items
            elif val.startswith("{") and val.endswith("}"):
                current_keys[key] = val  # Keep inline table as raw string
            else:
                # String value
                m = re.match(r'^"(.+)"$', val)
                if m:
                    current_keys[key] = m.group(1)
                else:
                    current_keys[key] = val

    if current_section:
        sections[current_section] = current_keys

    # ── Validate [module] section ────────────────────────────
    module_section = sections.get("module", {})
    for field in REQUIRED_MODULE_FIELDS:
        if field not in module_section:
            errors.append(f"[module] missing required field: {field}")

    module_id = module_section.get("id", "")
    if isinstance(module_id, str) and module_id and not MODULE_ID_RE.match(module_id):
        errors.append(f"[module].id '{module_id}' must match {MODULE_ID_RE.pattern}")

    version = module_section.get("version", "")
    if isinstance(version, str) and version and not SEMVER_RE.match(version):
        errors.append(f"[module].version '{version}' must be semver (e.g. 1.0.0)")

    language = module_section.get("language", "")
    if isinstance(language, str) and language and language not in LANGUAGES:
        errors.append(f"[module].language '{language}' not in recognised list: {', '.join(sorted(LANGUAGES))}")

    entry = module_section.get("entry", "")
    if isinstance(entry, str) and entry:
        entry_path = path.parent / entry
        if not entry_path.exists():
            errors.append(f"[module].entry '{entry}' not found at {entry_path}")

    # ── Validate [module.author] section ─────────────────────
    author_section = sections.get("module.author", {})
    if not author_section:
        errors.append("Missing [module.author] section")
    else:
        for field in REQUIRED_AUTHOR_FIELDS:
            if field not in author_section:
                errors.append(f"[module.author] missing required field: {field}")

    # ── Validate [module.declare] section ────────────────────
    declare_section = sections.get("module.declare", {})
    if declare_section:
        for field, expected_type in REQUIRED_DECLARE_FIELDS.items():
            val = declare_section.get(field)
            if val is not None and not isinstance(val, expected_type):
                errors.append(f"[module.declare].{field} should be a list")

        handlers = declare_section.get("handlers", [])
        if isinstance(handlers, list):
            for h in handlers:
                if h not in KNOWN_HANDLERS:
                    errors.append(f"[module.declare].handlers contains unknown handler '{h}' (known: {', '.join(KNOWN_HANDLERS)})")

        requires = declare_section.get("requires", [])
        if not isinstance(requires, list):
            errors.append("[module.declare].requires should be a list")
    # [module.declare] itself is optional (provided=[] if absent)

    # ── Validate [compatibility] section ─────────────────────
    compat_section = sections.get("compatibility", {})
    min_proto = compat_section.get("min_protocol_version", "")
    if isinstance(min_proto, str) and min_proto and not re.match(r"^draft-\d{2}$|^v\d+\.\d+\.\d+$", min_proto):
        errors.append(f"[compatibility].min_protocol_version '{min_proto}' should be 'draft-NN' or 'vMAJOR.MINOR.PATCH'")

    # ── Validate directory structure ─────────────────────────
    mod_dir = path.parent
    has_module_dir = (mod_dir / "module").is_dir()
    if not has_module_dir:
        errors.append("Missing module/ directory (required by SPEC 10.2)")

    return errors


# ── Build ──────────────────────────────────────────────────

def cmd_build(module_dir: str, output: str | None = None) -> None:
    path = Path(module_dir).resolve()
    manifest = path / "manifest.toml"

    print(f"Validating {module_dir}...")
    errors = validate_manifest(manifest)
    if errors:
        print("Validation failed:")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    print("  ✓ manifest.toml valid")

    # Read module name and version for output filename
    text = manifest.read_text(encoding="utf-8")
    mod_id = _parse_field(text, "module", "id", "unknown")
    mod_ver = _parse_field(text, "module", "version", "0.0.0")
    safe_id = mod_id.replace(".", "-")

    if output is None:
        output = f"{safe_id}-v{mod_ver}.amod"

    print(f"Packaging → {output} ...")
    with tarfile.open(output, "w:gz") as tar:
        tar.add(str(path), arcname=path.name)

    size = os.path.getsize(output)
    if size > 50 * 1024 * 1024:
        print(f"  ⚠ Package is {_fmt_size(size)} — exceeds 50MB recommended limit")
    else:
        print(f"  ✓ Package: {_fmt_size(size)}")

    print(f"\n✅ Built: {output}")


# ── Validate ───────────────────────────────────────────────

def cmd_validate(module_dir: str) -> None:
    path = Path(module_dir).resolve()
    manifest = path / "manifest.toml"

    errors = validate_manifest(manifest)
    if errors:
        print(f"❌ Validation failed ({len(errors)} error{'s' if len(errors) > 1 else ''}):\n")
        for e in errors:
            print(f"   ✗ {e}")
        sys.exit(1)
    else:
        print("✅ All checks passed — module is ready for packaging")
        print(f"   Package command: artic-pkg build {module_dir}")


# ── Info ───────────────────────────────────────────────────

def cmd_info(file_path: str) -> None:
    path = Path(file_path).resolve()
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    if not tarfile.is_tarfile(str(path)):
        print(f"Not a valid tar archive: {path}")
        sys.exit(1)

    with tarfile.open(str(path), "r:gz") as tar:
        members = tar.getmembers()

    if not members:
        print("Empty archive")
        return

    top_dir = Path(members[0].path).parts[0]
    total_size = sum(m.size for m in members)

    # Try to read manifest
    manifest_member = None
    for m in members:
        if m.path.endswith("manifest.toml"):
            manifest_member = m
            break

    print(f"Package:   {path.name}")
    print(f"Size:      {_fmt_size(path.stat().st_size)}")
    print(f"Top dir:   {top_dir}")
    print(f"Files:     {len(members)} ({_fmt_size(total_size)} uncompressed)")
    print()

    if manifest_member:
        with tarfile.open(str(path), "r:gz") as tar:
            f = tar.extractfile(manifest_member)
            if f:
                content = f.read().decode("utf-8")
                mod_id = _parse_field(content, "module", "id", "?")
                mod_name = _parse_field(content, "module", "name", "?")
                mod_ver = _parse_field(content, "module", "version", "?")
                mod_lang = _parse_field(content, "module", "language", "?")
                mod_entry = _parse_field(content, "module", "entry", "?")

                print(f"Module ID:  {mod_id}")
                print(f"Name:       {mod_name}")
                print(f"Version:    {mod_ver}")
                print(f"Language:   {mod_lang}")
                print(f"Entry:      {mod_entry}")

                # Declared services
                provides = _parse_list(content, "module.declare", "provides")
                if provides:
                    print(f"Provides:   {', '.join(provides)}")

                requires = _parse_list(content, "module.declare", "requires")
                if requires:
                    print(f"Requires:   {', '.join(requires)}")
    else:
        print("(no manifest.toml found in archive)")


# ── Extract ────────────────────────────────────────────────

def cmd_extract(file_path: str, dest_dir: str | None = None) -> None:
    path = Path(file_path).resolve()
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    if not tarfile.is_tarfile(str(path)):
        print(f"Not a valid tar archive: {path}")
        sys.exit(1)

    if dest_dir:
        dest = Path(dest_dir).resolve()
        dest.mkdir(parents=True, exist_ok=True)
    else:
        dest = Path.cwd()

    with tarfile.open(str(path), "r:gz") as tar:
        tar.extractall(path=str(dest))

    print(f"✅ Extracted {len(tar.getmembers())} files to {dest}")


# ── Helpers ────────────────────────────────────────────────

def _parse_field(text: str, section: str, key: str, default: str = "") -> str:
    """Parse a simple TOML string field from a section."""
    in_section = False
    for line in text.splitlines():
        s = line.strip()
        if re.match(rf"^\[{re.escape(section)}\]$", s):
            in_section = True
            continue
        if in_section:
            if s.startswith("["):
                break
            m = re.match(rf'^{re.escape(key)}\s*=\s*"(.+)"$', s)
            if m:
                return m.group(1)
            # bare value (no quotes)
            m2 = re.match(rf'^{re.escape(key)}\s*=\s*(\S+)$', s)
            if m2:
                return m2.group(1)
    return default


def _parse_list(text: str, section: str, key: str) -> list[str]:
    """Parse a TOML array field from a section."""
    in_section = False
    for line in text.splitlines():
        s = line.strip()
        if re.match(rf"^\[{re.escape(section)}\]$", s):
            in_section = True
            continue
        if in_section:
            if s.startswith("["):
                break
            m = re.match(rf'^{re.escape(key)}\s*=\s*\[(.+)\]$', s)
            if m:
                items = re.findall(r'"([^"]*)"', m.group(1))
                return items
    return []


def _fmt_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


# ── CLI ────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="artic-pkg",
        description="Artic Protocol .amod module package tool",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # build
    p_build = sub.add_parser("build", help="Build .amod from a module directory")
    p_build.add_argument("module_dir", help="Path to the module directory (must contain manifest.toml)")
    p_build.add_argument("-o", "--output", help="Output .amod file path (default: <module-id>-v<version>.amod)")

    # validate
    p_val = sub.add_parser("validate", help="Validate a module directory against SPEC section 10")
    p_val.add_argument("module_dir", help="Path to the module directory")

    # info
    p_info = sub.add_parser("info", help="Show info about an existing .amod package")
    p_info.add_argument("file", help="Path to .amod file")

    # extract
    p_ext = sub.add_parser("extract", help="Extract an .amod package")
    p_ext.add_argument("file", help="Path to .amod file")
    p_ext.add_argument("dest_dir", nargs="?", default=None, help="Destination directory (default: current dir)")

    args = parser.parse_args()

    if args.command == "build":
        cmd_build(args.module_dir, args.output)
    elif args.command == "validate":
        cmd_validate(args.module_dir)
    elif args.command == "info":
        cmd_info(args.file)
    elif args.command == "extract":
        cmd_extract(args.file, args.dest_dir)


if __name__ == "__main__":
    main()
