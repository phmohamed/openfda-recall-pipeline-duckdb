import os, sys, tempfile, unittest
from datetime import date
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from fdapipe.extract import month_windows, build_url, extract, PAGE
from fdapipe.transform import clean, transform, reason_group, parse_date
from fdapipe.load import load, run_checks, run_reports

REC = {"recall_number": "D-0001-2024", "event_id": 123, "classification": "Class II", "status": "Ongoing",
       "recalling_firm": "  Acme   Pharma ", "state": "nj", "country": "United States",
       "report_date": "20240115", "recall_initiation_date": "20231220",
       "reason_for_recall": "Failed dissolution specification at 12 month stability",
       "product_description": "Tablets", "voluntary_mandated": "Voluntary: Firm Initiated", "product_type": "Drugs"}


class TestExtract(unittest.TestCase):
    def test_month_windows_handle_year_end_and_leap(self):
        w = list(month_windows(date(2023, 12, 1), date(2024, 2, 1)))
        self.assertEqual(w, [("20231201", "20231231"), ("20240101", "20240131"), ("20240201", "20240229")])

    def test_url_has_range_and_skip(self):
        u = build_url("20240101", "20240131", skip=200)
        self.assertIn("report_date:[20240101+TO+20240131]", u); self.assertIn("skip=200", u)

    def test_paging_stops_on_short_page(self):
        calls = []
        def fake(url):
            calls.append(url)
            n = PAGE if "skip=0" in url else 3
            return {"results": [dict(REC, recall_number=f"D-{len(calls)}-{i}") for i in range(n)]}
        with tempfile.TemporaryDirectory() as d:
            n = extract(date(2024, 1, 1), date(2024, 1, 1), os.path.join(d, "x.jsonl"), fetch=fake)
        self.assertEqual(n, PAGE + 3); self.assertEqual(len(calls), 2)


class TestTransform(unittest.TestCase):
    def test_clean_normalises(self):
        r = clean(REC)
        self.assertEqual(r["recalling_firm"], "ACME PHARMA"); self.assertEqual(r["state"], "NJ")
        self.assertEqual(r["report_date"], date(2024, 1, 15)); self.assertEqual(r["reason_group"], "potency or dissolution")

    def test_bad_dates_become_none(self):
        self.assertIsNone(parse_date("2024-01-15")); self.assertIsNone(parse_date(None))

    def test_reason_rules(self):
        self.assertEqual(reason_group("Lack of sterility assurance"), "contamination")
        self.assertEqual(reason_group("Incorrect carton label"), "labeling or packaging")
        self.assertEqual(reason_group("something unusual"), "other")

    def test_dedupe_and_drop_missing_key(self):
        rows = transform([REC, dict(REC), dict(REC, recall_number="")])
        self.assertEqual(len(rows), 1)
        rows = transform([REC, dict(REC, event_id=124)])  # same number, different event: keep both
        self.assertEqual(len(rows), 2)


class TestLoad(unittest.TestCase):
    def setUp(self):
        recs = [REC,
                dict(REC, recall_number="D-0002-2024", classification="Class I", report_date="20240210",
                     recall_initiation_date="20240201", reason_for_recall="Microbial contamination"),
                dict(REC, recall_number="D-0003-2024", report_date="20240305", recall_initiation_date="20240301",
                     recalling_firm="Other Co", reason_for_recall="Mislabeled carton")]
        self.con = load(transform(recs))

    def test_checks_pass_on_clean_data(self):
        self.assertTrue(all(v == 0 for v in run_checks(self.con).values()))

    def test_checks_catch_bad_class_and_dates(self):
        self.con.execute("INSERT INTO recalls SELECT * REPLACE ('Class IV' AS classification, 'D-9' AS recall_number) FROM recalls LIMIT 1")
        self.con.execute("UPDATE recalls SET recall_initiation_date = DATE '2030-01-01' WHERE recall_number='D-0002-2024'")
        c = run_checks(self.con)
        self.assertEqual(c["classification is I, II or III"], 1); self.assertEqual(c["initiation not after report date"], 1)

    def test_reports(self):
        r = run_reports(self.con)
        self.assertEqual(int(r["reason_groups"].recalls.sum()), 3)
        self.assertEqual(int(r["monthly_by_class"].recalls.sum()), 3)
        d = r["days_to_report"].set_index("classification")
        self.assertEqual(d.loc["Class I", "median_days"], 9)


if __name__ == "__main__":
    unittest.main()
