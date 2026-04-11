"""Tests for search_utils SQL escaping and csv_safe_cell."""

import pytest

from app.services.search_utils import _escape_sql_like_wildcards
from app.utils.csv_safe import csv_safe_cell


class TestEscapeSqlLikeWildcards:
    def test_returns_none_and_empty_unchanged(self):
        assert _escape_sql_like_wildcards(None) is None
        assert _escape_sql_like_wildcards("") == ""

    def test_escapes_backslash_percent_and_underscore_in_order(self):
        assert _escape_sql_like_wildcards(r"a\\b%c_d") == r"a\\\\b\%c\_d"

    def test_leaves_plain_text_unchanged(self):
        assert _escape_sql_like_wildcards("normal text 123") == "normal text 123"


class TestCsvSafeCell:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            (None, ""),
            ("simple", "simple"),
            ("=SUM(A1:A2)", "'=SUM(A1:A2)"),
            ("  +1+2", "'  +1+2"),
            ("\tcmd", "\tcmd"),
            ('say "hello"', '"say ""hello"""'),
            ("a,b", '"a,b"'),
            ("a\nb", '"a\nb"'),
            ("  @hidden,formula", '"\'  @hidden,formula"'),
        ],
    )
    def test_csv_safe_cell_covers_formula_and_csv_escaping(self, raw, expected):
        assert csv_safe_cell(raw) == expected
