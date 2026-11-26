"""End to end: extract -> transform -> load -> checks -> reports.

    python src/run.py 2023-01 2025-06
"""
import json, os, sys
from datetime import date
sys.path.insert(0, os.path.dirname(__file__))
from fdapipe.extract import extract
from fdapipe.transform import transform
from fdapipe.load import load, run_checks, run_reports


def ym(s):
    y, m = s.split("-"); return date(int(y), int(m), 1)


if __name__ == "__main__":
    start, end = ym(sys.argv[1]), ym(sys.argv[2])
    os.makedirs("data", exist_ok=True)
    n = extract(start, end, "data/raw_enforcement.jsonl")
    print("extracted", n)
    rows = transform(json.loads(l) for l in open("data/raw_enforcement.jsonl"))
    print("clean rows", len(rows))
    con = load(rows, "data/recalls.duckdb")
    checks = run_checks(con)
    for k, v in checks.items():
        print(("PASS " if v == 0 else "FAIL ") + k, v)
    for name, df in run_reports(con).items():
        df.to_csv(f"data/{name}.csv", index=False)
        print("\n" + name); print(df.head(12).to_string(index=False))
    if any(v for v in checks.values()):
        sys.exit("data quality checks failed")
