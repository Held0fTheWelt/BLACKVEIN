"""Data export/import API (admin only, high-risk operations)."""
from __future__ import annotations

from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.api.v1 import api_v1_bp
from app.auth.feature_registry import FEATURE_MANAGE_DATA_EXPORT, FEATURE_MANAGE_DATA_IMPORT
from app.auth.permissions import current_user_is_admin, current_user_is_super_admin, require_feature
from app.services import data_export_service, data_import_service
from app.extensions import limiter
from app.utils.error_handler import log_full_error, ERROR_MESSAGES


def _get_user_id_for_rate_limit():
    """Return the current user's ID for rate limiting, or a default identifier."""
    try:
        user_id = get_jwt_identity()
        if user_id:
            return str(user_id)
    except Exception:
        pass
    # Fallback to request IP if JWT identity unavailable
    return request.remote_addr


@api_v1_bp.route("/data/export", methods=["POST"])
@jwt_required()
@limiter.limit("5 per hour", key_func=_get_user_id_for_rate_limit)
@require_feature(FEATURE_MANAGE_DATA_EXPORT)
def export_data():
    """
    Export data as structured JSON, optionally encrypted.

    Body:
    - {"scope": "full"}
    - {"scope": "table", "table": "users"}
    - {"scope": "rows", "table": "users", "primary_keys": [1, 2, 3]}
    - {"scope": "full", "encrypt": true, "password": "secure_password"}

    Optional fields:
    - encrypt (bool): If true, encrypt the export with AES-256-CBC
    - password (str): Required if encrypt=true. User-provided password for encryption
    """
    if not current_user_is_admin():
        return jsonify({"error": "Forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    scope = (payload.get("scope") or "").strip().lower()
    encrypt = payload.get("encrypt", False)
    password = payload.get("password", "")

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

        # Apply encryption if requested
        if encrypt:
            if not password:
                return jsonify({"error": "Password required for encryption"}), 400
            try:
                export = data_export_service.encrypt_export(export, password)
                export["encrypted"] = True
            except ValueError as exc:
                log_full_error(exc, "Data export encryption failed", route=request.path, method=request.method)
                return jsonify({"error": ERROR_MESSAGES["validation_error"]}), 400

    except ValueError as exc:
        log_full_error(exc, "Data export validation failed", route=request.path, method=request.method)
        return jsonify({"error": ERROR_MESSAGES["validation_error"]}), 400

    return jsonify(export), 200


@api_v1_bp.route("/data/export/decrypt", methods=["POST"])
@jwt_required()
@limiter.limit("5 per hour", key_func=_get_user_id_for_rate_limit)
@require_feature(FEATURE_MANAGE_DATA_EXPORT)
def decrypt_export():
    """
    Decrypt an encrypted export payload.

    Body:
    - encrypted_data: base64-encoded ciphertext
    - iv: base64-encoded initialization vector
    - salt: base64-encoded salt
    - password: user-provided password for decryption
    - (optional fields: version, algorithm, pbkdf2_iterations)
    """
    if not current_user_is_admin():
        return jsonify({"error": "Forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    password = payload.get("password", "")

    if not password:
        return jsonify({"error": "Password required for decryption"}), 400

    # Validate encrypted payload structure
    required_fields = ["encrypted_data", "iv", "salt"]
    for field in required_fields:
        if field not in payload:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    try:
        decrypted_data = data_export_service.decrypt_export(payload, password)
    except ValueError as exc:
        log_full_error(exc, "Data export decryption failed", route=request.path, method=request.method)
        return jsonify({"error": "Decryption failed. Invalid password or corrupted data."}), 400
    except TypeError as exc:
        log_full_error(exc, "Invalid decrypted data format", route=request.path, method=request.method)
        return jsonify({"error": "Decryption failed. Invalid data format."}), 400

    return jsonify(decrypted_data), 200


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
@limiter.limit("1 per hour", key_func=_get_user_id_for_rate_limit)
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
        log_full_error(exc, "Data import execution failed", route=request.path, method=request.method)
        return (
            jsonify(
                {
                    "ok": False,
                    "issues": [
                        {"code": "IMPORT_ERROR", "message": "Import operation failed", "table": None},
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

