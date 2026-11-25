import psycopg2
from flask import g, has_app_context

from app.config import DATABASE_URL


def _connect():
    return psycopg2.connect(DATABASE_URL, connect_timeout=10)


class _RequestConnection:
    """The connection shared by everything that runs during one web request.

    It behaves like a normal connection, but close() does nothing: the real
    connection is closed once, when the request ends (close_request_connection).
    That way the existing pattern keeps working unchanged:

        conn = get_connection()
        try:
            with conn, conn.cursor() as cur:
                ...
        finally:
            conn.close()
    """

    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        self._conn.__enter__()  # commits at the end of the block, or rolls back on an error
        return self

    def __exit__(self, *exc_info):
        return self._conn.__exit__(*exc_info)

    def close(self):
        pass

    def __getattr__(self, name):
        return getattr(self._conn, name)


def get_connection():
    """A database connection.

    During a web request every caller shares one, so a page that needs several
    queries connects once instead of once per query. Connecting to a remote
    database is the slow part. Outside a request (scripts, the shell) each call
    gets its own connection, as before.
    """
    if not has_app_context():
        return _connect()
    if "db_conn" not in g or g.db_conn.closed:
        g.db_conn = _connect()
    return _RequestConnection(g.db_conn)


def close_request_connection(error=None):
    """Registered in create_app. Closes the request's connection when the request ends."""
    conn = g.pop("db_conn", None)
    if conn is not None:
        conn.close()


def check_connection():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    finally:
        conn.close()
    print("connected")
