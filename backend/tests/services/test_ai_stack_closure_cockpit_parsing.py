"""Tests for ai_stack_closure_cockpit_parsing.py - Closure cockpit audit parsing."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import json
import pytest

from app.services.ai_stack.ai_stack_closure_cockpit_parsing import (
    EXPECTED_GATE_ORDER,
    extract_gate_id,
    extract_heading_statement,
    extract_level_reason,
    ordered_gate_stack,
    parse_closure_notes,
    parse_gate_summary_rows,
    read_audit_json,
    read_audit_text,
)


class TestReadAuditText:
    """Tests for read_audit_text function."""

    def test_read_audit_text_success(self, tmp_path):
        """Test reading valid audit text file."""
        test_file = tmp_path / "audit.md"
        test_file.write_text("# Audit Report\nContent here", encoding="utf-8")

        result = read_audit_text(test_file)
        assert result == "# Audit Report\nContent here"

    def test_read_audit_text_empty_file(self, tmp_path):
        """Test reading empty file."""
        test_file = tmp_path / "empty.md"
        test_file.write_text("", encoding="utf-8")

        result = read_audit_text(test_file)
        assert result == ""

    def test_read_audit_text_unicode_content(self, tmp_path):
        """Test reading file with unicode characters."""
        test_file = tmp_path / "unicode.md"
        test_file.write_text("# Report\n✓ Status: éxcellent", encoding="utf-8")

        result = read_audit_text(test_file)
        assert "✓" in result
        assert "éxcellent" in result

    def test_read_audit_text_file_not_found(self, tmp_path):
        """Test reading non-existent file."""
        nonexistent = tmp_path / "nonexistent.md"

        result = read_audit_text(nonexistent)
        assert result == ""

    def test_read_audit_text_permission_error(self):
        """Test reading file with permission error."""
        with patch.object(Path, "read_text") as mock_read:
            mock_read.side_effect = PermissionError()
            test_path = Path("/some/path")

            result = read_audit_text(test_path)
            assert result == ""

    def test_read_audit_text_multiline_content(self, tmp_path):
        """Test reading multiline content."""
        test_file = tmp_path / "multiline.md"
        content = "Line 1\nLine 2\nLine 3"
        test_file.write_text(content, encoding="utf-8")

        result = read_audit_text(test_file)
        assert result.count("\n") == 2


class TestReadAuditJson:
    """Tests for read_audit_json function."""

    def test_read_audit_json_valid(self, tmp_path):
        """Test reading valid JSON file."""
        test_file = tmp_path / "data.json"
        data = {"gate_id": "G1", "status": "closed"}
        test_file.write_text(json.dumps(data), encoding="utf-8")

        result = read_audit_json(test_file)
        assert result == data

    def test_read_audit_json_empty_dict(self, tmp_path):
        """Test reading file with empty dict."""
        test_file = tmp_path / "empty.json"
        test_file.write_text("{}", encoding="utf-8")

        result = read_audit_json(test_file)
        assert result == {}

    def test_read_audit_json_nested_dict(self, tmp_path):
        """Test reading nested dictionary."""
        test_file = tmp_path / "nested.json"
        data = {
            "gates": {
                "G1": {"status": "closed"},
                "G2": {"status": "open"},
            }
        }
        test_file.write_text(json.dumps(data), encoding="utf-8")

        result = read_audit_json(test_file)
        assert result == data
        assert result["gates"]["G1"]["status"] == "closed"

    def test_read_audit_json_file_not_found(self, tmp_path):
        """Test reading non-existent file."""
        nonexistent = tmp_path / "nonexistent.json"

        result = read_audit_json(nonexistent)
        assert result == {}

    def test_read_audit_json_invalid_json(self, tmp_path):
        """Test reading invalid JSON."""
        test_file = tmp_path / "invalid.json"
        test_file.write_text("{ invalid json", encoding="utf-8")

        result = read_audit_json(test_file)
        assert result == {}

    def test_read_audit_json_json_array_not_dict(self, tmp_path):
        """Test reading JSON array (not dict)."""
        test_file = tmp_path / "array.json"
        test_file.write_text('[{"id": 1}, {"id": 2}]', encoding="utf-8")

        result = read_audit_json(test_file)
        assert result == {}

    def test_read_audit_json_json_null(self, tmp_path):
        """Test reading JSON null."""
        test_file = tmp_path / "null.json"
        test_file.write_text("null", encoding="utf-8")

        result = read_audit_json(test_file)
        assert result == {}

    def test_read_audit_json_json_string(self, tmp_path):
        """Test reading JSON string (not dict)."""
        test_file = tmp_path / "string.json"
        test_file.write_text('"just a string"', encoding="utf-8")

        result = read_audit_json(test_file)
        assert result == {}

    def test_read_audit_json_unicode_content(self, tmp_path):
        """Test reading JSON with unicode."""
        test_file = tmp_path / "unicode.json"
        data = {"message": "Status ✓ éxcellent"}
        test_file.write_text(json.dumps(data), encoding="utf-8")

        result = read_audit_json(test_file)
        assert result["message"] == "Status ✓ éxcellent"


class TestExtractGateId:
    """Tests for extract_gate_id function."""

    def test_extract_gate_id_simple_gate(self):
        """Test extracting simple gate IDs."""
        assert extract_gate_id("G1") == "G1"
        assert extract_gate_id("G2") == "G2"
        assert extract_gate_id("G10") == "G10"

    def test_extract_gate_id_with_whitespace(self):
        """Test extracting gate ID with surrounding whitespace."""
        assert extract_gate_id("  G1  ") == "G1"
        assert extract_gate_id("\tG5\t") == "G5"
        assert extract_gate_id(" G10 ") == "G10"

    def test_extract_gate_id_with_extra_text(self):
        """Test extracting gate ID with additional text."""
        assert extract_gate_id("G1 - Something") == "G1"
        assert extract_gate_id("G3|extra|data") == "G3"
        assert extract_gate_id("G8(with parentheses)") == "G8"

    def test_extract_gate_id_g9b(self):
        """Test extracting G9B specifically."""
        assert extract_gate_id("G9B") == "G9B"
        assert extract_gate_id("  G9B  ") == "G9B"
        assert extract_gate_id("G9B - Special") == "G9B"

    def test_extract_gate_id_g9b_takes_precedence(self):
        """Test that G9B is detected before G9."""
        assert extract_gate_id("G9B Details") == "G9B"

    def test_extract_gate_id_invalid(self):
        """Test with invalid gate IDs."""
        assert extract_gate_id("X1") is None
        assert extract_gate_id("G") is None
        assert extract_gate_id("GX") is None

    def test_extract_gate_id_large_numbers(self):
        """Test that G followed by any number of digits works."""
        assert extract_gate_id("G11") == "G11"
        assert extract_gate_id("G100") == "G100"

    def test_extract_gate_id_empty_string(self):
        """Test with empty string."""
        assert extract_gate_id("") is None

    def test_extract_gate_id_only_whitespace(self):
        """Test with only whitespace."""
        assert extract_gate_id("   ") is None
        assert extract_gate_id("\t\n") is None

    def test_extract_gate_id_case_sensitive(self):
        """Test that extraction is case-sensitive."""
        assert extract_gate_id("g1") is None  # lowercase fails
        assert extract_gate_id("G1") == "G1"  # uppercase works


class TestParseGateSummaryRows:
    """Tests for parse_gate_summary_rows function."""

    def test_parse_gate_summary_valid_row(self):
        """Test parsing valid gate summary row."""
        markdown = "| G1 | `structural` | `complete` | `high` | [Report](docs/g1.md) |"

        result = parse_gate_summary_rows(markdown)

        assert len(result) == 1
        row = result[0]
        assert row["gate_id"] == "G1"
        assert row["structural_status"] == "structural"
        assert row["closure_level_status"] == "complete"
        assert row["evidence_quality"] == "high"
        assert len(row["artifact_refs"]) == 1
        assert row["artifact_refs"][0]["label"] == "Report"

    def test_parse_gate_summary_multiple_rows(self):
        """Test parsing multiple rows."""
        markdown = """
| G1 | `status1` | `closed` | `high` | [Ref1](docs/r1.md) |
| G2 | `status2` | `open` | `medium` | [Ref2](docs/r2.md) |
"""

        result = parse_gate_summary_rows(markdown)
        assert len(result) == 2
        assert result[0]["gate_id"] == "G1"
        assert result[1]["gate_id"] == "G2"

    def test_parse_gate_summary_with_spaces_in_cells(self):
        """Test parsing with spaces in cell content."""
        markdown = "| G1 with text | `status text` | `closure text` | `quality text` | [Long Label](docs/file.md) |"

        result = parse_gate_summary_rows(markdown)
        assert len(result) == 1
        assert result[0]["gate_label"] == "G1 with text"

    def test_parse_gate_summary_g9b(self):
        """Test parsing G9B row."""
        markdown = "| G9B | `structural` | `complete` | `high` | [Report](docs/g9b.md) |"

        result = parse_gate_summary_rows(markdown)
        assert len(result) == 1
        assert result[0]["gate_id"] == "G9B"

    def test_parse_gate_summary_no_match(self):
        """Test parsing with no matching rows."""
        markdown = """
# Header
Some text
Not a table row
"""

        result = parse_gate_summary_rows(markdown)
        assert result == []

    def test_parse_gate_summary_malformed_row(self):
        """Test parsing malformed rows."""
        markdown = """
| G1 | missing columns |
| G2 | `status` | no link |
"""

        result = parse_gate_summary_rows(markdown)
        assert result == []

    def test_parse_gate_summary_empty_string(self):
        """Test parsing empty string."""
        result = parse_gate_summary_rows("")
        assert result == []

    def test_parse_gate_summary_invalid_gate_id_skipped(self):
        """Test that invalid gate IDs are skipped."""
        markdown = """
| G1 | `status` | `closed` | `high` | [Ref](docs/g1.md) |
| X1 | `status` | `closed` | `high` | [Ref](docs/x1.md) |
| G2 | `status` | `closed` | `high` | [Ref](docs/g2.md) |
"""

        result = parse_gate_summary_rows(markdown)
        assert len(result) == 2
        assert result[0]["gate_id"] == "G1"
        assert result[1]["gate_id"] == "G2"


class TestParseClosureNotes:
    """Tests for parse_closure_notes function."""

    def test_parse_closure_notes_single_gate(self):
        """Test parsing closure note for single gate."""
        markdown = "| G1 | `complete` | This gate is complete. |"

        result = parse_closure_notes(markdown)

        assert result["G1"] == "This gate is complete."

    def test_parse_closure_notes_multiple_gates(self):
        """Test parsing closure notes for multiple gates."""
        markdown = """
| G1 | `complete` | Note for G1 |
| G2 | `partial` | Note for G2 |
| G9B | `complete` | Note for G9B |
"""

        result = parse_closure_notes(markdown)
        assert result["G1"] == "Note for G1"
        assert result["G2"] == "Note for G2"
        assert result["G9B"] == "Note for G9B"

    def test_parse_closure_notes_no_match_for_empty_note(self):
        """Test parsing with empty note doesn't match regex."""
        markdown = "| G1 | `complete` | |"

        result = parse_closure_notes(markdown)
        # The regex requires content in the note part, so empty notes don't match
        assert result == {}

    def test_parse_closure_notes_no_match(self):
        """Test parsing with no matching rows."""
        markdown = """
# Header
Some text
| Invalid | format | here |
"""

        result = parse_closure_notes(markdown)
        assert result == {}

    def test_parse_closure_notes_empty_string(self):
        """Test parsing empty string."""
        result = parse_closure_notes("")
        assert result == {}

    def test_parse_closure_notes_with_backticks_in_note(self):
        """Test parsing with backticks in note text."""
        markdown = "| G1 | `complete` | Use `code` here |"

        result = parse_closure_notes(markdown)
        assert result["G1"] == "Use `code` here"

    def test_parse_closure_notes_with_pipes_escaped(self):
        """Test parsing note with special characters."""
        markdown = "| G1 | `complete` | Status: 100% |"

        result = parse_closure_notes(markdown)
        assert result["G1"] == "Status: 100%"


class TestExtractHeadingStatement:
    """Tests for extract_heading_statement function."""

    def test_extract_heading_statement_valid(self):
        """Test extracting statement from valid heading."""
        markdown = """
### Status

**Complete and verified**

Some other content
"""

        result = extract_heading_statement(markdown, "Status")
        assert result == "Complete and verified"

    def test_extract_heading_statement_with_text_after(self):
        """Test extracting when more content follows."""
        markdown = """
### Status

**Complete**

Regular paragraph text

### Next Section
"""

        result = extract_heading_statement(markdown, "Status")
        assert result == "Complete"

    def test_extract_heading_statement_no_heading(self):
        """Test when heading doesn't exist."""
        markdown = "# Title\nContent here"

        result = extract_heading_statement(markdown, "Missing")
        assert result == "unknown"

    def test_extract_heading_statement_heading_with_no_statement(self):
        """Test heading with no statement content."""
        markdown = """
### Status

Some regular text

### Next
"""

        result = extract_heading_statement(markdown, "Status")
        assert result == "unknown"

    def test_extract_heading_statement_empty_markdown(self):
        """Test with empty markdown."""
        result = extract_heading_statement("", "Status")
        assert result == "unknown"

    def test_extract_heading_statement_blank_lines(self):
        """Test with blank lines between heading and statement."""
        markdown = """
### Status


**Complete**
"""

        result = extract_heading_statement(markdown, "Status")
        assert result == "Complete"

    def test_extract_heading_statement_multiple_bold_statements(self):
        """Test with multiple bold statements (takes first)."""
        markdown = """
### Status

**First Statement**

**Second Statement**
"""

        result = extract_heading_statement(markdown, "Status")
        assert result == "First Statement"

    def test_extract_heading_statement_finds_bold_before_next_heading(self):
        """Test that bold statements before next heading are found."""
        markdown = """
### Status

Paragraph
**Found This**

### Other

**Not This**
"""

        result = extract_heading_statement(markdown, "Status")
        # Should find the bold statement before the next heading
        assert result == "Found This"

    def test_extract_heading_statement_no_bold_before_next_heading(self):
        """Test with no bold statement before next heading."""
        markdown = """
### Status

Paragraph text only

### Other

**Bold But Wrong**
"""

        result = extract_heading_statement(markdown, "Status")
        assert result == "unknown"


class TestExtractLevelReason:
    """Tests for extract_level_reason function."""

    def test_extract_level_reason_valid(self):
        """Test extracting valid reason."""
        markdown = """
### Assessment

Reason: This gate demonstrates complete control structures and comprehensive test coverage. The implementation is production-ready.
"""

        result = extract_level_reason(markdown, "Assessment")
        assert "demonstrates complete control" in result
        assert "production-ready" in result

    def test_extract_level_reason_no_reason_line(self):
        """Test when no 'Reason:' line exists."""
        markdown = """
### Assessment

Some paragraph without reason keyword.
"""

        result = extract_level_reason(markdown, "Assessment")
        assert result == "No explicit reason paragraph found."

    def test_extract_level_reason_heading_missing(self):
        """Test when heading doesn't exist."""
        markdown = "# Title\nContent"

        result = extract_level_reason(markdown, "Missing")
        assert result == "No authoritative rationale found."

    def test_extract_level_reason_truncates_at_two_lines(self):
        """Test that reason is limited to two lines."""
        markdown = """
### Assessment

Reason: First line of reason.
Second line of reason.
Third line not included.
"""

        result = extract_level_reason(markdown, "Assessment")
        assert "First line of reason." in result
        assert "Second line of reason." in result
        assert "Third line" not in result

    def test_extract_level_reason_stops_at_next_heading(self):
        """Test that extraction stops at next heading."""
        markdown = """
### Assessment

Reason: First part.
Second part.

### Next Section
Reason: This should not be included.
"""

        result = extract_level_reason(markdown, "Assessment")
        assert "First part" in result
        assert "Next Section" not in result

    def test_extract_level_reason_empty_markdown(self):
        """Test with empty markdown."""
        result = extract_level_reason("", "Assessment")
        assert result == "No authoritative rationale found."

    def test_extract_level_reason_skips_blank_lines(self):
        """Test that blank lines are skipped."""
        markdown = """
### Assessment

Reason: Important statement.

Extra paragraph.
"""

        result = extract_level_reason(markdown, "Assessment")
        # Should include both non-empty lines
        assert "Important statement." in result


class TestOrderedGateStack:
    """Tests for ordered_gate_stack function."""

    def test_ordered_gate_stack_all_gates(self):
        """Test ordering with all expected gates."""
        gates_by_id = {
            gate_id: {"gate_id": gate_id, "status": "closed"}
            for gate_id in EXPECTED_GATE_ORDER
        }

        result = ordered_gate_stack(gates_by_id)

        assert len(result) == len(EXPECTED_GATE_ORDER)
        for i, gate in enumerate(result):
            assert gate["gate_id"] == EXPECTED_GATE_ORDER[i]

    def test_ordered_gate_stack_subset_of_gates(self):
        """Test ordering with subset of gates."""
        gates_by_id = {
            "G1": {"gate_id": "G1"},
            "G5": {"gate_id": "G5"},
            "G10": {"gate_id": "G10"},
        }

        result = ordered_gate_stack(gates_by_id)

        assert len(result) == 3
        assert result[0]["gate_id"] == "G1"
        assert result[1]["gate_id"] == "G5"
        assert result[2]["gate_id"] == "G10"

    def test_ordered_gate_stack_empty_dict(self):
        """Test with empty dictionary."""
        result = ordered_gate_stack({})
        assert result == []

    def test_ordered_gate_stack_extra_gates_ignored(self):
        """Test that gates not in EXPECTED_GATE_ORDER are ignored."""
        gates_by_id = {
            "G1": {"gate_id": "G1"},
            "G2": {"gate_id": "G2"},
            "UNKNOWN": {"gate_id": "UNKNOWN"},
            "G3": {"gate_id": "G3"},
        }

        result = ordered_gate_stack(gates_by_id)

        assert len(result) == 3
        gate_ids = [gate["gate_id"] for gate in result]
        assert "UNKNOWN" not in gate_ids
        assert gate_ids == ["G1", "G2", "G3"]

    def test_ordered_gate_stack_preserves_gate_data(self):
        """Test that gate data is preserved in order."""
        gates_by_id = {
            "G1": {"gate_id": "G1", "status": "closed", "quality": "high"},
            "G2": {"gate_id": "G2", "status": "open", "quality": "medium"},
        }

        result = ordered_gate_stack(gates_by_id)

        assert result[0]["status"] == "closed"
        assert result[0]["quality"] == "high"
        assert result[1]["status"] == "open"
        assert result[1]["quality"] == "medium"

    def test_ordered_gate_stack_none_values_skipped(self):
        """Test that None values in dict don't crash."""
        gates_by_id = {
            "G1": {"gate_id": "G1"},
            "G2": None,  # This should be skipped
            "G3": {"gate_id": "G3"},
        }

        result = ordered_gate_stack(gates_by_id)

        assert len(result) == 2
        assert result[0]["gate_id"] == "G1"
        assert result[1]["gate_id"] == "G3"
