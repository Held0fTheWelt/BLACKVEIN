"""
Test suite for HTML sanitization in forum endpoints.
Ensures stored XSS prevention via HTML injection filtering.
"""
import pytest
from app.services.forum_service import _sanitize_html, create_thread, create_post
from app.models import ForumCategory, ForumThread, User
from app.extensions import db


class TestHTMLSanitization:
    """Test HTML sanitization function."""

    def test_sanitize_strips_script_tags(self):
        """Script tags should be completely stripped."""
        dirty = "Hello <script>alert('XSS')</script> World"
        clean = _sanitize_html(dirty)
        assert "<script>" not in clean
        assert "alert" not in clean
        assert "Hello" in clean
        assert "World" in clean

    def test_sanitize_strips_iframe_tags(self):
        """Iframe tags should be completely stripped."""
        dirty = "Content <iframe src='http://evil.com'></iframe>"
        clean = _sanitize_html(dirty)
        assert "<iframe>" not in clean
        assert "iframe" not in clean
        assert "Content" in clean

    def test_sanitize_strips_event_handlers(self):
        """Event handlers should be stripped from allowed tags."""
        dirty = '<p onclick="alert(\'XSS\')">Click me</p>'
        clean = _sanitize_html(dirty)
        assert "onclick" not in clean
        assert "alert" not in clean
        assert "Click me" in clean

    def test_sanitize_allows_safe_tags(self):
        """Safe tags should be preserved."""
        dirty = '<p>Hello <b>bold</b> <i>italic</i> <em>emphasis</em> <strong>strong</strong></p>'
        clean = _sanitize_html(dirty)
        assert "<p>" in clean
        assert "<b>" in clean
        assert "</b>" in clean
        assert "<i>" in clean
        assert "</i>" in clean
        assert "<em>" in clean
        assert "</em>" in clean
        assert "<strong>" in clean
        assert "</strong>" in clean
        assert "Hello" in clean
        assert "bold" in clean
        assert "italic" in clean
        assert "emphasis" in clean
        assert "strong" in clean

    def test_sanitize_allows_safe_links(self):
        """Links with safe href attribute should be preserved."""
        dirty = '<a href="https://example.com">Click here</a>'
        clean = _sanitize_html(dirty)
        assert "<a" in clean
        assert 'href="https://example.com"' in clean
        assert "Click here" in clean

    def test_sanitize_strips_javascript_url(self):
        """JavaScript URLs in href should be stripped."""
        dirty = '<a href="javascript:alert(\'XSS\')">Click</a>'
        clean = _sanitize_html(dirty)
        # bleach should strip the dangerous href
        assert "javascript:" not in clean

    def test_sanitize_allows_br_tag(self):
        """Break tags should be allowed."""
        dirty = "Line 1<br>Line 2"
        clean = _sanitize_html(dirty)
        assert "<br" in clean or "<br>" in clean
        assert "Line 1" in clean
        assert "Line 2" in clean

    def test_sanitize_removes_html_comments(self):
        """HTML comments should be stripped."""
        dirty = "Content<!-- Secret data -->"
        clean = _sanitize_html(dirty)
        assert "<!--" not in clean
        assert "Secret" not in clean
        assert "Content" in clean

    def test_sanitize_removes_style_tags(self):
        """Style tags should be stripped."""
        dirty = '<style>body { display: none; }</style>Content'
        clean = _sanitize_html(dirty)
        assert "<style>" not in clean
        assert "display: none" not in clean
        assert "Content" in clean

    def test_sanitize_removes_style_attributes(self):
        """Style attributes should be stripped."""
        dirty = '<p style="background: url(javascript:alert())">Text</p>'
        clean = _sanitize_html(dirty)
        assert "style" not in clean
        assert "javascript" not in clean
        assert "Text" in clean

    def test_sanitize_removes_onclick_attribute(self):
        """Onclick attributes should be stripped."""
        dirty = '<b onclick="alert(\'xss\')">Bold</b>'
        clean = _sanitize_html(dirty)
        assert "onclick" not in clean
        assert "alert" not in clean
        assert "Bold" in clean

    def test_sanitize_empty_string(self):
        """Empty string should return empty string."""
        assert _sanitize_html("") == ""

    def test_sanitize_none_input(self):
        """None input should return empty string."""
        assert _sanitize_html(None) == ""

    def test_sanitize_non_string_input(self):
        """Non-string input should return empty string."""
        assert _sanitize_html(123) == ""
        assert _sanitize_html([]) == ""

    def test_sanitize_preserves_text_only(self):
        """Plain text should be preserved as-is."""
        text = "This is a simple text message without any HTML"
        assert _sanitize_html(text) == text

    def test_sanitize_complex_xss_payload(self):
        """Complex XSS payload should be sanitized."""
        dirty = '''
        <p>Content</p>
        <svg onload="alert('xss')">
        <script>alert('xss')</script>
        <iframe src="evil.com"></iframe>
        <img src=x onerror="alert('xss')">
        '''
        clean = _sanitize_html(dirty)
        assert "onload" not in clean
        assert "onerror" not in clean
        assert "<script>" not in clean
        assert "<svg" not in clean
        assert "<iframe" not in clean
        assert "Content" in clean

    def test_sanitize_img_tag_stripped(self):
        """Image tags should be stripped (not in safe list)."""
        dirty = '<img src="image.jpg" alt="test">'
        clean = _sanitize_html(dirty)
        assert "<img" not in clean


class TestForumThreadSanitization:
    """Test HTML sanitization in forum thread creation."""

    @pytest.fixture
    def setup_forum(self, app, client):
        """Setup forum category for testing."""
        with app.app_context():
            # Create a test category
            category = ForumCategory(
                slug="test-category",
                title="Test Category",
                description="Test",
                is_active=True,
                is_private=False,
                sort_order=1,
            )
            db.session.add(category)
            db.session.commit()
            return category.id

    def test_create_thread_sanitizes_content(self, app, setup_forum):
        """Thread content should be sanitized on creation."""
        with app.app_context():
            category = ForumCategory.query.get(setup_forum)
            dirty_content = '<p>Hello <script>alert("xss")</script></p>'

            thread, post, err = create_thread(
                category=category,
                author_id=None,
                title="Test Thread",
                content=dirty_content
            )

            assert err is None
            assert thread is not None
            assert post is not None
            assert "<script>" not in post.content
            assert "alert" not in post.content
            assert "Hello" in post.content

    def test_create_thread_allows_safe_html(self, app, setup_forum):
        """Thread content should preserve safe HTML tags."""
        with app.app_context():
            category = ForumCategory.query.get(setup_forum)
            safe_content = '<p>Hello <b>bold</b> <i>italic</i> text</p>'

            thread, post, err = create_thread(
                category=category,
                author_id=None,
                title="Test Thread",
                content=safe_content
            )

            assert err is None
            assert thread is not None
            assert post is not None
            assert "<b>" in post.content
            assert "<i>" in post.content
            assert "bold" in post.content
            assert "italic" in post.content


class TestForumPostSanitization:
    """Test HTML sanitization in forum post creation and updates."""

    @pytest.fixture
    def setup_forum_with_thread(self, app):
        """Setup forum category and thread for testing."""
        with app.app_context():
            # Create category
            category = ForumCategory(
                slug="test-cat",
                title="Test Category",
                is_active=True,
                is_private=False,
                sort_order=1,
            )
            db.session.add(category)
            db.session.commit()

            # Create thread
            thread = ForumThread(
                category_id=category.id,
                author_id=None,
                slug="test-thread",
                title="Test Thread",
                status="open",
            )
            db.session.add(thread)
            db.session.commit()

            return thread.id

    def test_create_post_sanitizes_content(self, app, setup_forum_with_thread):
        """Post content should be sanitized on creation."""
        with app.app_context():
            thread = ForumThread.query.get(setup_forum_with_thread)
            dirty_content = '<p>Reply <iframe src="evil.com"></iframe></p>'

            post, err = create_post(
                thread=thread,
                author_id=None,
                content=dirty_content
            )

            assert err is None
            assert post is not None
            assert "<iframe>" not in post.content
            assert "evil.com" not in post.content
            assert "Reply" in post.content

    def test_create_post_allows_safe_tags(self, app, setup_forum_with_thread):
        """Post content should preserve safe tags."""
        with app.app_context():
            thread = ForumThread.query.get(setup_forum_with_thread)
            safe_content = '<p>Check this <a href="https://example.com">link</a></p>'

            post, err = create_post(
                thread=thread,
                author_id=None,
                content=safe_content
            )

            assert err is None
            assert post is not None
            assert "<a" in post.content
            assert "href" in post.content
            assert "example.com" in post.content


class TestXSSPayloads:
    """Test against various known XSS payloads."""

    def test_sanitize_img_onerror_payload(self):
        """img onerror payload should be sanitized."""
        payload = '<img src=x onerror="alert(\'xss\')">'
        clean = _sanitize_html(payload)
        assert "onerror" not in clean
        assert "<img" not in clean

    def test_sanitize_svg_onload_payload(self):
        """SVG onload payload should be sanitized."""
        payload = '<svg onload="alert(\'xss\')">'
        clean = _sanitize_html(payload)
        assert "onload" not in clean
        assert "<svg" not in clean

    def test_sanitize_body_onload_payload(self):
        """Body onload payload should be sanitized."""
        payload = '<body onload="alert(\'xss\')">'
        clean = _sanitize_html(payload)
        assert "onload" not in clean
        assert "<body" not in clean

    def test_sanitize_input_onfocus_payload(self):
        """Input onfocus payload should be sanitized."""
        payload = '<input onfocus="alert(\'xss\')" autofocus>'
        clean = _sanitize_html(payload)
        assert "onfocus" not in clean
        assert "<input" not in clean

    def test_sanitize_marquee_onstart_payload(self):
        """Marquee onstart payload should be sanitized."""
        payload = '<marquee onstart="alert(\'xss\')">'
        clean = _sanitize_html(payload)
        assert "onstart" not in clean
        assert "<marquee" not in clean

    def test_sanitize_data_uri_payload(self):
        """Data URI in link should be sanitized."""
        payload = '<a href="data:text/html,<script>alert(\'xss\')</script>">Click</a>'
        clean = _sanitize_html(payload)
        # Link should be stripped if it contains javascript execution
        assert "script>" not in clean or "alert" not in clean

    def test_sanitize_vbscript_protocol(self):
        """VBScript protocol should be sanitized."""
        payload = '<a href="vbscript:alert(\'xss\')">Click</a>'
        clean = _sanitize_html(payload)
        assert "vbscript:" not in clean

    def test_sanitize_embedded_null_byte(self):
        """Null bytes should not cause issues."""
        payload = 'Hello\x00<script>alert("xss")</script>'
        clean = _sanitize_html(payload)
        assert "<script>" not in clean
        assert "alert" not in clean
