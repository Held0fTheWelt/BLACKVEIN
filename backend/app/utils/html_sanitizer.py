"""
Strict allowlist-based HTML sanitization for wiki and other user-authored content.
Removes script tags, event handlers, javascript: URLs, and dangerous attributes.
"""
import re

import bleach

# Tags commonly produced by markdown (extra): keep structure and formatting only.
WIKI_ALLOWED_TAGS = {
    "p", "br", "hr", "div", "span",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "strong", "b", "em", "i", "u", "s", "code", "pre",
    "blockquote", "a",
    "table", "thead", "tbody", "tr", "th", "td",
}

# Only href and title on links; no onclick, etc.
WIKI_ALLOWED_ATTRS = {
    "a": ["href", "title"],
}

# Schemes allowed in href (no javascript:, data:, vbscript:).
WIKI_ALLOWED_PROTOCOLS = {"http", "https", "mailto"}


def sanitize_wiki_html(html: str) -> str:
    """
    Sanitize HTML produced from markdown for safe display.
    Uses allowlist of tags/attributes; strips script, event handlers, dangerous URLs.
    Returns empty string if input is None or not a string.
    """
    if html is None:
        return ""
    if not isinstance(html, str):
        return ""
    if not html.strip():
        return html

    cleaned = bleach.clean(
        html,
        tags=WIKI_ALLOWED_TAGS,
        attributes=WIKI_ALLOWED_ATTRS,
        protocols=WIKI_ALLOWED_PROTOCOLS,
        strip=True,
        strip_comments=True,
    )
    # Defense in depth: strip any remaining event handler attributes (bleach strips unknown attrs).
    cleaned = re.sub(r"\s+on\w+\s*=\s*[\"'][^\"']*[\"']", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+on\w+\s*=\s*[^\s>]+", "", cleaned, flags=re.IGNORECASE)
    return cleaned
