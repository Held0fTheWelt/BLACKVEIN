#!/usr/bin/env python3
"""Standalone script for decrypting encrypted export files.

This script allows decrypting exported data offline without requiring
API access. It reads an encrypted JSON file and a password, then outputs
the decrypted data.

Usage:
    python decrypt_export.py <encrypted_file> <password>
    python decrypt_export.py export_encrypted.json mypassword

Output:
    Decrypted JSON is written to stdout (or optionally to a file)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add backend app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services import encryption_service


def main():
    parser = argparse.ArgumentParser(
        description="Decrypt an encrypted export file with AES-256-CBC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Decrypt to stdout
  python decrypt_export.py export_encrypted.json mypassword

  # Decrypt to output file
  python decrypt_export.py export_encrypted.json mypassword -o decrypted.json

  # Pretty-print the decrypted output
  python decrypt_export.py export_encrypted.json mypassword -p
        """,
    )

    parser.add_argument(
        "encrypted_file",
        type=str,
        help="Path to encrypted JSON export file",
    )
    parser.add_argument(
        "password",
        type=str,
        help="Password used to encrypt the file",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output file (default: stdout)",
    )
    parser.add_argument(
        "-p",
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON output",
    )

    args = parser.parse_args()

    # Read encrypted file
    encrypted_file = Path(args.encrypted_file)
    if not encrypted_file.exists():
        print(f"Error: File not found: {encrypted_file}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(encrypted_file, "r") as f:
            encrypted_payload = json.load(f)
    except json.JSONDecodeError as exc:
        print(f"Error: Invalid JSON in encrypted file: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Error: Failed to read file: {exc}", file=sys.stderr)
        sys.exit(1)

    # Decrypt
    try:
        decrypted_data = encryption_service.decrypt_export(encrypted_payload, args.password)
    except ValueError as exc:
        print(f"Error: Decryption failed: {exc}", file=sys.stderr)
        sys.exit(1)
    except TypeError as exc:
        print(f"Error: Invalid decrypted data: {exc}", file=sys.stderr)
        sys.exit(1)

    # Output
    if args.pretty:
        output_json = json.dumps(decrypted_data, indent=2, sort_keys=True)
    else:
        output_json = json.dumps(decrypted_data, separators=(",", ":"))

    if args.output:
        try:
            with open(args.output, "w") as f:
                f.write(output_json)
            print(f"Decrypted data written to: {args.output}", file=sys.stderr)
        except Exception as exc:
            print(f"Error: Failed to write output file: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
