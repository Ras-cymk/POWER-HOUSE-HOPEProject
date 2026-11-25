from flask import url_for

from app.rights import granted_codes, load_catalogue

ROLE_NAMES = {"superadmin": "Superadmin", "admin": "Admin", "user": "User"}

# Modules that already have a real screen. The others use the placeholder page
# until their screens are built. Add a module here when its screen is ready.
MODULE_SCREENS = {"customer": "customers.customer_list"}


def module_url(module_code):
    """Where the menu and the tiles send a person for this module."""
    endpoint = MODULE_SCREENS.get(module_code)
    if endpoint:
        return url_for(endpoint)
    return url_for("modules.module_page", module_code=module_code)


def module_access(user):
    """Every module in screen order, with what this person may do in it.

    Each item has module_code, module_name, rights (each with perm_code, perm_name
    and granted), held and total (counts), and accessible (True when they hold at
    least one right in the module). Superadmins hold every right. This is the one
    place that decides who may open a module, so the menu, the tiles and the
    server check cannot disagree.
    """
    everything = user["role_code"] == "superadmin"
    granted = set() if everything else granted_codes(user["user_id"])
    modules = []
    for module in load_catalogue():
        rights = [
            {
                "perm_code": r["perm_code"],
                "perm_name": r["perm_name"],
                "granted": everything or r["perm_code"] in granted,
            }
            for r in module["rights"]
        ]
        held = sum(1 for r in rights if r["granted"])
        modules.append(
            {
                "module_code": module["module_code"],
                "module_name": module["module_name"],
                "rights": rights,
                "held": held,
                "total": len(rights),
                "accessible": held > 0,
            }
        )
    return modules


def build_nav(user, modules):
    """What the sidebar and the tiles show: the modules this person may open, and
    the User Management entry for admins and superadmins."""
    return {
        "modules": [m for m in modules if m["accessible"]],
        "can_manage_users": user["role_code"] in ("admin", "superadmin"),
    }
