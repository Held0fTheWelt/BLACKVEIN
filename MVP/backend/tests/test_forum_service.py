"""Unit tests for forum_service.py — covers service-layer logic directly."""
from datetime import datetime, timedelta, timezone

import pytest

from app.extensions import db
from app.services import forum_service
from app.models import (
    ForumCategory,
    ForumThread,
    ForumPost,
    ForumPostLike,
    ForumReport,
    ForumThreadSubscription,
    Notification,
    User,
    Role,
    ForumTag,
    ForumThreadTag,
    ForumThreadBookmark,
)
from app.services.forum_service import (
    _normalize_tag_value,
    _utc_now,
    bookmark_thread,
    create_category,
    create_notifications_for_thread_reply,
    create_post,
    create_report,
    create_thread,
    delete_category,
    get_category_by_slug_for_user,
    get_or_create_tags,
    get_post_by_id,
    get_report_by_id,
    get_thread_by_id,
    get_thread_by_slug,
    hide_post,
    hide_thread,
    increment_thread_view,
    like_post,
    list_bookmarked_threads,
    list_categories_for_user,
    list_posts_for_thread,
    list_reports,
    list_reports_for_target,
    list_tags_for_thread,
    list_threads_for_category,
    merge_threads,
    move_thread,
    recalc_thread_counters,
    set_thread_archived,
    set_thread_featured,
    set_thread_lock,
    set_thread_pinned,
    set_thread_tags,
    set_thread_unarchived,
    soft_delete_post,
    soft_delete_thread,
    split_thread_from_post,
    subscribe_thread,
    unbookmark_thread,
    unhide_post,
    unlike_post,
    unsubscribe_thread,
    update_category,
    update_post,
    update_report_status,
    update_thread,
    user_can_access_category,
    user_can_create_thread,
    user_can_edit_post,
    user_can_like_post,
    user_can_moderate_category,
    user_can_post_in_thread,
    user_can_soft_delete_post,
    user_can_view_post,
    user_can_view_thread,
    user_is_admin,
    user_is_moderator,
)


@pytest.fixture(autouse=True)
def clear_forum_view_rate_limit_cache():
    """Clear the view rate-limit cache so tests do not affect each other."""
    forum_service._VIEW_RATE_LIMIT_CACHE.clear()
    yield
    forum_service._VIEW_RATE_LIMIT_CACHE.clear()


@pytest.fixture
def forum_data(app, test_user, admin_user):
    """Shared forum data (categories, threads, posts, tags) for coverage-oriented tests."""
    with app.app_context():
        user, _ = test_user
        admin, _ = admin_user

        cat_general = ForumCategory(
            slug="general",
            title="General Discussion",
            description="General discussion",
            is_active=True,
            is_private=False,
            sort_order=0,
        )
        db.session.add(cat_general)
        db.session.flush()

        cat_private = ForumCategory(
            slug="private",
            title="Private Category",
            description="Private category",
            is_active=True,
            is_private=True,
            sort_order=1,
        )
        db.session.add(cat_private)
        db.session.flush()

        thread1 = ForumThread(
            category_id=cat_general.id,
            title="Test Thread 1",
            slug="test-thread-1",
            author_id=user.id,
            created_at=datetime.now(timezone.utc),
        )
        db.session.add(thread1)
        db.session.flush()

        thread2 = ForumThread(
            category_id=cat_general.id,
            title="Test Thread 2",
            slug="test-thread-2",
            author_id=admin.id,
            created_at=datetime.now(timezone.utc) - timedelta(days=1),
            is_locked=True,
        )
        db.session.add(thread2)
        db.session.flush()

        post1 = ForumPost(
            thread_id=thread1.id,
            author_id=user.id,
            content="First post content",
            created_at=datetime.now(timezone.utc),
        )
        db.session.add(post1)
        db.session.flush()

        post2 = ForumPost(
            thread_id=thread1.id,
            author_id=admin.id,
            content="Reply to first post",
            created_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        db.session.add(post2)

        tag1 = ForumTag(label="python", slug="python")
        tag2 = ForumTag(label="javascript", slug="javascript")
        db.session.add(tag1)
        db.session.add(tag2)
        db.session.flush()

        tt1 = ForumThreadTag(thread_id=thread1.id, tag_id=tag1.id)
        tt2 = ForumThreadTag(thread_id=thread2.id, tag_id=tag2.id)
        db.session.add(tt1)
        db.session.add(tt2)

        db.session.commit()
        return {
            "user": user,
            "admin": admin,
            "cat_general": cat_general.id,
            "cat_private": cat_private.id,
            "thread1": thread1.id,
            "thread2": thread2.id,
            "post1": post1.id,
            "post2": post2.id,
            "tag1": tag1.id,
            "tag2": tag2.id,
        }


def _make_user(role_name, username, banned=False):
    """Helper to create a user with given role."""
    role = Role.query.filter_by(name=role_name).first()
    from werkzeug.security import generate_password_hash
    u = User(
        username=username,
        password_hash=generate_password_hash("Pass1234"),
        role_id=role.id,
        is_banned=banned,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _make_category(slug="test-cat", title="Test Cat", is_active=True, is_private=False, required_role=None):
    cat = ForumCategory(slug=slug, title=title, is_active=is_active, is_private=is_private, required_role=required_role)
    db.session.add(cat)
    db.session.flush()
    return cat


def _make_thread(category, slug="test-thread", title="Test Thread", status="open", author=None):
    t = ForumThread(
        category_id=category.id,
        slug=slug,
        title=title,
        status=status,
        author_id=author.id if author else None,
    )
    db.session.add(t)
    db.session.flush()
    return t


def _make_post(thread, author=None, content="Test content", status="visible", parent=None):
    p = ForumPost(
        thread_id=thread.id,
        author_id=author.id if author else None,
        content=content,
        status=status,
        parent_post_id=parent.id if parent else None,
    )
    db.session.add(p)
    db.session.flush()
    return p


# --- Permission helpers -------------------------------------------------------


class TestPermissionHelpers:

    def test_user_is_moderator_with_mod(self, app):
        with app.app_context():
            mod = _make_user(Role.NAME_MODERATOR, "perm_mod")
            db.session.commit()
            assert user_is_moderator(mod) is True

    def test_user_is_moderator_with_user(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "perm_user")
            db.session.commit()
            assert user_is_moderator(u) is False

    def test_user_is_moderator_with_none(self, app):
        with app.app_context():
            assert user_is_moderator(None) is False

    def test_user_is_admin_true(self, app):
        with app.app_context():
            a = _make_user(Role.NAME_ADMIN, "perm_admin")
            db.session.commit()
            assert user_is_admin(a) is True

    def test_user_is_admin_false(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "perm_user2")
            db.session.commit()
            assert user_is_admin(u) is False

    def test_user_can_access_category_public(self, app):
        with app.app_context():
            cat = _make_category()
            db.session.commit()
            assert user_can_access_category(None, cat) is True

    def test_user_can_access_category_private_no_user(self, app):
        with app.app_context():
            cat = _make_category(slug="priv", is_private=True)
            db.session.commit()
            assert user_can_access_category(None, cat) is False

    def test_user_can_access_category_private_mod(self, app):
        with app.app_context():
            cat = _make_category(slug="priv2", is_private=True)
            mod = _make_user(Role.NAME_MODERATOR, "access_mod")
            db.session.commit()
            assert user_can_access_category(mod, cat) is True

    def test_user_can_access_inactive_admin_only(self, app):
        with app.app_context():
            cat = _make_category(slug="inact", is_active=False)
            u = _make_user(Role.NAME_USER, "access_u")
            a = _make_user(Role.NAME_ADMIN, "access_a")
            db.session.commit()
            assert user_can_access_category(u, cat) is False
            assert user_can_access_category(a, cat) is True

    def test_user_can_access_required_role(self, app):
        with app.app_context():
            cat = _make_category(slug="rolecat", required_role=Role.NAME_MODERATOR)
            u = _make_user(Role.NAME_USER, "access_roleuser")
            mod = _make_user(Role.NAME_MODERATOR, "access_rolemod")
            db.session.commit()
            assert user_can_access_category(u, cat) is False
            assert user_can_access_category(mod, cat) is True


class TestThreadViewPermissions:

    def test_deleted_thread_hidden_from_user(self, app):
        with app.app_context():
            cat = _make_category(slug="delcat")
            t = _make_thread(cat, slug="del-thread", status="deleted")
            u = _make_user(Role.NAME_USER, "view_u")
            db.session.commit()
            assert user_can_view_thread(u, t) is False

    def test_deleted_thread_visible_to_mod(self, app):
        with app.app_context():
            cat = _make_category(slug="delcat2")
            t = _make_thread(cat, slug="del-thread2", status="deleted")
            mod = _make_user(Role.NAME_MODERATOR, "view_mod")
            db.session.commit()
            assert user_can_view_thread(mod, t) is True

    def test_hidden_thread_hidden_from_user(self, app):
        with app.app_context():
            cat = _make_category(slug="hcat")
            t = _make_thread(cat, slug="h-thread", status="hidden")
            u = _make_user(Role.NAME_USER, "view_h")
            db.session.commit()
            assert user_can_view_thread(u, t) is False

    def test_archived_thread_hidden_from_user(self, app):
        with app.app_context():
            cat = _make_category(slug="archcat")
            t = _make_thread(cat, slug="arch-thread", status="archived")
            u = _make_user(Role.NAME_USER, "view_arch")
            db.session.commit()
            assert user_can_view_thread(u, t) is False


class TestPostPermissions:

    def test_view_post_visible(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "vp_user")
            cat = _make_category(slug="vpcat")
            t = _make_thread(cat, slug="vp-t", author=u)
            p = _make_post(t, author=u)
            db.session.commit()
            assert user_can_view_post(u, p) is True

    def test_view_deleted_post_user_no(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "vdp_user")
            cat = _make_category(slug="vdpcat")
            t = _make_thread(cat, slug="vdp-t", author=u)
            p = _make_post(t, author=u, status="deleted")
            db.session.commit()
            assert user_can_view_post(u, p) is False

    def test_view_hidden_post_mod_yes(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "vhp_user")
            mod = _make_user(Role.NAME_MODERATOR, "vhp_mod")
            cat = _make_category(slug="vhpcat")
            t = _make_thread(cat, slug="vhp-t", author=u)
            p = _make_post(t, author=u, status="hidden")
            db.session.commit()
            assert user_can_view_post(mod, p) is True

    def test_can_edit_own_post(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "ep_user")
            cat = _make_category(slug="epcat")
            t = _make_thread(cat, slug="ep-t", author=u)
            p = _make_post(t, author=u)
            db.session.commit()
            assert user_can_edit_post(u, p) is True

    def test_cannot_edit_hidden_own_post(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "ehp_user")
            cat = _make_category(slug="ehpcat")
            t = _make_thread(cat, slug="ehp-t", author=u)
            p = _make_post(t, author=u, status="hidden")
            db.session.commit()
            assert user_can_edit_post(u, p) is False

    def test_banned_user_cannot_edit(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "bep_user", banned=True)
            cat = _make_category(slug="bepcat")
            t = _make_thread(cat, slug="bep-t")
            p = _make_post(t, author=u)
            db.session.commit()
            assert user_can_edit_post(u, p) is False

    def test_can_soft_delete_own(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "sd_user")
            cat = _make_category(slug="sdcat")
            t = _make_thread(cat, slug="sd-t", author=u)
            p = _make_post(t, author=u)
            db.session.commit()
            assert user_can_soft_delete_post(u, p) is True

    def test_cannot_soft_delete_others(self, app):
        with app.app_context():
            u1 = _make_user(Role.NAME_USER, "sd_u1")
            u2 = _make_user(Role.NAME_USER, "sd_u2")
            cat = _make_category(slug="sd2cat")
            t = _make_thread(cat, slug="sd2-t", author=u1)
            p = _make_post(t, author=u1)
            db.session.commit()
            assert user_can_soft_delete_post(u2, p) is False

    def test_like_post_requires_visibility(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "lp_user")
            cat = _make_category(slug="lpcat", is_private=True)
            t = _make_thread(cat, slug="lp-t")
            p = _make_post(t, content="secret")
            db.session.commit()
            assert user_can_like_post(u, p) is False

    def test_like_post_locked_thread(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "lpl_user")
            cat = _make_category(slug="lplcat")
            t = _make_thread(cat, slug="lpl-t", author=u)
            t.is_locked = True
            t.status = "locked"
            p = _make_post(t, author=u)
            db.session.commit()
            assert user_can_like_post(u, p) is False

    def test_like_hidden_post_no(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "lph_user")
            cat = _make_category(slug="lphcat")
            t = _make_thread(cat, slug="lph-t", author=u)
            p = _make_post(t, author=u, status="hidden")
            db.session.commit()
            assert user_can_like_post(u, p) is False

    def test_banned_user_cannot_like(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "blp_user", banned=True)
            cat = _make_category(slug="blpcat")
            t = _make_thread(cat, slug="blp-t")
            p = _make_post(t, content="x")
            db.session.commit()
            assert user_can_like_post(u, p) is False

    def test_moderate_category_user_no(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "mc_user")
            cat = _make_category(slug="mccat")
            db.session.commit()
            assert user_can_moderate_category(u, cat) is False

    def test_moderate_category_mod_yes(self, app):
        with app.app_context():
            mod = _make_user(Role.NAME_MODERATOR, "mc_mod")
            cat = _make_category(slug="mc2cat")
            # Moderators must be explicitly assigned to categories
            from app.models.forum import ModeratorAssignment
            assignment = ModeratorAssignment(user_id=mod.id, category_id=cat.id)
            db.session.add(assignment)
            db.session.commit()
            assert user_can_moderate_category(mod, cat) is True


# --- Category operations -------------------------------------------------------


class TestCategoryOperations:

    def test_list_categories_public(self, app):
        with app.app_context():
            _make_category(slug="lc1")
            _make_category(slug="lc2")
            db.session.commit()
            cats = list_categories_for_user(None)
            slugs = {c.slug for c in cats}
            assert "lc1" in slugs
            assert "lc2" in slugs

    def test_get_category_by_slug(self, app):
        with app.app_context():
            _make_category(slug="gs1")
            db.session.commit()
            cat = get_category_by_slug_for_user(None, "gs1")
            assert cat is not None
            assert cat.slug == "gs1"

    def test_get_category_private_no_user(self, app):
        with app.app_context():
            _make_category(slug="gs_priv", is_private=True)
            db.session.commit()
            cat = get_category_by_slug_for_user(None, "gs_priv")
            assert cat is None

    def test_create_category_success(self, app):
        with app.app_context():
            cat, err = create_category(
                slug="new-cat", title="New Cat", description="desc",
                parent_id=None, sort_order=0, is_active=True, is_private=False, required_role=None,
            )
            assert err is None
            assert cat.slug == "new-cat"

    def test_create_category_missing_slug(self, app):
        with app.app_context():
            cat, err = create_category(
                slug="", title="NoSlug", description=None,
                parent_id=None, sort_order=0, is_active=True, is_private=False, required_role=None,
            )
            assert err is not None

    def test_update_category(self, app):
        with app.app_context():
            cat = _make_category(slug="upcat")
            db.session.commit()
            cat = update_category(cat, title="Updated Title")
            assert cat.title == "Updated Title"

    def test_delete_category(self, app):
        with app.app_context():
            cat = _make_category(slug="delcat3")
            db.session.commit()
            cat_id = cat.id
            delete_category(cat)
            assert ForumCategory.query.get(cat_id) is None


# --- Thread operations -------------------------------------------------------


class TestThreadOperations:

    def test_create_thread_success(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "ct_user")
            cat = _make_category(slug="ctcat")
            db.session.commit()
            thread, post, err = create_thread(
                category=cat, author_id=u.id, title="My Thread", content="Hello World",
            )
            assert err is None
            assert thread is not None
            assert post is not None
            assert thread.title == "My Thread"
            assert post.content == "Hello World"

    def test_create_thread_empty_title(self, app):
        with app.app_context():
            cat = _make_category(slug="ctcat2")
            db.session.commit()
            thread, post, err = create_thread(
                category=cat, author_id=None, title="", content="body",
            )
            assert err is not None
            assert thread is None

    def test_create_thread_empty_content(self, app):
        with app.app_context():
            cat = _make_category(slug="ctcat3")
            db.session.commit()
            thread, post, err = create_thread(
                category=cat, author_id=None, title="Title", content="",
            )
            assert err is not None

    def test_list_threads_for_category(self, app):
        with app.app_context():
            cat = _make_category(slug="ltcat")
            _make_thread(cat, slug="lt1", title="Thread 1")
            _make_thread(cat, slug="lt2", title="Thread 2")
            _make_thread(cat, slug="lt3", title="Thread 3", status="deleted")
            db.session.commit()
            items, total = list_threads_for_category(cat)
            assert total == 2  # deleted excluded
            assert len(items) == 2

    def test_list_threads_include_hidden(self, app):
        with app.app_context():
            cat = _make_category(slug="lthcat")
            _make_thread(cat, slug="lth1", title="Open Thread")
            _make_thread(cat, slug="lth2", title="Hidden Thread", status="hidden")
            _make_thread(cat, slug="lth3", title="Archived Thread", status="archived")
            db.session.commit()
            items, total = list_threads_for_category(cat, include_hidden=False)
            assert total == 1  # only open
            items2, total2 = list_threads_for_category(cat, include_hidden=True)
            assert total2 == 3  # open + hidden + archived

    def test_get_thread_by_slug(self, app):
        with app.app_context():
            cat = _make_category(slug="gscat")
            _make_thread(cat, slug="gs-thread", title="GS Thread")
            db.session.commit()
            t = get_thread_by_slug("gs-thread")
            assert t is not None and t.title == "GS Thread"

    def test_get_thread_by_id(self, app):
        with app.app_context():
            cat = _make_category(slug="gicat")
            t = _make_thread(cat, slug="gi-thread", title="GI Thread")
            db.session.commit()
            fetched = get_thread_by_id(t.id)
            assert fetched is not None and fetched.id == t.id

    def test_update_thread_title(self, app):
        with app.app_context():
            cat = _make_category(slug="utcat")
            t = _make_thread(cat, slug="ut-thread")
            db.session.commit()
            t = update_thread(t, title="New Title")
            assert t.title == "New Title"

    def test_soft_delete_thread(self, app):
        with app.app_context():
            cat = _make_category(slug="sdtcat")
            t = _make_thread(cat, slug="sdt-thread")
            db.session.commit()
            t = soft_delete_thread(t)
            assert t.status == "deleted"
            assert t.deleted_at is not None

    def test_hide_thread(self, app):
        with app.app_context():
            cat = _make_category(slug="htcat")
            t = _make_thread(cat, slug="ht-thread")
            db.session.commit()
            t = hide_thread(t)
            assert t.status == "hidden"

    def test_lock_unlock(self, app):
        with app.app_context():
            cat = _make_category(slug="lucat")
            t = _make_thread(cat, slug="lu-thread")
            db.session.commit()
            t = set_thread_lock(t, True)
            assert t.is_locked is True
            assert t.status == "locked"
            t = set_thread_lock(t, False)
            assert t.is_locked is False
            assert t.status == "open"

    def test_pin_unpin(self, app):
        with app.app_context():
            cat = _make_category(slug="ppcat")
            t = _make_thread(cat, slug="pp-thread")
            db.session.commit()
            t = set_thread_pinned(t, True)
            assert t.is_pinned is True
            t = set_thread_pinned(t, False)
            assert t.is_pinned is False

    def test_feature_unfeature(self, app):
        with app.app_context():
            cat = _make_category(slug="ffcat")
            t = _make_thread(cat, slug="ff-thread")
            db.session.commit()
            t = set_thread_featured(t, True)
            assert t.is_featured is True
            t = set_thread_featured(t, False)
            assert t.is_featured is False

    def test_archive_unarchive(self, app):
        with app.app_context():
            cat = _make_category(slug="aucat")
            t = _make_thread(cat, slug="au-thread")
            db.session.commit()
            t = set_thread_archived(t)
            assert t.status == "archived"
            t = set_thread_unarchived(t)
            assert t.status == "open"

    def test_unarchive_non_archived_noop(self, app):
        with app.app_context():
            cat = _make_category(slug="unacat")
            t = _make_thread(cat, slug="una-thread", status="open")
            db.session.commit()
            t = set_thread_unarchived(t)
            assert t.status == "open"

    def test_move_thread(self, app):
        with app.app_context():
            cat1 = _make_category(slug="mvcat1")
            cat2 = _make_category(slug="mvcat2")
            t = _make_thread(cat1, slug="mv-thread")
            db.session.commit()
            t, err = move_thread(t, cat2)
            assert err is None
            assert t.category_id == cat2.id

    def test_move_thread_to_inactive(self, app):
        with app.app_context():
            cat1 = _make_category(slug="mvcat3")
            cat2 = _make_category(slug="mvcat4", is_active=False)
            t = _make_thread(cat1, slug="mv-thread2")
            db.session.commit()
            t, err = move_thread(t, cat2)
            assert err is not None

    def test_move_thread_same_category(self, app):
        with app.app_context():
            cat = _make_category(slug="mvcat5")
            t = _make_thread(cat, slug="mv-thread3")
            db.session.commit()
            t, err = move_thread(t, cat)
            assert err is None  # no-op

    def test_increment_view(self, app):
        with app.app_context():
            cat = _make_category(slug="ivcat")
            t = _make_thread(cat, slug="iv-thread")
            db.session.commit()
            assert t.view_count == 0
            increment_thread_view(t)
            assert t.view_count == 1

    def test_recalc_counters(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "rc_user")
            cat = _make_category(slug="rccat")
            t = _make_thread(cat, slug="rc-thread", author=u)
            p1 = _make_post(t, author=u, content="first")
            p2 = _make_post(t, author=u, content="second")
            db.session.commit()
            recalc_thread_counters(t)
            assert t.reply_count == 1  # 2 posts - 1
            assert t.last_post_id == p2.id


# --- Post operations ---------------------------------------------------------


class TestPostOperations:

    def test_create_post_success(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "cp_user")
            cat = _make_category(slug="cpcat")
            t = _make_thread(cat, slug="cp-thread", author=u)
            db.session.commit()
            post, err = create_post(thread=t, author_id=u.id, content="My post")
            assert err is None
            assert post is not None
            assert post.content == "My post"
            assert t.reply_count == 1

    def test_create_post_empty_content(self, app):
        with app.app_context():
            cat = _make_category(slug="cpcat2")
            t = _make_thread(cat, slug="cp-thread2")
            db.session.commit()
            post, err = create_post(thread=t, author_id=None, content="")
            assert err is not None
            assert post is None

    def test_create_post_with_parent(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "cpp_user")
            cat = _make_category(slug="cppcat")
            t = _make_thread(cat, slug="cpp-thread", author=u)
            parent = _make_post(t, author=u, content="parent")
            db.session.commit()
            reply, err = create_post(thread=t, author_id=u.id, content="reply", parent_post_id=parent.id)
            assert err is None
            assert reply.parent_post_id == parent.id

    def test_create_post_nested_reply_rejected(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "cpn_user")
            cat = _make_category(slug="cpncat")
            t = _make_thread(cat, slug="cpn-thread", author=u)
            parent = _make_post(t, author=u, content="parent")
            db.session.commit()
            reply, _ = create_post(thread=t, author_id=u.id, content="reply", parent_post_id=parent.id)
            nested, err = create_post(thread=t, author_id=u.id, content="nested", parent_post_id=reply.id)
            assert err is not None
            assert "depth" in err.lower()

    def test_create_post_parent_wrong_thread(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "cpw_user")
            cat = _make_category(slug="cpwcat")
            t1 = _make_thread(cat, slug="cpw-t1", author=u)
            t2 = _make_thread(cat, slug="cpw-t2", author=u)
            parent = _make_post(t1, author=u, content="parent")
            db.session.commit()
            _, err = create_post(thread=t2, author_id=u.id, content="reply", parent_post_id=parent.id)
            assert err is not None

    def test_create_post_parent_hidden(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "cph_user")
            cat = _make_category(slug="cphcat")
            t = _make_thread(cat, slug="cph-thread", author=u)
            parent = _make_post(t, author=u, content="parent", status="hidden")
            db.session.commit()
            _, err = create_post(thread=t, author_id=u.id, content="reply", parent_post_id=parent.id)
            assert err is not None

    def test_update_post(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "up_user")
            cat = _make_category(slug="upcat2")
            t = _make_thread(cat, slug="up-thread", author=u)
            p = _make_post(t, author=u, content="original")
            db.session.commit()
            p = update_post(p, content="updated", editor_id=u.id)
            assert p.content == "updated"
            assert p.edited_by == u.id

    def test_soft_delete_post(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "sdp_user")
            cat = _make_category(slug="sdpcat")
            t = _make_thread(cat, slug="sdp-thread", author=u)
            p = _make_post(t, author=u, content="deleteme")
            db.session.commit()
            p = soft_delete_post(p)
            assert p.status == "deleted"

    def test_hide_unhide_post(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "hup_user")
            cat = _make_category(slug="hupcat")
            t = _make_thread(cat, slug="hup-thread", author=u)
            p = _make_post(t, author=u, content="hideme")
            db.session.commit()
            p = hide_post(p)
            assert p.status == "hidden"
            p = unhide_post(p)
            assert p.status == "visible"

    def test_list_posts_for_thread(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "lp_user2")
            cat = _make_category(slug="lpcat2")
            t = _make_thread(cat, slug="lp-thread2", author=u)
            _make_post(t, author=u, content="p1")
            _make_post(t, author=u, content="p2")
            _make_post(t, author=u, content="p3", status="hidden")
            db.session.commit()
            items, total = list_posts_for_thread(t)
            assert total == 2  # hidden excluded
            items2, total2 = list_posts_for_thread(t, include_hidden=True)
            assert total2 == 3

    def test_get_post_by_id(self, app):
        with app.app_context():
            cat = _make_category(slug="gpcat")
            t = _make_thread(cat, slug="gp-thread")
            p = _make_post(t, content="findme")
            db.session.commit()
            fetched = get_post_by_id(p.id)
            assert fetched is not None


# --- Like/Unlike operations --------------------------------------------------


class TestLikeOperations:

    def test_like_post(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "like_user")
            cat = _make_category(slug="likecat")
            t = _make_thread(cat, slug="like-thread", author=u)
            p = _make_post(t, author=u, content="likeable", status="visible")
            p.like_count = 0
            db.session.commit()
            like, err = like_post(u, p)
            assert err is None
            assert like is not None
            assert p.like_count == 1

    def test_like_post_duplicate(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "like_dup_user")
            cat = _make_category(slug="likedupcat")
            t = _make_thread(cat, slug="likedup-thread", author=u)
            p = _make_post(t, author=u, content="likeable2", status="visible")
            p.like_count = 0
            db.session.commit()
            like1, _ = like_post(u, p)
            like2, _ = like_post(u, p)
            assert like1.id == like2.id
            assert p.like_count == 1  # not incremented twice

    def test_unlike_post(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "unlike_user")
            cat = _make_category(slug="unlikecat")
            t = _make_thread(cat, slug="unlike-thread", author=u)
            p = _make_post(t, author=u, content="unlikeable", status="visible")
            p.like_count = 0
            db.session.commit()
            like_post(u, p)
            assert p.like_count == 1
            unlike_post(u, p)
            assert p.like_count == 0

    def test_unlike_nonexistent(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "unlike_ne_user")
            cat = _make_category(slug="unlikenecat")
            t = _make_thread(cat, slug="unlikene-thread", author=u)
            p = _make_post(t, author=u, content="x", status="visible")
            p.like_count = 0
            db.session.commit()
            unlike_post(u, p)  # no-op, no error
            assert p.like_count == 0


# --- Subscribe/Unsubscribe ---------------------------------------------------


class TestSubscriptionOperations:

    def test_subscribe_and_unsubscribe(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "sub_user")
            cat = _make_category(slug="subcat")
            t = _make_thread(cat, slug="sub-thread", author=u)
            db.session.commit()
            sub = subscribe_thread(u, t)
            assert sub is not None
            # Subscribe again returns same
            sub2 = subscribe_thread(u, t)
            assert sub2.id == sub.id
            unsubscribe_thread(u, t)
            remaining = ForumThreadSubscription.query.filter_by(thread_id=t.id, user_id=u.id).first()
            assert remaining is None

    def test_unsubscribe_nonexistent(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "unsub_user")
            cat = _make_category(slug="unsubcat")
            t = _make_thread(cat, slug="unsub-thread", author=u)
            db.session.commit()
            unsubscribe_thread(u, t)  # no-op


# --- Bookmark operations -----------------------------------------------------


class TestBookmarkOperations:

    def test_bookmark_and_unbookmark(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "bm_user")
            cat = _make_category(slug="bmcat")
            t = _make_thread(cat, slug="bm-thread", author=u)
            db.session.commit()
            bm = bookmark_thread(u, t)
            assert bm is not None
            # Bookmark again returns same
            bm2 = bookmark_thread(u, t)
            assert bm2.id == bm.id
            unbookmark_thread(u, t)
            remaining = ForumThreadBookmark.query.filter_by(thread_id=t.id, user_id=u.id).first()
            assert remaining is None

    def test_unbookmark_nonexistent(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "unbm_user")
            cat = _make_category(slug="unbmcat")
            t = _make_thread(cat, slug="unbm-thread", author=u)
            db.session.commit()
            unbookmark_thread(u, t)  # no-op

    def test_list_bookmarked_threads(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "lbm_user")
            cat = _make_category(slug="lbmcat")
            t1 = _make_thread(cat, slug="lbm-t1", author=u)
            t2 = _make_thread(cat, slug="lbm-t2", author=u)
            db.session.commit()
            bookmark_thread(u, t1)
            bookmark_thread(u, t2)
            items, total = list_bookmarked_threads(u)
            assert total == 2
            assert len(items) == 2


# --- Report operations -------------------------------------------------------


class TestReportOperations:

    def test_create_report(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "rpt_user")
            cat = _make_category(slug="rptcat")
            t = _make_thread(cat, slug="rpt-thread", author=u)
            db.session.commit()
            report, err = create_report(
                target_type="thread", target_id=t.id, reported_by=u.id, reason="Spam",
            )
            assert err is None
            assert report.status == "open"

    def test_create_report_invalid_type(self, app):
        with app.app_context():
            report, err = create_report(
                target_type="invalid", target_id=1, reported_by=None, reason="Bad",
            )
            assert err is not None

    def test_create_report_empty_reason(self, app):
        with app.app_context():
            report, err = create_report(
                target_type="thread", target_id=1, reported_by=None, reason="",
            )
            assert err is not None

    def test_list_reports_with_filters(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "lr_user")
            cat = _make_category(slug="lrcat")
            t = _make_thread(cat, slug="lr-thread", author=u)
            db.session.commit()
            create_report(target_type="thread", target_id=t.id, reported_by=u.id, reason="R1")
            create_report(target_type="post", target_id=1, reported_by=u.id, reason="R2")
            items, total = list_reports()
            assert total >= 2
            items_t, total_t = list_reports(target_type="thread")
            assert total_t >= 1

    def test_update_report_status(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "urs_user")
            mod = _make_user(Role.NAME_MODERATOR, "urs_mod")
            cat = _make_category(slug="urscat")
            t = _make_thread(cat, slug="urs-thread", author=u)
            db.session.commit()
            report, _ = create_report(target_type="thread", target_id=t.id, reported_by=u.id, reason="test")
            report = update_report_status(report, status="resolved", handled_by=mod.id, resolution_note="Fixed")
            assert report.status == "resolved"
            assert report.resolution_note == "Fixed"

    def test_update_report_invalid_status(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "uri_user")
            cat = _make_category(slug="uricat")
            t = _make_thread(cat, slug="uri-thread", author=u)
            db.session.commit()
            report, _ = create_report(target_type="thread", target_id=t.id, reported_by=u.id, reason="test")
            with pytest.raises(ValueError):
                update_report_status(report, status="bogus", handled_by=None)

    def test_get_report_by_id(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "gri_user")
            cat = _make_category(slug="gricat")
            t = _make_thread(cat, slug="gri-thread", author=u)
            db.session.commit()
            report, _ = create_report(target_type="thread", target_id=t.id, reported_by=u.id, reason="test")
            fetched = get_report_by_id(report.id)
            assert fetched is not None

    def test_list_reports_for_target(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "lrt_user")
            cat = _make_category(slug="lrtcat")
            t = _make_thread(cat, slug="lrt-thread", author=u)
            db.session.commit()
            create_report(target_type="thread", target_id=t.id, reported_by=u.id, reason="r1")
            create_report(target_type="thread", target_id=t.id, reported_by=u.id, reason="r2")
            reports = list_reports_for_target("thread", t.id)
            assert len(reports) == 2


# --- Tag operations -----------------------------------------------------------


class TestTagOperations:

    def test_normalize_tag_normal(self, app):
        with app.app_context():
            assert _normalize_tag_value("Hello World") == "hello-world"

    def test_normalize_tag_empty(self, app):
        with app.app_context():
            assert _normalize_tag_value("") is None

    def test_normalize_tag_none(self, app):
        with app.app_context():
            assert _normalize_tag_value(None) is None

    def test_normalize_tag_special_chars(self, app):
        with app.app_context():
            result = _normalize_tag_value("  @#$  ")
            assert result is None  # only special chars normalize to empty

    def test_normalize_tag_unicode(self, app):
        with app.app_context():
            result = _normalize_tag_value("cafetería")
            assert result is not None  # some part remains after normalization

    def test_normalize_tag_whitespace_only(self, app):
        with app.app_context():
            assert _normalize_tag_value("   ") is None

    def test_get_or_create_tags(self, app):
        with app.app_context():
            tags = get_or_create_tags(["Feature", "Bug"])
            assert len(tags) == 2
            slugs = {t.slug for t in tags}
            assert "feature" in slugs
            assert "bug" in slugs

    def test_get_or_create_tags_empty(self, app):
        with app.app_context():
            tags = get_or_create_tags([])
            assert tags == []

    def test_get_or_create_tags_invalid(self, app):
        with app.app_context():
            tags = get_or_create_tags(["@#$"])
            assert tags == []

    def test_set_thread_tags(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "stt_user")
            cat = _make_category(slug="sttcat")
            t = _make_thread(cat, slug="stt-thread", author=u)
            db.session.commit()
            result = set_thread_tags(t, tags=["Alpha", "Beta"])
            assert len(result) == 2
            # Replace tags
            result2 = set_thread_tags(t, tags=["Gamma"])
            assert len(result2) == 1

    def test_list_tags_for_thread(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "ltt_user")
            cat = _make_category(slug="lttcat")
            t = _make_thread(cat, slug="ltt-thread", author=u)
            db.session.commit()
            set_thread_tags(t, tags=["X", "Y"])
            tags = list_tags_for_thread(t)
            assert len(tags) == 2


# --- Merge / Split -----------------------------------------------------------


class TestMergeSplit:

    def test_merge_threads(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "mg_user")
            cat = _make_category(slug="mgcat")
            source = _make_thread(cat, slug="mg-source", author=u)
            target = _make_thread(cat, slug="mg-target", author=u)
            _make_post(source, author=u, content="sp1")
            _make_post(source, author=u, content="sp2")
            _make_post(target, author=u, content="tp1")
            db.session.commit()
            err = merge_threads(source, target)
            assert err is None
            # Posts moved
            source_posts = ForumPost.query.filter_by(thread_id=source.id).all()
            target_posts = ForumPost.query.filter_by(thread_id=target.id).all()
            assert len(source_posts) == 0
            assert len(target_posts) == 3

    def test_split_thread(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "sp_user")
            cat = _make_category(slug="spcat")
            source = _make_thread(cat, slug="sp-source", author=u)
            root = _make_post(source, author=u, content="Root")
            reply = _make_post(source, author=u, content="Reply", parent=root)
            other = _make_post(source, author=u, content="Other")
            db.session.commit()
            root_id = root.id
            reply_id = reply.id
            other_id = other.id

            new_thread, err = split_thread_from_post(
                source_thread=source, root_post=root, new_title="Split",
            )
            assert err is None
            assert new_thread is not None
            # Check post assignment
            root_p = ForumPost.query.get(root_id)
            reply_p = ForumPost.query.get(reply_id)
            other_p = ForumPost.query.get(other_id)
            assert root_p.thread_id == new_thread.id
            assert reply_p.thread_id == new_thread.id
            assert other_p.thread_id == source.id

    def test_split_non_top_level_rejected(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "spnt_user")
            cat = _make_category(slug="spntcat")
            source = _make_thread(cat, slug="spnt-source", author=u)
            root = _make_post(source, author=u, content="Root")
            reply = _make_post(source, author=u, content="Reply", parent=root)
            db.session.commit()
            _, err = split_thread_from_post(
                source_thread=source, root_post=reply, new_title="Bad Split",
            )
            assert err is not None
            assert "top-level" in err.lower()

    def test_split_wrong_thread(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "spwt_user")
            cat = _make_category(slug="spwtcat")
            t1 = _make_thread(cat, slug="spwt-t1", author=u)
            t2 = _make_thread(cat, slug="spwt-t2", author=u)
            p = _make_post(t2, author=u, content="Post in t2")
            db.session.commit()
            _, err = split_thread_from_post(
                source_thread=t1, root_post=p, new_title="Bad",
            )
            assert err is not None

    def test_split_empty_title(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "spet_user")
            cat = _make_category(slug="spetcat")
            source = _make_thread(cat, slug="spet-source", author=u)
            root = _make_post(source, author=u, content="Root")
            db.session.commit()
            _, err = split_thread_from_post(
                source_thread=source, root_post=root, new_title="",
            )
            assert err is not None


# --- Notification helpers -----------------------------------------------------


class TestNotifications:

    def test_create_notifications_for_thread_reply(self, app):
        with app.app_context():
            u1 = _make_user(Role.NAME_USER, "notif_u1")
            u2 = _make_user(Role.NAME_USER, "notif_u2")
            cat = _make_category(slug="notifcat")
            t = _make_thread(cat, slug="notif-thread", author=u1)
            db.session.commit()
            subscribe_thread(u1, t)
            subscribe_thread(u2, t)
            post, _ = create_post(thread=t, author_id=u1.id, content="reply")
            create_notifications_for_thread_reply(t, post, u1.id)
            # u1 is author, should not get notification; u2 should
            notifs = Notification.query.filter_by(user_id=u2.id).all()
            assert len(notifs) >= 1
            notifs_u1 = Notification.query.filter_by(user_id=u1.id, event_type="thread_reply").all()
            assert len(notifs_u1) == 0


# --- Can create/post permissions -----------------------------------------------


class TestCanCreatePost:

    def test_user_can_create_thread(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "cct_user")
            cat = _make_category(slug="cctcat")
            db.session.commit()
            assert user_can_create_thread(u, cat) is True

    def test_banned_user_cannot_create_thread(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "cctb_user", banned=True)
            cat = _make_category(slug="cctbcat")
            db.session.commit()
            assert user_can_create_thread(u, cat) is False

    def test_anon_cannot_create_thread(self, app):
        with app.app_context():
            cat = _make_category(slug="ccta_cat")
            db.session.commit()
            assert user_can_create_thread(None, cat) is False

    def test_user_can_post_in_thread(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "cpt_user")
            cat = _make_category(slug="cptcat")
            t = _make_thread(cat, slug="cpt-thread", author=u)
            db.session.commit()
            assert user_can_post_in_thread(u, t) is True

    def test_user_cannot_post_in_locked_thread(self, app):
        with app.app_context():
            u = _make_user(Role.NAME_USER, "cplt_user")
            cat = _make_category(slug="cpltcat")
            t = _make_thread(cat, slug="cplt-thread", author=u)
            t.is_locked = True
            db.session.commit()
            assert user_can_post_in_thread(u, t) is False

    def test_mod_can_post_in_locked_thread(self, app):
        with app.app_context():
            mod = _make_user(Role.NAME_MODERATOR, "cpmlt_mod")
            cat = _make_category(slug="cpmltcat")
            t = _make_thread(cat, slug="cpmlt-thread")
            t.is_locked = True
            db.session.commit()
            assert user_can_post_in_thread(mod, t) is True


class TestForumServiceForumDataPermissions:
    """Test permission checking functions."""

    def test_user_is_moderator_with_moderator(self, app, moderator_user):
        """user_is_moderator returns True for moderators."""
        with app.app_context():
            user, _ = moderator_user
            assert forum_service.user_is_moderator(user) is True

    def test_user_is_moderator_with_admin(self, app, admin_user):
        """user_is_moderator returns True for admins."""
        with app.app_context():
            user, _ = admin_user
            assert forum_service.user_is_moderator(user) is True

    def test_user_is_moderator_with_regular_user(self, app, test_user):
        """user_is_moderator returns False for regular users."""
        with app.app_context():
            user, _ = test_user
            assert forum_service.user_is_moderator(user) is False

    def test_user_is_moderator_with_none(self):
        """user_is_moderator returns False for None."""
        assert forum_service.user_is_moderator(None) is False

    def test_user_is_admin_with_admin(self, app, admin_user):
        """user_is_admin returns True for admins."""
        with app.app_context():
            user, _ = admin_user
            assert forum_service.user_is_admin(user) is True

    def test_user_is_admin_with_regular_user(self, app, test_user):
        """user_is_admin returns False for regular users."""
        with app.app_context():
            user, _ = test_user
            assert forum_service.user_is_admin(user) is False

    def test_user_role_rank_none(self):
        """_user_role_rank returns 0 for None user."""
        rank = forum_service._user_role_rank(None)
        assert rank == 0


class TestForumServiceForumDataCategoryAccess:
    """Test category access control."""

    def test_list_categories_for_user(self, app, test_user, forum_data):
        """list_categories_for_user returns accessible categories."""
        with app.app_context():
            user, _ = test_user
            categories = forum_service.list_categories_for_user(user)
            assert isinstance(categories, list)
            assert len(categories) > 0

    def test_get_category_by_slug_for_user(self, app, test_user, forum_data):
        """get_category_by_slug_for_user returns category by slug."""
        with app.app_context():
            user, _ = test_user
            cat = forum_service.get_category_by_slug_for_user(user, "general")
            assert cat is not None
            assert cat.slug == "general"

    def test_user_can_access_public_category(self, app, test_user, forum_data):
        """user_can_access_category returns True for public categories."""
        with app.app_context():
            user, _ = test_user
            cat = ForumCategory.query.filter_by(slug="general").first()
            assert forum_service.user_can_access_category(user, cat) is True

    def test_user_can_access_private_category_as_admin(self, app, admin_user, forum_data):
        """user_can_access_category returns True for admins on private categories."""
        with app.app_context():
            user, _ = admin_user
            cat = ForumCategory.query.filter_by(slug="private").first()
            assert forum_service.user_can_access_category(user, cat) is True


class TestForumServiceForumDataThreads:
    """Test thread creation and management."""

    def test_create_thread_success(self, app, test_user, forum_data):
        """create_thread creates a thread successfully."""
        with app.app_context():
            user, _ = test_user
            cat = ForumCategory.query.get(forum_data["cat_general"])

            thread, post, error = forum_service.create_thread(
                category=cat,
                author_id=user.id,
                title="New Test Thread",
                content="This is the initial post"
            )

            assert error is None
            assert thread is not None
            assert post is not None
            assert thread.title == "New Test Thread"

    def test_create_thread_missing_title(self, app, test_user, forum_data):
        """create_thread fails with empty title."""
        with app.app_context():
            user, _ = test_user
            cat = ForumCategory.query.get(forum_data["cat_general"])

            thread, post, error = forum_service.create_thread(
                category=cat,
                author_id=user.id,
                title="",
                content="This is the initial post"
            )

            assert error is not None
            assert thread is None

    def test_normalize_slug(self):
        """_normalize_slug converts text to URL-friendly slug."""
        result = forum_service._normalize_slug("Hello World Test")
        assert isinstance(result, str)
        assert result.lower() == result

    def test_update_thread_title(self, app, forum_data):
        """update_thread updates thread title."""
        with app.app_context():
            thread = ForumThread.query.get(forum_data["thread1"])
            updated = forum_service.update_thread(thread, title="Updated Title")

            assert updated.title == "Updated Title"

    def test_soft_delete_thread(self, app, forum_data):
        """soft_delete_thread marks thread as deleted."""
        with app.app_context():
            thread = ForumThread.query.get(forum_data["thread1"])
            updated = forum_service.soft_delete_thread(thread)

            assert updated.deleted_at is not None

    def test_hide_thread(self, app, forum_data):
        """hide_thread sets status to hidden."""
        with app.app_context():
            thread = ForumThread.query.get(forum_data["thread1"])
            updated = forum_service.hide_thread(thread)

            assert updated.status == "hidden"

    def test_unhide_thread(self, app, forum_data):
        """unhide_thread restores thread visibility."""
        with app.app_context():
            thread = ForumThread.query.get(forum_data["thread1"])
            forum_service.hide_thread(thread)
            updated = forum_service.unhide_thread(thread)

            assert updated.status != "hidden"

    def test_set_thread_lock(self, app, forum_data):
        """set_thread_lock locks/unlocks a thread."""
        with app.app_context():
            thread = ForumThread.query.get(forum_data["thread1"])

            locked = forum_service.set_thread_lock(thread, True)
            assert locked.is_locked is True

            unlocked = forum_service.set_thread_lock(thread, False)
            assert unlocked.is_locked is False

    def test_set_thread_pinned(self, app, forum_data):
        """set_thread_pinned pins/unpins a thread."""
        with app.app_context():
            thread = ForumThread.query.get(forum_data["thread1"])

            pinned = forum_service.set_thread_pinned(thread, True)
            assert pinned.is_pinned is True

    def test_set_thread_featured(self, app, forum_data):
        """set_thread_featured features/unfeatures a thread."""
        with app.app_context():
            thread = ForumThread.query.get(forum_data["thread1"])

            featured = forum_service.set_thread_featured(thread, True)
            assert featured.is_featured is True

    def test_set_thread_archived(self, app, forum_data):
        """set_thread_archived archives a thread."""
        with app.app_context():
            thread = ForumThread.query.get(forum_data["thread1"])
            archived = forum_service.set_thread_archived(thread)

            assert archived.status == "archived"

    def test_increment_thread_view(self, app, forum_data):
        """increment_thread_view increases view count for anonymous users."""
        with app.app_context():
            thread = ForumThread.query.get(forum_data["thread1"])
            initial_views = thread.view_count or 0

            result = forum_service.increment_thread_view(thread, user_id=None)

            assert result is True
            updated = ForumThread.query.get(forum_data["thread1"])
            assert (updated.view_count or 0) > initial_views

    def test_increment_thread_view_rate_limit(self, app, test_user, forum_data):
        """Same user cannot increment view twice within 5 minutes."""
        with app.app_context():
            user, _ = test_user
            thread = ForumThread.query.get(forum_data["thread2"])  # Use thread2 (authored by admin)
            initial_views = thread.view_count or 0

            # First view should count
            result1 = forum_service.increment_thread_view(thread, user_id=user.id)
            assert result1 is True
            views_after_first = thread.view_count or 0
            assert views_after_first > initial_views

            # Second view within 5 minutes should be rate limited
            result2 = forum_service.increment_thread_view(thread, user_id=user.id)
            assert result2 is False
            views_after_second = ForumThread.query.get(forum_data["thread2"]).view_count or 0
            assert views_after_second == views_after_first

    def test_increment_thread_view_prevent_self_view(self, app, test_user, forum_data):
        """Thread author cannot count views on their own thread."""
        with app.app_context():
            user, _ = test_user
            # Get thread authored by the test user (or create one)
            thread = ForumThread.query.get(forum_data["thread1"])
            # Change author to our test user
            thread.author_id = user.id
            from app.extensions import db
            db.session.commit()

            initial_views = thread.view_count or 0

            # Author trying to view own thread should not count
            result = forum_service.increment_thread_view(thread, user_id=user.id)
            assert result is False
            updated = ForumThread.query.get(forum_data["thread1"])
            assert (updated.view_count or 0) == initial_views

    def test_increment_thread_view_multiple_users(self, app, test_user, forum_data):
        """Different users can each count one view within 5 minutes."""
        with app.app_context():
            thread = ForumThread.query.get(forum_data["thread2"])
            user1, _ = test_user
            user2 = _make_user(Role.NAME_USER, "forum_data_view_user2")
            db.session.commit()

            initial_views = thread.view_count or 0

            result1 = forum_service.increment_thread_view(thread, user_id=user1.id)
            assert result1 is True
            views1 = ForumThread.query.get(forum_data["thread2"]).view_count or 0
            assert views1 > initial_views

            result2 = forum_service.increment_thread_view(thread, user_id=user2.id)
            assert result2 is True
            views2 = ForumThread.query.get(forum_data["thread2"]).view_count or 0
            assert views2 > views1


class TestForumServiceForumDataPosts:
    """Test post creation and management."""

    def test_create_post_success(self, app, test_user, forum_data):
        """create_post creates a post successfully."""
        with app.app_context():
            user, _ = test_user
            thread = ForumThread.query.get(forum_data["thread1"])

            post, error = forum_service.create_post(
                thread=thread,
                author_id=user.id,
                content="New post content"
            )

            assert error is None
            assert post is not None
            assert post.content == "New post content"

    def test_create_post_missing_content(self, app, test_user, forum_data):
        """create_post fails with empty content."""
        with app.app_context():
            user, _ = test_user
            thread = ForumThread.query.get(forum_data["thread1"])

            post, error = forum_service.create_post(
                thread=thread,
                author_id=user.id,
                content=""
            )

            assert error is not None
            assert post is None

    def test_update_post(self, app, forum_data):
        """update_post updates post content."""
        with app.app_context():
            post = ForumPost.query.get(forum_data["post1"])
            updated = forum_service.update_post(post, content="Updated content", editor_id=post.author_id)

            assert updated.content == "Updated content"

    def test_soft_delete_post(self, app, forum_data):
        """soft_delete_post marks post as deleted."""
        with app.app_context():
            post = ForumPost.query.get(forum_data["post1"])
            updated = forum_service.soft_delete_post(post)

            assert updated.deleted_at is not None

    def test_hide_post(self, app, forum_data):
        """hide_post hides a post."""
        with app.app_context():
            post = ForumPost.query.get(forum_data["post1"])
            updated = forum_service.hide_post(post)

            assert updated.status == "hidden"

    def test_unhide_post(self, app, forum_data):
        """unhide_post shows a hidden post."""
        with app.app_context():
            post = ForumPost.query.get(forum_data["post1"])
            forum_service.hide_post(post)
            updated = forum_service.unhide_post(post)

            assert updated.status != "hidden"

    def test_get_post_by_id(self, app, forum_data):
        """get_post_by_id retrieves a post by ID."""
        with app.app_context():
            post = forum_service.get_post_by_id(forum_data["post1"])
            assert post is not None
            assert post.id == forum_data["post1"]

    def test_get_post_by_id_not_found(self, app):
        """get_post_by_id returns None for invalid ID."""
        with app.app_context():
            post = forum_service.get_post_by_id(99999)
            assert post is None


class TestForumServiceForumDataLikes:
    """Test post liking functionality."""

    def test_like_post_success(self, app, test_user, forum_data):
        """like_post adds a like successfully."""
        with app.app_context():
            user, _ = test_user
            post = ForumPost.query.get(forum_data["post1"])

            like, error = forum_service.like_post(user, post)

            assert error is None
            assert like is not None
            assert like.user_id == user.id

    def test_like_post_already_liked(self, app, test_user, forum_data):
        """like_post returns error when already liked."""
        with app.app_context():
            user, _ = test_user
            post = ForumPost.query.get(forum_data["post1"])

            # First like
            forum_service.like_post(user, post)
            db.session.commit()

            # Try to like again - should return existing like
            like, error = forum_service.like_post(user, post)

            assert error is None
            assert like is not None

    def test_unlike_post(self, app, test_user, forum_data):
        """unlike_post removes a like."""
        with app.app_context():
            user, _ = test_user
            post = ForumPost.query.get(forum_data["post1"])

            forum_service.like_post(user, post)
            db.session.commit()

            forum_service.unlike_post(user, post)

            like = ForumPostLike.query.filter_by(
                user_id=user.id,
                post_id=post.id
            ).first()
            assert like is None


class TestForumServiceForumDataReports:
    """Test forum report functionality."""

    def test_create_report_success(self, app, test_user, forum_data):
        """create_report creates a report successfully."""
        with app.app_context():
            user, _ = test_user

            report, error = forum_service.create_report(
                target_type="post",
                target_id=forum_data["post1"],
                reported_by=user.id,
                reason="Inappropriate content"
            )

            assert error is None
            assert report is not None
            if report:
                assert report.reason == "Inappropriate content"

    def test_get_report_by_id(self, app, test_user, forum_data):
        """get_report_by_id retrieves a report by ID."""
        with app.app_context():
            user, _ = test_user
            report, _ = forum_service.create_report(
                target_type="post",
                target_id=forum_data["post1"],
                reported_by=user.id,
                reason="Test report"
            )
            db.session.commit()

            retrieved = forum_service.get_report_by_id(report.id)
            assert retrieved is not None
            assert retrieved.id == report.id

    def test_list_reports_for_target(self, app, test_user, forum_data):
        """list_reports_for_target returns reports for a target."""
        with app.app_context():
            user, _ = test_user
            forum_service.create_report(
                target_type="post",
                target_id=forum_data["post1"],
                reported_by=user.id,
                reason="Test report 1"
            )
            db.session.commit()

            reports = forum_service.list_reports_for_target("post", forum_data["post1"])
            assert isinstance(reports, list)
            assert len(reports) > 0

    def test_update_report_status(self, app, test_user, forum_data, admin_user):
        """update_report_status updates report status."""
        with app.app_context():
            user, _ = test_user
            admin, _ = admin_user

            report, _ = forum_service.create_report(
                target_type="post",
                target_id=forum_data["post1"],
                reported_by=user.id,
                reason="Test"
            )
            db.session.commit()

            updated = forum_service.update_report_status(
                report,
                status="resolved",
                handled_by=admin.id,
                resolution_note="Fixed"
            )

            assert updated.status == "resolved"


class TestForumServiceForumDataSubscriptions:
    """Test thread subscriptions."""

    def test_subscribe_thread(self, app, test_user, forum_data):
        """subscribe_thread subscribes a user to a thread."""
        with app.app_context():
            user, _ = test_user
            thread = ForumThread.query.get(forum_data["thread1"])

            sub = forum_service.subscribe_thread(user, thread)

            assert sub is not None
            assert sub.user_id == user.id
            assert sub.thread_id == thread.id

    def test_unsubscribe_thread(self, app, test_user, forum_data):
        """unsubscribe_thread removes a subscription."""
        with app.app_context():
            user, _ = test_user
            thread = ForumThread.query.get(forum_data["thread1"])

            forum_service.subscribe_thread(user, thread)
            db.session.commit()

            forum_service.unsubscribe_thread(user, thread)

            sub = ForumThreadSubscription.query.filter_by(
                user_id=user.id,
                thread_id=thread.id
            ).first()
            assert sub is None


class TestForumServiceForumDataBookmarks:
    """Test thread bookmarks."""

    def test_bookmark_thread(self, app, test_user, forum_data):
        """bookmark_thread bookmarks a thread."""
        with app.app_context():
            user, _ = test_user
            thread = ForumThread.query.get(forum_data["thread1"])

            bookmark = forum_service.bookmark_thread(user, thread)

            assert bookmark is not None
            assert bookmark.user_id == user.id

    def test_unbookmark_thread(self, app, test_user, forum_data):
        """unbookmark_thread removes a bookmark."""
        with app.app_context():
            user, _ = test_user
            thread = ForumThread.query.get(forum_data["thread1"])

            forum_service.bookmark_thread(user, thread)
            db.session.commit()

            forum_service.unbookmark_thread(user, thread)

            bookmark = ForumThreadBookmark.query.filter_by(
                user_id=user.id,
                thread_id=thread.id
            ).first()
            assert bookmark is None

    def test_list_bookmarked_threads(self, app, test_user, forum_data):
        """list_bookmarked_threads returns user's bookmarked threads."""
        with app.app_context():
            user, _ = test_user
            thread = ForumThread.query.get(forum_data["thread1"])

            forum_service.bookmark_thread(user, thread)
            db.session.commit()

            threads, total = forum_service.list_bookmarked_threads(user, page=1, per_page=10)

            assert isinstance(threads, list)
            assert isinstance(total, int)


class TestForumServiceForumDataTags:
    """Test tag functionality."""

    def test_get_or_create_tags(self, app):
        """get_or_create_tags creates or retrieves tags."""
        with app.app_context():
            tags = forum_service.get_or_create_tags(["python", "javascript"])

            assert isinstance(tags, list)
            assert len(tags) == 2

    def test_set_thread_tags(self, app, forum_data):
        """set_thread_tags assigns tags to a thread."""
        with app.app_context():
            thread = ForumThread.query.get(forum_data["thread1"])

            tags = forum_service.set_thread_tags(thread, tags=["rust", "go"])

            assert isinstance(tags, list)
            assert len(tags) >= 2

    def test_list_tags_for_thread(self, app, forum_data):
        """list_tags_for_thread returns tags for a thread."""
        with app.app_context():
            thread = ForumThread.query.get(forum_data["thread1"])

            tags = forum_service.list_tags_for_thread(thread)

            assert isinstance(tags, list)

    def test_batch_tag_thread_counts(self, app, forum_data):
        """batch_tag_thread_counts returns counts for multiple tags."""
        with app.app_context():
            tag_ids = [forum_data["tag1"], forum_data["tag2"]]

            counts = forum_service.batch_tag_thread_counts(tag_ids)

            assert isinstance(counts, dict)
            assert len(counts) >= 1

    def test_tag_thread_count(self, app, forum_data):
        """tag_thread_count returns thread count for a tag."""
        with app.app_context():
            tag = ForumTag.query.get(forum_data["tag1"])

            count = forum_service.tag_thread_count(tag)

            assert isinstance(count, int)
            assert count >= 0

    def test_list_all_tags(self, app):
        """list_all_tags returns paginated tags."""
        with app.app_context():
            tags, total = forum_service.list_all_tags(page=1, per_page=10)

            assert isinstance(tags, list)
            assert isinstance(total, int)

    def test_delete_tag_success(self, app, forum_data):
        """delete_tag removes a tag if not in use."""
        with app.app_context():
            # Create a new unused tag
            tag = ForumTag(label="unused", slug="unused")
            db.session.add(tag)
            db.session.commit()

            error = forum_service.delete_tag(tag)

            assert error is None
            deleted = ForumTag.query.get(tag.id)
            assert deleted is None


class TestForumServiceForumDataCategoryCrud:
    """Test category creation and management."""

    def test_create_category_success(self, app):
        """create_category creates a category successfully."""
        with app.app_context():
            cat, error = forum_service.create_category(
                slug="test-cat",
                title="Test Category",
                description="Test",
                parent_id=None,
                sort_order=0,
                is_active=True,
                is_private=False,
                required_role=None
            )

            assert error is None
            assert cat is not None
            assert cat.slug == "test-cat"

    def test_create_category_duplicate_slug(self, app, forum_data):
        """create_category fails with duplicate slug."""
        with app.app_context():
            cat, error = forum_service.create_category(
                slug="general",
                title="Duplicate",
                description="Test",
                parent_id=None,
                sort_order=0,
                is_active=True,
                is_private=False,
                required_role=None
            )

            assert error is not None
            assert cat is None

    def test_update_category(self, app, forum_data):
        """update_category updates category fields."""
        with app.app_context():
            cat = ForumCategory.query.get(forum_data["cat_general"])

            updated = forum_service.update_category(
                cat,
                title="Updated Title",
                description="Updated description"
            )

            assert updated.title == "Updated Title"
