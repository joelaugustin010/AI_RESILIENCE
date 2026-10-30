"""Audit public references for Kochi's official final ward-map publication.

Fetches the KSMART interactive page, same-origin JavaScript, and the official
final-map PDF URL pattern. This is source discovery and text cross-checking
only; a PDF is not a substitute for GIS boundary geometry.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

BASE = "https://wardmap.ksmart.live"
PAGE_URL = BASE + "/map?district=Ernakulam&localbody=Cochin&type=Corporation"
PDF_URL = BASE + "/FinalN/map/Map_FinalN_Ernakulam_Cochin.pdf"
OUT = Path("reports/kochi_final_map_source_discovery.json")
ROSTER = Path("data/reference/kochi_official_ward_roster_2025.json")
UA = "AI_RESILIENCE educational project; official-source provenance discovery"
MAX_SCRIPT_BYTES = 1_500_000
MAX_PDF_BYTES = 30_000_000
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


def get(url: str, limit: int) -> tuple[bytes, str, str]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "wardmap.ksmart.live":
        raise ValueError(f"Refusing non-official or non-HTTPS URL: {url}")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Accept": "text/html,application/javascript,application/pdf,application/json,*/*"},
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError(f"Response exceeds configured {limit}-byte limit: {url}")
        return data, response.geturl(), response.headers.get("Content-Type", "")


def resolve(url: str, base: str) -> str | None:
    absolute = urllib.parse.urljoin(base, url.strip())
    parsed = urllib.parse.urlparse(absolute)
    if parsed.scheme == "https" and parsed.hostname == "wardmap.ksmart.live":
        return absolute
    return None


def normalize(value: str) -> str:
    return "".join(ch for ch in value.casefold() if ch.isalnum())


def audit_final_pdf() -> dict:
    try:
        raw, final_url, content_type = get(PDF_URL, MAX_PDF_BYTES)
        if not raw.startswith(b"%PDF-"):
            raise ValueError(f"Response did not have a PDF signature (content-type={content_type})")
        reader = PdfReader(BytesIO(raw), strict=False)
        page_text = [page.extract_text() or "" for page in reader.pages]
        full_text = "\n".join(page_text)
        normalized_text = normalize(full_text)
        extracted_labels = []
        for number, name in re.findall(r"(?m)^\s*(\d{1,2})\s*[-–]\s*([A-Z][A-Z ]{2,60})\s*$", full_text):
            extracted_labels.append({"ward_number": int(number), "map_label": name.strip()})
        roster_payload = json.loads(ROSTER.read_text(encoding="utf-8"))
        wards = roster_payload.get("wards", [])
        checks = []
        for code, name in wards:
            target = normalize(name)
            checks.append({"ward_code": code, "official_name": name, "text_found": bool(target and target in normalized_text)})
        found = sum(row["text_found"] for row in checks)
        official_by_number = {int(code[-3:]): name for code, name in wards}
        labels_by_number = {}
        for row in extracted_labels:
            labels_by_number.setdefault(row["ward_number"], []).append(row["map_label"])
        numbered_comparison = []
        for number in range(1, 77):
            labels = labels_by_number.get(number, [])
            official_name = official_by_number.get(number)
            numbered_comparison.append({
                "ward_number": number,
                "official_sec_name": official_name,
                "final_map_labels": labels,
                "exact_normalized_match": any(normalize(label) == normalize(official_name or "") for label in labels),
            })
        return {
            "url": PDF_URL,
            "final_url": final_url,
            "http_content_type": content_type,
            "pdf_signature_valid": True,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "page_count": len(reader.pages),
            "extracted_text_characters": len(full_text),
            "official_ward_name_text_matches": found,
            "official_ward_name_text_missing": [row for row in checks if not row["text_found"]],
            "numbered_map_labels_extracted": len(extracted_labels),
            "numbered_map_labels": extracted_labels,
            "numbered_comparison_exact_name_matches": sum(row["exact_normalized_match"] for row in numbered_comparison),
            "numbered_comparison": numbered_comparison,
            "page_text_preview": [text[:2400] for text in page_text[:3]],
            "status": "OFFICIAL_FINAL_MAP_PDF_REFERENCE_ONLY_NOT_GIS_GEOMETRY",
        }
    except Exception as exc:
        return {
            "url": PDF_URL,
            "status": "PDF_FETCH_OR_TEXT_AUDIT_FAILED",
            "error": f"{type(exc).__name__}: {exc}",
        }


def main() -> int:
    try:
        raw, final_url, content_type = get(PAGE_URL, MAX_SCRIPT_BYTES)
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
        keyword_evidence = []
        for url in script_urls:
            try:
                data, landed, ctype = get(url, MAX_SCRIPT_BYTES)
                text = data.decode("utf-8", errors="replace")
                scripts.append({"url": landed, "content_type": ctype, "bytes_read": len(data)})
                for match in re.findall(r"""(?:(?:https?:)?//[^\s"'<>]+|/(?:api|data|files|FinalN|map)[^\s"'<>]*)""", text):
                    cleaned = match.rstrip(");,]")
                    absolute = resolve(cleaned, landed)
                    if absolute and any(term in absolute.casefold() for term in ("ward", "geojson", "json", "api", "finaln", "boundary", "map/")):
                        relevant_references.add(absolute)
                for match in re.findall(r"""['"]([^'"]{0,240}(?:geojson|wardboundary|ward_boundary|finaln|/api/)[^'"]{0,240})['"]""", text, flags=re.IGNORECASE):
                    relevant_references.add(match)
                for pattern in ("FinalN/map", "FinalN/notification", "geojson", "fetch(", "axios", "Cochin", "wb_kerala", "VectorTile", "MVT", "tileGrid", "tileSize", "fromLonLat", "getTileUrlFunction", "projection", "extent", "wardBoundary"):
                    positions = [m.start() for m in re.finditer(re.escape(pattern), text, flags=re.IGNORECASE)][:8]
                    for pos in positions:
                        keyword_evidence.append({"script_url": landed, "pattern": pattern, "snippet": text[max(0, pos-180):min(len(text), pos+320)]})
            except Exception as exc:
                scripts.append({"url": url, "error": f"{type(exc).__name__}: {exc}"})

        pdf_audit = audit_final_pdf()
        script_variable_evidence = []
        for script in scripts:
            if "url" not in script or not script.get("url", "").endswith(".js"):
                continue
            try:
                script_bytes, _, _ = get(script["url"], MAX_SCRIPT_BYTES)
                js = script_bytes.decode("utf-8", errors="replace")
                for variable in ("e1", "Jx", "Fy", "nR", "n1", "iR"):
                    for match in list(re.finditer(r"(?:const|let|var)?\s*" + re.escape(variable) + r"\s*=", js))[:6]:
                        script_variable_evidence.append({"script_url": script["url"], "variable": variable, "snippet": js[max(0, match.start()-180):min(len(js), match.start()+500)]})
            except Exception as exc:
                script_variable_evidence.append({"script_url": script.get("url"), "error": f"{type(exc).__name__}: {exc}"})
        result = {
            "source_page": PAGE_URL,
            "final_url": final_url,
            "retrieved_content_type": content_type,
            "retrieved_html_bytes": len(raw),
            "page_title": "".join(parser.title_parts).strip(),
            "html_shell_note": "The page is a client-rendered application; page labels may be rendered by JavaScript.",
            "official_same_origin_scripts": scripts,
            "candidate_public_references": sorted(relevant_references),
            "keyword_evidence": keyword_evidence[:60],
            "script_variable_evidence": script_variable_evidence[:40],
            "final_map_pdf_audit": pdf_audit,
            "status": "SOURCE_DISCOVERY_AND_PDF_TEXT_AUDIT_ONLY",
            "limitations": [
                "A final-notification PDF and ward-name text checks do not establish that a GIS layer's polygons match the legally notified boundaries.",
                "The PDF is retained as an official visual/reference source only; this script does not extract or approve boundary geometries.",
                "No official geometry is promoted into the production map by this script.",
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
