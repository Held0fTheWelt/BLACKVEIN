"""Central feature access resolver: tier rules, prior expectations, /auth/me alignment."""

from __future__ import annotations

from app.auth.feature_access_resolver import (
    ACCESS_TIER_ADMIN,
    ACCESS_TIER_AUTHENTICATED,
    ACCESS_TIER_MODERATOR,
    FEATURE_ACCESS_RULES,
    REASON_AREA_DENIED,
    REASON_BANNED,
    REASON_INVALID_FEATURE,
    REASON_NO_USER,
    REASON_TIER_DENIED,
    REASON_TIER_MET,
    resolve_feature_access,
    user_privilege_tier,
)
from app.auth.feature_registry import (
    FEATURE_DASHBOARD_METRICS,
    FEATURE_DASHBOARD_USER_SETTINGS,
    FEATURE_IDS,
    FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE,
    FEATURE_MANAGE_GAME_OPERATIONS,
    FEATURE_MANAGE_NEWS,
    user_can_access_feature,
)
from app.extensions import db
from app.models import Area, Role, User
from werkzeug.security import generate_password_hash


def test_feature_access_rules_cover_all_registered_ids():
    assert set(FEATURE_IDS) == set(FEATURE_ACCESS_RULES)


def test_user_privilege_tier_matches_role_ladder(app):
    with app.app_context():
        admin_role = Role.query.filter_by(name=Role.NAME_ADMIN).first()
        mod_role = Role.query.filter_by(name=Role.NAME_MODERATOR).first()
        user_role = Role.query.filter_by(name=Role.NAME_USER).first()
        admin = User(username="tier-admin", password_hash=generate_password_hash("x"), role_id=admin_role.id)
        mod = User(username="tier-mod", password_hash=generate_password_hash("x"), role_id=mod_role.id)
        reg = User(username="tier-user", password_hash=generate_password_hash("x"), role_id=user_role.id)
        banned = User(
            username="tier-ban",
            password_hash=generate_password_hash("x"),
            role_id=admin_role.id,
            is_banned=True,
        )
        db.session.add_all([admin, mod, reg, banned])
        db.session.commit()
        assert user_privilege_tier(admin) == ACCESS_TIER_ADMIN
        assert user_privilege_tier(mod) == ACCESS_TIER_MODERATOR
        assert user_privilege_tier(reg) == ACCESS_TIER_AUTHENTICATED
        assert user_privilege_tier(banned) == 0


def test_resolve_feature_access_reasons(app):
    with app.app_context():
        admin_role = Role.query.filter_by(name=Role.NAME_ADMIN).first()
        mod_role = Role.query.filter_by(name=Role.NAME_MODERATOR).first()
        admin = User(username="rsn-admin", password_hash=generate_password_hash("x"), role_id=admin_role.id)
        mod = User(username="rsn-mod", password_hash=generate_password_hash("x"), role_id=mod_role.id)
        db.session.add_all([admin, mod])
        db.session.commit()

        ok, d = resolve_feature_access(None, FEATURE_MANAGE_NEWS)
        assert ok is False and d["reason"] == REASON_NO_USER

        ok, d = resolve_feature_access(admin, "not.a.feature")
        assert ok is False and d["reason"] == REASON_INVALID_FEATURE

        ok, d = resolve_feature_access(mod, FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
        assert ok is False and d["reason"] == REASON_TIER_DENIED

        ok, d = resolve_feature_access(mod, FEATURE_MANAGE_NEWS)
        assert ok is True and d["reason"] == REASON_TIER_MET

        area_game = Area.query.filter_by(slug="game").first()
        area_wiki = Area.query.filter_by(slug="wiki").first()
        from app.auth.feature_registry import set_feature_areas

        set_feature_areas(FEATURE_MANAGE_GAME_OPERATIONS, [area_game.id])
        mod.areas.append(area_wiki)
        db.session.commit()
        ok, d = resolve_feature_access(mod, FEATURE_MANAGE_GAME_OPERATIONS)
        assert ok is False and d["reason"] == REASON_AREA_DENIED


def test_user_can_access_feature_delegates_to_resolver(app):
    with app.app_context():
        admin_role = Role.query.filter_by(name=Role.NAME_ADMIN).first()
        user_role = Role.query.filter_by(name=Role.NAME_USER).first()
        admin = User(username="del-admin", password_hash=generate_password_hash("x"), role_id=admin_role.id)
        reg = User(username="del-user", password_hash=generate_password_hash("x"), role_id=user_role.id)
        db.session.add_all([admin, reg])
        db.session.commit()
        ok, detail = resolve_feature_access(reg, FEATURE_DASHBOARD_USER_SETTINGS)
        assert ok and detail["reason"] == REASON_TIER_MET
        assert user_can_access_feature(reg, FEATURE_DASHBOARD_USER_SETTINGS) is True
        assert user_can_access_feature(reg, FEATURE_DASHBOARD_METRICS) is False
        assert user_can_access_feature(admin, FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE) is True


def test_banned_user_denied_with_reason(app):
    with app.app_context():
        admin_role = Role.query.filter_by(name=Role.NAME_ADMIN).first()
        u = User(username="ban-rs", password_hash=generate_password_hash("x"), role_id=admin_role.id, is_banned=True)
        db.session.add(u)
        db.session.commit()
        ok, d = resolve_feature_access(u, FEATURE_MANAGE_NEWS)
        assert ok is False and d["reason"] == REASON_BANNED
