"""
Inline external script/stylesheet URLs into HTML so charts work when loaded from file:// in QWebEngineView.
"""
from __future__ import annotations

import re
import urllib.error
import urllib.request


def _fetch_url(url: str, timeout: float = 10.0) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AnalyticsGraphShare/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, Exception):
        return None


def inline_external_resources(html: str) -> str:
    """
    Replace external script src and stylesheet href (http/https) with inline content
    so the page works when loaded from file:// (e.g. in QWebEngineView).
    """
    result = html

    # Scripts: <script src="https://..."></script> -> <script>...content...</script>
    script_pattern = re.compile(
        r'<script([^>]*)\ssrc=["\'](https?://[^"\']+)["\']([^>]*)></script>',
        re.IGNORECASE,
    )

    def replace_script(m: re.Match) -> str:
        pre, url, post = m.group(1), m.group(2), m.group(3)
        content = _fetch_url(url)
        if content is None:
            return m.group(0)
        return f"<script{pre}{post}>\n{content}\n</script>"

    result = script_pattern.sub(replace_script, result)

    # Stylesheets: <link rel="stylesheet" href="https://..."> -> <style>...content...</style>
    link_pattern = re.compile(
        r'<link([^>]*)\srel=["\']stylesheet["\']([^>]*)href=["\'](https?://[^"\']+)["\']([^>]*)>',
        re.IGNORECASE,
    )

    def replace_link(m: re.Match) -> str:
        url = m.group(3)
        content = _fetch_url(url)
        if content is None:
            return m.group(0)
        return f"<style>\n{content}\n</style>"

    result = link_pattern.sub(replace_link, result)

    return result
