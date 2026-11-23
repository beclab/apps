"""Olares users and admins from LLDAP, as Router reads them: lldap-provider's
read-only snapshot, fetched with the Pod's service account token (the chart
binds it to the ClusterRole backend:lldap-provider). An admin is a member of
lldap_admin, which includes the owner."""
import json
import logging
import os
import threading
import time
import urllib.request

log = logging.getLogger("comfyapp.studio")

ADMIN_GROUP = "lldap_admin"
RESYNC = 30


class Directory:
    def __init__(self, url=None, token_file=None, fetch=None):
        self.url = (url if url is not None else os.environ.get("STUDIO_LLDAP_URL") or "").rstrip("/")
        self.token_file = token_file if token_file is not None else os.environ.get("STUDIO_SA_TOKEN") or ""
        self.fetch = fetch or self._fetch
        self.users = None
        self.at = 0
        self.lock = threading.Lock()

    def _fetch(self):
        headers = {}
        if self.token_file and os.path.exists(self.token_file):
            with open(self.token_file) as f:
                headers["Authorization"] = "Bearer " + f.read().strip()
        req = urllib.request.Request(self.url + "/readonly/snapshot", headers=headers)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=10) as r:
            return json.load(r)

    def refresh(self):
        """Fetch the snapshot unless the last one is fresh (worker thread).
        A failed fetch keeps the last good snapshot."""
        if not self.url or time.time() - self.at < RESYNC:
            return
        with self.lock:
            if time.time() - self.at < RESYNC:
                return
            self.at = time.time()
            try:
                data = self.fetch()
                self.users = {u["id"]: any(g.get("displayName") == ADMIN_GROUP for g in u.get("groups") or [])
                              for u in data.get("users") or [] if u.get("id")}
            except Exception as e:
                log.warning("studio: LLDAP snapshot from %s failed: %s", self.url, e)

    def names(self):
        return sorted(self.users or ())

    def lookup(self, name):
        """admin, user or unknown; None before any snapshot has loaded."""
        users = self.users
        if users is None:
            return None
        if name not in users:
            return "unknown"
        return "admin" if users[name] else "user"
