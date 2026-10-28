"""Детерминированные тестовые данные: лиды, менеджеры, история стадий."""
import random
from datetime import datetime, timedelta, timezone

from app.db import connect

MANAGERS = ["Анна", "Борис", "Виктория", "Глеб"]
SOURCES = ["site", "telegram", "referral", "ads"]
# вероятность дойти до оплаты зависит от источника
WIN_CHANCE = {"referral": 0.5, "site": 0.3, "telegram": 0.25, "ads": 0.12}


def build(n_leads: int = 400, seed: int = 7, start: datetime | None = None):
    rng = random.Random(seed)
    start = start or datetime(2026, 9, 1, tzinfo=timezone.utc)
    leads, events = [], []
    for lead_id in range(1, n_leads + 1):
        source = rng.choice(SOURCES)
        manager_id = rng.randint(1, len(MANAGERS))
        amount = round(rng.choice([30000, 60000, 90000, 150000, 250000]) * rng.uniform(0.8, 1.2), 2)
        created = start + timedelta(days=rng.randint(0, 55), hours=rng.randint(8, 20), minutes=rng.randint(0, 59))
        leads.append((lead_id, source, manager_id, amount, created))
        events.append((lead_id, "new", created))
        t = created
        if rng.random() < 0.7:
            t += timedelta(hours=rng.randint(1, 48))
            events.append((lead_id, "qualified", t))
            if rng.random() < 0.6:
                t += timedelta(hours=rng.randint(4, 96))
                events.append((lead_id, "proposal", t))
                t += timedelta(hours=rng.randint(12, 240))
                final = "won" if rng.random() < min(0.9, WIN_CHANCE[source] * 1.8) else "lost"
                events.append((lead_id, final, t))
            else:
                t += timedelta(hours=rng.randint(4, 48))
                events.append((lead_id, "lost", t))
        else:
            t += timedelta(hours=rng.randint(2, 72))
            events.append((lead_id, "lost", t))
    return leads, events


def load(n_leads: int = 400, seed: int = 7) -> None:
    leads, events = build(n_leads, seed)
    with connect() as conn:
        conn.execute("TRUNCATE stage_events, leads, managers RESTART IDENTITY CASCADE")
        with conn.cursor() as cur:
            cur.executemany("INSERT INTO managers (name) VALUES (%s)", [(m,) for m in MANAGERS])
            cur.executemany(
                "INSERT INTO leads (id, source, manager_id, amount, created_at) VALUES (%s, %s, %s, %s, %s)",
                leads,
            )
            cur.executemany("INSERT INTO stage_events (lead_id, stage, at) VALUES (%s, %s, %s)", events)
        conn.commit()


if __name__ == "__main__":
    load()
    print("seeded")
