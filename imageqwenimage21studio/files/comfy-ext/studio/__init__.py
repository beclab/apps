"""The studio backend: /studio/api/* routes inside ComfyUI.

Jobs and assets live in studio.db so every device sees the same queue and
history across restarts. The app is an Olares shared app: each job and asset
belongs to the user in X-Bfl-User and is theirs alone unless it is in a
project (projects.py). Execution
events are taken from PromptServer's send_sync (ComfyUI only sends them to the
submitting socket) and fanned out over SSE.
"""
import asyncio
import collections
import hashlib
import importlib
import importlib.util
import json
import logging
import os
import random
import re
import shutil
import time
import uuid
from urllib.parse import quote

from aiohttp import ClientError, ClientSession, ClientTimeout, web

from . import graph, llm, media, projects
from .directory import RESYNC, Directory
from .llm import Llm, LlmError
from .store import ACTIVE, RETRYABLE, Store

log = logging.getLogger("comfyapp.studio")

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
CLIENT_ID = "comfyapp-studio"
UPLOAD_LIMIT = 512 << 20
DISK_LOW = 5 << 30
MAX_COUNT = 4
LLM_IMAGES = 6
NAME_MAX = 80
IMAGE_OUTPUT_NAME_MAX = 10
# mask: a painted inpaint mask; edit: an image the front end prepared (the
# expand canvas).
UPLOAD_SOURCES = ("upload", "mask", "edit")
EXAMPLE_MIME = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
    ".mp4": "video/mp4", ".webm": "video/webm",
    ".m4a": "audio/mp4", ".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg", ".opus": "audio/ogg", ".flac": "audio/flac",
}

STAGES = [
    ("sampling", ("SamplerCustomAdvanced", "KSampler", "KSamplerAdvanced", "SamplerCustom")),
    ("decoding", ("VAEDecode", "VAEDecodeAudio", "VAEDecodeTiled", "CreateVideo")),
    ("encoding", ("CLIPTextEncode", "ImageScaleToTotalPixels", "GetVideoComponents")),
    ("loading", ("UNETLoader", "CLIPLoader", "VAELoader", "DualCLIPLoader", "CheckpointLoaderSimple", "LoadImage", "LoadVideo", "LoadAudio")),
    ("saving", ("SaveVideo", "SaveImage", "SaveAudio", "SaveAnimatedWEBP")),
]


def with_profile_stages(profile):
    """STAGES plus the model node classes profile.stages adds."""
    extra = (profile or {}).get("stages") or {}
    return [(name, tuple(extra.get(name) or ()) + classes) for name, classes in STAGES]


MD5_RE = re.compile(r"^[0-9a-f]{32}$")
# An Olares local name; it names the user's folder under .users.
USER_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")
# nginx adds it to every /studio/api/ request it proxies.
EDGE_HEADER = "X-Studio-Edge"
LOOPBACK = ("127.0.0.1", "::1")


def file_md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stage_of(cls, stages=STAGES):
    for name, classes in stages:
        if cls in classes:
            return name
    if "Sampler" in cls:
        return "sampling"
    if "Decode" in cls:
        return "decoding"
    if "Loader" in cls or cls.startswith("Load"):
        return "loading"
    if cls.startswith("Save"):
        return "saving"
    return None


def clean_name(s, fallback):
    s = re.sub(r"[\x00-\x1f/\\]+", " ", s or "").strip()
    return (s or fallback)[:NAME_MAX]


def load_hooks():
    """studio/app_hooks.py from the app's studio/hooks.py, or None."""
    name = __name__ + ".app_hooks"
    if importlib.util.find_spec(name) is None:
        return None
    return importlib.import_module(name)


class Bus:
    """Numbered events with a replay buffer for Last-Event-ID."""

    def __init__(self, keep=2000):
        self.seq = 0
        self.buf = collections.deque(maxlen=keep)
        self.subs = set()

    def publish(self, kind, data, audience=None):
        """audience: None for everyone, else (owner, project) or an owner."""
        self.seq += 1
        ev = (self.seq, kind, data, audience)
        self.buf.append(ev)
        for q in list(self.subs):
            try:
                q.put_nowait(ev)
            except asyncio.QueueFull:
                self.subs.discard(q)

    def since(self, last):
        if last >= self.seq:
            return []
        if not self.buf or self.buf[0][0] > last + 1:
            return None
        return [ev for ev in self.buf if ev[0] > last]


class Studio:
    def __init__(self, server):
        import folder_paths
        from comfy.cli_args import args

        self.server = server
        self.queue = server.prompt_queue
        self.base = "http://127.0.0.1:%d" % args.port
        with open(os.path.join(PKG, "studio.json")) as f:
            self.cfg = json.load(f)
        self.variants = {v["id"]: v for v in self.cfg.get("variants") or []}
        self.preferred = os.environ.get("STUDIO_VARIANT") or self.cfg.get("defaultVariant") or ""
        self.device = os.environ.get("STUDIO_DEVICE") or ""
        self.console = (os.environ.get("STUDIO_CONSOLE") or "http://127.0.0.1:8090").rstrip("/")
        self.admin = os.environ.get("STUDIO_ADMIN") or ""
        self.directory = Directory()
        self.installed_at = 0
        self.installed_ids = None
        self.flows = self.cfg["flows"]
        self.kind = self.flows[0].get("output") or "video"
        self.profile = self.cfg.get("profile") or {}
        self.examples_dir = os.environ.get("STUDIO_EXAMPLES") or ""
        self.examples = {x["id"]: x for x in self.profile.get("examples") or []} if self.examples_dir else {}
        self.rewrite_modes = llm.modes(self.kind, self.profile.get("promptTemplate"), self.profile.get("prompts"))
        self.stages = with_profile_stages(self.profile)
        self.samplers = set(self.stages[0][1])
        self.hooks = load_hooks()
        self.apis = {}
        for f in self.flows:
            with open(os.path.join(PKG, "flows", f["api"])) as fh:
                self.apis[f["mode"]] = json.load(fh)
        data = os.environ.get("STUDIO_DATA") or os.path.join(folder_paths.base_path, "studio-data")
        self.data = data
        self.llm = Llm(os.environ.get("STUDIO_LLM_BASE_URL"), os.environ.get("STUDIO_LLM_MODEL"), os.environ.get("STUDIO_LLM_API_KEY"),
                       state=os.path.join(data, "studio", "llm.json"))
        self.input_dir = folder_paths.get_input_directory()
        self.output_dir = folder_paths.get_output_directory()
        self.poster_dir = os.path.join(data, "studio", "posters")
        os.makedirs(self.poster_dir, exist_ok=True)
        os.makedirs(self.input_dir, exist_ok=True)
        self.store = Store(os.path.join(data, "db", "studio.db"), self.admin,
                           image_favorites=self.kind == "image" and not self.profile.get("composer"))
        self.bus = Bus()
        self.events = asyncio.Queue()
        self.classes = {}
        self.cancelling = set()
        self.posting = set()
        self.joining = set()
        self.spawning = set()
        self.tasks = set()
        self.queue_dirty = False
        self.booted = time.time()
        self.warm = False
        self.http = None

    # helpers

    async def run(self, fn, *a, **kw):
        return await asyncio.get_running_loop().run_in_executor(None, lambda: fn(*a, **kw))

    async def post(self, path, body):
        return await self.call("POST", self.base + path, body)

    async def call(self, method, url, body=None):
        if self.http is None:
            self.http = ClientSession(timeout=ClientTimeout(total=120))
        async with self.http.request(method, url, json=body) as r:
            try:
                data = await r.json(content_type=None)
            except Exception:
                data = {"error": (await r.text())[:2000]}
            return r.status, data

    def replace_of(self, variant, mode=None):
        v = self.variants.get(variant) or {}
        out = dict(v.get("replace") or {})
        out.update((v.get("replaceModes") or {}).get(mode) or {})
        return out

    async def installed(self, *, wanted=None):
        """Variant ids whose models the console reports done, or None when
        it does not say (no groups, or unreachable)."""
        cached = self.installed_ids
        fresh = time.time() - self.installed_at < 3
        # The picker can see a finished download before this cache expires.
        if fresh and (not wanted or cached is None or wanted in cached):
            return cached
        ids = None
        try:
            status, data = await self.call("GET", self.console + "/api/status")
            groups = data.get("groups") if status == 200 and isinstance(data, dict) else None
            if groups:
                ids = [g["id"] for g in groups if g.get("state") == "done"]
        except Exception as e:
            log.warning("studio: console status: %s", e)
        if ids is None and fresh:
            return cached
        self.installed_at, self.installed_ids = time.time(), ids
        return ids

    async def job_variant(self, params):
        """The job's precision: params.variant, else the preferred one, else
        the first installed."""
        if not self.variants:
            return ""
        asked = params.get("variant")
        v = asked or self.preferred
        if v not in self.variants:
            raise graph.JobError("bad_variant", "Unknown precision", variant=v)
        ok = await self.installed(wanted=asked)
        if ok is not None and v not in ok:
            if asked:
                raise graph.JobError("variant_missing", "This precision is not downloaded", variant=v)
            v = next((x for x in self.variants if x in ok), v)
        return v

    def disk(self):
        try:
            u = shutil.disk_usage(self.data)
            return {"free": u.free, "total": u.total, "low": u.free < DISK_LOW}
        except OSError:
            return None

    def check_disk(self):
        if (self.disk() or {}).get("low"):
            raise graph.JobError("disk_low", "Less than 5 GB of disk left")

    def queue_snapshot(self):
        running, queued = self.queue.get_current_queue_volatile()
        ids = self.store.ids_by_prompt([x[1] for x in (*running, *queued)])
        return {"running": [ids.get(x[1], x[1]) for x in running],
                "pending": [ids.get(x[1], x[1]) for x in sorted(queued, key=lambda x: x[0])]}

    @staticmethod
    def aud(item):
        return item.get("owner", ""), item.get("project")

    def publish_job(self, job):
        if job and job.get("relation") == "segment":
            self.mirror(job)
        elif job:
            self.job_view(job, publish=True)

    def later(self, coro):
        t = asyncio.ensure_future(coro)
        self.tasks.add(t)
        t.add_done_callback(self.tasks.discard)

    def publish_asset(self, asset):
        if asset:
            self.bus.publish("asset", asset, self.aud(asset))

    def user_of(self, request):
        """The Olares user behind the request: X-Bfl-User, which the Olares
        edge sets after login and strips from clients. Without it only a
        script in the Pod (loopback, not through nginx) acts as the admin;
        anyone else is None."""
        headers = getattr(request, "headers", None) or {}
        user = (headers.get("X-Bfl-User") or "").strip()
        if user:
            return user if USER_RE.match(user) else None
        if headers.get(EDGE_HEADER) or getattr(request, "remote", "127.0.0.1") not in LOOPBACK:
            return None
        return getattr(self, "admin", "")

    def lookup(self, user):
        d = getattr(self, "directory", None)
        return d.lookup(user) if d and user else None

    def is_admin(self, request):
        """An admin in LLDAP (lldap_admin), as Router decides; the installer
        while the directory has not been reachable."""
        user = self.user_of(request)
        found = self.lookup(user)
        if found in ("admin", "user"):
            return found == "admin"
        admin = getattr(self, "admin", "")
        return not admin or user == admin

    def authed(self, handler):
        async def h(request):
            user = self.user_of(request)
            if user is None:
                return self.err(401, "no_user", "Open the app from your Olares desktop")
            if self.lookup(user) == "unknown":
                return self.err(401, "unknown_directory_user", "This user is not in the Olares directory")
            return await handler(request)
        return h

    async def directory_loop(self):
        while True:
            await asyncio.get_event_loop().run_in_executor(None, self.directory.refresh)
            await asyncio.sleep(RESYNC)

    def user_dir(self, root, owner):
        """root/.users/<owner>: Olares Files shows a user only their own
        folder under .users (from 1.12.9)."""
        d = os.path.join(root, ".users", owner or "_")
        os.makedirs(d, exist_ok=True)
        return d

    def space_path(self, owner, project, kind):
        """input/.users/<owner>/<Private or the project's folder>/<kind>."""
        return os.path.join(self.input_dir, ".users", owner or "_", project["dir"] if project else projects.PRIVATE_DIR, kind)

    def space_dir(self, owner, project, kind):
        d = self.space_path(owner, project, kind)
        os.makedirs(d, exist_ok=True)
        return d

    def viewer(self, request):
        return self.user_of(request), self.is_admin(request)

    def project_of(self, item):
        return self.store.project(item.get("project")) if item and item.get("project") else None

    def sees_asset(self, a, user, admin=False):
        """Its own rules, or an input of a project job the user sees."""
        if projects.can_view(a, self.project_of(a), user, admin):
            return True
        return any(projects.role(self.store.project(pid), user, admin) for pid in self.store.projects_using(a["id"]))

    def job_for(self, request, jid, edit=False):
        job = self.store.job(jid)
        if not job:
            return None
        check = projects.can_edit if edit else projects.can_view
        return job if check(job, self.project_of(job), *self.viewer(request)) else None

    def asset_for(self, request, aid, edit=False):
        a = self.store.asset(aid)
        if not a:
            return None
        user, admin = self.viewer(request)
        ok = projects.can_edit(a, self.project_of(a), user, admin) if edit else self.sees_asset(a, user, admin)
        return a if ok else None

    def writable(self, pid, user, admin):
        """(project, None) for a project the user may add to, (None, None) for
        their private space, or (None, error response)."""
        if not pid:
            return None, None
        p = self.store.project(pid)
        if not p or not projects.role(p, user, admin):
            return None, self.err(404, "no_project", "No such project")
        if not projects.can_add(p, user, admin):
            return None, self.err(403, "read_only", "You cannot add to this project")
        return p, None

    def derived_project(self, a, user, admin):
        p = self.project_of(a)
        return p if p and projects.can_add(p, user, admin) else None

    def relocate(self, path, owner, old_dir, new_dir):
        """path moved from one space folder of owner's to another, or None
        when it is not in old_dir."""
        path = os.path.abspath(path)
        for root in {os.path.abspath(self.input_dir), os.path.abspath(self.output_dir)}:
            base = os.path.join(root, ".users", owner or "_")
            old = os.path.join(base, old_dir) + os.sep
            if path.startswith(old):
                return os.path.join(base, new_dir, path[len(old):])
        return None

    def move_asset(self, a, project):
        """Into project, or the owner's private space for None, file and all
        (worker thread)."""
        old = self.project_of(a)
        fields = {"project": project["id"] if project else None}
        dst = self.relocate(a["path"], a.get("owner", ""), old["dir"] if old else projects.PRIVATE_DIR,
                            project["dir"] if project else projects.PRIVATE_DIR)
        if dst and os.path.exists(a["path"]):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            os.replace(a["path"], dst)
            fields["path"] = dst
        return self.store.update_asset(a["id"], **fields)

    def rename_dirs(self, p, new_dir):
        """Rename the project's folder in every user's space (worker thread)."""
        for root in {os.path.abspath(self.input_dir), os.path.abspath(self.output_dir)}:
            users = os.path.join(root, ".users")
            for u in os.listdir(users) if os.path.isdir(users) else []:
                src = os.path.join(users, u, p["dir"])
                if os.path.isdir(src):
                    os.replace(src, os.path.join(users, u, new_dir))
        for a in self.store.assets_of_project(p["id"]):
            dst = self.relocate(a["path"], a.get("owner", ""), p["dir"], new_dir)
            if dst:
                self.store.update_asset(a["id"], path=dst)

    def input_name(self, asset):
        """The file name, relative to the input directory, a loader node
        takes for this asset."""
        p = os.path.abspath(asset["path"])
        root = os.path.abspath(self.input_dir)
        if os.path.commonpath((p, root)) == root:
            return os.path.relpath(p, root)
        dst = os.path.join(self.space_dir(asset.get("owner", ""), self.project_of(asset), "uploads"),
                           "st-%s%s" % (asset["id"], os.path.splitext(p)[1]))
        name = os.path.relpath(dst, root)
        if not os.path.exists(dst):
            try:
                os.link(p, dst)
            except OSError:
                shutil.copyfile(p, dst)
        return name

    def estimate(self, flow, items, params, variant):
        """Seconds from the app hooks when they cover this device, else None."""
        if not self.hooks or not hasattr(self.hooks, "estimate"):
            return None
        devices = getattr(self.hooks, "DEVICES", None)
        if devices is not None and self.device not in devices:
            return None
        p, _ = graph.resolve_params(flow, params, items, self.profile)
        try:
            s = self.hooks.estimate(flow["mode"], variant, p.get("resolution") or "",
                                    float(p.get("duration") or 5), p.get("aspect") or "",
                                    items, p.get("prompt") or "")
        except Exception:
            log.exception("studio: app_hooks.estimate failed")
            return None
        return round(float(s)) if s is not None else None

    # asset registration

    def _ingest(self, tmp, filename, source, owner="", job_id=None, keep_path=False, md5=None, project=None):
        """Probe a file, move it into place and make its poster (worker thread)."""
        aid = uuid.uuid4().hex
        md5 = md5 or file_md5(tmp)
        src = tmp
        if os.path.splitext(filename)[1].lower() in media.HEIC_EXT:
            png = tmp + ".png"
            media.heic_to_png(tmp, png)
            os.remove(tmp)
            src = png
        info = media.probe(src)
        if keep_path:
            path = src
        else:
            path = os.path.join(self.space_dir(owner, project, "uploads"), "st-%s%s" % (aid, info["ext"]))
            if media.needs_normalize(src, info):
                path = os.path.splitext(path)[0] + ".mp4"
                media.trim(src, path, 0, info["duration"] or 3600)
                os.remove(src)
                info = media.probe(path)
            else:
                os.replace(src, path)
        poster = None
        try:
            poster = media.poster(path, info["kind"], os.path.join(self.user_dir(self.poster_dir, owner), aid + ".webp"), info["duration"])
        except Exception as e:
            log.warning("studio: poster for %s failed: %s", path, e)
        name = clean_name(os.path.splitext(filename)[0], info["kind"])
        if source == "output" and info["kind"] == "image":
            name = name[:IMAGE_OUTPUT_NAME_MAX].rstrip()
        return {
            "id": aid, "kind": info["kind"], "source": source,
            "name": name,
            "path": path, "mime": info["mime"], "bytes": os.path.getsize(path),
            "width": info["width"], "height": info["height"], "duration": info["duration"],
            "has_audio": info["has_audio"], "poster": poster, "job_id": job_id, "md5": md5, "owner": owner,
            "fps": info.get("fps"),
            "project": project["id"] if project else None,
        }

    def backfill_md5(self):
        for a in self.store.assets_without_md5():
            try:
                self.store.update_asset(a["id"], md5=file_md5(a["path"]))
            except OSError:
                pass

    # jobs

    def resolve_items(self, assets, owner=None, admin=False):
        items = []
        seen = set()
        for x in assets or []:
            a = self.store.asset(str(x.get("id", "")))
            role = x.get("role")
            if not a or a["deleted"] or (owner is not None and not self.sees_asset(a, owner, admin)):
                raise graph.JobError("asset_missing", "An asset was deleted", asset=x.get("id"))
            if role not in graph.ASSET_ROLES:
                raise graph.JobError("bad_role", "Unknown asset role", role=role)
            if graph.ROLE_KIND[role] != a["kind"]:
                raise graph.JobError("wrong_kind", "This asset cannot take that role", asset=a["id"], role=role)
            if (a["id"], role) in seen:
                continue
            seen.add((a["id"], role))
            it = {"id": a["id"], "role": role, "kind": a["kind"], "duration": a["duration"],
                  "has_audio": a["has_audio"], "asset": a}
            if role == "ref_image" and x.get("tag") in self.ref_tags:
                it["tag"] = x["tag"]
            items.append(it)
        return items

    @property
    def ref_tags(self):
        return {t["id"] for t in self.profile.get("refTags") or []}

    def plan(self, body, owner=None, admin=False):
        items = self.resolve_items(body.get("assets"), owner, admin)
        params = body.get("params") or {}
        graph.segment_items(items, params)
        speed = params.get("speed")
        aspect = graph.aspect_route(params.get("aspect"), items, self.profile.get("aspectDefault"))
        flow = graph.pick_flow(self.flows, items, body.get("mode") or "auto", speed if speed in graph.SPEEDS else None, aspect)
        return flow, items

    async def submit(self, body, parent_id=None, relation=None, owner="", admin=False, project=None):
        flow, items = self.plan(body, owner, admin)
        params = dict(body.get("params") or {})
        params["prompt"] = body.get("prompt", "")
        count = max(1, min(MAX_COUNT, int(body.get("count") or 1)))
        spec = {"prompt": body.get("prompt", ""), "mode": body.get("mode") or "auto",
                "assets": [{"id": it["id"], "role": it["role"], **({"tag": it["tag"]} if it.get("tag") else {})} for it in items],
                "params": body.get("params") or {}}
        if count > 1:
            spec["batch"] = uuid.uuid4().hex
        if body.get("action"):
            spec["action"] = str(body["action"])[:32]
        jobs = []
        variant = await self.job_variant(params)
        size = graph.output_size(flow, items, params, self.profile)
        segs = self.segments_of(flow, items, params, variant, size)
        graph.check_output(self.profile, variant, size, None if segs else items)
        before = await self.enhance_source(flow, items, params, owner, project)
        if segs:
            job = await self.submit_segments(flow, items, params, variant, segs, spec, before,
                                             parent_id or body.get("parent_id"), relation or body.get("relation"), owner, project)
            self.queue_dirty = True
            return [job]
        for i in range(count):
            p = dict(params)
            if p.get("seed") not in (None, "") and count > 1:
                p["seed"] = int(p["seed"]) + i
            jid = str(uuid.uuid4())
            prompt, used = self.assemble(flow, jid, items, p, variant, owner, project)
            if before:
                used["before"] = before
            job = self.store.add_job({"id": jid, "mode": flow["mode"], "variant": variant, "spec": spec, "used": used,
                                      "status": "queued", "stage": "queued", "parent_id": parent_id or body.get("parent_id"),
                                      "relation": relation or body.get("relation"), "owner": owner,
                                      "project": project["id"] if project else None})
            jobs.append(await self.enqueue(job, prompt))
        return jobs

    def assemble(self, flow, jid, items, params, variant, owner, project):
        """graph.assemble for one execution, writing into the owner's or project's outputs."""
        return graph.assemble(flow, self.apis[flow["mode"]], jid, items, params, self.replace_of(variant, flow["mode"]),
                              file_of=lambda it: self.input_name(it["asset"]),
                              names={it["id"]: it["asset"]["name"] for it in items}, profile=self.profile,
                              prefix="%s/" % os.path.relpath(self.space_path(owner, project, "outputs"), self.input_dir))

    async def enqueue(self, job, prompt):
        jid, pid = job["id"], job["prompt_id"]
        self.classes[jid] = {k: v.get("class_type", "") for k, v in prompt.items()}
        self.posting.add(pid)
        try:
            status, resp = await self.post("/prompt", {"prompt": prompt, "prompt_id": pid, "client_id": CLIENT_ID,
                                                       "extra_data": {"studio_job": jid}})
            if status != 200 and self.store.job(jid)["prompt_id"] == pid:
                self.finish(jid, "failed", self.prompt_error(resp))
        except (ClientError, OSError, asyncio.TimeoutError):
            # A lost response does not mean the engine rejected the prompt.
            # Let queue/history reconciliation settle it before another attempt.
            log.warning("studio: submission response lost for %s", pid, exc_info=True)
        finally:
            self.posting.discard(pid)
            self.queue_dirty = True
        job = self.store.job(jid)
        self.publish_job(job)
        return job

    def segments_of(self, flow, items, params, variant, size):
        """graph.plan_segments for a whole video the flow can slice itself,
        or None (a preview, a flow without segment roles, no ffmpeg to join)."""
        if graph.segment_of(params) or not graph.has_role(flow, "segment_start") or not media.ffmpeg():
            return None
        return graph.plan_segments(self.profile, variant, size, items)

    async def submit_segments(self, flow, items, params, variant, segs, spec, before, parent_id, relation, owner, project):
        """A parent job without a prompt and one hidden child per segment,
        all queued now so the models stay loaded between them."""
        pid = str(uuid.uuid4())
        p = dict(params)
        if p.get("seed") in (None, ""):
            p["seed"] = random.randrange(graph.MAX_SEED)
        used = {"seed": int(p["seed"]), "segments": [dict(s, job=None) for s in segs]}
        if before:
            used["before"] = before
        self.store.add_job({"id": pid, "mode": flow["mode"], "variant": variant, "spec": spec, "used": used,
                            "status": "running", "stage": "queued", "step": None, "steps": None, "started": time.time(),
                            "parent_id": parent_id, "relation": relation, "owner": owner,
                            "project": project["id"] if project else None})
        self.spawning.add(pid)
        try:
            for i in range(len(segs)):
                if self.store.job(pid)["status"] not in ACTIVE:
                    break
                await self.submit_segment(pid, i, flow, items, p, variant, spec, owner, project)
        finally:
            self.spawning.discard(pid)
        return self.job_view(self.store.job(pid), publish=True)

    async def submit_segment(self, pid, i, flow, items, params, variant, spec, owner, project):
        parent = self.store.job(pid)
        segs = parent["used"]["segments"]
        s = segs[i]
        cid = str(uuid.uuid4())
        p = dict(params, segment={"start": s["start"], "duration": s["duration"]})
        prompt, used = self.assemble(flow, cid, items, p, variant, owner, project)
        self.classes[cid] = {k: v.get("class_type", "") for k, v in prompt.items()}
        self.store.add_job({"id": cid, "mode": flow["mode"], "variant": variant, "spec": spec, "used": used,
                            "status": "queued", "stage": "queued", "parent_id": pid, "relation": "segment", "owner": owner,
                            "project": project["id"] if project else None})
        segs[i] = dict(s, job=cid)
        self.store.update_job(pid, used=dict(parent["used"], segments=segs))
        status, resp = await self.post("/prompt", {"prompt": prompt, "prompt_id": cid, "client_id": CLIENT_ID,
                                                   "extra_data": {"studio_job": cid}})
        if status != 200:
            self.store.update_job(cid, status="failed", finished=time.time(), error=self.prompt_error(resp))
            await self.advance(pid)

    def job_view(self, job, publish=False):
        """A job as the front end sees it: a segmented parent carries
        segments {done, total}; segment children are never published."""
        if not job or job.get("relation") == "segment":
            return job
        segs = (job.get("used") or {}).get("segments")
        if segs:
            kids = {c["id"]: c for c in self.store.children(job["id"], "segment")}
            job = dict(job, segments={"done": sum((kids.get(s["job"]) or {}).get("status") == "done" for s in segs), "total": len(segs)})
        if publish:
            self.bus.publish("job", job, self.aud(job))
        return job

    def parts_of(self, parent):
        """(path, skip, keep) of each segment's result, or None while one is missing."""
        segs = parent["used"]["segments"]
        parts = []
        for i, s in enumerate(segs):
            c = self.store.job(s["job"]) if s.get("job") else None
            files = [f for f in ((c or {}).get("used") or {}).get("files") or [] if os.path.exists(f)]
            if not c or c["status"] != "done" or not files:
                return None
            parts.append((files[0], s["skip"], s["keep"] if i < len(segs) - 1 else None))
        return parts

    async def advance(self, pid):
        """Moves a segmented parent on after one of its children changed:
        fails it when a segment did not finish, joins the results once all did."""
        parent = self.store.job(pid)
        if not parent or parent["status"] not in ACTIVE or pid in self.joining:
            return
        kids = [self.store.job(s["job"]) if s.get("job") else None for s in parent["used"]["segments"]]
        bad = next((c for c in kids if c and c["status"] in ("failed", "cancelled", "interrupted")), None)
        if bad:
            i = kids.index(bad)
            self.finish(pid, "failed", dict(bad.get("error") or {"code": bad["status"]}, code="segment_failed",
                                            segment=i + 1, segments=len(kids), cause=(bad.get("error") or {}).get("code") or bad["status"]))
            for c in kids:
                if c and c["status"] in ACTIVE:
                    await self.cancel(c["id"])
            return
        if not all(c and c["status"] == "done" for c in kids):
            self.job_view(self.store.job(pid), publish=True)
            return
        parts = self.parts_of(parent)
        if not parts:
            self.finish(pid, "failed", {"code": "segment_lost", "message": "A segment's result is missing"})
            return
        self.joining.add(pid)
        try:
            self.job_view(self.store.update_job(pid, stage="saving", step=None, steps=None), publish=True)
            src = next((x for x in parent["spec"].get("assets") or [] if x.get("role") == "source_video"), None)
            a = self.store.asset(src["id"]) if src else None
            first = parts[0][0]
            dst = os.path.join(os.path.dirname(first), "%s-%s.mp4" % (os.path.splitext(os.path.basename(first))[0], pid[:8]))
            await self.run(media.join, parts, a["path"], dst, 0, a["duration"])
            rel = os.path.relpath(dst, self.output_dir)
            await self.add_outputs(self.store.job(pid), {"videos": [{"filename": os.path.basename(rel), "subfolder": os.path.dirname(rel),
                                                                      "type": "output"}]})
            self._rm(*[p for p, _, _ in parts])
            self.finish(pid, "done")
        except (media.MediaError, OSError, TypeError) as e:
            self.finish(pid, "failed", {"code": "join_failed", "message": str(e)[:300]})
        finally:
            self.joining.discard(pid)

    def mirror(self, child):
        """Shows a running segment's stage and steps on its parent."""
        parent = self.store.job(child["parent_id"])
        if parent and parent["status"] in ACTIVE and parent["id"] not in self.joining:
            self.job_view(self.store.update_job(parent["id"], stage=child["stage"] or "queued", step=child["step"], steps=child["steps"]),
                          publish=True)

    async def enhance_source(self, flow, items, params, owner=None, project=None):
        """What a result is compared with: {asset, offset} of the source video
        or image. A preview of a flow that cannot cut the video itself runs on
        a clip trimmed here, which replaces the source in items."""
        src = next((it for it in items if it["role"] in graph.SOURCE_ROLES), None)
        if not src:
            return None
        seg = graph.segment_of(params) if src["role"] == "source_video" else None
        if not seg:
            return {"asset": src["id"], "offset": 0}
        if graph.has_role(flow, "segment_start"):
            return {"asset": src["id"], "offset": seg[0]}
        a = src["asset"]
        end = min(seg[0] + seg[1], a["duration"] or seg[0] + seg[1])
        tmp = os.path.join(self.input_dir, ".trim-%s.mp4" % uuid.uuid4().hex)
        try:
            await self.run(media.trim, a["path"], tmp, seg[0], end)
            n = await self.run(self._ingest, tmp, "%s %.1f-%.1fs.mp4" % (a["name"], seg[0], end), "trim", owner=owner, project=project)
        except media.MediaError as e:
            self._rm(tmp)
            raise graph.JobError("trim_failed", str(e)[:300])
        clip = self.store.add_asset(n)
        self.publish_asset(clip)
        src.update(id=clip["id"], duration=clip["duration"], has_audio=clip["has_audio"], asset=clip)
        return {"asset": clip["id"], "offset": 0}

    def prompt_error(self, resp):
        err = resp.get("error") if isinstance(resp, dict) else None
        msg = err.get("message") if isinstance(err, dict) else str(err or resp)[:500]
        details = []
        for nid, ne in ((resp or {}).get("node_errors") or {}).items():
            for e in ne.get("errors", []):
                details.append("%s: %s %s" % (ne.get("class_type", nid), e.get("message", ""), e.get("details", "")))
        return {"code": "invalid", "message": msg, "details": details[:8]}

    # ComfyUI events

    def on_comfy(self, event, data):
        if event == "status":
            self.queue_dirty = True
            return
        if isinstance(data, dict) and data.get("prompt_id"):
            self.events.put_nowait((event, data))

    async def event_loop(self):
        while True:
            event, data = await self.events.get()
            try:
                await self.handle(event, data)
            except Exception:
                log.exception("studio: handling %s", event)

    async def handle(self, event, data):
        job = self.store.job_by_prompt(data["prompt_id"])
        if not job or job["status"] not in ACTIVE:
            return
        jid = job["id"]
        now = time.time()
        if job["stage"] == "cancelling" and event in ("executing", "progress"):
            return
        if event == "execution_start":
            self.queue_dirty = True
            self.publish_job(self.store.update_job(jid, status="running", stage="loading", started=now))
        elif event == "executing":
            node = data.get("node")
            if node is None:
                return
            st = stage_of(self.classes.get(jid, {}).get(node, ""), self.stages)
            if st and st != job["stage"]:
                fields = {"stage": st}
                if st == "sampling" and job["step"] is None:
                    fields.update(step=0)
                self.publish_job(self.store.update_job(jid, **fields))
        elif event == "progress":
            cls = self.classes.get(jid, {}).get(data.get("node"), "")
            if cls in self.samplers or job["stage"] == "sampling":
                self.store.update_job(jid, stage="sampling", step=data.get("value"), steps=data.get("max"))
                target = self.store.job(job["parent_id"]) if job.get("relation") == "segment" else job
                if target:
                    self.bus.publish("progress", {"id": target["id"], "attempt": target["attempt"], "stage": "sampling",
                                                  "step": data.get("value"), "steps": data.get("max")}, self.aud(target))
        elif event == "executed":
            await self.add_outputs(job, data.get("output") or {})
        elif event == "execution_success":
            self.warm = True
            self.finish(jid, "done")
        elif event == "execution_error":
            msg = str(data.get("exception_message", ""))
            code = "oom" if "out of memory" in msg.lower() or "outofmemory" in data.get("exception_type", "").lower() else "node_error"
            self.finish(jid, "failed", {"code": code, "node_type": data.get("node_type"), "message": msg[:2000]})
        elif event == "execution_interrupted":
            self.finish(jid, "cancelled" if jid in self.cancelling else "interrupted",
                        None if jid in self.cancelling else {"code": "interrupted", "message": "Interrupted"})

    def finish(self, jid, status, error=None):
        self.cancelling.discard(jid)
        self.classes.pop(jid, None)
        self.queue_dirty = True
        fields = {"status": status, "finished": time.time()}
        if error:
            fields["error"] = error
        if status == "done":
            fields["stage"] = None
        job = self.store.update_job(jid, **fields)
        self.publish_job(job)
        if job and job.get("relation") == "segment":
            self.later(self.advance(job["parent_id"]))

    def _chip_name(self, m):
        a = self.store.asset(m.group(1))
        return os.path.splitext(a["name"])[0] if a else ""

    def _source_label(self, job):
        src = next((x for x in job["spec"].get("assets") or [] if x.get("role") in graph.SOURCE_ROLES), None)
        a = self.store.asset(src["id"]) if src else None
        if not a:
            return ""
        scale = (job.get("used") or {}).get("scale")
        return "%s ×%g" % (a["name"], scale) if scale else a["name"]

    async def add_outputs(self, job, ui):
        files = []
        for v in ui.values():
            if isinstance(v, list):
                files += [x for x in v if isinstance(x, dict) and x.get("filename") and x.get("type", "output") == "output"]
        if job.get("relation") == "segment":
            paths = [os.path.join(self.output_dir, f.get("subfolder") or "", f["filename"]) for f in files]
            known = (job.get("used") or {}).get("files") or []
            new = [p for p in paths if p not in known and os.path.exists(p)]
            if new:
                self.store.update_job(job["id"], used=dict(job["used"], files=known + new))
            return
        outs = list(job["outputs"] or [])
        known = {self.store.asset(a)["path"] for a in outs if self.store.asset(a)}
        for f in files:
            path = os.path.join(self.output_dir, f.get("subfolder") or "", f["filename"])
            if path in known or not os.path.exists(path):
                continue
            label = graph.TOKEN.sub(self._chip_name, job["spec"].get("prompt") or "").strip().split("\n")[0] or self._source_label(job)
            try:
                a = await self.run(self._ingest, path, clean_name(label, job["mode"]) + os.path.splitext(path)[1], "output",
                                   owner=job.get("owner", ""), job_id=job["id"], keep_path=True, project=self.project_of(job))
            except Exception as e:
                log.warning("studio: output %s: %s", path, e)
                continue
            if self.store.job(job["id"])["prompt_id"] != job["prompt_id"]:
                return
            asset = self.store.add_asset(a)
            self.publish_asset(asset)
            outs.append(asset["id"])
        if outs != (job["outputs"] or []):
            self.publish_job(self.store.update_job(job["id"], outputs=outs))

    async def queue_loop(self):
        last = None
        while True:
            await asyncio.sleep(0.3)
            if not self.queue_dirty:
                continue
            self.queue_dirty = False
            snap = self.queue_snapshot()
            if snap != last:
                last = snap
                self.bus.publish("queue", snap)

    async def reconcile(self):
        snap = self.queue_snapshot()
        live = set(snap["running"]) | set(snap["pending"])
        for job in self.store.jobs_by_status(ACTIVE):
            jid = job["id"]
            segs = (job.get("used") or {}).get("segments")
            if segs:
                if jid not in self.spawning and not all(x.get("job") for x in segs):
                    self.finish(jid, "interrupted", {"code": "lost", "message": "Studio restarted before all segments were queued"})
                    for x in segs:
                        c = self.store.job(x["job"]) if x.get("job") else None
                        if c and c["status"] in ACTIVE:
                            await self.cancel(c["id"])
                else:
                    await self.advance(jid)
                continue
            pid = job["prompt_id"]
            if jid in live or pid in self.posting:
                continue
            hist = self.queue.get_history(prompt_id=pid).get(pid)
            if hist:
                await self.add_outputs(job, {k: v for o in (hist.get("outputs") or {}).values() for k, v in o.items()})
                if self.store.job(jid)["prompt_id"] != pid:
                    continue
                st = (hist.get("status") or {}).get("status_str")
                if st == "success":
                    self.finish(jid, "done")
                else:
                    err = next((d for e, d in (hist.get("status") or {}).get("messages", []) if e == "execution_error"), None)
                    if err:
                        self.finish(jid, "failed", {"code": "oom" if "out of memory" in str(err.get("exception_message", "")).lower() else "node_error",
                                                    "node_type": err.get("node_type"), "message": str(err.get("exception_message", ""))[:2000]})
                    else:
                        self.finish(jid, "cancelled" if jid in self.cancelling else "interrupted",
                                    None if jid in self.cancelling else {"code": "interrupted", "message": "Interrupted"})
            elif time.time() - job["queued_at"] > 15:
                self.finish(jid, "interrupted", {"code": "lost", "message": "ComfyUI restarted before the job finished"})

    async def reconcile_loop(self):
        while True:
            try:
                await self.reconcile()
            except Exception:
                log.exception("studio: reconcile")
            await asyncio.sleep(15)

    # routes

    def routes(self, r):
        P = "/studio/api"
        a = self.authed
        r.get(P + "/health")(a(self.h_health))
        r.get(P + "/events")(a(self.h_events))
        r.get(P + "/jobs")(a(self.h_jobs))
        r.post(P + "/jobs")(a(self.h_submit))
        r.post(P + "/preflight")(a(self.h_preflight))
        r.get(P + "/jobs/{id}")(a(self.h_job))
        r.patch(P + "/jobs/{id}")(a(self.h_job_patch))
        r.delete(P + "/jobs/{id}")(a(self.h_job_delete))
        r.post(P + "/jobs/{id}/cancel")(a(self.h_cancel))
        r.post(P + "/jobs/{id}/retry")(a(self.h_retry))
        r.post(P + "/uploads")(a(self.h_upload))
        r.get(P + "/assets")(a(self.h_assets))
        r.get(P + "/assets/by-md5/{md5}")(a(self.h_asset_by_md5))
        r.get(P + "/assets/{id}")(a(self.h_asset))
        r.patch(P + "/assets/{id}")(a(self.h_asset_patch))
        r.delete(P + "/assets/{id}")(a(self.h_asset_delete))
        r.post(P + "/assets/{id}/trim")(a(self.h_trim))
        r.post(P + "/frames")(a(self.h_frame))
        r.get(P + "/media/{id}")(a(self.h_media))
        r.get(P + "/poster/{id}")(a(self.h_poster))
        r.post(P + "/free")(a(self.h_free))
        r.get(P + "/examples/{id}/files/{file}")(a(self.h_example_file))
        r.post(P + "/examples/{id}/use")(a(self.h_example_use))
        r.post(P + "/prompt/rewrite")(a(self.h_rewrite))
        r.get(P + "/llm/models")(a(self.h_llm_models))
        r.put(P + "/llm/model")(a(self.h_llm_model))
        r.put(P + "/models/{variant}")(a(self.h_model_add))
        r.delete(P + "/models/{variant}")(a(self.h_model_delete))
        r.get(P + "/projects")(a(self.h_projects))
        r.post(P + "/projects")(a(self.h_project_add))
        r.patch(P + "/projects/{id}")(a(self.h_project_patch))
        r.put(P + "/projects/{id}/members/{user}")(a(self.h_member_put))
        r.delete(P + "/projects/{id}/members/{user}")(a(self.h_member_delete))
        r.get(P + "/users")(a(self.h_users))

    @staticmethod
    def err(status, code, message, **extra):
        return web.json_response({"error": {"code": code, "message": message, **extra}}, status=status)

    async def body(self, request):
        try:
            b = await request.json()
            return b if isinstance(b, dict) else {}
        except Exception:
            return {}

    async def h_health(self, request):
        flows = []
        for f in self.flows:
            flows.append({"mode": f["mode"], "label": f.get("label") or f["mode"], "output": f.get("output") or self.kind, "route": f.get("route") or {},
                          "roles": graph.flow_roles(f, self.profile), "speed": (f.get("route") or {}).get("speed") or "",
                          "aspect": (f.get("route") or {}).get("aspect") or "",
                          "autogrow": [g["role"] for g in f.get("autogrow") or []]})
        return web.json_response({
            "ok": True, "name": self.cfg.get("name"), "title": self.cfg.get("title"), "meta": self.cfg.get("meta"),
            "kind": self.kind, "composer": self.profile.get("composer") or "", "actions": self.profile.get("actions") or [],
            "variant": self.preferred, "variants": [{"id": v["id"], "label": v["label"]} for v in self.variants.values()] or None,
            "flows": flows, "tiers": list(graph.tiers(self.profile)), "uploadLimit": UPLOAD_LIMIT, "maxCount": MAX_COUNT,
            "profile": {k: self.profile.get(k) for k in ("strings", "promptTemplate", "aspectDefault", "videoWorkspace", "fixedScale", "outputLimit", "outputPixelFrames")
                        if self.profile.get(k)},
            "refTags": [t["id"] for t in self.profile.get("refTags") or []],
            "examples": [self.example_info(x) for x in self.examples.values()],
            "ffmpeg": bool(media.ffmpeg()), "segmentFull": bool(media.ffmpeg()) and any(graph.has_role(f, "segment_start") for f in self.flows),
            "queue": self.queue_snapshot(), "disk": self.disk(), "seq": self.bus.seq,
            "warm": self.warm, "time": time.time(), "user": self.user_of(request), "admin": self.is_admin(request),
            "llm": dict(self.llm.status(), modes=list(self.rewrite_modes)) if self.rewrite_modes else {"ready": False, "modes": []},
        })

    async def h_rewrite(self, request):
        b = await self.body(request)
        text = (b.get("prompt") or "").strip()
        if not text:
            return self.err(400, "bad_request", "A prompt is required")
        mode, task, flow = b.get("mode") or "", b.get("task") or "generate", b.get("flow") or ""
        system = llm.system_prompt(mode, self.kind, self.profile.get("promptTemplate"), task, flow, self.profile.get("prompts"),
                                   text)
        if not system:
            return self.err(400, "bad_mode", "Unknown rewrite mode")
        assets, images = await self.rewrite_assets(b.get("assets") or [], mode != "translate_en", *self.viewer(request))
        user = llm.job_text(text, self.kind, flow, b.get("duration"), b.get("aspect") or "", task, assets,
                            mode != "translate_en" and mode.endswith("_en"))
        t0 = time.time()
        try:
            fields = llm.sampling(mode, self.kind, task, self.llm.model, self.llm.effort, self.llm.info())
            labels = {a["label"]: a["token"] for a in assets if a.get("label")}
            out = await self.llm.rewrite(text, system, user, images, fields, labels=labels)
        except LlmError as e:
            log.info("studio: rewrite %s/%s failed after %.1fs: %s", mode, flow or task, time.time() - t0, e.code)
            return self.err(e.status, e.code, e.message)
        log.info("studio: rewrite %s/%s with %d images in %.1fs", mode, flow or task, len(images), time.time() - t0)
        return web.json_response({"prompt": out})

    async def rewrite_assets(self, items, attach, owner=None, admin=False):
        """The tray as job_text assets, and (token, data URL) pairs for the
        images, and the posters of videos, the chat model is shown."""
        tokens = self.profile.get("tokens") or {}
        rows = []
        for it in items[:16]:
            a = self.store.asset(it.get("id") or "") if isinstance(it, dict) else None
            if a and not a.get("deleted") and it.get("role") != "mask" and (owner is None or self.sees_asset(a, owner, admin)):
                rows.append((it.get("role") or "", a))
        edge = 1024 if sum(a["kind"] != "audio" for _, a in rows) <= 3 else 768
        loop = asyncio.get_event_loop()
        out, images, n, seen = [], [], {}, set()
        for role, a in rows:
            tok, label = "{{%s}}" % a["id"], ""
            if tokens.get(role) and a["id"] not in seen:
                n[role] = n.get(role, 0) + 1
                label = tokens[role].replace("{n}", str(n[role]))
            seen.add(a["id"])
            src = a["path"] if a["kind"] == "image" else a.get("poster") if a["kind"] == "video" else None
            attached = ""
            if attach and src and os.path.exists(src) and len(images) < LLM_IMAGES:
                try:
                    images.append((tok, await loop.run_in_executor(None, media.data_url, src, edge)))
                    attached = "image attached" if a["kind"] == "image" else "a frame of it attached"
                except Exception as e:
                    log.info("studio: rewrite skips %s: %s", a["id"], e)
            out.append({"token": tok, "role": role, "kind": a["kind"], "name": a.get("name"), "duration": a.get("duration"),
                        "label": label, "attached": attached})
        return out, images

    async def h_llm_models(self, request):
        if request.query.get("refresh"):
            await self.llm.probe()
        return web.json_response(dict(self.llm.status(), models=self.llm.models))

    async def h_llm_model(self, request):
        if not self.is_admin(request):
            return self.err(403, "admin_only", "Only the admin can change this")
        b = await self.body(request)
        model = (b.get("model") or "").strip()
        if not model:
            return self.err(400, "bad_request", "A model is required")
        effort = b.get("effort")
        self.llm.select(model, effort.strip() if isinstance(effort, str) else None)
        return web.json_response(dict(self.llm.status(), models=self.llm.models))

    async def h_events(self, request):
        resp = web.StreamResponse(headers={"Content-Type": "text/event-stream", "Cache-Control": "no-cache",
                                           "X-Accel-Buffering": "no"})
        await resp.prepare(request)
        q = asyncio.Queue(maxsize=5000)
        self.bus.subs.add(q)
        user, admin = self.viewer(request)

        def visible(aud):
            if aud is None:
                return True
            owner, project = aud if isinstance(aud, tuple) else (aud, None)
            if project:
                return projects.role(self.store.project(project), user, admin) is not None
            return owner == user

        async def send(ev):
            seq, kind, data, aud = ev
            if not visible(aud):
                return
            await resp.write(("id: %d\nevent: %s\ndata: %s\n\n" % (seq, kind, json.dumps(data, separators=(",", ":")))).encode())

        try:
            await resp.write(b"retry: 3000\n\n")
            last = request.headers.get("Last-Event-ID") or request.query.get("last")
            replay = None
            if last and last.isdigit():
                replay = self.bus.since(int(last))
            if replay is None:
                await send((self.bus.seq, "hello", {"seq": self.bus.seq, "queue": self.queue_snapshot(), "resync": bool(last)}, None))
            else:
                for ev in replay:
                    await send(ev)
            while True:
                try:
                    ev = await asyncio.wait_for(q.get(), 15)
                except asyncio.TimeoutError:
                    if q not in self.bus.subs:
                        break
                    await resp.write(b"event: ping\ndata: {}\n\n")
                    continue
                await send(ev)
        except (ConnectionResetError, asyncio.CancelledError, RuntimeError):
            pass
        finally:
            self.bus.subs.discard(q)
        return resp

    async def h_jobs(self, request):
        q = request.query
        user, admin = self.viewer(request)
        pid = q.get("project") or None
        if pid and not projects.role(self.store.project(pid), user, admin):
            return self.err(404, "no_project", "No such project")
        jobs = self.store.jobs(q.get("before"), q.get("starred") == "1", min(100, int(q.get("limit", 30))), owner=user, project=pid,
                               after=q.get("after"), q=q.get("q"))
        ids = {a["id"] for j in jobs for a in j["spec"].get("assets", [])} | {o for j in jobs for o in j["outputs"] or []}
        assets = {}
        for aid in ids:
            a = self.store.asset(aid)
            if a:
                assets[aid] = a
        return web.json_response({"jobs": [self.job_view(j) for j in jobs], "assets": assets, "queue": self.queue_snapshot(), "seq": self.bus.seq})

    async def h_asset(self, request):
        a = self.asset_for(request, request.match_info["id"])
        return web.json_response(a) if a else self.err(404, "not_found", "No such asset")

    async def h_job(self, request):
        job = self.job_for(request, request.match_info["id"])
        return web.json_response(self.job_view(job)) if job else self.err(404, "not_found", "No such job")

    async def h_submit(self, request):
        body = await self.body(request)
        try:
            self.check_disk()
            user, admin = self.viewer(request)
            project, denied = self.writable(body.get("project"), user, admin)
            if denied:
                return denied
            jobs = await self.submit(body, owner=user, admin=admin, project=project)
        except graph.JobError as e:
            return web.json_response({"error": e.as_dict()}, status=400)
        return web.json_response({"jobs": jobs})

    async def h_preflight(self, request):
        body = await self.body(request)
        params = dict(body.get("params") or {}, prompt=body.get("prompt", ""))
        try:
            flow, items = self.plan(body, *self.viewer(request))
            variant = await self.job_variant(params)
            size = graph.output_size(flow, items, params, self.profile)
            output = {"width": size[0], "height": size[1], "scale": size[2]} if size else None
            segs = self.segments_of(flow, items, params, variant, size)
            graph.check_output(self.profile, variant, size, None if segs else items)
            if segs and output:
                output["segments"] = len(segs)
        except graph.JobError as e:
            return web.json_response({"ok": False, "error": e.as_dict(), "disk": self.disk()})
        est = self.estimate(flow, items, params, variant)
        resolved, sources = graph.resolve_params(flow, params, items, self.profile)
        count = max(1, min(MAX_COUNT, int(body.get("count") or 1)))
        warnings = []
        disk = self.disk()
        if disk and disk["low"]:
            warnings.append({"code": "disk_low"})
        return web.json_response({"ok": True, "mode": flow["mode"], "label": flow.get("label"), "variant": variant, "estimate": est,
                                  "total": est * count if est is not None else None, "warnings": warnings, "disk": disk, "output": output,
                                  "params": {**{k: resolved[k] for k in ("aspect", "duration", "resolution") if k in resolved}, "sources": sources}})

    async def h_job_patch(self, request):
        body = await self.body(request)
        jid = request.match_info["id"]
        job = self.job_for(request, jid, edit=True)
        if not job:
            return self.err(404, "not_found", "No such job")
        fields = {}
        if "starred" in body and not self.store.image_favorites:
            fields["starred"] = bool(body["starred"])
        if "project" in body and (body["project"] or None) != job.get("project"):
            if job["status"] in ACTIVE:
                return self.err(409, "active", "Wait for the job to finish")
            project, denied = self.writable(body["project"], *self.viewer(request))
            if denied:
                return denied
            gone = self.aud(job)
            for aid in job["outputs"] or []:
                a = self.store.asset(aid)
                if a and a.get("owner", "") == job.get("owner", ""):
                    self.publish_asset(await self.run(self.move_asset, a, project))
            fields["project"] = project["id"] if project else None
            self.bus.publish("job_deleted", {"id": jid}, gone)
        job = self.store.update_job(jid, **fields)
        if "starred" in body and self.store.image_favorites:
            for asset in self.store.star_job_outputs(jid, bool(body["starred"])):
                self.publish_asset(asset)
            job = self.store.job(jid)
        self.publish_job(job)
        return web.json_response(job)

    async def h_job_delete(self, request):
        jid = request.match_info["id"]
        job = self.job_for(request, jid, edit=True)
        if not job:
            return self.err(404, "not_found", "No such job")
        if job["status"] in ACTIVE:
            return self.err(409, "active", "Cancel the job first")
        self.store.update_job(jid, deleted=True)
        for c in self.store.children(jid, "segment"):
            self._rm(*((c.get("used") or {}).get("files") or []))
            self.store.update_job(c["id"], deleted=True)
        self.bus.publish("job_deleted", {"id": jid}, self.aud(job))
        return web.json_response({"ok": True})

    async def h_cancel(self, request):
        jid = request.match_info["id"]
        job = self.job_for(request, jid, edit=True)
        if not job:
            return self.err(404, "not_found", "No such job")
        if job["status"] not in ACTIVE:
            return web.json_response(job)
        await self.cancel(jid)
        return web.json_response(self.job_view(self.store.job(jid)))

    async def cancel(self, jid):
        job = self.store.job(jid)
        segs = (job.get("used") or {}).get("segments")
        if segs:
            self.finish(jid, "cancelled")
            for s in segs:
                c = self.store.job(s["job"]) if s.get("job") else None
                if c and c["status"] in ACTIVE:
                    await self.cancel(c["id"])
            return
        self.cancelling.add(jid)
        snap = self.queue_snapshot()
        if jid in snap["running"]:
            self.publish_job(self.store.update_job(jid, stage="cancelling"))
        await self.post("/api/jobs/%s/cancel" % job["prompt_id"], {})
        if jid not in snap["running"] and self.store.job(jid)["prompt_id"] == job["prompt_id"]:
            self.finish(jid, "cancelled")

    async def h_retry(self, request):
        job = self.job_for(request, request.match_info["id"], edit=True)
        if not job:
            return self.err(404, "not_found", "No such job")
        body = await self.body(request)
        attempt = body.get("attempt")
        if type(attempt) is not int or attempt < 1:
            return self.err(400, "bad_attempt", "Invalid retry attempt")
        if attempt != job["attempt"] or job["status"] not in RETRYABLE:
            return web.json_response({"jobs": [self.job_view(job)]})
        user, admin = self.viewer(request)
        if (job.get("used") or {}).get("segments"):
            try:
                return web.json_response({"jobs": [await self.resume_segments(job, user, admin)]})
            except graph.JobError as e:
                return web.json_response({"error": e.as_dict()}, status=400)
        spec = dict(job["spec"], mode=job["mode"])
        params = dict(spec.get("params") or {}, variant=job["variant"])
        old_used = job.get("used") or {}
        if old_used.get("seed") is not None:
            params["seed"] = old_used["seed"]
        try:
            self.check_disk()
            variant = await self.job_variant(params)
            job = self.job_for(request, request.match_info["id"], edit=True)
            if not job:
                return self.err(404, "not_found", "No such job")
            if attempt != job["attempt"] or job["status"] not in RETRYABLE:
                return web.json_response({"jobs": [job]})
            flow, items = self.plan(spec, job["owner"], admin)
            graph.check_output(self.profile, variant, graph.output_size(flow, items, params, self.profile), items)
            pid = str(uuid.uuid4())
            prompt, used = self.assemble(flow, pid, items, dict(params, prompt=spec.get("prompt", "")), variant, job["owner"], self.project_of(job))
            if old_used.get("before"):
                used["before"] = old_used["before"]
        except graph.JobError as e:
            return web.json_response({"error": e.as_dict()}, status=400)
        retried = self.store.retry_job(job["id"], attempt, pid, used)
        if not retried:
            return web.json_response({"jobs": [self.store.job(job["id"])]})
        self.cancelling.discard(job["id"])
        return web.json_response({"jobs": [await self.enqueue(retried, prompt)]})

    def done_segment(self, s):
        c = self.store.job(s["job"]) if s.get("job") else None
        return bool(c and c["status"] == "done" and any(os.path.exists(f) for f in (c.get("used") or {}).get("files") or []))

    async def resume_segments(self, job, user, admin):
        """Runs again only the segments that have no result, same seed."""
        pid = job["id"]
        flow, items = self.plan(dict(job["spec"], mode=job["mode"]), job.get("owner", ""), admin)
        params = dict(job["spec"].get("params") or {}, prompt=job["spec"].get("prompt", ""), seed=job["used"]["seed"])
        project = self.store.project(job["project"]) if job.get("project") else None
        if not self.store.retry_job(pid, job["attempt"], str(uuid.uuid4()), job["used"]):
            return self.job_view(self.store.job(pid))
        self.store.update_job(pid, status="running", started=time.time())
        self.spawning.add(pid)
        try:
            for i, s in enumerate(job["used"]["segments"]):
                if self.store.job(pid)["status"] not in ACTIVE:
                    break
                if not self.done_segment(s):
                    await self.submit_segment(pid, i, flow, items, params, job["variant"], job["spec"], job.get("owner", ""), project)
        finally:
            self.spawning.discard(pid)
        self.queue_dirty = True
        await self.advance(pid)
        return self.job_view(self.store.job(pid), publish=True)

    async def h_upload(self, request):
        owner, admin = self.viewer(request)
        source = request.query.get("source") or "upload"
        if source not in UPLOAD_SOURCES:
            return self.err(400, "bad_source", "Unknown upload source")
        project, denied = self.writable(request.query.get("project"), owner, admin)
        if denied:
            return denied
        pid = project["id"] if project else None
        try:
            reader = await request.multipart()
        except Exception:
            return self.err(400, "bad_upload", "Expected a multipart upload")
        field = await reader.next()
        while field is not None and field.name != "file":
            field = await reader.next()
        if field is None or not field.filename:
            return self.err(400, "bad_upload", "No file")
        tmp = os.path.join(self.input_dir, ".up-%s%s" % (uuid.uuid4().hex, os.path.splitext(field.filename)[1].lower()[:8]))
        size = 0
        h = hashlib.md5()
        try:
            with open(tmp, "wb") as f:
                while True:
                    chunk = await field.read_chunk(1 << 20)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > UPLOAD_LIMIT:
                        raise web.HTTPRequestEntityTooLarge(max_size=UPLOAD_LIMIT, actual_size=size)
                    f.write(chunk)
                    h.update(chunk)
            md5 = h.hexdigest()
            same = self.store.asset_by_md5(md5, owner, pid)
            if same:
                self._rm(tmp)
                return web.json_response({**same, "deduped": True})
            a = await self.run(self._ingest, tmp, field.filename, source, owner=owner, md5=md5, project=project)
            same = self.store.asset_by_md5(md5, owner, pid)
            if same:
                self._rm(a["path"], a["poster"])
                return web.json_response({**same, "deduped": True})
        except web.HTTPRequestEntityTooLarge:
            self._rm(tmp)
            return self.err(413, "too_large", "Files up to 512 MB", limit=UPLOAD_LIMIT)
        except media.MediaError as e:
            self._rm(tmp)
            return self.err(415, str(e).split(":")[0], "This file type is not supported")
        except Exception as e:
            self._rm(tmp)
            log.exception("studio: upload")
            return self.err(500, "upload_failed", str(e)[:300])
        asset = self.store.add_asset(a)
        self.publish_asset(asset)
        return web.json_response(asset)

    @staticmethod
    def _rm(*paths):
        for p in paths:
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass

    async def h_assets(self, request):
        q = request.query
        user, admin = self.viewer(request)
        pid = q.get("project") or None
        if pid and not projects.role(self.store.project(pid), user, admin):
            return self.err(404, "no_project", "No such project")
        assets = self.store.assets(q.get("kind"), q.get("source"), q.get("q"), q.get("starred") == "1",
                                   q.get("before"), min(200, int(q.get("limit", 60))),
                                   owner=user, project=pid, after=q.get("after"))
        result = {"assets": assets}
        if q.get("with_jobs") == "1":
            ids = {a["job_id"] for a in assets if a["job_id"]}
            jobs = self.store.jobs(owner=user, project=pid, limit=len(ids), ids=ids)
            result["jobs"] = {j["id"]: self.job_view(j) for j in jobs}
        return web.json_response(result)

    async def h_asset_by_md5(self, request):
        md5 = request.match_info["md5"].lower()
        if not MD5_RE.match(md5):
            return self.err(400, "bad_md5", "Expected 32 hex digits")
        a = self.store.asset_by_md5(md5, self.user_of(request), request.query.get("project") or None)
        return web.json_response(a) if a else self.err(404, "not_found", "No such asset")

    async def h_asset_patch(self, request):
        aid = request.match_info["id"]
        a = self.asset_for(request, aid, edit=True)
        if not a:
            return self.err(404, "not_found", "No such asset")
        body = await self.body(request)
        fields = {}
        if "name" in body:
            fields["name"] = clean_name(str(body["name"]), "asset")
        if "starred" in body:
            fields["starred"] = bool(body["starred"])
        if "project" in body and (body["project"] or None) != a.get("project"):
            if self.store.asset_in_use(aid):
                return self.err(409, "in_use", "A queued job uses this asset")
            project, denied = self.writable(body["project"], *self.viewer(request))
            if denied:
                return denied
            self.bus.publish("asset_deleted", {"id": aid}, self.aud(a))
            await self.run(self.move_asset, a, project)
        a = self.store.update_asset(aid, **fields)
        self.publish_asset(a)
        if self.store.image_favorites and "starred" in fields and a["source"] == "output" and a["job_id"]:
            job = self.store.job(a["job_id"])
            if job and not job["deleted"] and self.aud(job) == self.aud(a):
                self.publish_job(job)
        return web.json_response(a)

    async def h_asset_delete(self, request):
        aid = request.match_info["id"]
        a = self.asset_for(request, aid, edit=True)
        if not a:
            return self.err(404, "not_found", "No such asset")
        if self.store.asset_in_use(aid):
            return self.err(409, "in_use", "A queued job uses this asset")
        self.store.update_asset(aid, deleted=True)
        link = "st-%s%s" % (aid, os.path.splitext(a["path"])[1])
        self._rm(a["path"], a["poster"], os.path.join(self.space_path(a.get("owner", ""), self.project_of(a), "uploads"), link),
                 os.path.join(self.input_dir, ".users", a.get("owner") or "_", link))
        self.bus.publish("asset_deleted", {"id": aid}, self.aud(a))
        return web.json_response({"ok": True})

    async def h_trim(self, request):
        a = self.asset_for(request, request.match_info["id"])
        user, admin = self.viewer(request)
        if not a or a["deleted"] or a["kind"] not in ("video", "audio"):
            return self.err(404, "not_found", "No such clip")
        body = await self.body(request)
        try:
            start, end = float(body.get("start", 0)), float(body.get("end", 0))
        except (TypeError, ValueError):
            return self.err(400, "bad_range", "Bad range")
        if not (0 <= start < end) or (a["duration"] and start >= a["duration"]):
            return self.err(400, "bad_range", "Bad range")
        ext = ".mp4" if a["kind"] == "video" else ".wav"
        tmp = os.path.join(self.input_dir, ".trim-%s%s" % (uuid.uuid4().hex, ext))
        try:
            await self.run(media.trim, a["path"], tmp, start, end)
            n = await self.run(self._ingest, tmp, "%s %.1f-%.1fs%s" % (a["name"], start, end, ext), "trim", owner=user,
                               project=self.derived_project(a, user, admin))
        except media.MediaError as e:
            self._rm(tmp)
            return self.err(500 if "ffmpeg" not in str(e) else 501, "trim_failed", str(e)[:300])
        asset = self.store.add_asset(n)
        self.publish_asset(asset)
        return web.json_response(asset)

    async def h_frame(self, request):
        body = await self.body(request)
        a = self.asset_for(request, str(body.get("asset", "")))
        user, admin = self.viewer(request)
        if not a or a["deleted"] or a["kind"] != "video":
            return self.err(404, "not_found", "No such video")
        last = body.get("at") == "last"
        t = None if last else max(0.0, float(body.get("t") or 0))
        tmp = os.path.join(self.input_dir, ".frame-%s.png" % uuid.uuid4().hex)
        try:
            await self.run(media.grab_frame, a["path"], tmp, t=t, last=last)
            label = "%s %s" % (a["name"], "last frame" if last else "@ %.2fs" % t)
            n = await self.run(self._ingest, tmp, label + ".png", "frame", owner=user, job_id=a.get("job_id"),
                               project=self.derived_project(a, user, admin))
        except Exception as e:
            self._rm(tmp)
            return self.err(500, "frame_failed", str(e)[:300])
        asset = self.store.add_asset(n)
        self.publish_asset(asset)
        return web.json_response(asset)

    async def h_media(self, request):
        a = self.asset_for(request, request.match_info["id"])
        if not a or a["deleted"] or not os.path.exists(a["path"]):
            return self.err(404, "not_found", "No such file")
        ext = os.path.splitext(a["path"])[1]
        disp = "attachment" if request.query.get("download") else "inline"
        fname = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "_", a["name"]).strip()
        if not fname.lower().endswith(ext.lower()):
            fname += ext
        fallback = re.sub(r"%|[^\x20-\x7e]+", "_", fname)
        disposition = '%s; filename="%s"' % (disp, fallback)
        if fname != fallback:
            disposition += "; filename*=UTF-8''" + quote(fname)
        return web.FileResponse(a["path"], headers={
            "Content-Type": a["mime"], "Content-Disposition": disposition,
            "Cache-Control": "private, no-store" if disp == "attachment" else "private, max-age=31536000, immutable",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; sandbox",
        })

    async def h_poster(self, request):
        a = self.asset_for(request, request.match_info["id"])
        if not a or not a.get("poster") or not os.path.exists(a["poster"]):
            return self.err(404, "not_found", "No poster")
        return web.FileResponse(a["poster"], headers={"Content-Type": "image/webp", "Cache-Control": "private, max-age=31536000, immutable",
                                                      "X-Content-Type-Options": "nosniff"})

    # examples

    @staticmethod
    def example_url(x, key):
        return "/studio/api/examples/%s/files/%s" % (x["id"], key)

    def example_info(self, x):
        def kind(key):
            return EXAMPLE_MIME.get(os.path.splitext(key)[1].lower(), "").split("/")[0]
        return {"id": x["id"], "flow": x["flow"], "variant": x.get("variant") or "", "prompt": x.get("prompt") or {},
                "assets": [{"role": a["role"], "kind": kind(a["file"]), "url": self.example_url(x, a["file"])} for a in x["assets"]],
                "result": self.example_url(x, x["result"]) if x.get("result") else None}

    def example_path(self, x, key):
        files = [a["file"] for a in x["assets"]] + ([x["result"]] if x.get("result") else [])
        p = os.path.join(self.examples_dir, key)
        return p if key in files and os.path.isfile(p) else None

    async def h_example_file(self, request):
        x = self.examples.get(request.match_info["id"])
        p = x and self.example_path(x, request.match_info["file"])
        if not p:
            return self.err(404, "not_found", "No such file")
        return web.FileResponse(p, headers={
            "Content-Type": EXAMPLE_MIME.get(os.path.splitext(p)[1].lower(), "application/octet-stream"),
            "Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff",
        })

    async def h_example_use(self, request):
        """The example's assets, added to the library unless already there."""
        x = self.examples.get(request.match_info["id"])
        if not x:
            return self.err(404, "not_found", "No such example")
        owner, admin = self.viewer(request)
        project, denied = self.writable(request.query.get("project"), owner, admin)
        if denied:
            return denied
        pid = project["id"] if project else None
        out = []
        for a in x["assets"]:
            p = self.example_path(x, a["file"])
            if not p:
                return self.err(404, "not_found", "Example file missing", file=a["file"])
            md5 = await self.run(file_md5, p)
            asset = self.store.asset_by_md5(md5, owner, pid)
            if not asset:
                name = a["file"][len(x["id"]) + 1:]
                tmp = os.path.join(self.input_dir, ".ex-%s%s" % (uuid.uuid4().hex, os.path.splitext(name)[1].lower()))
                try:
                    await self.run(shutil.copyfile, p, tmp)
                    n = await self.run(self._ingest, tmp, name, "example", owner=owner, md5=md5, project=project)
                except Exception as e:
                    self._rm(tmp)
                    log.exception("studio: example %s", x["id"])
                    return self.err(500, "example_failed", str(e)[:300])
                asset = self.store.asset_by_md5(md5, owner, pid)
                if asset:
                    self._rm(n["path"], n["poster"])
                else:
                    asset = self.store.add_asset(n)
                    self.publish_asset(asset)
            out.append({"role": a["role"], "asset": asset})
        return web.json_response({"assets": out})

    async def h_model_add(self, request):
        if not self.is_admin(request):
            return self.err(403, "admin_only", "Only the admin can download models")
        v = request.match_info["variant"]
        if v not in self.variants:
            return self.err(404, "not_found", "Unknown precision")
        return await self.model_change("PUT", v)

    async def h_model_delete(self, request):
        if not self.is_admin(request):
            return self.err(403, "admin_only", "Only the admin can delete models")
        v = request.match_info["variant"]
        if v not in self.variants:
            return self.err(404, "not_found", "Unknown precision")
        if any(j["variant"] == v for j in self.store.jobs_by_status(ACTIVE)):
            return self.err(409, "in_use", "A queued job uses this precision")
        resp = await self.model_change("DELETE", v)
        if resp.status == 200:
            await self.post("/free", {"unload_models": True, "free_memory": True})
            self.warm = False
        return resp

    async def model_change(self, method, v):
        try:
            status, data = await self.call(method, "%s/api/groups/%s" % (self.console, v))
        except Exception as e:
            return self.err(502, "console_unreachable", str(e)[:300])
        self.installed_at = 0
        if status != 200:
            return self.err(status, "console", (data or {}).get("error") or "The Model Console refused")
        return web.json_response(data)

    async def h_free(self, request):
        if not self.is_admin(request):
            return self.err(403, "admin_only", "Only the admin can free GPU memory")
        status, resp = await self.post("/free", {"unload_models": True, "free_memory": True})
        self.warm = False
        return web.json_response({"ok": status == 200})

    # projects

    @staticmethod
    def project_view(p, user, admin):
        return dict(p, role=projects.role(p, user, admin))

    def managed(self, request):
        """(project, user, admin) when the user administers it, else (None, error)."""
        user, admin = self.viewer(request)
        p = self.store.project(request.match_info["id"])
        r = projects.role(p, user, admin)
        if not r:
            return None, self.err(404, "no_project", "No such project")
        if r != "admin":
            return None, self.err(403, "project_admin_only", "Only a project admin can change this")
        return (p, user, admin), None

    def project_settings(self, b, fields):
        if b.get("access") in projects.ACCESS:
            fields["access"] = b["access"]
        if b.get("default_role") in ("viewer", "editor"):
            fields["default_role"] = b["default_role"]
        return fields

    async def h_projects(self, request):
        user, admin = self.viewer(request)
        return web.json_response({"projects": [self.project_view(p, user, admin) for p in self.store.projects()
                                               if projects.role(p, user, admin)]})

    async def h_project_add(self, request):
        user, admin = self.viewer(request)
        b = await self.body(request)
        name = clean_name(str(b.get("name") or ""), "")
        if not name:
            return self.err(400, "bad_request", "A name is required")
        if self.store.project_by_name(name):
            return self.err(409, "name_taken", "A project with this name exists")
        fields = self.project_settings(b, {"id": uuid.uuid4().hex, "name": name, "owner": user,
                                           "dir": projects.dir_name(name, [p["dir"] for p in self.store.projects()])})
        p = self.store.add_project(fields)
        self.bus.publish("projects", {"id": p["id"]})
        return web.json_response(self.project_view(p, user, admin))

    async def h_project_patch(self, request):
        ok, denied = self.managed(request)
        if denied:
            return denied
        p, user, admin = ok
        b = await self.body(request)
        fields = self.project_settings(b, {})
        if "archived" in b:
            fields["archived"] = bool(b["archived"])
        name = clean_name(str(b.get("name") or ""), "") if "name" in b else ""
        if name and name != p["name"]:
            same = self.store.project_by_name(name)
            if same and same["id"] != p["id"]:
                return self.err(409, "name_taken", "A project with this name exists")
            if self.store.project_active(p["id"]):
                return self.err(409, "active", "Wait for the project's jobs to finish")
            new_dir = projects.dir_name(name, [x["dir"] for x in self.store.projects() if x["id"] != p["id"]])
            if new_dir != p["dir"]:
                await self.run(self.rename_dirs, p, new_dir)
            fields.update(name=name, dir=new_dir)
        p = self.store.update_project(p["id"], **fields)
        self.bus.publish("projects", {"id": p["id"]})
        return web.json_response(self.project_view(p, user, admin))

    async def h_member_put(self, request):
        ok, denied = self.managed(request)
        if denied:
            return denied
        p, user, admin = ok
        member = request.match_info["user"]
        role = (await self.body(request)).get("role")
        if not USER_RE.match(member) or self.lookup(member) == "unknown":
            return self.err(400, "bad_user", "No such Olares user")
        if role not in projects.ROLES:
            return self.err(400, "bad_role", "Unknown role")
        p = self.store.set_member(p["id"], member, role)
        self.bus.publish("projects", {"id": p["id"]})
        return web.json_response(self.project_view(p, user, admin))

    async def h_member_delete(self, request):
        ok, denied = self.managed(request)
        if denied:
            return denied
        p, user, admin = ok
        p = self.store.set_member(p["id"], request.match_info["user"], None)
        self.bus.publish("projects", {"id": p["id"]})
        return web.json_response(self.project_view(p, user, admin))

    async def h_users(self, request):
        d = getattr(self, "directory", None)
        return web.json_response({"users": d.names() if d else []})


def setup():
    try:
        from server import PromptServer
    except ImportError:
        return
    server = PromptServer.instance
    try:
        studio = Studio(server)
    except Exception:
        log.exception("studio: backend disabled")
        return
    studio.routes(server.routes)
    orig = server.send_sync

    def send_sync(event, data, sid=None):
        orig(event, data, sid)
        if isinstance(event, str):
            try:
                server.loop.call_soon_threadsafe(studio.on_comfy, event, data)
            except RuntimeError:
                pass

    server.send_sync = send_sync
    for coro in (studio.event_loop(), studio.queue_loop(), studio.reconcile_loop(), studio.directory_loop()):
        server.loop.create_task(coro)
    server.loop.run_in_executor(None, studio.backfill_md5)
    if studio.llm.base and studio.rewrite_modes:
        server.loop.create_task(studio.llm.probe())
    log.info("studio: ready, variant %s, %d flows", studio.preferred or "-", len(studio.flows))
