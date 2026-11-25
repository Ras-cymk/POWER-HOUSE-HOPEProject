from app.db import get_connection

PAGE_SIZE = 25
MAX_SEARCH = 100
DEFAULT_SORT = "custno"

# What each sort key orders by. Only these fixed pieces are ever put into the
# SQL text, never anything taken from the request.
SORT_COLUMNS = {
    "custno": "custno",
    "custname": "lower(custname)",
    "payterm": "payterm",
}


def like_pattern(term):
    """A pattern for  LIKE ... ESCAPE '!'  that finds the term anywhere in a value.

    The characters % _ and ! in the term are taken literally, so searching for
    "50%" does not match everything.
    """
    escaped = term.replace("!", "!!").replace("%", "!%").replace("_", "!_")
    return f"%{escaped}%"


def customer_page(term, payterm, sort, descending, page, page_size=PAGE_SIZE):
    """One page of the active customers that match the search and the pay-terms filter.

    Returns a dict with rows, total (all matches), page and pages (the page
    number is kept inside the real range), first and last (row numbers shown),
    pay_terms (every pay term in use, for the filter list) and payterm (the
    filter that was applied. It is ignored if it is not one of pay_terms).
    """
    order = SORT_COLUMNS.get(sort, SORT_COLUMNS[DEFAULT_SORT])
    direction = "DESC" if descending else "ASC"

    conn = get_connection()
    try:
        # One connection and one transaction for all three queries
        with conn, conn.cursor() as cur:
            cur.execute("SELECT DISTINCT payterm FROM customer_active WHERE payterm IS NOT NULL ORDER BY payterm")
            pay_terms = [r[0] for r in cur.fetchall()]
            applied = payterm if payterm in pay_terms else None

            conditions, params = [], []
            if term:
                pattern = like_pattern(term)
                conditions.append(
                    "(custno ILIKE %s ESCAPE '!' OR custname ILIKE %s ESCAPE '!' OR address ILIKE %s ESCAPE '!')"
                )
                params += [pattern, pattern, pattern]
            if applied:
                conditions.append("payterm = %s")
                params.append(applied)
            where = " AND ".join(conditions) or "TRUE"

            cur.execute(f"SELECT count(*) FROM customer_active WHERE {where}", params)
            total = cur.fetchone()[0]
            pages = max(1, -(-total // page_size))
            page = min(max(page, 1), pages)

            cur.execute(
                f"""SELECT custno, custname, address, payterm
                      FROM customer_active
                     WHERE {where}
                     ORDER BY {order} {direction}, custno ASC
                     LIMIT %s OFFSET %s""",
                params + [page_size, (page - 1) * page_size],
            )
            rows = [
                {"custno": r[0], "custname": r[1], "address": r[2], "payterm": r[3]}
                for r in cur.fetchall()
            ]
    finally:
        conn.close()

    first = (page - 1) * page_size + 1 if rows else 0
    return {
        "rows": rows,
        "total": total,
        "page": page,
        "pages": pages,
        "first": first,
        "last": first + len(rows) - 1 if rows else 0,
        "pay_terms": pay_terms,
        "payterm": applied,
    }
