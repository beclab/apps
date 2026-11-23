"""studio.db: jobs and assets, kept apart from ComfyUI's own database."""
import json
import os
import sqlite3
import threading
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,            -- image | video | audio
  source TEXT NOT NULL,          -- upload | output | frame | trim | mask | edit | example
  name TEXT NOT NULL,
  path TEXT NOT NULL,
  mime TEXT NOT NULL,
  bytes INTEGER NOT NULL DEFAULT 0,
  width INTEGER, height INTEGER,
  duration REAL,
  has_audio INTEGER NOT NULL DEFAULT 0,
  poster TEXT,
  job_id TEXT,
  starred INTEGER NOT NULL DEFAULT 0,
  deleted INTEGER NOT NULL DEFAULT 0,
  created REAL NOT NULL,
  md5 TEXT,                      -- of the file as uploaded, before any conversion
  fps REAL,
  owner TEXT NOT NULL DEFAULT '' -- the Olares user (X-Bfl-User)
);
CREATE INDEX IF NOT EXISTS assets_created ON assets(created);
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,           -- stable across retries
  prompt_id TEXT NOT NULL DEFAULT '',
  attempt INTEGER NOT NULL DEFAULT 1,
  queued_at REAL,
  mode TEXT NOT NULL,
  variant TEXT NOT NULL,
  spec TEXT NOT NULL,            -- {prompt, mode, assets: [{id, role}], params, batch?, action?}
  used TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL,          -- queued | running | done | failed | cancelled | interrupted
  stage TEXT,
  step INTEGER, steps INTEGER,
  error TEXT,
  outputs TEXT NOT NULL DEFAULT '[]',
  parent_id TEXT, relation TEXT,
  starred INTEGER NOT NULL DEFAULT 0,
  deleted INTEGER NOT NULL DEFAULT 0,
  created REAL NOT NULL, started REAL, finished REAL,
  owner TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS jobs_created ON jobs(created);
CREATE INDEX IF NOT EXISTS jobs_status ON jobs(status);
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  dir TEXT NOT NULL,             -- the folder under each member's .users/<user>/
  owner TEXT NOT NULL,
  access TEXT NOT NULL DEFAULT 'invited',   -- invited | everyone
  default_role TEXT NOT NULL DEFAULT 'editor',
  archived INTEGER NOT NULL DEFAULT 0,
  created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS project_members (
  project_id TEXT NOT NULL,
  user TEXT NOT NULL,
  role TEXT NOT NULL,            -- admin | editor | viewer
  PRIMARY KEY (project_id, user)
);
"""

JSON_FIELDS = {"spec", "used", "error", "outputs"}
ACTIVE = ("queued", "running")
RETRYABLE = ("failed", "cancelled", "interrupted")

# An output can be moved independently of its job. Only images still in the
# job's space count toward its favorites filter or its legacy favorite action.
IMAGE_OUTPUTS = """
json_each(jobs.outputs) AS output JOIN assets AS a ON a.id=output.value
WHERE a.kind='image' AND a.source='output' AND a.deleted=0 AND a.job_id=jobs.id
  AND a.owner=jobs.owner AND a.project IS jobs.project
"""
IMAGE_FAVORITES = f"EXISTS (SELECT 1 FROM {IMAGE_OUTPUTS} AND a.starred=1)"


def _like(q):
    return "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _row(r):
    if r is None:
        return None
    d = dict(r)
    if "output_starred" in d:
        d["starred"] = d.pop("output_starred")
    for k in JSON_FIELDS & d.keys():
        d[k] = json.loads(d[k]) if d[k] else None
    for k in ("starred", "deleted", "has_audio"):
        if k in d:
            d[k] = bool(d[k])
    return d


class Store:
    def __init__(self, path, owner="", *, image_favorites=False):
        """owner takes the rows written before there were owners."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        self.image_favorites = image_favorites
        self._job_select = (f"SELECT jobs.*, {IMAGE_FAVORITES} AS output_starred FROM jobs"
                            if image_favorites else "SELECT * FROM jobs")
        with self.lock:
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA busy_timeout=5000")
            self.db.executescript(SCHEMA)
            cols = {r[1] for r in self.db.execute("PRAGMA table_info(assets)")}
            if "md5" not in cols:
                self.db.execute("ALTER TABLE assets ADD COLUMN md5 TEXT")
            if "fps" not in cols:
                self.db.execute("ALTER TABLE assets ADD COLUMN fps REAL")
            self.db.execute("CREATE INDEX IF NOT EXISTS assets_md5 ON assets(md5)")
            for table in ("assets", "jobs"):
                if "owner" not in {r[1] for r in self.db.execute("PRAGMA table_info(%s)" % table)}:
                    self.db.execute("ALTER TABLE %s ADD COLUMN owner TEXT NOT NULL DEFAULT ''" % table)
                if owner:
                    self.db.execute("UPDATE %s SET owner=? WHERE owner=''" % table, (owner,))
                self.db.execute("CREATE INDEX IF NOT EXISTS %s_owner ON %s(owner, created)" % (table, table))
                if "project" not in {r[1] for r in self.db.execute("PRAGMA table_info(%s)" % table)}:
                    self.db.execute("ALTER TABLE %s ADD COLUMN project TEXT" % table)
                self.db.execute("CREATE INDEX IF NOT EXISTS %s_project ON %s(project, created)" % (table, table))
            cols = {r[1] for r in self.db.execute("PRAGMA table_info(jobs)")}
            for name, typ in (("prompt_id", "TEXT NOT NULL DEFAULT ''"), ("attempt", "INTEGER NOT NULL DEFAULT 1"), ("queued_at", "REAL")):
                if name not in cols:
                    self.db.execute("ALTER TABLE jobs ADD COLUMN %s %s" % (name, typ))
            self.db.execute("UPDATE jobs SET prompt_id=id WHERE prompt_id=''")
            self.db.execute("UPDATE jobs SET queued_at=created WHERE queued_at IS NULL")
            self.db.execute("CREATE UNIQUE INDEX IF NOT EXISTS jobs_prompt_id ON jobs(prompt_id)")
            if image_favorites:
                # Consume the old job flags in the same transaction so an
                # image unfavorited after migration stays that way on restart.
                self.db.executescript(f"""
                    BEGIN IMMEDIATE;
                    UPDATE assets SET starred=1 WHERE starred=0 AND id IN (
                        SELECT a.id FROM jobs, {IMAGE_OUTPUTS} AND jobs.starred=1
                    );
                    UPDATE jobs SET starred=0 WHERE starred=1;
                    COMMIT;
                """)

    def _q(self, sql, args=()):
        with self.lock:
            return self.db.execute(sql, args).fetchall()

    def _x(self, sql, args=()):
        with self.lock:
            return self.db.execute(sql, args).rowcount

    # assets

    def add_asset(self, a):
        a = {"created": time.time(), "starred": 0, "deleted": 0, "has_audio": 0, **a}
        cols = ",".join(a)
        self._x("INSERT INTO assets (%s) VALUES (%s)" % (cols, ",".join("?" * len(a))), [int(v) if isinstance(v, bool) else v for v in a.values()])
        return self.asset(a["id"])

    def asset(self, aid):
        r = self._q("SELECT * FROM assets WHERE id=?", (aid,))
        return _row(r[0]) if r else None

    @staticmethod
    def _scope(sql, args, owner, project):
        """project: that project's rows; else owner's own, outside projects."""
        if project:
            args.append(project)
            return sql + " AND project=?"
        if owner is not None:
            args.append(owner)
            return sql + " AND owner=? AND project IS NULL"
        return sql

    def asset_by_md5(self, md5, owner=None, project=None):
        sql, args = "SELECT * FROM assets WHERE md5=? AND deleted=0", [md5]
        sql = self._scope(sql, args, owner, project)
        if project and owner is not None:
            sql += " AND owner=?"
            args.append(owner)
        for r in self._q(sql + " ORDER BY created DESC", args):
            if os.path.exists(r["path"]):
                return _row(r)
        return None

    def assets_without_md5(self):
        return [_row(r) for r in self._q("SELECT id, path FROM assets WHERE md5 IS NULL AND deleted=0")]

    def assets(self, kind=None, source=None, q=None, starred=None, before=None, limit=60, owner=None, project=None, after=None):
        sql, args = "SELECT * FROM assets WHERE deleted=0", []
        sql = self._scope(sql, args, owner, project)
        if kind:
            sql += " AND kind=?"
            args.append(kind)
        if source:
            sql += " AND source=?"
            args.append(source)
        else:
            sql += " AND source<>'mask'"
        if q:
            sql += " AND name LIKE ? ESCAPE '\\'"
            args.append(_like(q))
        if starred:
            sql += " AND starred=1"
        if before:
            sql += " AND created<?"
            args.append(float(before))
        if after:
            sql += " AND created>=?"
            args.append(float(after))
        sql += " ORDER BY created DESC LIMIT ?"
        args.append(int(limit))
        return [_row(r) for r in self._q(sql, args)]

    def update_asset(self, aid, **fields):
        if not fields:
            return self.asset(aid)
        sets = ",".join("%s=?" % k for k in fields)
        self._x("UPDATE assets SET %s WHERE id=?" % sets, [int(v) if isinstance(v, bool) else v for v in fields.values()] + [aid])
        return self.asset(aid)

    def asset_in_use(self, aid):
        for j in self.jobs_by_status(ACTIVE):
            if any(x.get("id") == aid for x in j["spec"].get("assets", [])):
                return True
        return False

    # jobs

    def add_job(self, j):
        j = {"created": time.time(), **j}
        j = {"prompt_id": j["id"], "queued_at": j["created"], **j}
        for k in JSON_FIELDS & j.keys():
            j[k] = json.dumps(j[k])
        cols = ",".join(j)
        self._x("INSERT INTO jobs (%s) VALUES (%s)" % (cols, ",".join("?" * len(j))), list(j.values()))
        return self.job(j["id"])

    def job(self, jid):
        r = self._q(self._job_select + " WHERE id=?", (jid,))
        return _row(r[0]) if r else None

    def job_by_prompt(self, prompt_id):
        r = self._q("SELECT * FROM jobs WHERE prompt_id=?", (prompt_id,))
        return _row(r[0]) if r else None

    def ids_by_prompt(self, prompt_ids):
        """{prompt_id: job id} for the prompts that belong to a job."""
        if not prompt_ids:
            return {}
        return dict(self._q("SELECT prompt_id, id FROM jobs WHERE prompt_id IN (%s)" % ",".join("?" * len(prompt_ids)), list(prompt_ids)))

    def retry_job(self, jid, attempt, prompt_id, used):
        """Atomically claim one execution, keeping the original job and batch."""
        changed = self._x(
            "UPDATE jobs SET prompt_id=?, attempt=attempt+1, queued_at=?, used=?, "
            "status='queued', stage='queued', step=NULL, steps=NULL, started=NULL, finished=NULL, error=NULL, outputs='[]' "
            "WHERE id=? AND attempt=? AND deleted=0 AND status IN (%s)" % ",".join("?" * len(RETRYABLE)),
            (prompt_id, time.time(), json.dumps(used), jid, attempt, *RETRYABLE))
        return self.job(jid) if changed else None

    def jobs(self, before=None, starred=None, limit=30, owner=None, project=None, after=None, q=None, ids=None):
        sql, args = self._job_select + " WHERE deleted=0 AND (relation IS NULL OR relation!='segment')", []
        sql = self._scope(sql, args, owner, project)
        if ids is not None:
            if not ids:
                return []
            sql += " AND id IN (%s)" % ",".join("?" * len(ids))
            args.extend(ids)
        if starred:
            sql += " AND status='done' AND output_starred=1" if self.image_favorites else " AND starred=1"
        if before:
            sql += " AND created<?"
            args.append(float(before))
        if after:
            sql += " AND created>=?"
            args.append(float(after))
        if q:
            sql += " AND json_extract(spec, '$.prompt') LIKE ? ESCAPE '\\'"
            args.append(_like(q))
        sql += " ORDER BY created DESC LIMIT ?"
        args.append(int(limit))
        return [_row(r) for r in self._q(sql, args)]

    def children(self, parent_id, relation):
        return [_row(r) for r in self._q("SELECT * FROM jobs WHERE parent_id=? AND relation=? ORDER BY created", [parent_id, relation])]

    def jobs_by_status(self, statuses):
        return [_row(r) for r in self._q("SELECT * FROM jobs WHERE status IN (%s) ORDER BY created" % ",".join("?" * len(statuses)), list(statuses))]

    def update_job(self, jid, **fields):
        if fields:
            for k in JSON_FIELDS & fields.keys():
                fields[k] = json.dumps(fields[k])
            sets = ",".join("%s=?" % k for k in fields)
            self._x("UPDATE jobs SET %s WHERE id=?" % sets, [int(v) if isinstance(v, bool) else v for v in fields.values()] + [jid])
        return self.job(jid)

    def star_job_outputs(self, jid, starred):
        """Support older image clients that favorite every output of a job."""
        return [_row(r) for r in self._q(f"""
            UPDATE assets SET starred=? WHERE starred<>? AND id IN (
                SELECT a.id FROM jobs, {IMAGE_OUTPUTS} AND jobs.id=? AND jobs.deleted=0
            ) RETURNING *
        """, (starred, starred, jid))]


    def projects_using(self, aid):
        """Projects of the jobs that take this asset."""
        like = "%%\"id\": \"%s\"%%" % aid
        return {r[0] for r in self._q("SELECT DISTINCT project FROM jobs WHERE deleted=0 AND project IS NOT NULL AND spec LIKE ?", (like,))}

    def project_active(self, pid):
        return bool(self._q("SELECT 1 FROM jobs WHERE project=? AND status IN (%s) LIMIT 1" % ",".join("?" * len(ACTIVE)), (pid,) + ACTIVE))

    def assets_of_project(self, pid):
        return [_row(r) for r in self._q("SELECT * FROM assets WHERE project=?", (pid,))]

    # projects

    def add_project(self, p):
        p = {"created": time.time(), "access": "invited", "default_role": "editor", "archived": 0, **p}
        self._x("INSERT INTO projects (%s) VALUES (%s)" % (",".join(p), ",".join("?" * len(p))), list(p.values()))
        return self.project(p["id"])

    def project(self, pid):
        r = self._q("SELECT * FROM projects WHERE id=?", (pid,)) if pid else None
        if not r:
            return None
        d = _row(r[0])
        d["archived"] = bool(d["archived"])
        d["members"] = {m["user"]: m["role"] for m in self._q("SELECT user, role FROM project_members WHERE project_id=?", (pid,))}
        return d

    def projects(self):
        return [self.project(r["id"]) for r in self._q("SELECT id FROM projects ORDER BY created")]

    def project_by_name(self, name):
        key = name.strip().casefold()
        return next((p for p in self.projects() if p["name"].strip().casefold() == key), None)

    def update_project(self, pid, **fields):
        if fields:
            sets = ",".join("%s=?" % k for k in fields)
            self._x("UPDATE projects SET %s WHERE id=?" % sets, [int(v) if isinstance(v, bool) else v for v in fields.values()] + [pid])
        return self.project(pid)

    def set_member(self, pid, user, role):
        if role:
            self._x("INSERT INTO project_members (project_id, user, role) VALUES (?, ?, ?) "
                    "ON CONFLICT(project_id, user) DO UPDATE SET role=excluded.role", (pid, user, role))
        else:
            self._x("DELETE FROM project_members WHERE project_id=? AND user=?", (pid, user))
        return self.project(pid)
