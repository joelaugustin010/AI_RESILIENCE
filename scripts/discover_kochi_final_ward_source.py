"""Discover the official KSMART final ward-map page's public data references.

This is a bounded provenance-discovery utility. It fetches only the official
KSMART page and same-origin script assets, records public URL references, and
does not promote or download boundary geometries as verified data.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

BASE = "https://wardmap.ksmart.live"
PAGE_URL = BASE + "/map?district=Ernakulam&localbody=Cochin&type=Corporation"
OUT = Path("reports/kochi_final_map_source_discovery.json")
UA = "AI_RESILIENCE educational project; official-source provenance discovery"
MAX_SCRIPT_BYTES = 1_500_000
MAX_SCRIPTS = 20


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []
        self.scripts: list[str] = []
        self.title_parts: list[str] = []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])
        elif tag == "script" and values.get("src"):
            self.scripts.append(values["src"])
        elif tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)


def get(url: str, limit: int = MAX_SCRIPT_BYTES) -> tuple[bytes, str, str]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "wardmap.ksmart.live":
        raise ValueError(f"Refusing non-official or non-HTTPS URL: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/javascript,application/json,*/*"})
    with urllib.request.urlopen(req, timeout=30) as response:
        content = response.read(limit + 1)
        if len(content) > limit:
            content = content[:limit]
        return content, response.geturl(), response.headers.get("Content-Type", "")


def resolve(url: str, base: str) -> str | None:
    absolute = urllib.parse.urljoin(base, url.strip())
    parsed = urllib.parse.urlparse(absolute)
    if parsed.scheme == "https" and parsed.hostname == "wardmap.ksmart.live":
        return absolute
    return None


def main() -> int:
    try:
        raw, final_url, content_type = get(PAGE_URL)
        html = raw.decode("utf-8", errors="replace")
        parser = LinkParser()
        parser.feed(html)
        script_urls = []
        for source in parser.scripts:
            resolved = resolve(source, final_url)
            if resolved and resolved not in script_urls:
                script_urls.append(resolved)
        script_urls = script_urls[:MAX_SCRIPTS]

        scripts = []
        relevant_references = set()
        for url in script_urls:
            try:
                data, landed, ctype = get(url)
                text = data.decode("utf-8", errors="replace")
                scripts.append({"url": landed, "content_type": ctype, "bytes_read": len(data)})
                for match in re.findall(r"""(?:(?:https?:)?//[^\s"'<>]+|/(?:api|data|files|FinalN|map)[^\s"'<>]*)""", text):
                    cleaned = match.rstrip(");,]")
                    absolute = resolve(cleaned, landed)
                    if absolute:
                        low = absolute.casefold()
                        if any(term in low for term in ("ward", "geojson", "json", "api", "finaln", "boundary", "map/")):
                            relevant_references.add(absolute)
                # Also retain named endpoint fragments where a URL is assembled dynamically.
                for match in re.findall(r"""['"]([^'"]{0,220}(?:geojson|wardboundary|ward_boundary|finaln|/api/)[^'"]{0,220})['"]""", text, flags=re.IGNORECASE):
                    relevant_references.add(match)
            except Exception as exc:
                scripts.append({"url": url, "error": f"{type(exc).__name__}: {exc}"})

        text_hits = []
        for pattern in (r"FINAL\s+NOTIFICATION", r"DRAFT\s+NOTIFICATION", r"geojson", r"ward.?boundary", r"api/"):
            found = re.findall(pattern, html, flags=re.IGNORECASE)
            text_hits.append({"pattern": pattern, "occurrences": len(found)})

        result = {
            "source_page": PAGE_URL,
            "final_url": final_url,
            "retrieved_content_type": content_type,
            "retrieved_html_bytes": len(raw),
            "page_title": "".join(parser.title_parts).strip(),
            "page_indicates_final_notification": bool(re.search(r"FINAL\s+NOTIFICATION", html, flags=re.IGNORECASE)),
            "page_indicates_draft_notification": bool(re.search(r"DRAFT\s+NOTIFICATION", html, flags=re.IGNORECASE)),
            "official_same_origin_scripts": scripts,
            "candidate_public_references": sorted(relevant_references),
            "html_text_checks": text_hits,
            "status": "SOURCE_DISCOVERY_ONLY_NOT_GEOMETRY_VERIFICATION",
            "limitations": [
                "A final-notification page label is not by itself proof that a downloaded GIS geometry matches the legally notified boundary.",
                "No geometry is approved or integrated by this script.",
                "Only HTTPS resources on wardmap.ksmart.live are fetched."
            ]
        }
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f"KOCHI_FINAL_MAP_DISCOVERY_BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
