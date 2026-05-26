"""Manual MYH source-check script for scheduler-ready validation.

Run from the part_3 folder:

    python backend/scripts/check_source_status.py

The script does not download source files and does not refresh PostgreSQL. It
only checks the configured MYH source location, prints a readable summary, and
writes the local runtime/source_status.json manifest by default.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from backend.app.services.source_check import SourceCheckConfig, build_config_from_env, run_source_check


def parse_args() -> argparse.Namespace:
    """Read command-line arguments for the manual source-check script."""
    parser = argparse.ArgumentParser(description="Check the configured MYH result source page.")
    parser.add_argument("--source-url", help="Override MYH_SOURCE_URL for this check.")
    parser.add_argument(
        "--configured-file",
        action="append",
        default=None,
        help="Known source file name or URL to include when automatic discovery is not enough. Can be used multiple times.",
    )
    parser.add_argument("--manifest-path", type=Path, help="Where to write/read the local source-status JSON manifest.")
    parser.add_argument("--local-csv-path", type=Path, help="Optional curated CSV path used to compare local source_year coverage.")
    parser.add_argument("--timeout-seconds", type=int, help="HTTP timeout for the source-page check.")
    parser.add_argument("--no-write-manifest", action="store_true", help="Print the check result without writing the JSON manifest.")
    return parser.parse_args()


def build_config_from_args(args: argparse.Namespace) -> SourceCheckConfig:
    """Apply command-line overrides on top of environment defaults."""
    env_config = build_config_from_env()
    return SourceCheckConfig(
        source_url=args.source_url or env_config.source_url,
        configured_files=tuple(args.configured_file) if args.configured_file else env_config.configured_files,
        manifest_path=args.manifest_path or env_config.manifest_path,
        local_csv_path=args.local_csv_path or env_config.local_csv_path,
        timeout_seconds=args.timeout_seconds or env_config.timeout_seconds,
    )


def format_status_summary(result: dict[str, Any], manifest_path: Path | None = None) -> str:
    """Format a source-check result for human-readable terminal output."""
    lines = [
        "MYH source check summary",
        "=" * 24,
        f"Status: {result.get('status')}",
        f"Checked at: {result.get('checked_at')}",
        f"Source URL: {result.get('source_url')}",
        f"HTTP status: {result.get('http_status')}",
        f"Latest visible source year: {result.get('known_latest_source_snapshot')}",
        f"Local latest source_year: {result.get('local_latest_source_year')}",
        f"Up to date: {result.get('up_to_date')}",
        f"Discovered file candidates: {len(result.get('discovered_files', []))}",
        f"Configured file candidates: {len(result.get('configured_files', []))}",
        f"Message: {result.get('message')}",
    ]
    if result.get("error"):
        lines.append(f"Error: {result.get('error')}")
    if manifest_path is not None:
        lines.append(f"Manifest: {manifest_path}")
    return "\n".join(lines)


def main() -> None:
    """Run one source check and print a readable result."""
    args = parse_args()
    config = build_config_from_args(args)
    result = run_source_check(config, write_manifest=not args.no_write_manifest)
    manifest_path = None if args.no_write_manifest else config.manifest_path
    print(format_status_summary(result, manifest_path))


if __name__ == "__main__":
    main()
