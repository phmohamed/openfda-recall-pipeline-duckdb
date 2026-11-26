"""Clean raw enforcement records into flat rows."""
import re
from datetime import datetime

CLASSES = {"Class I", "Class II", "Class III"}

# Reasons are free text. These keyword groups are a simple, transparent rule set, not a model.
REASON_RULES = [
    ("contamination", r"contaminat|microbial|sterility|steril|particulate|foreign|bacteri|mold|endotoxin"),
    ("potency or dissolution", r"potency|dissolution|assay|out of specification|oos|sub-?potent|super-?potent|content uniformity|impurit"),
    ("labeling or packaging", r"label|packag|mislabel|carton|insert|barcode|expir"),
    ("cgmp deviation", r"cgmp|good manufacturing|manufacturing practice"),
    ("undeclared ingredient", r"undeclared|unapproved|not approved"),
]


def parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y%m%d").date()
    except ValueError:
        return None


def reason_group(text: str) -> str:
    t = (text or "").lower()
    for name, pat in REASON_RULES:
        if re.search(pat, t):
            return name
    return "other"


def clean(rec: dict) -> dict:
    return {
        "recall_number": (rec.get("recall_number") or "").strip(),
        "event_id": str(rec.get("event_id") or ""),
        "classification": (rec.get("classification") or "").strip(),
        "status": (rec.get("status") or "").strip(),
        "recalling_firm": re.sub(r"\s+", " ", (rec.get("recalling_firm") or "").strip()).upper(),
        "state": (rec.get("state") or "").strip().upper(),
        "country": (rec.get("country") or "").strip(),
        "voluntary_mandated": (rec.get("voluntary_mandated") or "").strip(),
        "product_type": (rec.get("product_type") or "").strip(),
        "report_date": parse_date(rec.get("report_date")),
        "recall_initiation_date": parse_date(rec.get("recall_initiation_date")),
        "reason": (rec.get("reason_for_recall") or "").strip(),
        "reason_group": reason_group(rec.get("reason_for_recall")),
        "product_description": (rec.get("product_description") or "").strip(),
    }


def transform(records):
    seen, out = set(), []
    for r in records:
        row = clean(r)
        key = (row["recall_number"], row["event_id"])
        if not row["recall_number"] or key in seen:
            continue
        seen.add(key); out.append(row)
    return out
