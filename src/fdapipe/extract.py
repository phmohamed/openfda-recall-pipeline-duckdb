"""Pull drug enforcement (recall) records from openFDA, one month at a time."""
import json, time, urllib.parse, urllib.request
from datetime import date

BASE = "https://api.fda.gov/drug/enforcement.json"
PAGE = 100  # openFDA rejects larger pages without an API key


def month_windows(start: date, end: date):
    """Yield (YYYYMMDD, YYYYMMDD) first and last day of each month from start to end."""
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        last = date.fromordinal(date(ny, nm, 1).toordinal() - 1)
        yield f"{y}{m:02d}01", last.strftime("%Y%m%d")
        y, m = ny, nm


def build_url(lo: str, hi: str, skip: int = 0, limit: int = PAGE) -> str:
    q = f"report_date:[{lo}+TO+{hi}]"
    return f"{BASE}?search={q}&limit={limit}&skip={skip}"


def fetch_json(url: str, retries: int = 3):
    for i in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:  # openFDA returns 404 when a window has no matches
                return {"results": [], "meta": {"results": {"total": 0}}}
            if i == retries - 1:
                raise
        except Exception:
            if i == retries - 1:
                raise
        time.sleep(2 * (i + 1))


def extract(start: date, end: date, out_path: str, fetch=fetch_json):
    n = 0
    with open(out_path, "w") as f:
        for lo, hi in month_windows(start, end):
            skip = 0
            while True:
                d = fetch(build_url(lo, hi, skip))
                rows = d.get("results", [])
                for r in rows:
                    f.write(json.dumps(r) + "\n"); n += 1
                if len(rows) < PAGE:
                    break
                skip += PAGE
    return n
