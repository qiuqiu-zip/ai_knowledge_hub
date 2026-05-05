from __future__ import annotations

import html
import re
from pathlib import PurePosixPath


_LOW_VALUE_FILENAMES = {
    "404.md": "low_value_path:404",
    "_404.md": "low_value_path:404",
    "404.html": "low_value_path:404",
    "_coverpage.md": "low_value_path:coverpage",
    "_navbar.md": "low_value_path:navigation",
    "_sidebar.md": "low_value_path:navigation",
    "_footer.md": "low_value_path:navigation",
    ".nojekyll": "low_value_path:decorative",
    "cname": "low_value_path:decorative",
}

_ASSET_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".webp",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".woff",
    ".woff2",
    ".ttf",
}

_SKIP_SEGMENTS = {"node_modules", ".git", "dist", "build", "public", "assets", "static", "images", "img"}

_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", flags=re.DOTALL)
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", flags=re.IGNORECASE | re.DOTALL)
_IMG_TAG_RE = re.compile(r"<(img|picture|source|svg)\b[^>]*>(?:.*?</\1>)?", flags=re.IGNORECASE | re.DOTALL)
_HTML_TAG_RE = re.compile(r"</?(div|span|p|a|section|article|header|footer|main|center|figure|figcaption|small|strong|em|b|i|u|br)\b[^>]*>", flags=re.IGNORECASE)
_MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_BADGE_RE = re.compile(r"\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)")
_RST_DIRECTIVE_RE = re.compile(r"^\s*\.\.\s+([_\w-]+::?|_.*:)\s*$", flags=re.MULTILINE)
_SEPARATOR_RE = re.compile(r"^\s*[=\-~`]{3,}\s*$", flags=re.MULTILINE)
_BADGE_LINE_RE = re.compile(r"^(.*?(shields\.io|badgen\.net|badge|stargazers|forks|stars|license|downloads).*)$", flags=re.IGNORECASE)
_REDIRECT_HINT_RE = re.compile(r"(已迁移至|该网站已迁移|moved to|relocated|redirect|meta refresh|window\.location)", flags=re.IGNORECASE)
_RAW_IMAGE_URL_RE = re.compile(r"https?://raw\.githubusercontent\.com/[^\s)]+?\.(png|jpg|jpeg|gif|svg|webp)", flags=re.IGNORECASE)
_ENTITY_RE = re.compile(r"&(?:nbsp|ensp|emsp|thinsp|amp|lt|gt|quot|apos);", flags=re.IGNORECASE)
_NOISE_PHRASE_RE = re.compile(
    r"(keep these links|translations will automatically update|site view|site_pv|site_uv|busuanzi|visitor count|page views?)",
    flags=re.IGNORECASE,
)
_LINK_ONLY_RE = re.compile(r"^(?:https?://\S+\s*)+$", flags=re.IGNORECASE)


def is_low_value_document_path(file_path: str | None) -> tuple[bool, str]:
    p = (file_path or "").strip().lower().replace("\\", "/")
    if not p:
        return True, "low_value_path:empty"
    pure = PurePosixPath(p)
    name = pure.name
    if name in _LOW_VALUE_FILENAMES:
        return True, _LOW_VALUE_FILENAMES[name]
    if pure.suffix in _ASSET_EXTENSIONS:
        return True, "low_value_path:asset"
    segments = set(part.lower() for part in pure.parts)
    if segments.intersection(_SKIP_SEGMENTS):
        return True, "low_value_path:asset_dir"
    return False, "ok"


def clean_markdown_noise(text: str | None) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    cleaned = _HTML_COMMENT_RE.sub(" ", raw)
    cleaned = _SCRIPT_STYLE_RE.sub(" ", cleaned)
    cleaned = _IMG_TAG_RE.sub(" ", cleaned)
    cleaned = _HTML_TAG_RE.sub(" ", cleaned)
    cleaned = _MD_BADGE_RE.sub(" ", cleaned)
    cleaned = _MD_IMAGE_RE.sub(" ", cleaned)
    cleaned = _RAW_IMAGE_URL_RE.sub(" ", cleaned)
    cleaned = _RST_DIRECTIVE_RE.sub(" ", cleaned)
    cleaned = _SEPARATOR_RE.sub(" ", cleaned)
    cleaned = _ENTITY_RE.sub(" ", cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = cleaned.replace("busuanzi", " ")
    lines = []
    for line in cleaned.splitlines():
        item = line.strip()
        if not item:
            continue
        item = item.strip("#*`> ")
        if not item:
            continue
        if _BADGE_LINE_RE.search(item):
            continue
        lowered = item.lower()
        if any(token in lowered for token in ("site view", "site_pv", "site_uv", "<!--", "-->", "<div", "</div", "<span", "</span")):
            continue
        if _NOISE_PHRASE_RE.search(item):
            continue
        if _LINK_ONLY_RE.match(item):
            continue
        lines.append(item)
    normalized = re.sub(r"\s+", " ", " ".join(lines)).strip()
    return normalized


def is_low_value_document_content(content: str | None, file_path: str | None) -> tuple[bool, str]:
    cleaned = clean_markdown_noise(content)
    if not cleaned:
        return True, "low_value_content:empty"
    if len(cleaned) < 80:
        return True, "low_value_content:too_short"
    lowered_path = (file_path or "").lower()
    if lowered_path.endswith("_coverpage.md"):
        return True, "low_value_content:coverpage"
    if _REDIRECT_HINT_RE.search(cleaned):
        if len(cleaned) < 240:
            return True, "low_value_content:redirect"
    words = cleaned.split(" ")
    link_like = sum(1 for w in words if w.startswith("http://") or w.startswith("https://"))
    if link_like >= max(3, len(words) // 3):
        return True, "low_value_content:mostly_noise"
    noise_token_hits = sum(
        1
        for token in ("badge", "logo", "coverpage", "navbar", "sidebar", "site view", "busuanzi")
        if token in cleaned.lower()
    )
    if noise_token_hits >= 4 and len(cleaned) < 260:
        return True, "low_value_content:noise_ratio_high"
    return False, "ok"


def should_ingest_document(file_path: str | None, content: str | None) -> tuple[bool, str, str]:
    path_low, path_reason = is_low_value_document_path(file_path)
    cleaned = clean_markdown_noise(content)
    if path_low:
        return False, path_reason, cleaned
    content_low, content_reason = is_low_value_document_content(content, file_path)
    if content_low:
        return False, content_reason, cleaned
    return True, "ok", cleaned
