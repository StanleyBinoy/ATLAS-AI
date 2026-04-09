# This module provides read-only live web search and page fetch helpers for ATLAS.
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from html.parser import HTMLParser
import re
from urllib.parse import parse_qs, urlparse

import requests


DEFAULT_HEADERS = {"User-Agent": "ATLAS/1.0"}
MAX_PAGE_CHARS = 2500


class _TextExtractor(HTMLParser):
    """Extract readable text content from HTML."""

    def __init__(self):
        """Initialize the HTML text extractor."""
        super().__init__()
        self.parts = []
        self.skip_tags = {"script", "style"}
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        """Track tags that should be ignored."""
        if tag in self.skip_tags:
            self.skip_depth += 1

    def handle_endtag(self, tag):
        """Stop skipping ignored tags when they end."""
        if tag in self.skip_tags and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data):
        """Collect visible text chunks from HTML content."""
        if not self.skip_depth:
            self.parts.append(data)

    def get_text(self):
        """Return cleaned visible text extracted from the HTML page."""
        return " ".join(part.strip() for part in self.parts if part.strip())


def search_web(query, max_results=5, timeout=10):
    """Search the web and return normalized result dictionaries."""
    try:
        response = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=DEFAULT_HEADERS,
            timeout=timeout,
        )
        response.raise_for_status()
        results = normalize_search_results(response.text, max_results=max_results)
        if results:
            return results
        return [{
            "title": "Web search unavailable",
            "url": "",
            "snippet": "Live web search returned no parsable results.",
            "success": False,
            "status": "empty",
        }]
    except Exception as exc:
        error_text = str(exc)
        status = "blocked" if "proxy" in error_text.lower() or "127.0.0.1" in error_text else "unavailable"
        return [{
            "title": "Web search unavailable",
            "url": "",
            "snippet": f"Live web search failed: {exc}",
            "success": False,
            "status": status,
        }]


def normalize_search_results(raw_html, max_results=5):
    """Convert raw DuckDuckGo HTML into normalized result dictionaries."""
    pattern = re.compile(
        r'<a[^>]+class="result__a"[^>]+href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>',
        re.DOTALL,
    )
    snippets = re.findall(
        r'<a[^>]+class="result__snippet"[^>]*>(?P<snippet>.*?)</a>|<div[^>]+class="result__snippet"[^>]*>(?P<divsnippet>.*?)</div>',
        raw_html,
        re.DOTALL,
    )
    results = []

    for index, match in enumerate(pattern.finditer(raw_html)):
        if len(results) >= max_results:
            break

        href = _resolve_duckduckgo_url(match.group("href"))
        title = _clean_html_text(match.group("title"))
        snippet = ""
        if index < len(snippets):
            snippet = _clean_html_text(snippets[index][0] or snippets[index][1])

        results.append({
            "title": title,
            "url": href,
            "snippet": snippet,
            "success": True,
        })

    return results


def fetch_page(url, timeout=10):
    """Fetch a webpage and return a normalized page payload."""
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        response.raise_for_status()
        extractor = _TextExtractor()
        extractor.feed(response.text)
        title_match = re.search(r"<title>(.*?)</title>", response.text, re.IGNORECASE | re.DOTALL)
        title = _clean_html_text(title_match.group(1)) if title_match else url
        content = extractor.get_text()
        return {
            "url": url,
            "title": title,
            "content": content[:MAX_PAGE_CHARS],
            "success": True,
        }
    except Exception as exc:
        return {
            "url": url,
            "title": url,
            "content": "",
            "success": False,
            "error": str(exc),
        }


def fetch_pages_parallel(urls, max_workers=3):
    """Fetch multiple webpages in parallel and return their normalized payloads."""
    if not urls:
        return []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(fetch_page, urls))


def browse_and_summarize(query, max_results=3):
    """Search the web and fetch top pages for downstream summarization."""
    search_results = search_web(query, max_results=max_results)
    valid_results = [result for result in search_results if result.get("success") and result.get("url")]
    pages = fetch_pages_parallel([result["url"] for result in valid_results[:max_results]])
    web_status = "success" if valid_results else (search_results[0].get("status", "unavailable") if search_results else "unavailable")
    sources = [
        {"title": result.get("title", ""), "url": result.get("url", "")}
        for result in valid_results[:max_results]
    ]
    return {
        "query": query,
        "search_results": search_results,
        "pages": pages,
        "success": bool(valid_results),
        "web_status": web_status,
        "error_message": "" if valid_results else (search_results[0].get("snippet", "") if search_results else "Live web retrieval failed."),
        "sources": sources,
    }


def _resolve_duckduckgo_url(url):
    """Resolve DuckDuckGo redirect URLs into destination URLs."""
    parsed = urlparse(url)
    if "duckduckgo.com" not in parsed.netloc:
        return unescape(url)

    destination = parse_qs(parsed.query).get("uddg", [""])[0]
    return unescape(destination or url)


def _clean_html_text(text):
    """Strip tags and normalize whitespace in HTML-derived text."""
    no_tags = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", unescape(no_tags)).strip()
