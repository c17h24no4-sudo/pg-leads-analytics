from fastapi import FastAPI, HTTPException, Query

from app.db import fetch_all

app = FastAPI(title="pg-leads-analytics")

VIEWS = {
    "funnel": "SELECT * FROM funnel",
    "sources": "SELECT * FROM source_conversion ORDER BY win_rate_pct DESC",
    "managers": "SELECT * FROM manager_ranking ORDER BY place, name",
    "daily": "SELECT * FROM daily_leads",
}


@app.get("/stats/{name}")
def stats(name: str):
    query = VIEWS.get(name)
    if query is None:
        raise HTTPException(404, f"unknown report: {name}")
    return fetch_all(query)


@app.get("/leads")
def leads(source: str | None = None, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    # параметризованный запрос: значения не подставляются в SQL строкой
    return fetch_all(
        """
        SELECT l.id, l.source, m.name AS manager, l.amount, l.created_at,
               (SELECT stage FROM stage_events e WHERE e.lead_id = l.id ORDER BY at DESC LIMIT 1) AS stage
        FROM leads l
        JOIN managers m ON m.id = l.manager_id
        WHERE (%s::text IS NULL OR l.source = %s)
        ORDER BY l.created_at DESC, l.id
        LIMIT %s OFFSET %s
        """,
        (source, source, limit, offset),
    )
