"""Data export/import API (admin only, high-risk operations)."""
from __future__ import annotations

from flask import jsonify, request
from flask_jwt_extended import jwt_required

from app.api.v1 import api_v1_bp
from app.auth.feature_registry import FEATURE_MANAGE_DATA_EXPORT, FEATURE_MANAGE_DATA_IMPORT
from app.auth.permissions import current_user_is_admin, current_user_is_super_admin, require_feature
from app.services import data_export_service, data_import_service


@api_v1_bp.route("/data/export", methods=["POST"])
@jwt_required()
@require_feature(FEATURE_MANAGE_DATA_EXPORT)
def export_data():
    """
    Export data as structured JSON.

    Body:
    - {"scope": "full"}
    - {"scope": "table", "table": "users"}
    - {"scope": "rows", "table": "users", "primary_keys": [1, 2, 3]}
    """
    if not current_user_is_admin():
        return jsonify({"error": "Forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    scope = (payload.get("scope") or "").strip().lower()

    try:
        if scope == "full":
            export = data_export_service.export_full()
        elif scope == "table":
            table = (payload.get("table") or "").strip()
            if not table:
                return jsonify({"error": "Missing table for scope=table"}), 400
            export = data_export_service.export_table(table)
        elif scope == "rows":
            table = (payload.get("table") or "").strip()
            ids = payload.get("primary_keys")
            if not table or not isinstance(ids, list) or not ids:
                return jsonify({"error": "Missing table or primary_keys for scope=rows"}), 400
            export = data_export_service.export_table_rows(table, ids)
        else:
            return jsonify({"error": "Invalid or missing scope"}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(export), 200


@api_v1_bp.route("/data/import/preflight", methods=["POST"])
@jwt_required()
@require_feature(FEATURE_MANAGE_DATA_IMPORT)
def import_preflight():
    """Validate an import payload without writing to the database."""
    if not current_user_is_admin():
        return jsonify({"error": "Forbidden"}), 403

    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Missing JSON body"}), 400
    result = data_import_service.preflight_validate_payload(payload)
    return (
        jsonify(
            {
                "ok": result.ok,
                "issues": [
                    {"code": i.code, "message": i.message, "table": i.table} for i in result.issues
                ],
                "metadata": result.metadata,
            }
        ),
        200,
    )


@api_v1_bp.route("/data/import/execute", methods=["POST"])
@jwt_required()
@require_feature(FEATURE_MANAGE_DATA_IMPORT)
def import_execute():
    """Execute an import. SuperAdmin-only due to high risk."""
    if not current_user_is_super_admin():
        return jsonify({"error": "Forbidden. SuperAdmin required for import."}), 403

    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Missing JSON body"}), 400

    pre = data_import_service.preflight_validate_payload(payload)
    if not pre.ok:
        return (
            jsonify(
                {
                    "ok": False,
                    "issues": [
                        {"code": i.code, "message": i.message, "table": i.table} for i in pre.issues
                    ],
                    "metadata": pre.metadata,
                }
            ),
            400,
        )

    try:
        result = data_import_service.execute_import(payload)
    except data_import_service.ImportError as exc:
        return (
            jsonify(
                {
                    "ok": False,
                    "issues": [
                        {"code": "IMPORT_ERROR", "message": str(exc), "table": None},
                    ],
                    "metadata": pre.metadata,
                }
            ),
            400,
        )

    return (
        jsonify(
            {
                "ok": True,
                "issues": [
                    {"code": i.code, "message": i.message, "table": i.table} for i in result.issues
                ],
                "metadata": result.metadata,
            }
        ),
        200,
    )

