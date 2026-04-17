#!/usr/bin/env python3
"""Find origin docs with '## Decision' still present and add Migrated Decision pointers.

For each markdown under docs/ (excluding docs/ADR) that contains a '## Decision' section
but not a 'Migrated Decision' pointer, attempt to find a canonical ADR that references
that origin file. If found, remove the '## Decision' section and insert a pointer.
Files that cannot be auto-matched are reported for manual review.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
ADR_DIR = DOCS / 'ADR'

decision_re = re.compile(r'(?ms)^##\s+Decision\b.*?(?:^##\s+|\Z)')
migrated_re = re.compile(r'Migrated Decision', re.IGNORECASE)


def find_all_origins_with_decision():
    files = []
    for p in DOCS.rglob('*.md'):
        if ADR_DIR in p.parents:
            continue
        text = p.read_text(encoding='utf-8')
        if decision_re.search(text) and not migrated_re.search(text):
            files.append(p)
    return files


def find_referring_adr(origin_path: Path):
    origin_rel = str(origin_path.relative_to(ROOT)).replace('\\', '/')
    # First pass: exact path mention in ADRs
    for adr in sorted(ADR_DIR.glob('*.md')):
        text = adr.read_text(encoding='utf-8')
        if origin_rel in text:
            return adr
    # Second pass: filename only
    name = origin_path.name
    for adr in sorted(ADR_DIR.glob('*.md')):
        text = adr.read_text(encoding='utf-8')
        if name in text:
            return adr
    return None


def adr_title(adr_path: Path):
    text = adr_path.read_text(encoding='utf-8')
    for ln in text.splitlines():
        if ln.strip().startswith('# '):
            return ln.strip().lstrip('# ').strip()
    return adr_path.name


def insert_pointer_and_strip_decision(origin_path: Path, adr_path: Path):
    text = origin_path.read_text(encoding='utf-8')
    # remove Decision section
    new_text = decision_re.sub('', text)
    # build pointer
    title = adr_title(adr_path)
    pointer = f'**Migrated Decision:** See canonical ADR: [{title}](../../ADR/{adr_path.name})\n'
    lines = new_text.splitlines()
    insert_at = 0
    for i, ln in enumerate(lines[:10]):
        if ln.startswith('# '):
            insert_at = i+1
            break
    lines.insert(insert_at, '')
    lines.insert(insert_at, pointer)
    updated = '\n'.join(lines).rstrip() + '\n'
    origin_path.write_text(updated, encoding='utf-8')


def main():
    origins = find_all_origins_with_decision()
    if not origins:
        print('No origin files with Decision sections found needing pointers.')
        return
    unmatched = []
    updated = []
    for p in origins:
        adr = find_referring_adr(p)
        if adr:
            insert_pointer_and_strip_decision(p, adr)
            updated.append(str(p.relative_to(ROOT)).replace('\\', '/'))
        else:
            unmatched.append(str(p.relative_to(ROOT)).replace('\\', '/'))
    if updated:
        print('Updated origin files:')
        for u in updated:
            print('-', u)
    if unmatched:
        print('\nFiles requiring manual review (no matching ADR found):')
        for u in unmatched:
            print('-', u)


if __name__ == '__main__':
    main()
