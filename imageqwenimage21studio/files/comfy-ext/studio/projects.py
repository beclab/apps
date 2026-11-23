"""Who may see and change what, Runway style. A job or asset outside any
project is its owner's alone. Inside one, everyone with a role sees it; an
editor changes their own items, a project admin changes any. Olares admins
are admin of every project, but do not see anyone's private items."""
import re

ROLES = ("viewer", "editor", "admin")
ACCESS = ("invited", "everyone")
PRIVATE_DIR = "Private"
DIR_MAX = 60


def rank(role):
    return ROLES.index(role) + 1 if role in ROLES else 0


def role(project, user, admin=False):
    """The user's role in the project, or None."""
    if not project or not user:
        return None
    if admin or project["owner"] == user:
        return "admin"
    best = project["members"].get(user)
    if project["access"] == "everyone" and rank(project["default_role"]) > rank(best):
        best = project["default_role"]
    return best if best in ROLES else None


def can_add(project, user, admin=False):
    """May the user create jobs and assets in it (None: their private space)."""
    if project is None:
        return True
    return not project["archived"] and rank(role(project, user, admin)) >= rank("editor")


def can_view(item, project, user, admin=False):
    if not item.get("project"):
        return item.get("owner", "") == user
    return role(project, user, admin) is not None


def can_edit(item, project, user, admin=False):
    if not item.get("project"):
        return item.get("owner", "") == user
    if not project or project["archived"]:
        return False
    r = role(project, user, admin)
    return r == "admin" or (r == "editor" and item.get("owner", "") == user)


def dir_name(name, taken):
    """A folder name for the project, unique (case-insensitively) among taken."""
    base = re.sub(r'[\x00-\x1f/\\:*?"<>|]+', " ", name or "").strip().lstrip(".").strip()[:DIR_MAX] or "Project"
    used = {t.lower() for t in taken} | {PRIVATE_DIR.lower()}
    out, n = base, 1
    while out.lower() in used:
        n += 1
        out = "%s %d" % (base, n)
    return out
