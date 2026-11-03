"""Acquire and validate two newly identified official Edayar air-evidence sources.

Original PDFs are kept byte-for-byte under ``data/raw``. Existing files are never
silently replaced. This script validates transport, PDF structure, and source text;
it does not turn the DIC plot list into coordinates or permit records into emissions.
"""

from __future__ import annotations

import hashlib
from io import BytesIO
import json
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    {
        "filename": "KSPCB_CAAQMS_monthly_report_2026-09.pdf",
        "url": "https://kspcb.kerala.gov.in/fileViewer/UHIwKzVlZkpwTnVzaVAxY2lHZlRZS0swN04rRWJuOHBlVVNZeUNRdkZ5c0pkUlVxeDY5aDduT1AwUnR5TWt6cjRKdnp6R25UZS9ubC9oeEh3TmFUbFE9PQ%2A%2A/0?raw=1",
        "listing_url": "https://kspcb.kerala.gov.in/water-and-air-quality-directory",
        "publisher": "Kerala State Pollution Control Board",
        "allowed_host": "kspcb.kerala.gov.in",
        "publication_date": "2026-09-30",
        "expected_text": ["eloor", "pm10", "so2"],
        "coverage": "September 2026 CAAQMS monthly report; station and dates to be confirmed from PDF content.",
        "units": "As printed in the report; validate station table before producing extracts.",
        "limitations": [
            "Monthly summary reporting may omit exact pollutant averaging intervals, QA flags, completeness, and station coordinates.",
            "Ambient measurements do not identify an industrial source by themselves.",
        ],
    },
    {
        "filename": "DIC_DA_Edayar_allotment_details_2022.pdf",
        "url": "https://industry.kerala.gov.in/images/DA-DP/Ernakulam/DA_Edayar.pdf",
        "listing_url": "https://industry.kerala.gov.in/index.php/pages/infrastructure-support/industrial-development-areas-plots1",
        "publisher": "Directorate of Industries and Commerce, Government of Kerala",
        "allowed_host": "industry.kerala.gov.in",
        "publication_date": "2022-02-15",
        "expected_text": ["edayar", "allotment"],
        "coverage": "Edayar industrial-area plot allotment details; listing identifies a 15 February 2022 dated record.",
        "units": "Plot identifiers and areas as printed in the source; area units must be taken from the PDF table heading.",
        "limitations": [
            "A plot allotment record can support historical plot/name linkage but does not verify a facility's geographic coordinates or current occupancy.",
            "The record contains no stack-emission measurements and does not establish current operating status.",
        ],
    },
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def acquire(source: dict[str, object]) -> dict[str, object]:
    filename = str(source["filename"])
    raw_path = ROOT / "data" / "raw" / ("air_quality_reports" if filename.startswith("KSPCB") else "industrial") / filename
    metadata_path = raw_path.with_name(raw_path.name + ".metadata.json")
    request = Request(str(source["url"]), headers={"User-Agent": "AI_RESILIENCE evidence acquisition/1.0"})
    with urlopen(request, timeout=30) as response:
        content = response.read()
        final_url = response.geturl()
        content_type = response.headers.get("Content-Type", "")
        status = response.status

    if status != 200:
        raise ValueError(f"{filename}: HTTP status {status}")
    if not final_url.startswith("https://") or str(source["allowed_host"]) not in final_url:
        raise ValueError(f"{filename}: unexpected final URL {final_url}")
    if "pdf" not in content_type.casefold() and not content.startswith(b"%PDF-"):
        raise ValueError(f"{filename}: response is not identified as a PDF ({content_type})")
    if not content.startswith(b"%PDF-"):
        raise ValueError(f"{filename}: invalid PDF signature; response was not saved")

    reader = PdfReader(BytesIO(content), strict=True)
    if not reader.pages:
        raise ValueError(f"{filename}: PDF has no pages")
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    if len(text.strip()) < 500:
        raise ValueError(f"{filename}: insufficient extractable source text")
    normalized = " ".join(text.casefold().split())
    missing = [term for term in source["expected_text"] if str(term).casefold() not in normalized]
    if missing:
        raise ValueError(f"{filename}: expected source markers absent: {missing}")

    raw_path.parent.mkdir(parents=True, exist_ok=True)
    digest = sha256(content)
    if raw_path.exists() and sha256(raw_path.read_bytes()) != digest:
        raise FileExistsError(f"Refusing to overwrite a different existing source file: {raw_path}")
    if not raw_path.exists():
        raw_path.write_bytes(content)

    metadata = {
        "publisher": source["publisher"],
        "source_url": source["url"],
        "listing_url": source["listing_url"],
        "retrieved_on": date.today().isoformat(),
        "publication_date": source["publication_date"],
        "publication_date_basis": "Directory/listing label; verify against the PDF itself where stated.",
        "http_status": status,
        "final_url": final_url,
        "content_type": content_type,
        "sha256": digest,
        "bytes": len(content),
        "pages": len(reader.pages),
        "source_text_validation": {"minimum_extracted_characters": 500, "characters": len(text), "expected_markers": source["expected_text"], "passed": True},
        "coverage": source["coverage"],
        "units": source["units"],
        "licence": "No dataset-specific open licence identified in the source listing or document reviewed; retain attribution and confirm reuse terms before redistribution.",
        "limitations": source["limitations"],
    }
    serialized = json.dumps(metadata, indent=2, ensure_ascii=False) + "\n"
    if metadata_path.exists():
        existing = json.loads(metadata_path.read_text(encoding="utf-8"))
        if existing.get("sha256") != digest or existing.get("source_url") != source["url"]:
            raise FileExistsError(f"Refusing to overwrite conflicting source metadata: {metadata_path}")
    else:
        metadata_path.write_text(serialized, encoding="utf-8")
    return {"file": str(raw_path.relative_to(ROOT)), "metadata": str(metadata_path.relative_to(ROOT)), "sha256": digest, "pages": len(reader.pages), "text_characters": len(text), "content_type": content_type}


def main() -> None:
    result = [acquire(source) for source in SOURCES]
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
