"""User CRUD API: list (admin), get (admin or self), update (admin or self), delete (admin)."""
import logging
import re
from datetime import datetime

from flask import jsonify, request, current_app
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api.v1 import api_v1_bp
from app.auth.feature_registry import FEATURE_MANAGE_USERS, user_can_access_feature
from app.auth.permissions import (
    admin_may_assign_role_level,
    admin_may_edit_target,
    current_user_is_admin,
    current_user_is_super_admin,
    get_current_user,
    require_jwt_admin,
)
from app.auth.admin_security import admin_security, admin_security_sensitive
from app.extensions import limiter, db
from app.services import log_activity
from app.services.user_service import (
    assign_role as assign_role_service,
    ban_user as ban_user_service,
    change_password as change_password_service,
    get_user_by_id,
    list_users,
    unban_user as unban_user_service,
    update_user as update_user_service,
    delete_user as delete_user_service,
    count_user_threads,
    count_user_posts,
    count_user_bookmarks,
    get_user_recent_threads,
    get_user_recent_posts,
    get_user_bookmarks,
    get_user_tags,
    validate_password_complexity,
    validate_email_format,
    USERNAME_MAX_LENGTH,
)

logger = logging.getLogger(__name__)

# Role level bounds (0-9999)
ROLE_LEVEL_MIN = 0
ROLE_LEVEL_MAX = 9999


def _validate_role_level_bounds(level: int) -> tuple[bool, str | None]:
    """
    Validate that role_level is within bounds [0, 9999].
    Returns (is_valid, error_message) tuple.
    """
    if level < ROLE_LEVEL_MIN or level > ROLE_LEVEL_MAX:
        return False, f"role_level must be between {ROLE_LEVEL_MIN} and {ROLE_LEVEL_MAX}"
    return True, None


def _log_privilege_change(admin_id: int, user_id: int, old_role: str, new_role: str, old_level: int = None, new_level: int = None, reason: str = None):
    """
    Log a privilege/role change with security alerts for SuperAdmin grants.
    Logs to both application logger and activity log.
    """
    from app.models.user import SUPERADMIN_THRESHOLD

    admin_name = f"admin_id={admin_id}"
    current_admin = get_user_by_id(admin_id) if admin_id else None
    if current_admin:
        admin_name = f"{current_admin.username}(id={admin_id})"

    user_name = f"user_id={user_id}"
    target_user = get_user_by_id(user_id) if user_id else None
    if target_user:
        user_name = f"{target_user.username}(id={user_id})"

    # Build log message
    changes = []
    if old_role != new_role:
        changes.append(f"role {old_role} -> {new_role}")
    if old_level is not None and new_level is not None and old_level != new_level:
        changes.append(f"role_level {old_level} -> {new_level}")

    change_desc = ", ".join(changes) if changes else "privilege level"
    base_msg = f"Privilege change: {admin_name} modified {user_name}: {change_desc}"

    # Log to application logger with structured data
    current_app.logger.warning(
        base_msg,
        extra={
            "event_type": "privilege_change",
            "event": "privilege_change",
            "admin_id": admin_id,
            "admin_username": current_admin.username if current_admin else None,
            "user_id": user_id,
            "user_username": target_user.username if target_user else None,
            "old_role": old_role,
            "new_role": new_role,
            "old_role_level": old_level,
            "new_role_level": new_level,
            "reason": reason,
        }
    )

    # Security alert: SuperAdmin grant
    if new_role == "admin" and new_level is not None and new_level >= SUPERADMIN_THRESHOLD:
        alert_msg = f"SECURITY ALERT: SuperAdmin privilege granted by {admin_name} to {user_name}"
        current_app.logger.critical(
            alert_msg,
            extra={
                "event_type": "superadmin_grant",
                "event": "superadmin_grant",
                "admin_id": admin_id,
                "admin_username": current_admin.username if current_admin else None,
                "user_id": user_id,
                "user_username": target_user.username if target_user else None,
                "new_role": new_role,
                "new_role_level": new_level,
                "reason": reason,
            }
        )

    # Also log to activity log for admin dashboard
    metadata = {
        "old_role": old_role,
        "new_role": new_role,
    }
    if old_level is not None:
        metadata["old_role_level"] = old_level
    if new_level is not None:
        metadata["new_role_level"] = new_level
    if reason:
        metadata["reason"] = reason

    severity = "critical" if (new_role == "admin" and new_level is not None and new_level >= SUPERADMIN_THRESHOLD) else "warning"

    log_activity(
        actor=current_admin,
        category="privilege_change",
        action="role_level_modified",
        status=severity,
        message=base_msg,
        route=request.path if request else None,
        method=request.method if request else None,
        target_type="user",
        target_id=str(user_id),
        metadata=metadata,
    )


def _parse_int(value, default, min_val=None, max_val=None):
    if value is None:
        return default
    try:
        n = int(value)
        if min_val is not None and n < min_val:
            return default
        if max_val is not None and n > max_val:
            return max_val
        return n
    except (TypeError, ValueError):
        return default


def _validate_username(username: str) -> tuple[bool, str | None]:
    """
    Validate username field.
    - 3-32 characters (for user-facing display, stricter than internal 2-80)
    - alphanumeric, underscore, hyphen
    Returns (is_valid, error_message)
    """
    if not isinstance(username, str):
        return False, "Username must be a string"

    username = username.strip()
    if not username:
        return False, "Username cannot be empty"

    if len(username) < 3:
        return False, "Username must be at least 3 characters"

    if len(username) > 32:
        return False, "Username must be at most 32 characters"

    # Allow alphanumeric, underscore, hyphen
    if not re.match(r"^[a-zA-Z0-9_-]+$", username):
        return False, "Username can only contain letters, numbers, underscores, and hyphens"

    return True, None


def _validate_email(email: str) -> tuple[bool, str | None]:
    """
    Validate email field using RFC 5322 format validator.
    Returns (is_valid, error_message)
    """
    if not isinstance(email, str):
        return False, "Email must be a string"

    email = email.strip()
    if not email:
        return False, "Email cannot be empty"

    # Use the existing validate_email_format from user_service
    is_valid, result = validate_email_format(email)
    if not is_valid:
        return False, f"Invalid email format: {result}"

    return True, None


def _validate_display_name(display_name: str) -> tuple[bool, str | None]:
    """
    Validate display_name field.
    - 1-100 characters
    - no control characters
    Returns (is_valid, error_message)
    """
    if not isinstance(display_name, str):
        return False, "Display name must be a string"

    display_name = display_name.strip()
    if not display_name:
        return False, "Display name cannot be empty"

    if len(display_name) > 100:
        return False, "Display name must be at most 100 characters"

    # Check for control characters (ASCII 0-31, 127)
    if any(ord(c) < 32 or ord(c) == 127 for c in display_name):
        return False, "Display name contains invalid characters (control characters)"

    return True, None


def _validate_bio(bio: str) -> tuple[bool, str | None]:
    """
    Validate bio/description field.
    - 0-500 characters
    - no control characters
    Returns (is_valid, error_message)
    """
    if not isinstance(bio, str):
        return False, "Bio must be a string"

    bio = bio.strip()
    if len(bio) > 500:
        return False, "Bio must be at most 500 characters"

    # Check for control characters (ASCII 0-31, 127)
    if any(ord(c) < 32 or ord(c) == 127 for c in bio):
        return False, "Bio contains invalid characters (control characters)"

    return True, None


def _validate_phone(phone: str) -> tuple[bool, str | None]:
    """
    Validate phone field.
    - Optional (can be empty/None)
    - If provided: basic international format validation
    - Allows: +, digits, spaces, hyphens, parentheses
    Returns (is_valid, error_message)
    """
    if phone is None:
        return True, None

    if not isinstance(phone, str):
        return False, "Phone must be a string"

    phone = phone.strip()
    if not phone:
        return True, None  # Empty is allowed

    # Basic international phone format: +1-234-567-8900 or (123) 456-7890, etc
    # Allow: digits, +, -, (), space
    if not re.match(r"^[\d\s\-()++]*$", phone):
        return False, "Phone contains invalid characters"

    # Must have at least some digits
    if not re.search(r"\d", phone):
        return False, "Phone must contain at least one digit"

    # Max 20 characters (international standard)
    if len(phone) > 20:
        return False, "Phone must be at most 20 characters"

    return True, None


def _validate_birthday(birthday: str) -> tuple[bool, str | None]:
    """
    Validate birthday field.
    - Optional (can be empty/None)
    - If provided: YYYY-MM-DD format
    - Must be a valid date
    Returns (is_valid, error_message)
    """
    if birthday is None:
        return True, None

    if not isinstance(birthday, str):
        return False, "Birthday must be a string"

    birthday = birthday.strip()
    if not birthday:
        return True, None  # Empty is allowed

    # Validate YYYY-MM-DD format
    try:
        parsed_date = datetime.strptime(birthday, "%Y-%m-%d")
        # Ensure the date is not in the future
        if parsed_date > datetime.now():
            return False, "Birthday cannot be in the future"
        return True, None
    except ValueError:
        return False, "Birthday must be in YYYY-MM-DD format"


@api_v1_bp.route("/users", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def users_list():
    """List users (admin only). Query: page, limit, q (search username/email)."""
    if not current_user_is_admin():
        return jsonify({"error": "Forbidden"}), 403
    if not user_can_access_feature(get_current_user(), FEATURE_MANAGE_USERS):
        return jsonify({"error": "Forbidden. You do not have access to this feature."}), 403
    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 20, min_val=1, max_val=100)
    search = request.args.get("q", "").strip() or None
    items, total = list_users(page=page, per_page=limit, search=search)
    return jsonify({
        "items": [u.to_dict(include_email=True, include_ban=True, include_areas=True) for u in items],
        "total": total,
        "page": page,
        "per_page": limit,
    }), 200


@api_v1_bp.route("/users/<int:user_id>", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def users_get(user_id):
    """
    Get one user by id. RESTRICTED: Admin can view any user; regular users can only view self.
    Returns different data based on viewer permission:
    - Self: All data (email, preferences, etc.)
    - Admin: All data for moderation (email, ban status, areas, etc.)
    - Other users: 403 Forbidden (use /users/<id>/profile for public profile)
    """
    current = get_current_user()
    if current is None:
        return jsonify({"error": "User not found"}), 404

    # SECURITY: Strict permission check - only allow admin or self
    # Non-admin users cannot view other users' private data
    is_viewing_self = current.id == user_id
    is_admin = current_user_is_admin()

    if not is_viewing_self and not is_admin:
        # Non-admin attempting cross-user access
        return jsonify({"error": "Forbidden"}), 403

    # If admin is viewing another user, verify feature access
    if not is_viewing_self and is_admin:
        if not user_can_access_feature(current, FEATURE_MANAGE_USERS):
            return jsonify({"error": "Forbidden. You do not have access to this feature."}), 403

    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Check if viewing self and account is banned
    if is_viewing_self and getattr(user, "is_banned", False):
        return jsonify({"error": "Account is restricted."}), 403

    # Determine what data to include based on viewer role
    include_email = is_admin or is_viewing_self
    include_ban = is_admin
    include_areas = is_admin

    return jsonify(user.to_dict(
        include_email=include_email,
        include_ban=include_ban,
        include_areas=include_areas
    )), 200


@api_v1_bp.route("/users/<int:user_id>/preferences", methods=["PUT"])
@limiter.limit("30 per minute")
@jwt_required()
def users_preferences(user_id):
    """Update user preferences (e.g. preferred_language). User can update self; admin can update any."""
    current = get_current_user()
    if current is None:
        return jsonify({"error": "User not found"}), 404
    if current.id != user_id and not current_user_is_admin():
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    kwargs = {}
    if "preferred_language" in data:
        kwargs["preferred_language"] = data.get("preferred_language")
    if not kwargs:
        return jsonify({"error": "No preference fields to update"}), 400
    user, err = update_user_service(user_id, **kwargs)
    if err:
        status = 400 if err == "Unsupported language" else 404
        return jsonify({"error": err}), status
    include_email = current_user_is_admin() or current.id == user.id
    include_ban = current_user_is_admin()
    include_areas = current_user_is_admin()
    return jsonify(user.to_dict(include_email=include_email, include_ban=include_ban, include_areas=include_areas)), 200


@api_v1_bp.route("/users/<int:user_id>/password", methods=["PUT"])
@limiter.limit("10 per minute")
@jwt_required()
def users_change_password(user_id):
    """
    Change password (self only). Body: current_password, new_password.
    Requires valid current_password. Password changes are not available via generic user update.
    """
    current = get_current_user()
    if current is None:
        return jsonify({"error": "User not found"}), 404
    if current.id != user_id:
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    current_password = data.get("current_password")
    new_password = data.get("new_password")
    if current_password is None or new_password is None:
        return jsonify({"error": "current_password and new_password are required"}), 400
    # Validate password complexity
    is_valid, error_msg = validate_password_complexity(new_password)
    if not is_valid:
        return jsonify({"error": error_msg, "code": "PASSWORD_WEAK"}), 400
    user, err = change_password_service(
        user_id,
        current_password=current_password,
        new_password=new_password,
    )
    if err:
        return jsonify({"error": err}), 400
    return jsonify({"message": "Password updated"}), 200


@api_v1_bp.route("/users/<int:user_id>", methods=["PUT"])
@limiter.limit("30 per minute")
@jwt_required()
def users_update(user_id):
    """
    Update a user. Admin can update users with strictly lower role_level; user can only update self (no role/role_level).
    Body: optional username, email, preferred_language, role (admin only), role_level (admin only, hierarchy rules).
    """
    current = get_current_user()
    if current is None:
        return jsonify({"error": "User not found"}), 404
    target = get_user_by_id(user_id)
    if not target:
        return jsonify({"error": "User not found"}), 404
    if current.id != user_id:
        if not current_user_is_admin():
            return jsonify({"error": "Forbidden"}), 403
        if not user_can_access_feature(current, FEATURE_MANAGE_USERS):
            return jsonify({"error": "Forbidden. You do not have access to this feature."}), 403
        actor_level = getattr(current, "role_level", 0) or 0
        target_level = getattr(target, "role_level", 0) or 0
        if not admin_may_edit_target(actor_level, target_level):
            return jsonify({"error": "Forbidden. You may only edit users with a lower role level."}), 403

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    if "password" in data or "current_password" in data:
        return jsonify({
            "error": "Password changes are not allowed via this endpoint. Use PUT /api/v1/users/<id>/password with current_password and new_password."
        }), 400

    kwargs = {}

    # Validate and extract username
    if "username" in data:
        username_val = data.get("username")
        is_valid, error = _validate_username(username_val)
        if not is_valid:
            return jsonify({"error": f"Invalid username: {error}"}), 400
        kwargs["username"] = username_val

    # Validate and extract email
    if "email" in data:
        email_val = data.get("email")
        is_valid, error = _validate_email(email_val)
        if not is_valid:
            return jsonify({"error": f"Invalid email: {error}"}), 400
        kwargs["email"] = email_val

    # Validate and extract display_name (future field)
    if "display_name" in data:
        display_name_val = data.get("display_name")
        is_valid, error = _validate_display_name(display_name_val)
        if not is_valid:
            return jsonify({"error": f"Invalid display_name: {error}"}), 400
        # Note: display_name field not yet in User model, but validation is ready

    # Validate and extract bio/description (future field)
    if "bio" in data:
        bio_val = data.get("bio")
        is_valid, error = _validate_bio(bio_val)
        if not is_valid:
            return jsonify({"error": f"Invalid bio: {error}"}), 400
        # Note: bio field not yet in User model, but validation is ready

    # Validate and extract phone (future field)
    if "phone" in data:
        phone_val = data.get("phone")
        is_valid, error = _validate_phone(phone_val)
        if not is_valid:
            return jsonify({"error": f"Invalid phone: {error}"}), 400
        # Note: phone field not yet in User model, but validation is ready

    # Validate and extract birthday (future field)
    if "birthday" in data:
        birthday_val = data.get("birthday")
        is_valid, error = _validate_birthday(birthday_val)
        if not is_valid:
            return jsonify({"error": f"Invalid birthday: {error}"}), 400
        # Note: birthday field not yet in User model, but validation is ready

    if "preferred_language" in data:
        kwargs["preferred_language"] = data.get("preferred_language")
    if current.id != user_id and current_user_is_admin():
        if "role" in data:
            kwargs["role"] = data.get("role")
        if "role_level" in data:
            try:
                new_level = int(data.get("role_level"))
            except (TypeError, ValueError):
                return jsonify({"error": "role_level must be an integer"}), 400
            # Bounds check: must be 0-9999
            is_valid, err = _validate_role_level_bounds(new_level)
            if not is_valid:
                return jsonify({"error": err}), 400
            actor_level = getattr(current, "role_level", 0) or 0
            target_level = getattr(target, "role_level", 0) or 0
            if not admin_may_assign_role_level(actor_level, user_id, new_level, current.id):
                return jsonify({"error": "Forbidden. You may not assign a role level higher than or equal to your own."}), 403
            kwargs["role_level"] = new_level
    elif current.id == user_id and "role_level" in data:
        if not current_user_is_super_admin():
            return jsonify({"error": "Forbidden. Only SuperAdmin may change their own role level."}), 403
        try:
            new_level = int(data.get("role_level"))
        except (TypeError, ValueError):
            return jsonify({"error": "role_level must be an integer"}), 400
        # Bounds check: must be 0-9999
        is_valid, err = _validate_role_level_bounds(new_level)
        if not is_valid:
            return jsonify({"error": err}), 400
        from app.models.user import SUPERADMIN_THRESHOLD
        if new_level < SUPERADMIN_THRESHOLD:
            return jsonify({"error": "Forbidden. SuperAdmin may only set own role level to at least 100."}), 403
        kwargs["role_level"] = new_level

    # Capture before values for role/role_level changes
    old_role = target.role if "role" in kwargs else None
    old_role_level = target.role_level if "role_level" in kwargs else None

    user, err = update_user_service(user_id, **kwargs)
    if err:
        status = 409 if err in ("Username already taken", "Email already registered") else 400
        if err == "User not found":
            status = 404
        return jsonify({"error": err}), status

    log_activity(
        actor=current,
        category="admin",
        action="user_updated",
        status="success",
        message=f"User updated: {user.username}",
        route=request.path,
        method=request.method,
        target_type="user",
        target_id=str(user.id),
    )

    # Log privilege changes with security alerts for role/role_level modifications
    if "role" in kwargs or "role_level" in kwargs:
        reason_str = None
        if isinstance(data, dict) and "reason" in data:
            reason_str = data.get("reason")
        _log_privilege_change(
            admin_id=current.id,
            user_id=user.id,
            old_role=old_role or target.role,
            new_role=user.role,
            old_level=old_role_level,
            new_level=user.role_level,
            reason=reason_str,
        )

    include_email = current_user_is_admin() or current.id == user.id
    include_ban = current_user_is_admin()
    include_areas = current_user_is_admin()
    return jsonify(user.to_dict(include_email=include_email, include_ban=include_ban, include_areas=include_areas)), 200


@api_v1_bp.route("/users/<int:user_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
@admin_security_sensitive(operation_name="user_deletion", require_super_admin=True)
def users_delete(user_id):
    """Delete a user (admin only, SuperAdmin required, 2FA required). Admin may only delete users with strictly lower role_level."""
    if not user_can_access_feature(get_current_user(), FEATURE_MANAGE_USERS):
        return jsonify({"error": "Forbidden. You do not have access to this feature."}), 403

    current = get_current_user()
    target_user = get_user_by_id(user_id)
    if not target_user:
        return jsonify({"error": "User not found"}), 404
    actor_level = getattr(current, "role_level", 0) or 0
    target_level = getattr(target_user, "role_level", 0) or 0
    if not admin_may_edit_target(actor_level, target_level):
        return jsonify({"error": "Forbidden. You may only delete users with a lower role level."}), 403

    ok, err = delete_user_service(user_id)
    if not ok:
        return jsonify({"error": err or "User not found"}), 404

    log_activity(
        actor=current,
        category="admin",
        action="user_deleted",
        status="success",
        message=f"User deleted: id={user_id}" + (f" ({target_user.username})" if target_user else ""),
        route=request.path,
        method=request.method,
        target_type="user",
        target_id=str(user_id),
    )

    return jsonify({"message": "Deleted"}), 200


@api_v1_bp.route("/users/<int:user_id>/role", methods=["PATCH"])
@limiter.limit("30 per minute")
@admin_security(require_2fa=True, require_super_admin=False, rate_limit="10/minute", audit_log=True)
def users_assign_role(user_id):
    """Assign role to a user (admin only, 2FA required). Admin may only assign to users with strictly lower role_level. Body: role (user, qa, moderator, admin), optional reason."""
    if not user_can_access_feature(get_current_user(), FEATURE_MANAGE_USERS):
        return jsonify({"error": "Forbidden. You do not have access to this feature."}), 403
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    role_name = data.get("role")
    if role_name is None:
        return jsonify({"error": "role is required"}), 400
    current = get_current_user()
    target = get_user_by_id(user_id)
    if not target:
        return jsonify({"error": "User not found"}), 404
    actor_level = getattr(current, "role_level", 0) or 0
    target_level = getattr(target, "role_level", 0) or 0

    # SECURITY: Prevent privilege escalation/elevation
    from app.models import Role
    role_obj = Role.query.filter_by(name=(role_name or "").strip().lower()).first()
    if not role_obj:
        return jsonify({"error": "Invalid role"}), 400

    # Determine the new role_level
    # If role_level is explicitly provided, use it; otherwise keep the target's existing level
    has_role_level_in_request = "role_level" in data
    if has_role_level_in_request:
        try:
            new_role_level = int(data.get("role_level"))
        except (TypeError, ValueError):
            return jsonify({"error": "role_level must be an integer"}), 400
        # Bounds check: must be 0-9999
        is_valid, err = _validate_role_level_bounds(new_role_level)
        if not is_valid:
            return jsonify({"error": err}), 400
    else:
        new_role_level = target_level  # Keep existing level

    # SECURITY: Check for privilege escalation
    # 1. Cannot assign role to anyone (including self) at a higher role_level than own
    if new_role_level > actor_level:
        reason = "Cannot assign role level higher than your own level"
        if user_id == current.id:
            reason = "Cannot elevate yourself above current role level"
        return jsonify({"error": reason, "code": "PRIVILEGE_DENIED"}), 403

    # 2. For self-assignment: cannot assign a level >= own level (prevent lateral/down moves that maintain privilege)
    if user_id == current.id:
        # Admin cannot modify their own level at all via PATCH endpoint
        # Only changing role is allowed if it's to a lower level (but this is still restricted)
        # Actually, the safest approach: prevent any self-modification via this endpoint
        if has_role_level_in_request or role_name != current.role:
            return jsonify({
                "error": "Cannot modify your own role or role level via this endpoint. Use PUT /users/<id> for self-changes if allowed."
            }), 403

    # 3. If assigning to someone else, they must have strictly lower role_level
    if user_id != current.id:
        if not admin_may_edit_target(actor_level, target_level):
            return jsonify({"error": "Forbidden. You may only assign roles to users with a lower role level."}), 403

    # Capture before value for role change
    old_role = target.role

    user, err = assign_role_service(user_id, role_name, actor_id=current.id if current else None)
    if err:
        status = 404 if err == "User not found" else 400
        return jsonify({"error": err}), status

    # If role_level was provided, update it
    if has_role_level_in_request:
        from app.extensions import db
        user.role_level = new_role_level
        db.session.commit()

    log_activity(
        actor=current,
        category="admin",
        action="user_role_changed",
        status="success",
        message=f"User role set to {user.role}",
        route=request.path,
        method=request.method,
        target_type="user",
        target_id=str(user.id),
        metadata={"new_role": user.role},
    )

    # Log privilege change with security alerts
    reason_str = data.get("reason") if isinstance(data.get("reason"), str) else None
    _log_privilege_change(
        admin_id=current.id,
        user_id=user.id,
        old_role=old_role,
        new_role=user.role,
        old_level=target.role_level,
        new_level=user.role_level,
        reason=reason_str,
    )

    return jsonify(user.to_dict(include_email=True, include_ban=True, include_areas=True)), 200


@api_v1_bp.route("/users/<int:user_id>/ban", methods=["POST"])
@limiter.limit("30 per minute")
@admin_security(require_2fa=False, require_super_admin=False, rate_limit="20/minute", audit_log=True)
def users_ban(user_id):
    """Ban a user (admin only). Admin may only ban users with strictly lower role_level. Body: optional reason."""
    if not user_can_access_feature(get_current_user(), FEATURE_MANAGE_USERS):
        return jsonify({"error": "Forbidden. You do not have access to this feature."}), 403
    current = get_current_user()
    target = get_user_by_id(user_id)
    if not target:
        return jsonify({"error": "User not found"}), 404
    actor_level = getattr(current, "role_level", 0) or 0
    target_level = getattr(target, "role_level", 0) or 0
    if not admin_may_edit_target(actor_level, target_level):
        return jsonify({"error": "Forbidden. You may only ban users with a lower role level."}), 403
    data = request.get_json(silent=True) or {}
    reason = data.get("reason") if isinstance(data.get("reason"), str) else None
    if reason is not None:
        reason = reason.strip() or None
    user, err = ban_user_service(user_id, reason=reason, actor_id=current.id if current else None)
    if err:
        status = 404 if err == "User not found" else 400
        return jsonify({"error": err}), status
    log_activity(
        actor=current,
        category="admin",
        action="user_banned",
        status="success",
        message=f"User banned: {user.username}",
        route=request.path,
        method=request.method,
        target_type="user",
        target_id=str(user.id),
    )
    return jsonify(user.to_dict(include_email=True, include_ban=True, include_areas=True)), 200


@api_v1_bp.route("/users/<int:user_id>/unban", methods=["POST"])
@limiter.limit("30 per minute")
@admin_security(require_2fa=True, require_super_admin=False, rate_limit="20/minute", audit_log=True)
def users_unban(user_id):
    """Unban a user (admin only, 2FA required). Admin may only unban users with strictly lower role_level."""
    if not user_can_access_feature(get_current_user(), FEATURE_MANAGE_USERS):
        return jsonify({"error": "Forbidden. You do not have access to this feature."}), 403
    current = get_current_user()
    target = get_user_by_id(user_id)
    if not target:
        return jsonify({"error": "User not found"}), 404
    actor_level = getattr(current, "role_level", 0) or 0
    target_level = getattr(target, "role_level", 0) or 0
    if not admin_may_edit_target(actor_level, target_level):
        return jsonify({"error": "Forbidden. You may only unban users with a lower role level."}), 403
    user, err = unban_user_service(user_id)
    if err:
        status = 404 if err == "User not found" else 400
        return jsonify({"error": err}), status
    log_activity(
        actor=current,
        category="admin",
        action="user_unbanned",
        status="success",
        message=f"User unbanned: {user.username}",
        route=request.path,
        method=request.method,
        target_type="user",
        target_id=str(user.id),
    )
    return jsonify(user.to_dict(include_email=True, include_ban=True, include_areas=True)), 200


# --- User Profiles (Phase 4) ---


@api_v1_bp.route("/users/<int:user_id>/profile", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required(optional=True)
def users_profile(user_id):
    """
    Get public user profile with activity summary.
    Returns: basic user info, activity counts, recent threads/posts, bookmarks count, tags.
    No authentication required (public endpoint).
    """
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Basic user info (public safe data)
    profile = {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_seen_at": user.last_seen_at.isoformat() if user.last_seen_at else None,
    }

    # Activity counts
    profile["stats"] = {
        "thread_count": count_user_threads(user.id),
        "post_count": count_user_posts(user.id),
        "bookmark_count": count_user_bookmarks(user.id),
    }

    # Recent activity
    profile["recent_threads"] = get_user_recent_threads(user.id, limit=10)
    profile["recent_posts"] = get_user_recent_posts(user.id, limit=10)

    # Tags used by this user
    profile["tags"] = get_user_tags(user.id, limit=15)

    return jsonify(profile), 200


@api_v1_bp.route("/users/<int:user_id>/bookmarks", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def users_bookmarks(user_id):
    """
    Get bookmarked threads for a user.
    Only the user themselves or admins can view their bookmarks.
    Query: page, limit.
    """
    current = get_current_user()
    if current is None:
        return jsonify({"error": "User not found"}), 404

    # Users can only view their own bookmarks
    if current.id != user_id and not current_user_is_admin():
        return jsonify({"error": "Forbidden"}), 403

    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 20, min_val=1, max_val=100)

    bookmarks, total = get_user_bookmarks(user_id, limit=limit, page=page)

    return jsonify({
        "items": bookmarks,
        "total": total,
        "page": page,
        "per_page": limit,
    }), 200


@api_v1_bp.route("/forum/tags/popular", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required(optional=True)
def forum_tags_popular():
    """
    Get popular tags across all threads.
    Query: limit (default 20, max 100).
    Returns list of tags with label, slug, thread_count.
    """
    limit = _parse_int(request.args.get("limit"), 20, min_val=1, max_val=100)

    from app.models import ForumTag, ForumThreadTag, ForumThread
    tags_data = db.session.query(
        ForumTag.id,
        ForumTag.label,
        ForumTag.slug,
        db.func.count(ForumThreadTag.thread_id).label("thread_count")
    ).outerjoin(
        ForumThreadTag, ForumTag.id == ForumThreadTag.tag_id
    ).outerjoin(
        ForumThread, ForumThreadTag.thread_id == ForumThread.id
    ).filter(
        ForumThread.status.notin_(("deleted",))
    ).group_by(
        ForumTag.id, ForumTag.label, ForumTag.slug
    ).order_by(
        db.func.count(ForumThreadTag.thread_id).desc()
    ).limit(limit).all()

    tags = [
        {
            "id": tag[0],
            "label": tag[1],
            "slug": tag[2],
            "thread_count": tag[3] or 0,
        }
        for tag in tags_data
    ]

    return jsonify({"items": tags}), 200


@api_v1_bp.route("/forum/tags/<slug>", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required(optional=True)
def forum_tag_detail(slug):
    """
    Get tag details with threads using this tag.
    Query: page, limit.
    Returns tag info and paginated list of threads.
    """
    from app.models import ForumTag, ForumThreadTag, ForumThread

    tag = ForumTag.query.filter_by(slug=slug).first()
    if not tag:
        return jsonify({"error": "Tag not found"}), 404

    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 20, min_val=1, max_val=100)

    # Get threads with this tag (exclude deleted)
    threads_query = ForumThread.query.join(
        ForumThreadTag, ForumThread.id == ForumThreadTag.thread_id
    ).filter(
        ForumThreadTag.tag_id == tag.id,
        ForumThread.status.notin_(("deleted",))
    ).order_by(ForumThread.created_at.desc())

    total = threads_query.count()
    threads = threads_query.offset((page - 1) * limit).limit(limit).all()

    return jsonify({
        "tag": {
            "id": tag.id,
            "label": tag.label,
            "slug": tag.slug,
        },
        "threads": [
            {
                "id": t.id,
                "title": t.title,
                "slug": t.slug,
                "author_id": t.author_id,
                "author_username": t.author.username if t.author else None,
                "post_count": t.reply_count,
                "view_count": t.view_count,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in threads
        ],
        "total": total,
        "page": page,
        "per_page": limit,
    }), 200
