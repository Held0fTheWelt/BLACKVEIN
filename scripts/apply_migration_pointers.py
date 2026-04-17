#!/usr/bin/env python3
"""Apply migration pointers to origin files referenced by ADRs.

For each file in docs/ADR, extract any referenced origin paths (docs/archive, docs/MVPs, etc.).
For each origin file, if it doesn't already contain a 'Migrated Decision' pointer, insert one
and strip the original '## Decision' section to avoid duplicate information.

Usage: .venv\Scripts\python.exe scripts\apply_migration_pointers.py
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ADR_DIR = ROOT / 'docs' / 'ADR'

link_re = re.compile(r'\[.*?\]\((docs/[A-Za-z0-9_\-/\.]+\.md)\)')
decision_re = re.compile(r'(?ms)^##\s+Decision\b.*?(?:^##\s+|\Z)')
migrated_line_tpl = '**Migrated Decision:** See canonical ADR: [{title}](../../ADR/{adrfile})\n'


def find_origins(adr_path: Path):
    text = adr_path.read_text(encoding='utf-8')
    origins = set()
    for m in link_re.finditer(text):
        p = m.group(1)
        if p.startswith('docs/'):
            origins.add((p, adr_path.name))
    # Also look for explicit 'Migrated from' lines with backticks
    for m in re.finditer(r'`(docs/[\w\-\./]+\.md)`', text):
        origins.add((m.group(1), adr_path.name))
    return origins


def apply_pointer(origin_rel: str, adr_path: Path):
    origin_file = ROOT / origin_rel
    if not origin_file.exists():
        return False, 'missing'
    text = origin_file.read_text(encoding='utf-8')
    # If pointer already present, skip
    if 'Migrated Decision' in text and str(adr_path.name) in text:
        return False, 'exists'
    # Remove Decision section to avoid duplication
    new_text = decision_re.sub('', text)
    # Insert pointer near top (after title or first line)
    title = adr_path.read_text(encoding='utf-8').splitlines()[0].lstrip('# ').strip()
    pointer = migrated_line_tpl.format(title=title, adrfile=adr_path.name)
    lines = new_text.splitlines()
    insert_at = 0
    for i, ln in enumerate(lines[:10]):
        if ln.startswith('# '):
            insert_at = i+1
            break
    # Ensure a blank line after pointer
    lines.insert(insert_at, '')
    lines.insert(insert_at, pointer)
    updated = '\n'.join(lines).rstrip() + '\n'
    origin_file.write_text(updated, encoding='utf-8')
    return True, 'updated'


def main():
    modified = []
    for adr in sorted(ADR_DIR.glob('*.md')):
        origins = find_origins(adr)
        for origin_rel, _ in origins:
            changed, status = apply_pointer(origin_rel, adr)
            if changed:
                modified.append(origin_rel)
    if modified:
        print('Updated origin files:')
        for m in sorted(set(modified)):
            print('-', m)
    else:
        print('No origin files required changes.')


if __name__ == '__main__':
    main()
