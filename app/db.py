import os
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

DSN = os.environ.get("DATABASE_URL", "postgresql://leads:leads@localhost:5434/leads")


@contextmanager
def connect():
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        yield conn


def fetch_all(query: str, params: tuple = ()) -> list[dict]:
    with connect() as conn:
        return conn.execute(query, params).fetchall()
