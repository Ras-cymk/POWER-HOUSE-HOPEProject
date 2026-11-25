from flask import Blueprint, abort, render_template, request, url_for

from app.customers import DEFAULT_SORT, MAX_SEARCH, SORT_COLUMNS, customer_page
from app.navigation import build_nav, module_access
from app.security import current_user, login_required


customers_bp = Blueprint("customers", __name__)


@customers_bp.get("/customers")
@login_required
def customer_list():
    user = current_user()
    modules = module_access(user)
    # Anyone holding at least one Customer right may open the list: the rights
    # catalogue has no separate "view customer" right. This is the same rule as
    # the menu and @module_required, computed once and also used for the sidebar.
    if not any(m["accessible"] for m in modules if m["module_code"] == "customer"):
        abort(403)

    q = request.args.get("q", "").strip()[:MAX_SEARCH]
    sort = request.args.get("sort", DEFAULT_SORT)
    if sort not in SORT_COLUMNS:
        sort = DEFAULT_SORT
    descending = request.args.get("dir") == "desc"
    page = request.args.get("page", 1, type=int)  # anything that is not a number counts as 1

    data = customer_page(q, request.args.get("terms", ""), sort, descending, page)

    def link(**changes):
        """A link to this page that keeps the search, filter and sort. None leaves a value out."""
        args = {
            "q": q or None,
            "terms": data["payterm"],
            "sort": sort if sort != DEFAULT_SORT else None,
            "dir": "desc" if descending else None,
            "page": None,
        }
        args.update(changes)
        return url_for("customers.customer_list", **args)

    def page_link(number):
        return link(page=number if number > 1 else None)

    def sort_link(key):
        # Clicking the column that is sorted ascending flips it to descending
        return link(sort=key if key != DEFAULT_SORT else None, dir="desc" if sort == key and not descending else None, page=None)

    return render_template(
        "customers.html",
        nav=build_nav(user, modules),
        data=data,
        q=q,
        sort=sort,
        descending=descending,
        page_link=page_link,
        sort_link=sort_link,
        clear_link=url_for("customers.customer_list"),
    )
