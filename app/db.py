import psycopg2
from app.config import DATABASE_URL


def get_connection():
    return psycopg2.connect(DATABASE_URL, connect_timeout=10)


def check_connection():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    finally:
        conn.close()
    print("connected")