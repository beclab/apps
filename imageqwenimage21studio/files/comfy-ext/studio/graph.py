"""Pick a flow for a job and turn the flow's API workflow into a prompt.

Pure functions over plain dicts (studio.json flows, API workflows, asset
records), so they run and are tested without ComfyUI.
"""
import copy
import math
import random
import re

# mask: white where an edit may change the first ref_image; source_video,
# source_image: what an enhance flow upscales.
ASSET_ROLES = ("first_frame", "last_frame", "ref_image", "ref_video", "ref_audio", "mask", "source_video", "source_image")
ROLE_KIND = {"first_frame": "image", "last_frame": "image", "ref_image": "image", "ref_video": "video", "ref_audio": "audio",
             "mask": "image", "source_video": "video", "source_image": "image"}
SOURCE_ROLES = ("source_video", "source_image")
SPEEDS = ("quality", "fast")
# aspect "follow": the output keeps image 1's shape (the parameter bar's
# "follow image 1").
FOLLOW = "follow"
TOKEN = re.compile(r"\{\{([A-Za-z0-9_-]{1,64})\}\}")
CJK = re.compile(u"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")
MAX_SEED = 2 ** 50


class JobError(Exception):
    def __init__(self, code, message, **extra):
        super().__init__(message)
        self.code = code
        self.message = message
        self.extra = extra

    def as_dict(self):
        return {"code": self.code, "message": self.message, **self.extra}


def check_route(flow, items):
    """None when the flow takes these assets, else why not.

    items: [{"role", "kind", "duration"}]."""
    route = flow.get("route") or {}
    accepts = route.get("accepts") or {}
    counts, seconds = {}, {}
    for it in items:
        role = it["role"]
        lim = accepts.get(role)
        if not lim:
            return {"code": "role_not_accepted", "role": role}
        if ROLE_KIND.get(role) != it.get("kind"):
            return {"code": "wrong_kind", "role": role, "kind": it.get("kind")}
        counts[role] = counts.get(role, 0) + 1
        if counts[role] > lim["max"]:
            return {"code": "too_many", "role": role, "max": lim["max"]}
        d = it.get("duration")
        if d is not None:
            if lim.get("minSeconds") and d < lim["minSeconds"] - 0.05:
                return {"code": "too_short", "role": role, "min": lim["minSeconds"]}
            if lim.get("maxSeconds") and d > lim["maxSeconds"] + 0.05:
                return {"code": "too_long", "role": role, "max": lim["maxSeconds"]}
            seconds[role] = seconds.get(role, 0) + d
            if lim.get("totalSeconds") and seconds[role] > lim["totalSeconds"] + 0.05:
                return {"code": "total_too_long", "role": role, "max": lim["totalSeconds"]}
    if route.get("maxTotal") and len(items) > route["maxTotal"]:
        return {"code": "too_many_total", "max": route["maxTotal"]}
    need = route.get("requiresAny") or []
    if need and not any(it["role"] in need for it in items):
        return {"code": "requires_any", "roles": need}
    missing = [r for r in route.get("requiresAll") or [] if r not in counts]
    if missing:
        return {"code": "requires_all", "roles": missing}
    return None


def aspect_route(aspect, items, defaults=None):
    """Which route.aspect a job with images takes: follow (keep image 1's
    shape) or ratio (a picked aspect ratio). A mask always follows; no
    pick ("auto") takes defaults[single|multi], else follow. None without
    images.

    Mirrored by aspectRoute in web/src/plan.ts; both run
    testdata/aspect_route.json."""
    n = sum(1 for it in items or () if it.get("role") == "ref_image")
    if not n:
        return None
    if any(it.get("role") == "mask" for it in items) or aspect == FOLLOW:
        return FOLLOW
    if aspect not in (None, "", "auto"):
        return "ratio"
    return (defaults or {}).get("multi" if n > 1 else "single") or FOLLOW


def pick_flow(flows, items, mode="auto", speed=None, aspect=None):
    """Pick the requested mode's speed variant, the mode itself, or the first
    compatible flow in auto mode, preferring the requested speed."""
    speed_of = lambda f: (f.get("route") or {}).get("speed") or ""
    fits = lambda f: not aspect or (f.get("route") or {}).get("aspect") in (None, "", aspect)
    order = [f for f in flows if speed and speed_of(f) == speed and fits(f)] + [f for f in flows if not speed_of(f) and fits(f)]
    if mode and mode != "auto":
        variant = next((f for f in order if speed and speed_of(f) == speed and (f.get("route") or {}).get("of") == mode), None)
        flow = variant or next((f for f in flows if f["mode"] == mode), None)
        if not flow:
            raise JobError("unknown_mode", "Unknown mode", mode=mode)
        why = check_route(flow, items)
        if why:
            raise JobError("flow_rejects_assets", "This mode cannot take these assets", mode=flow["mode"], reason=why)
        return flow
    reasons = {}
    for f in order:
        why = check_route(f, items)
        if why is None:
            return f
        reasons[f["mode"]] = why
    raise JobError("no_flow", "No mode takes this combination of assets", reasons=reasons)


def _tokens(items, tokens):
    """Asset id -> tokens[role] with {n} its number within its role in tray order."""
    out, n = {}, {}
    for it in items:
        tok = (tokens or {}).get(it["role"])
        if tok and it["id"] not in out:
            n[it["role"]] = n.get(it["role"], 0) + 1
            out[it["id"]] = tok.replace("{n}", str(n[it["role"]]))
    return out


def render_prompt(text, items, names, tokens=None):
    """Turn {{asset-id}} chips into the model's syntax (profile.tokens),
    else the asset's name."""
    tags = _tokens(items, tokens)

    def sub(m):
        aid = m.group(1)
        return tags.get(aid) or names.get(aid, "")

    return TOKEN.sub(sub, text or "")


def ref_note(items, profile, prompt):
    """The phrases of the images marked with a refTag, in the prompt's
    language (Chinese when it has CJK text, else English), as one sentence."""
    phrases = {t["id"]: t.get("phrase") or {} for t in (profile or {}).get("refTags") or []}
    toks = _tokens(items, (profile or {}).get("tokens"))
    lang = "zh" if CJK.search(prompt or "") else "en"
    parts = [phrases[it["tag"]][lang].replace("{ref}", toks[it["id"]])
             for it in items if it.get("tag") in phrases and it["id"] in toks and phrases[it["tag"]].get(lang)]
    if not parts:
        return ""
    return "；".join(parts) + "。" if lang == "zh" else "; ".join(parts) + "."


def _refs(value):
    return isinstance(value, list) and len(value) == 2 and isinstance(value[0], str) and isinstance(value[1], int)


def _sinks(g):
    used = {v[0] for node in g.values() for v in node.get("inputs", {}).values() if _refs(v)}
    return [nid for nid in g if nid not in used]


def _prune(g, sinks):
    keep, todo = set(), [s for s in sinks if s in g]
    while todo:
        nid = todo.pop()
        if nid in keep:
            continue
        keep.add(nid)
        for v in g[nid].get("inputs", {}).values():
            if _refs(v) and v[0] in g:
                todo.append(v[0])
    return {k: v for k, v in g.items() if k in keep}


def _cut_links_from(g, src):
    for node in g.values():
        ins = node.get("inputs", {})
        for k in [k for k, v in ins.items() if _refs(v) and v[0] == src]:
            del ins[k]


def _bypass(g, nid, field):
    """Skip node nid: whatever read its output reads its input field."""
    node = g.get(nid)
    if node is None:
        raise JobError("bad_flow", "The workflow has no node %s" % nid)
    src = node.get("inputs", {}).get(field)
    if not _refs(src):
        raise JobError("bad_flow", "Node %s has no link at %s" % (nid, field))
    for other in g.values():
        ins = other.get("inputs", {})
        for k, v in list(ins.items()):
            if _refs(v) and v[0] == nid:
                ins[k] = list(src)
    del g[nid]


def _set(g, node, field, value):
    if node not in g:
        raise JobError("bad_flow", "The workflow has no node %s" % node)
    g[node].setdefault("inputs", {})[field] = value


def tiers(profile):
    """Megapixels per resolution tier id, in display order."""
    return {t["id"]: t["megapixels"] for t in (profile or {}).get("tiers") or []}


def _in_unit(mp, inp):
    """Megapixels as the input takes them: unit edge is the side of a
    square of that many megapixels (1 MP = 1024²)."""
    if inp.get("unit") == "edge":
        return int(round(math.sqrt(mp) * 1024 / 32)) * 32
    return mp


def budget_share(mp, inp, by_role):
    """The tier's megapixels for each of the input's budget.role assets,
    cut to an equal share of budget.megapixels when they would exceed it."""
    b = inp.get("budget")
    n = len(by_role.get(b["role"]) or []) if b else 0
    if not n or mp * n <= b["megapixels"]:
        return mp
    return math.floor(b["megapixels"] / n * 100) / 100


def default_tier(inp, profile):
    """The tier of a resolution input's default, else the first."""
    mp = tiers(profile)
    d = inp.get("default")
    for k, v in mp.items():
        if d is not None and abs(_in_unit(v, inp) - float(d)) < 1e-6:
            return k
    return next(iter(mp), None)


def flow_roles(flow, profile=None):
    """The flow's parameter inputs by role, as /health sends them."""
    roles = {}
    for i in flow.get("inputs", []):
        if i.get("role"):
            roles[i["role"]] = {k: i.get(k) for k in ("min", "max", "step", "default", "options", "optional") if i.get(k) is not None}
            if i["role"] == "resolution":
                roles["resolution"]["default"] = default_tier(i, profile)
    return roles


SIZE_ROLES = ("first_frame", "ref_image", "ref_video", "source_video", "source_image")


def has_role(flow, role):
    return any(i.get("role") == role for i in flow.get("inputs", []))


def _clamp(v, r):
    v = float(v)
    if r.get("min") is not None:
        v = max(float(r["min"]), v)
    if r.get("max") is not None:
        v = min(float(r["max"]), v)
    return v


def _num(v):
    return int(v) if float(v).is_integer() else v


def job_scale(flow, params, profile=None):
    """The upscale factor: params.scale within the scale input's range, else
    its default; profile.fixedScale for a flow without a scale input."""
    r = flow_roles(flow).get("scale")
    if not r:
        return float((profile or {}).get("fixedScale") or 0) or None
    v = params.get("scale")
    v = r.get("default") if v in (None, "") else v
    try:
        return _clamp(v, r) if v is not None else None
    except (TypeError, ValueError):
        raise JobError("bad_scale", "Bad upscale factor", scale=v)


def segment_of(params):
    """params.segment as (start, duration) seconds, None for the whole video."""
    s = params.get("segment")
    if not s:
        return None
    try:
        start, dur = float(s.get("start") or 0), float(s.get("duration") or 0)
    except (AttributeError, TypeError, ValueError):
        raise JobError("bad_segment", "Bad preview range")
    if start < 0 or dur <= 0:
        raise JobError("bad_segment", "Bad preview range")
    return start, dur


def segment_items(items, params):
    """A preview's source video counts as the seconds it runs on, so a
    route's maxSeconds limits what is processed, not the upload."""
    seg = segment_of(params)
    if not seg:
        return
    for it in items:
        if it["role"] == "source_video" and it.get("duration"):
            if seg[0] >= it["duration"]:
                raise JobError("bad_segment", "The preview starts after the end of the video")
            it["duration"] = min(seg[1], it["duration"] - seg[0])


def output_size(flow, items, params, profile=None):
    """(width, height, scale) of the result for the source video or image, or None."""
    src = next((it.get("asset") or it for it in items or () if it.get("role") in SOURCE_ROLES), None)
    scale = job_scale(flow, params, profile) if src else None
    if not src or not src.get("width") or not src.get("height") or not scale:
        return None
    return int(round(src["width"] * scale / 2)) * 2, int(round(src["height"] * scale / 2)) * 2, scale


ASSUMED_FPS = 30


def output_frames(items):
    """(frames, fps) of the source video the job runs on (a preview counts
    only its range, see segment_items), or None without a source video."""
    it = next((it for it in items or () if it.get("role") == "source_video"), None)
    if not it or not it.get("duration"):
        return None
    fps = (it.get("asset") or {}).get("fps") or ASSUMED_FPS
    return int(math.ceil(float(it["duration"]) * fps)), fps


def _per_variant(profile, key, variant):
    lim = (profile or {}).get(key) or {}
    return lim.get(variant) if variant in lim else lim.get("default")


def check_output(profile, variant, size, items=None):
    """Raise when the result is larger than profile.outputLimit allows for
    this variant (megapixels; "default" for apps without variants), or when
    megapixels × frames of the source video passes profile.outputPixelFrames."""
    mp = _per_variant(profile, "outputLimit", variant)
    if size and mp and size[0] * size[1] > mp * 1e6 + 1:
        raise JobError("output_too_large", "The result would be larger than this model can make here",
                       max=mp, width=size[0], height=size[1], variant=variant or "")
    budget = _per_variant(profile, "outputPixelFrames", variant)
    run = output_frames(items) if budget else None
    if size and run and size[0] * size[1] / 1e6 * run[0] > budget:
        max_frames = int(budget * 1e6 / (size[0] * size[1]))
        raise JobError("output_too_long", "The video is too long to upscale to this size here",
                       max_seconds=math.floor(max_frames / run[1] * 10) / 10, width=size[0], height=size[1],
                       frames=run[0], variant=variant or "")


SEGMENT_PAD = 0.5
SEGMENT_MIN = 2.0


def plan_segments(profile, variant, size, items, pad=SEGMENT_PAD):
    """Segments a whole video over profile.outputPixelFrames runs as, or None
    when it fits in one run. Each is {start, duration} for the workflow's own
    slice plus {skip, keep} frames of its result that go into the joined
    video; inner boundaries run pad seconds of context on both sides. Times
    sit half a frame before a frame, so the slice's pts comparison picks it
    whatever the float rounding."""
    budget = _per_variant(profile, "outputPixelFrames", variant)
    run = output_frames(items) if budget and size else None
    if not run or size[0] * size[1] / 1e6 * run[0] <= budget:
        return None
    total, fps = run
    most = int(budget * 1e6 / (size[0] * size[1]))
    pad_f = int(round(pad * fps))
    room = most - 2 * pad_f
    if room < SEGMENT_MIN * fps:
        raise JobError("output_too_long", "The video is too long to upscale to this size here",
                       max_seconds=math.floor(most / fps * 10) / 10, width=size[0], height=size[1],
                       frames=total, variant=variant or "")
    n = int(math.ceil(total / room))
    bounds = [int(round(i * total / n)) for i in range(n + 1)]
    segs = []
    for i in range(n):
        a = max(0, bounds[i] - pad_f) if i else 0
        b = min(total, bounds[i + 1] + pad_f) if i < n - 1 else total
        segs.append({"start": round(max(0.0, (a - 0.5) / fps), 4), "duration": round((b - a) / fps, 4),
                     "skip": bounds[i] - a, "keep": bounds[i + 1] - bounds[i]})
    return segs


def aspect_value(label):
    try:
        a, b = str(label).split(" ")[0].split(":")
        return float(a) / float(b)
    except (ValueError, ZeroDivisionError):
        return None


def nearest_aspect(options, width, height):
    r = math.log(width / height)
    scored = [(abs(math.log(v) - r), o) for o in options for v in [aspect_value(o)] if v]
    return min(scored, key=lambda x: x[0])[1] if scored else None


def first_size(items):
    for role in SIZE_ROLES:
        for it in items or ():
            a = it.get("asset") or it
            if it.get("role") == role and a.get("width") and a.get("height"):
                return a["width"], a["height"]
    return None


def resolve_roles(roles, params, items=(), tier_ids=()):
    """Final aspect, duration and resolution with where each came from
    ("user", "image" or "default"). An unknown aspect or resolution falls
    back like an unset one; duration is clamped to the input's range. The
    prompt text is never read for size, aspect or length.

    Mirrored by resolveParams in web/src/plan.ts; both run
    testdata/resolve_params.json."""
    out, src = dict(params), {}
    out.pop("aspect", None)
    r = roles.get("aspect")
    if r:
        opts = r.get("options") or []
        a = params.get("aspect")
        pick = next((o for o in opts if a not in (None, "", "auto") and (o == a or o.split(" ")[0] == a)), None)
        size = first_size(items)
        if pick:
            out["aspect"], src["aspect"] = pick, "user"
        elif size and nearest_aspect(opts, *size):
            out["aspect"], src["aspect"] = nearest_aspect(opts, *size), "image"
        elif r.get("default"):
            out["aspect"], src["aspect"] = r["default"], "default"
    d = roles.get("duration")
    if d:
        v = params.get("duration")
        src["duration"] = "default" if v in (None, "") else "user"
        v = d.get("default") if v in (None, "") else v
        if v is not None:
            v = float(v)
            if d.get("min") is not None:
                v = max(float(d["min"]), v)
            if d.get("max") is not None:
                v = min(float(d["max"]), v)
            out["duration"] = v
    res = roles.get("resolution")
    if res:
        v = params.get("resolution")
        if v in tier_ids:
            out["resolution"], src["resolution"] = v, "user"
        elif res.get("default") or tier_ids:
            out["resolution"], src["resolution"] = res.get("default") or tier_ids[0], "default"
    return out, src


def resolve_params(flow, params, items=(), profile=None):
    return resolve_roles(flow_roles(flow, profile), params, items, list(tiers(profile)))


def assemble(flow, api, job_id, items, params, replace=None, file_of=None, names=None, profile=None, prefix="studio/"):
    """The prompt for one job.

    items: the job's assets in tray order, [{"id", "role", "kind",
    "has_audio", "tag"}], the first ref_image the one an edit changes; file_of(item)
    is the name a loader node takes;
    params: prompt, duration, aspect, resolution, seed, steps;
    profile: studio.json's profile (tiers, tokens)."""
    file_of = file_of or (lambda it: it["file"])
    profile = profile or {}
    params, sources = resolve_params(flow, params, items, profile)
    g = copy.deepcopy(api)
    sinks = _sinks(g)
    if replace:
        for node in g.values():
            ins = node.get("inputs", {})
            for k, v in ins.items():
                if isinstance(v, str) and v in replace:
                    ins[k] = replace[v]

    by_role = {}
    for it in items:
        by_role.setdefault(it["role"], []).append(it)
    grown = {ag["role"] for ag in flow.get("autogrow") or []}

    seed = params.get("seed")
    if seed is None or seed == "":
        seed = random.randrange(MAX_SEED)
    seed = int(seed)
    used = {"seed": seed}
    roles = flow_roles(flow, profile)
    segment = segment_of(params) if has_role(flow, "segment_start") else None
    if segment:
        used["segment"] = {"start": segment[0], "duration": segment[1]}

    for inp in flow.get("inputs", []):
        role = inp.get("role")
        if not role:
            continue
        targets = [(inp["node"], inp["field"])] + [(t["node"], t["field"]) for t in inp.get("also") or []]
        value = None
        if role in ASSET_ROLES and role not in grown:
            got = by_role.get(role) or []
            if got:
                value = file_of(got[0])
            elif inp.get("optional"):
                _cut_links_from(g, inp["node"])
                if inp.get("bypass"):
                    _bypass(g, inp["bypass"]["node"], inp["bypass"]["field"])
                continue
            else:
                raise JobError("missing_asset", "This mode needs a %s" % role.replace("_", " "), role=role)
        elif role == "prompt":
            value = render_prompt(params.get("prompt", ""), items, names or {}, profile.get("tokens"))
            if not value.strip() and inp.get("optional") and inp.get("default"):
                value = inp["default"]
            if not value.strip():
                raise JobError("empty_prompt", "Write a prompt first")
            note = ref_note(items, profile, value)
            if note:
                used["refNote"] = note
                value = note + "\n" + value
        elif role == "duration":
            if params.get("duration") is None:
                continue
            value = used["duration"] = params["duration"]
        elif role == "aspect":
            if not params.get("aspect"):
                continue
            value = used["aspect"] = params["aspect"]
            if sources.get("aspect") != "user":
                used["aspectAuto"] = True
        elif role == "resolution":
            if not params.get("resolution"):
                continue
            mp = budget_share(tiers(profile)[params["resolution"]], inp, by_role)
            if mp != tiers(profile)[params["resolution"]]:
                used["megapixelsEach"] = mp
            value = _in_unit(mp, inp)
            used["resolution"] = params["resolution"]
        elif role == "seed":
            value = seed
        elif role == "steps":
            s = params.get("steps")
            if not s:
                continue
            value = int(s)
            used["steps"] = value
        elif role == "scale":
            value = job_scale(flow, params, profile)
            if value is None:
                continue
            value = used["scale"] = _num(value)
        elif role == "denoise":
            v = params.get("denoise")
            v = roles["denoise"].get("default") if v in (None, "") else v
            if v is None:
                continue
            value = used["denoise"] = _num(_clamp(v, roles["denoise"]))
        elif role == "segment_on":
            value = bool(segment)
        elif role in ("segment_start", "segment_length"):
            if not segment:
                continue
            value = segment[0] if role == "segment_start" else segment[1]
        else:
            continue
        for node, field in targets:
            _set(g, node, field, value)
    if "scale" not in used and any(has_role(flow, r) for r in SOURCE_ROLES) and profile.get("fixedScale"):
        used["scale"] = _num(float(profile["fixedScale"]))

    for ag in flow.get("autogrow") or []:
        target = g.get(ag["node"])
        if target is None:
            raise JobError("bad_flow", "The workflow has no node %s" % ag["node"])
        ins = target.setdefault("inputs", {})
        prefixes = [l["prefix"] for l in ag["links"]]
        for k in [k for k in ins if any(k.startswith(p) for p in prefixes)]:
            del ins[k]
        start = ag.get("start") or 0
        first, clones = None, set()
        for i, it in enumerate(by_role.get(ag["role"]) or []):
            ids = {t: "%s_%s%d" % (t, ag["role"], i) for t in ag["template"]}
            clones.update(ids.values())
            for t in ag["template"]:
                if t not in g:
                    raise JobError("bad_flow", "The workflow has no node %s" % t)
                node = copy.deepcopy(g[t])
                for k, v in node.get("inputs", {}).items():
                    if _refs(v) and v[0] in ids:
                        node["inputs"][k] = [ids[v[0]], v[1]]
                g[ids[t]] = node
            g[ids[ag["file"]["node"]]]["inputs"][ag["file"]["field"]] = file_of(it)
            for l in ag["links"]:
                if l.get("when") == "has_audio" and not it.get("has_audio"):
                    continue
                ins["%s%d" % (l["prefix"], start + i)] = [ids[l["from"]], l["output"]]
            first = first or ids
        if first:
            # Nodes outside the autogrow that read a template node read the
            # first asset's copy (the edit's base image).
            # The templates stay as they are for a later autogrow of the same role.
            for nid, node in g.items():
                if nid in clones or nid in ag["template"]:
                    continue
                for k, v in node.get("inputs", {}).items():
                    if _refs(v) and v[0] in first:
                        node["inputs"][k] = [first[v[0]], v[1]]

    for nid in sinks:
        ins = g.get(nid, {}).get("inputs", {})
        if "filename_prefix" in ins:
            ins["filename_prefix"] = prefix + job_id
    return _prune(g, sinks), used
