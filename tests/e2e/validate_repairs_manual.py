#!/usr/bin/env python3
"""Manual validation script for World of Shadows gameplay seam repairs.

This script validates Phase 1-2 repairs without requiring complex test fixtures:
1. Session identifier persistence (cookie-based)
2. Template mapping configuration
3. Turn response validation against canonical contract
4. Frontend/backend integration seam integrity

Run with: python3 tests/e2e/validate_repairs_manual.py
"""

import sys
import os
from pathlib import Path

# Fix encoding for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add paths
backend_path = Path(__file__).parent.parent.parent / "backend"
frontend_path = Path(__file__).parent.parent.parent / "frontend"
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(frontend_path))


def test_template_mapping_config():
    """Test 1: Template mapping configuration loaded from YAML."""
    print("\n" + "="*70)
    print("TEST 1: Template Mapping Configuration")
    print("="*70)

    try:
        from app.routes_play import _PLAY_TEMPLATE_TO_CONTENT_MODULE_ID

        print("✓ Template mapping loaded successfully")
        print(f"  Current mappings: {_PLAY_TEMPLATE_TO_CONTENT_MODULE_ID}")

        # Verify god_of_carnage_solo mapping
        assert "god_of_carnage_solo" in _PLAY_TEMPLATE_TO_CONTENT_MODULE_ID
        assert _PLAY_TEMPLATE_TO_CONTENT_MODULE_ID["god_of_carnage_solo"] == "god_of_carnage"
        print("✓ god_of_carnage_solo → god_of_carnage mapping verified")

        # Verify config file exists
        config_path = Path(__file__).parent.parent.parent / "frontend" / "config" / "template_module_mapping.yaml"
        assert config_path.exists()
        print(f"✓ Config file exists at {config_path}")

        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backend_turn_validation():
    """Test 2: Backend turn response validation against canonical contract."""
    print("\n" + "="*70)
    print("TEST 2: Backend Turn Response Validation")
    print("="*70)

    try:
        from backend.app.api.v1.session_routes import _validate_world_engine_turn_contract
        from backend.app.services.game_service import GameServiceError

        # Test 2a: Valid turn response passes validation
        print("\n2a: Testing VALID turn response...")
        valid_turn = {
            "turn_number": 1,
            "turn_kind": "player",
            "interpreted_input": {"kind": "speech"},
            "narrative_commit": {"committed_scene_id": "scene_1"},
            "validation_outcome": {"status": "approved"},
            "visible_output_bundle": {"gm_narration": ["The room is quiet."]},
        }

        try:
            _validate_world_engine_turn_contract(valid_turn)
            print("  ✓ Valid turn response passed validation")
        except Exception as e:
            print(f"  ✗ Unexpected error: {e}")
            return False

        # Test 2b: Missing required field raises error
        print("\n2b: Testing INVALID turn response (missing visible_output_bundle)...")
        invalid_turn = {
            "turn_number": 1,
            "turn_kind": "player",
            "interpreted_input": {"kind": "speech"},
            "narrative_commit": {"committed_scene_id": "scene_1"},
            "validation_outcome": {"status": "approved"},
        }

        try:
            _validate_world_engine_turn_contract(invalid_turn)
            print("  ✗ Should have raised error for missing visible_output_bundle")
            return False
        except GameServiceError as e:
            print(f"  ✓ Correctly rejected invalid turn: {e}")

        # Test 2c: Wrong type validation
        print("\n2c: Testing INVALID field type (interpreted_input as string)...")
        wrong_type_turn = {
            "turn_number": 1,
            "turn_kind": "player",
            "interpreted_input": "speech",  # Should be dict
            "narrative_commit": {"committed_scene_id": "scene_1"},
            "validation_outcome": {"status": "approved"},
            "visible_output_bundle": {"gm_narration": ["The room is quiet."]},
        }

        try:
            _validate_world_engine_turn_contract(wrong_type_turn)
            print("  ✗ Should have raised error for wrong field type")
            return False
        except GameServiceError as e:
            print(f"  ✓ Correctly rejected wrong field type: {e}")

        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_frontend_turn_projection():
    """Test 3: Frontend turn response projection validates critical fields."""
    print("\n" + "="*70)
    print("TEST 3: Frontend Turn Response Projection")
    print("="*70)

    try:
        from app.routes_play import _build_play_shell_runtime_view

        # Test 3a: Complete response with all fields
        print("\n3a: Testing complete world-engine response...")
        complete_payload = {
            "trace_id": "trace_123",
            "turn": {
                "turn_number": 1,
                "turn_kind": "player",
                "raw_input": "I look around.",
                "interpreted_input": {"kind": "action"},
                "visible_output_bundle": {
                    "gm_narration": ["You see a room.", "It is quiet."],
                    "spoken_lines": ["Hello there."],
                },
                "validation_outcome": {"status": "approved"},
                "narrative_commit": {
                    "committed_scene_id": "scene_1",
                    "commit_reason_code": "natural_progression",
                    "situation_status": "stable",
                    "committed_consequences": ["You feel calm."],
                },
                "graph": {"errors": []},
            },
            "state": {
                "committed_state": {
                    "current_scene_id": "scene_1",
                    "last_narrative_commit": {},
                    "last_committed_consequences": ["You feel calm."],
                },
                "current_scene_id": "scene_1",
                "turn_counter": 1,
            },
        }

        view = _build_play_shell_runtime_view(complete_payload)

        # Verify key fields are extracted
        required_fields = {
            "turn_number": 1,
            "player_line": "I look around.",
            "interpreted_input_kind": "action",
            "validation_status": "approved",
            "committed_scene_id": "scene_1",
        }

        for field, expected in required_fields.items():
            actual = view.get(field)
            if actual == expected:
                print(f"  ✓ {field}: {actual}")
            else:
                print(f"  ✗ {field}: expected {expected}, got {actual}")
                return False

        # Verify narration is joined correctly
        expected_narration = "You see a room.\n\nIt is quiet."
        actual_narration = view.get("narration_text")
        if actual_narration == expected_narration:
            print(f"  ✓ narration_text correctly joined: {repr(actual_narration)}")
        else:
            print(f"  ✗ narration_text: expected {repr(expected_narration)}, got {repr(actual_narration)}")
            return False

        # Test 3b: Minimal response (missing optional fields)
        print("\n3b: Testing minimal response (graceful degradation)...")
        minimal_payload = {
            "trace_id": None,
            "turn": {
                "turn_number": 0,
                "turn_kind": "opening",
                "raw_input": "",
                "interpreted_input": {"kind": "opening"},
                "visible_output_bundle": {
                    "gm_narration": ["Welcome to the narrative."],
                },
                "validation_outcome": {"status": "approved"},
                "narrative_commit": {
                    "committed_scene_id": "start",
                },
            },
            "state": {
                "committed_state": {},
                "current_scene_id": "start",
            },
        }

        try:
            view = _build_play_shell_runtime_view(minimal_payload)
            print(f"  ✓ Minimal response handled gracefully")
            print(f"    - turn_kind: {view.get('interpreted_input_kind')}")
            print(f"    - narration: {view.get('narration_text')}")
        except Exception as e:
            print(f"  ✗ Failed to handle minimal response: {e}")
            return False

        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cookie_handling_code():
    """Test 4: Verify session persistence cookie handling code."""
    print("\n" + "="*70)
    print("TEST 4: Session Persistence Cookie Handling")
    print("="*70)

    try:
        # Check that routes_play.py imports make_response
        from app.routes_play import make_response
        print("✓ make_response imported (required for cookie setting)")

        # Check that request is imported
        from app.routes_play import request
        print("✓ request imported (required for cookie reading)")

        # Verify the play_shell function exists and has proper structure
        import inspect
        from app.routes_play import play_shell

        source = inspect.getsource(play_shell)

        # Check for cookie key construction
        if "wos_backend_session_" in source:
            print("✓ Cookie key construction found in play_shell")
        else:
            print("✗ Cookie key construction NOT found")
            return False

        # Check for request.cookies.get
        if "request.cookies.get(cookie_key)" in source:
            print("✓ Cookie retrieval code found")
        else:
            print("✗ Cookie retrieval code NOT found")
            return False

        # Check for set_cookie call
        if "response_obj.set_cookie" in source or ".set_cookie(" in source:
            print("✓ Cookie setting code found")
        else:
            print("✗ Cookie setting code NOT found")
            return False

        # Check for security flags (Flask set_cookie uses lowercase parameters)
        has_secure = "secure=True" in source
        has_httponly = "httponly=True" in source
        has_samesite = 'samesite=' in source

        if has_secure:
            print("✓ secure=True flag found")
        else:
            print("✗ secure=True flag NOT found")

        if has_httponly:
            print("✓ httponly=True flag found")
        else:
            print("✗ httponly=True flag NOT found")

        if has_samesite:
            print("✓ samesite flag found")
        else:
            print("✗ samesite flag NOT found")

        if has_secure and has_httponly and has_samesite:
            print("✓ All security flags found (secure, httponly, samesite)")
        else:
            print("✗ Some security flags missing")
            return False

        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""
    print("\n" + "="*70)
    print("WORLD OF SHADOWS - GAMEPLAY SEAM REPAIR VALIDATION")
    print("Phase 1-2 End-to-End Testing")
    print("="*70)

    tests = [
        ("Template Mapping Configuration", test_template_mapping_config),
        ("Backend Turn Validation", test_backend_turn_validation),
        ("Frontend Turn Projection", test_frontend_turn_projection),
        ("Cookie Handling Code", test_cookie_handling_code),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ FATAL ERROR in {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*70)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
