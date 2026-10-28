import pytest
from fastapi.testclient import TestClient

from app import seed
from app.api import app
from app.db import connect, fetch_all

try:
    with connect() as _c:
        _c.execute("SELECT 1")
    DB_UP = True
except Exception:
    DB_UP = False

pytestmark = pytest.mark.skipif(not DB_UP, reason="PostgreSQL недоступен: docker compose up -d")


@pytest.fixture(scope="module", autouse=True)
def data():
    seed.load(n_leads=400, seed=7)


def test_funnel_is_monotonic():
    rows = {r["stage"]: r["leads_count"] for r in fetch_all("SELECT * FROM funnel")}
    assert rows["new"] == 400
    assert rows["new"] >= rows["qualified"] >= rows["proposal"] >= rows["won"] > 0
    # каждый лид завершается либо won, либо lost
    assert rows["won"] + rows["lost"] == 400


def test_funnel_percent_of_all():
    rows = {r["stage"]: float(r["pct_of_all"]) for r in fetch_all("SELECT * FROM funnel")}
    assert rows["new"] == 100.0


def test_time_in_stage_has_no_negative_durations():
    bad = fetch_all("SELECT count(*) AS n FROM time_in_stage WHERE spent < interval '0'")
    assert bad[0]["n"] == 0
    # у последней стадии лида нет следующей: left_at пуст
    last = fetch_all("SELECT count(*) AS n FROM time_in_stage WHERE left_at IS NULL")
    assert last[0]["n"] == 400


def test_source_conversion_matches_raw_counts():
    expected = fetch_all(
        """SELECT l.source, count(*) AS won FROM leads l
           JOIN stage_events e ON e.lead_id = l.id AND e.stage = 'won' GROUP BY l.source"""
    )
    got = {r["source"]: r["won_count"] for r in fetch_all("SELECT * FROM source_conversion")}
    for row in expected:
        assert got[row["source"]] == row["won"]


def test_manager_ranking_shares_sum_to_100():
    rows = fetch_all("SELECT * FROM manager_ranking")
    assert len(rows) == 4
    assert abs(sum(float(r["share_pct"]) for r in rows) - 100.0) < 0.5
    assert min(r["place"] for r in rows) == 1


def test_daily_leads_covers_every_day_and_total():
    rows = fetch_all("SELECT * FROM daily_leads")
    assert sum(r["leads_count"] for r in rows) == 400
    days = [r["day"] for r in rows]
    assert all((b - a).days == 1 for a, b in zip(days, days[1:]))


def test_api_reports_and_unknown_report():
    client = TestClient(app)
    assert client.get("/stats/funnel").status_code == 200
    assert client.get("/stats/nope").status_code == 404


def test_api_leads_filter_and_injection_safe():
    client = TestClient(app)
    ok = client.get("/leads", params={"source": "ads", "limit": 5}).json()
    assert len(ok) == 5 and all(r["source"] == "ads" for r in ok)
    # значение с SQL-фрагментом трактуется как обычная строка и ничего не находит
    evil = client.get("/leads", params={"source": "ads' OR '1'='1"}).json()
    assert evil == []
    assert client.get("/leads", params={"limit": 1000}).status_code == 422
