import json

import psycopg2

from twin.pipeline.census2011 import Census2011Adapter
from twin.pipeline.base import run_pipeline
from twin.store.pg_sync import sync_to_postgres


def test_pg_sync_skips_without_dsn(tmp_paths):
    assert sync_to_postgres(tmp_paths, "") == {}


class _Cur:
    def __init__(self, log):
        self.log = log
        self.rowcount = 0

    def execute(self, sql, params=None):
        self.log.append(str(sql))

    def mogrify(self, sql, params=None):
        return str(sql).encode()

    def fetchall(self):
        return []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Conn:
    def __init__(self):
        self.log = []
        self.committed = False

    def cursor(self, *a, **k):
        return _Cur(self.log)

    def commit(self):
        self.committed = True

    def rollback(self):
        pass

    def close(self):
        pass


def test_pg_sync_writes_three_tables(ctx_census, monkeypatch):
    run_pipeline(Census2011Adapter(), ctx_census)
    conn = _Conn()
    monkeypatch.setattr(psycopg2, "connect", lambda dsn: conn)
    # execute_values drives cursor.execute/mogrify on our fake cursor
    from twin.store import pg_sync
    monkeypatch.setattr(pg_sync, "execute_values", lambda cur, sql, rows, template="", **k: cur.execute(sql + template))
    counts = sync_to_postgres(ctx_census.paths, "postgresql://fake")
    sql = "\n".join(conn.log)
    for t in ("twin_places", "twin_indicators", "dataset_versions"):
        assert f"INSERT INTO {t}" in sql and counts[t] > 0
    assert "ST_Multi(ST_GeomFromText" in sql and conn.committed
