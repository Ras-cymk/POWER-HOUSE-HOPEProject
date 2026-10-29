#!/usr/bin/env python3
"""Usage: python db/migrate.py [up|status]"""
import os, re, sys
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

MIG_DIR = Path(__file__).resolve().parent.parent / "supabase" / "migrations"
NAME_RE = re.compile(r"^(\d{14})_([a-z0-9_]+)\.sql$")
LOCK_ID = 727274  # arbitrary number; same for everyone

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "up"
    load_dotenv()
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL is missing. Copy .env.example to .env and fill it in.")

    files = sorted(p for p in MIG_DIR.glob("*.sql"))
    bad = [p.name for p in files if not NAME_RE.match(p.name)]
    if bad:
        sys.exit(f"Bad file name(s): {bad}. Use YYYYMMDDHHMMSS_description.sql")

    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("select pg_advisory_lock(%s)", (LOCK_ID,))
    cur.execute("""create schema if not exists supabase_migrations;
        create table if not exists supabase_migrations.schema_migrations (
            version text primary key, statements text[], name text);""")
    conn.commit()

    cur.execute("select version from supabase_migrations.schema_migrations")
    applied = {r[0] for r in cur.fetchall()}

    for p in files:
        version, name = NAME_RE.match(p.name).groups()
        done = version in applied
        if cmd == "status":
            print(("applied  " if done else "PENDING  ") + p.name)
            continue
        if done:
            continue
        print(f"Applying {p.name} ...")
        sql = p.read_text(encoding="utf-8")
        try:
            cur.execute(sql)
            cur.execute("insert into supabase_migrations.schema_migrations"
                        "(version, name, statements) values (%s,%s,%s)",
                        (version, name, [sql]))
            conn.commit()
        except Exception as e:
            conn.rollback()
            sys.exit(f"FAILED on {p.name}: {e}\nNothing from this file was applied.")
    print("Done.")
    cur.execute("select pg_advisory_unlock(%s)", (LOCK_ID,))
    conn.close()

if __name__ == "__main__":
    main()