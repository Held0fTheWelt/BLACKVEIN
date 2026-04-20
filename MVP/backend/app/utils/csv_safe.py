"""
CSV export helpers: escape for CSV and neutralize spreadsheet formula injection.
Cells that start with =, +, -, @, or \t (formula triggers) are prefixed so they are treated as text.
"""

FORMULA_PREFIX_CHARS = ("=", "+", "-", "@", "\t", "\r")


def csv_safe_cell(value) -> str:
    """
    Return a string safe for CSV: escape quotes and commas, and prefix formula-triggering
    values so spreadsheets do not execute them. Use for every user-influenced or free-text field.
    """
    if value is None:
        return ""
    s = str(value)
    # Neutralize formula injection: prefix with single quote so spreadsheet treats as text.
    if s and s.strip().startswith(FORMULA_PREFIX_CHARS):
        s = "'" + s
    if "\n" in s or "," in s or '"' in s:
        return '"' + s.replace('"', '""') + '"'
    return s
