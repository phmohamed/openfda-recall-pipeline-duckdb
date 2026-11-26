"""Load clean rows into DuckDB and run data quality checks and reporting queries."""
import duckdb

DDL = """
CREATE OR REPLACE TABLE recalls (
  recall_number VARCHAR, event_id VARCHAR, classification VARCHAR, status VARCHAR,
  recalling_firm VARCHAR, state VARCHAR, country VARCHAR, voluntary_mandated VARCHAR,
  product_type VARCHAR, report_date DATE, recall_initiation_date DATE,
  reason VARCHAR, reason_group VARCHAR, product_description VARCHAR)
"""

CHECKS = {
    "no duplicate recall keys": "SELECT count(*) FROM (SELECT recall_number, event_id FROM recalls GROUP BY 1,2 HAVING count(*)>1)",
    "no missing report_date": "SELECT count(*) FROM recalls WHERE report_date IS NULL",
    "classification is I, II or III": "SELECT count(*) FROM recalls WHERE classification NOT IN ('Class I','Class II','Class III')",
    "initiation not after report date": "SELECT count(*) FROM recalls WHERE recall_initiation_date > report_date",
    "no empty firm name": "SELECT count(*) FROM recalls WHERE recalling_firm = ''",
}

REPORTS = {
    "monthly_by_class": """
        SELECT date_trunc('month', report_date) AS month, classification, count(*) AS recalls
        FROM recalls GROUP BY 1,2 ORDER BY 1,2""",
    "reason_groups": """
        SELECT reason_group, count(*) AS recalls,
               round(100.0*count(*)/sum(count(*)) OVER (), 1) AS pct,
               count(*) FILTER (WHERE classification='Class I') AS class_i
        FROM recalls GROUP BY 1 ORDER BY recalls DESC""",
    "top_firms": """
        SELECT recalling_firm, count(*) AS recalls, count(DISTINCT event_id) AS events,
               count(*) FILTER (WHERE classification='Class I') AS class_i
        FROM recalls GROUP BY 1 ORDER BY recalls DESC LIMIT 15""",
    "days_to_report": """
        SELECT classification, count(*) AS n,
               median(date_diff('day', recall_initiation_date, report_date)) AS median_days,
               quantile_cont(date_diff('day', recall_initiation_date, report_date), 0.9) AS p90_days
        FROM recalls WHERE recall_initiation_date IS NOT NULL GROUP BY 1 ORDER BY 1""",
}


def load(rows, db_path=":memory:"):
    con = duckdb.connect(db_path)
    con.execute(DDL)
    if rows:
        cols = list(rows[0].keys())
        con.executemany(f"INSERT INTO recalls VALUES ({','.join('?'*len(cols))})", [[r[c] for c in cols] for r in rows])
    return con


def run_checks(con):
    return {name: con.execute(sql).fetchone()[0] for name, sql in CHECKS.items()}


def run_reports(con):
    return {name: con.execute(sql).df() for name, sql in REPORTS.items()}
