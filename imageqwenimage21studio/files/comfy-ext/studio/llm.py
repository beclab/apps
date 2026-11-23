"""Prompt rewriting through an OpenAI-compatible chat endpoint (Olares Router)."""
import asyncio
import json
import logging
import os
import re
import time

from aiohttp import ClientSession, ClientTimeout

log = logging.getLogger("comfyapp.studio")

REF = re.compile(r"\{\{[^{}]+\}\}")
THINK = re.compile(r"<think>.*?</think>", re.S)
FENCE = re.compile(r"^```[\w-]*\n(.*?)\n```$", re.S)
DEFAULT_MODEL = "default-chat"

REFS = ("- Keep every token written as {{...}} exactly as it appears, character for character. They are references to the "
        "user's uploaded assets. Do not translate, rename or drop them.")
ONLY = "- Output only the prompt, with no explanation and no code fence."
EN = "Write in English, translating the user's text if needed."
SAME = "Write in the same language as the user's text."
STRUCTURE = """You rewrite a video generation prompt into the structure below.

Rules:
%s
- Keep the user's subjects, characters and actions. Do not add or remove characters or change who they are.
- You may fill in camera work, lighting and sound that fit the description, briefly and concretely.
- %s
%s

Structure:
"""
GENERATE = """You rewrite a short image description into a detailed prompt for a text-to-image model.

Rules:
%s
- Keep the user's subject, the people and objects, and any text they want shown. Do not add or remove subjects.
- Add concrete visual detail that fits: composition and framing, setting, lighting, colors, materials, style or medium.
- Put any words that must appear in the image in double quotes, exactly as the user wrote them.
- One paragraph, at most about 120 words.
- %s
%s
"""
EDIT = """You rewrite an image editing instruction so an image editing model follows it precisely.

Rules:
%s
- The {{...}} tokens are the input images; the first image in the instruction is the one being edited unless the user says otherwise.
- State what to change and where, then what must stay the same (identity, pose, framing, the rest of the scene).
- Do not invent changes the user did not ask for.
- Keep it short: one to three sentences.
- %s
%s
"""
TRANSLATE = """You translate %s prompt into English.

Rules:
%s
- Translate faithfully. Keep the structure, line breaks and order; do not add, expand or summarize anything.
%s- Text that is already English stays as it is.
%s
"""
IN_IMAGE = "- Text that must appear in the image, usually in quotes, stays in its original language.\n"

# Appended to an app's own system prompt (profile.prompts); these win over it.
STUDIO_RULES = """

## Studio rules (these take precedence over anything above)

- The user's message starts with the job: the mode, duration or aspect ratio, and the assets. Assets are written as {{...}} tokens, and the list says what each one is and which label the model will see in its place. Attached images follow the user's prompt, each introduced by its token.
- Keep every {{...}} token from the user's prompt exactly as written, character for character, and refer to the user's assets only by their tokens: never write the label a token turns into, and never translate, rename or drop a token.
- %s
- Output only the prompt, with no explanation and no code fence."""
LANG_EN = ("Write the prompt in English, translating the user's text if needed. Words to be shown in the picture and "
           "spoken lines keep their original language. This replaces any other language rule.")
LANG_SAME = ("Write the prompt's descriptive text in the same language as the user's text; field names and fixed markers "
             "stay as specified. Words to be shown in the picture and spoken lines keep their original language. "
             "This replaces any other language rule.")

ROLE_TEXT = {"first_frame": "first frame", "last_frame": "last frame", "ref_image": "reference image",
             "ref_video": "reference video", "ref_audio": "reference audio", "mask": "mask"}


def modes(kind, template, prompts=None):
    """The rewrite modes a studio offers: video needs the app's prompts or
    its prompt template, image always has them."""
    if kind == "image":
        return ("enhance_en", "enhance", "translate_en")
    if prompts or template:
        return ("structure_en", "structure", "translate_en")
    return ()


def system_prompt(mode, kind, template, task="generate", flow="", prompts=None, text=None):
    """The system prompt for mode, or None when the studio does not offer it.
    task (image): generate or edit. flow (video): the flow's mode, whose
    prompts entry is used after prompts["shared"]. text: the user's prompt;
    translate mentions tokens only when it has some, since a small model
    otherwise writes made-up ones."""
    prompts = prompts or {}
    if mode not in modes(kind, template, prompts):
        return None
    if mode == "translate_en":
        refs = REFS if text is None or REF.search(text) else ""
        if kind == "image":
            return TRANSLATE % ("an image generation or editing", refs, IN_IMAGE, ONLY)
        return TRANSLATE % ("a video generation", refs, "", ONLY)
    english = mode.endswith("_en")
    own = prompts.get(task) if kind == "image" else prompts.get(flow)
    if own:
        head = prompts.get("shared", "") if kind != "image" else ""
        return (head + "\n\n" if head else "") + own + STUDIO_RULES % (LANG_EN if english else LANG_SAME)
    lang = EN if english else SAME
    if kind == "image":
        return (EDIT if task == "edit" else GENERATE) % (REFS, lang, ONLY)
    if not template:
        return None
    return STRUCTURE % (REFS, lang, ONLY) + template


def job_text(prompt, kind, flow="", duration=None, aspect="", task="", assets=(), english=False):
    """The user message: the job, the assets and the prompt. english: the
    user asked for an English prompt; said here too because an app guide's
    own language rule (Qwen's edit guide keeps Chinese Chinese) otherwise
    wins over the system prompt's. assets: dicts
    with token, role, kind, name, duration, label (what the model sees in
    place of the token) and attached (what follows the prompt for it, e.g.
    "image attached")."""
    lines = []
    if kind == "image":
        lines.append("Task: %s" % ("edit the input images" if task == "edit" else "generate an image"))
    else:
        lines.append("Mode: %s" % (flow or "video"))
        if duration:
            lines.append("Duration: %g seconds" % float(duration))
    if aspect and aspect != "auto":
        lines.append("Aspect ratio: %s (already set; do not write it in the prompt)" % aspect)
    if assets:
        lines.append("Assets:")
        for a in assets:
            bits = [ROLE_TEXT.get(a.get("role"), a.get("role") or a.get("kind") or "asset")]
            if a.get("name"):
                bits.append('"%s"' % a["name"])
            if a.get("duration"):
                bits.append("%.1f s" % float(a["duration"]))
            if a.get("label"):
                bits.append("the model sees it as %s" % a["label"])
            if a.get("attached"):
                bits.append(a["attached"])
            lines.append("- %s: %s" % (a["token"], ", ".join(bits)))
        if kind == "image" and task == "edit":
            lines.append("The first image is the one being edited.")
    if english:
        lines.append("Output language: English, whatever language the user prompt is in. Text to be shown in the "
                     "image and spoken lines keep their original language.")
    lines += ["", "User prompt:", prompt]
    return "\n".join(lines)


def sampling(mode, kind, task, model, effort="auto", info=None):
    """Request fields for mode. Video structuring and image edit think,
    with Qwen3.5's thinking preset (temperature 1.0, top_p 0.95); edit
    drops the presence penalty so the rewrite stays with what the user
    named. Without thinking a 9B model wrote the edit guide's thinking
    steps into its answer. Image generation skips thinking (the
    non-thinking preset, 0.7 and 0.8): it kept its quality and took about
    3 s instead of a minute. effort: the level picked in Settings, sent to
    the thinking modes; "auto" leaves the model's default. Router turns
    reasoning_effort "none" into each engine's thinking switch. info: the
    model's Router row; a model Router says cannot reason gets no effort.
    Qwen-only fields go to Qwen3.5 and 3.6 models alone, since other
    vendors reject unknown fields."""
    edit = kind == "image" and task == "edit"
    think = mode != "translate_en" and (kind != "image" or edit)
    if think:
        body = {"temperature": 1.0, "top_p": 0.95, "presence_penalty": 0.0 if edit else 1.5, "max_tokens": 8192}
    elif mode != "translate_en":
        body = {"temperature": 0.7, "top_p": 0.8, "presence_penalty": 1.5, "max_tokens": 4096}
    else:
        body = {"temperature": 0.7, "top_p": 0.8, "presence_penalty": 0.0, "max_tokens": 2048}
    m = (model or "").lower()
    if any(k in m for k in ("qwen3.5", "qwen3_5", "qwen3.6", "qwen3_6")):
        body.update(top_k=20, min_p=0.0)
    if not info or info.get("reasoning"):
        if not think:
            body["reasoning_effort"] = "none"
        elif effort and effort != "auto":
            body["reasoning_effort"] = effort
    return body


class LlmError(Exception):
    def __init__(self, code, message, status=502):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def clean(text):
    text = THINK.sub("", text or "").strip()
    m = FENCE.match(text)
    return (m.group(1) if m else text).strip()


def chat_models(data):
    """The chat models of a /models reply: id, vision, context, and whether
    it reasons with the effort levels it takes besides "none"."""
    out = []
    for m in (data or {}).get("data") or []:
        if not isinstance(m, dict) or not m.get("id"):
            continue
        if m.get("mode") not in (None, "", "chat"):
            continue
        sup = m.get("supports") or []
        if isinstance(sup, dict):
            sup = [k for k, v in sup.items() if v]
        sup = {str(s).replace("supports_", "") for s in sup}
        levels = [str(v) for v in (m.get("reasoning_levels") or []) if v and v != "none"]
        out.append({"id": m["id"], "vision": "vision" in sup or bool(m.get("supports_vision")),
                    "context": m.get("context_size") or 0, "reasoning": bool(m.get("reasoning")),
                    "levels": levels, "default_level": m.get("default_reasoning_level") or ""})
    return out


class Llm:
    """state: a json file keeping the model and thinking effort picked in
    Settings."""

    def __init__(self, base, model, key="", ttl=60, state=""):
        self.base = (base or "").rstrip("/")
        self.default = model or DEFAULT_MODEL
        self.key = key or ""
        self.ttl = ttl
        self.state = state
        self.selected = self.default
        self.chosen = "auto"
        if state and os.path.exists(state):
            try:
                with open(state) as f:
                    saved = json.load(f)
                self.selected = saved.get("model") or self.default
                self.chosen = saved.get("effort") or "auto"
            except (OSError, ValueError, AttributeError):
                pass
        self.ready = False
        self.listed = False
        self.models = []
        self.checked = 0.0
        self.probing = None

    @property
    def model(self):
        """The model requests go to: the selection while Router lists it,
        else default-chat. Before the first list the selection stands."""
        if self.selected == DEFAULT_MODEL or not self.listed or any(m["id"] == self.selected for m in self.models):
            return self.selected
        return DEFAULT_MODEL

    def info(self, model=None):
        model = model or self.model
        return next((m for m in self.models if m["id"] == model), None)

    @property
    def effort(self):
        """The chosen effort while the model in use takes it, else auto."""
        info = self.info()
        return self.chosen if info and self.chosen in info["levels"] else "auto"

    def select(self, model, effort=None):
        """effort None keeps the current choice."""
        self.selected = model or DEFAULT_MODEL
        if effort is not None:
            self.chosen = effort or "auto"
        if self.state:
            os.makedirs(os.path.dirname(self.state), exist_ok=True)
            tmp = self.state + ".tmp"
            with open(tmp, "w") as f:
                json.dump({"model": self.selected, "effort": self.chosen}, f)
            os.replace(tmp, self.state)

    def headers(self):
        return {"Authorization": "Bearer " + self.key} if self.key else {}

    def status(self):
        """The cached readiness; starts a background probe when stale. A
        failed probe is retried sooner, so Router installed later shows up."""
        ttl = self.ttl if self.ready else min(self.ttl, 15)
        if self.base and time.time() - self.checked > ttl and self.probing is None:
            self.probing = asyncio.ensure_future(self.probe())
        model = self.model
        info = self.info(model)
        return {"ready": self.ready, "model": model, "selected": self.selected,
                "fallback": model != self.selected, "vision": info["vision"] if info else None,
                "effort": self.effort, "levels": info["levels"] if info else [],
                "default_level": info["default_level"] if info else ""}

    async def probe(self):
        models = None
        try:
            async with ClientSession(timeout=ClientTimeout(total=5)) as s:
                async with s.get(self.base + "/models", headers=self.headers()) as r:
                    data = await r.json(content_type=None) if r.status == 200 else None
            if isinstance(data, dict):
                models = chat_models(data)
        except Exception as e:
            log.info("studio: llm probe %s: %s", self.base, e)
        ready = bool(models)
        if ready != self.ready:
            log.info("studio: llm %s at %s", "ready" if ready else "unavailable", self.base)
        if models is not None:
            self.models, self.listed = models, True
        self.ready, self.checked, self.probing = ready, time.time(), None
        return ready

    async def rewrite(self, prompt, system, user=None, images=(), fields=None, timeout=180, labels=None):
        """user: the message text (default: prompt); images: (token,
        data URL) pairs attached after it. A model that turns the images
        down gets the text alone. labels: what the image model sees for
        each token ({"<Picture 1>": "{{id}}"}); an app prompt written
        around those labels makes the chat model write them, so they are
        turned back into tokens."""
        if not self.base or not self.ready:
            raise LlmError("llm_unavailable", "No chat model is available", 503)
        model = self.model
        info = self.info(model)
        if info and not info["vision"]:
            images = ()
        try:
            out = await self._chat(model, system, user or prompt, images, fields, timeout)
        except LlmError as e:
            if not images or e.code != "llm_rejected":
                raise
            log.info("studio: llm %s refused images (%s), retrying with text", model, e.message)
            out = await self._chat(model, system, user or prompt, (), fields, timeout)
        for label in sorted(labels or {}, key=len, reverse=True):
            out = out.replace(label, labels[label])
        lost = set(REF.findall(prompt)) - set(REF.findall(out))
        if lost:
            raise LlmError("refs_lost", "The rewrite dropped asset references", 422)
        known = set(REF.findall(prompt)) | set(REF.findall(user or ""))
        made_up = set(REF.findall(out)) - known
        if made_up:
            log.info("studio: llm %s made up %s, removed", model, sorted(made_up))
            out = REF.sub(lambda m: m.group(0) if m.group(0) in known else "", out)
            out = re.sub(r"[ \t]{2,}", " ", re.sub(r"[ \t]+([,.;:!?])", r"\1", out)).strip()
        return out

    async def _chat(self, model, system, user, images, fields, timeout):
        content = user
        if images:
            content = [{"type": "text", "text": user}]
            for tok, url in images:
                content += [{"type": "text", "text": tok + ":"}, {"type": "image_url", "image_url": {"url": url}}]
        body = {"model": model, "stream": False, **(fields or {"temperature": 0.3}),
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}]}
        try:
            async with ClientSession(timeout=ClientTimeout(total=timeout)) as s:
                async with s.post(self.base + "/chat/completions", json=body, headers=self.headers()) as r:
                    data = await r.json(content_type=None)
                    if r.status != 200:
                        err = data.get("error") if isinstance(data, dict) else None
                        msg = (err.get("message") if isinstance(err, dict) else err) or "HTTP %d" % r.status
                        raise LlmError("llm_rejected" if 400 <= r.status < 500 else "llm_failed", str(msg)[:500])
        except asyncio.TimeoutError:
            raise LlmError("llm_timeout", "The chat model did not answer in time", 504)
        except LlmError:
            raise
        except Exception as e:
            raise LlmError("llm_failed", str(e)[:500])
        try:
            msg = data["choices"][0]["message"]
            out = clean(msg["content"])
        except (KeyError, IndexError, TypeError):
            raise LlmError("llm_failed", "The chat model returned no text")
        if not out:
            raise LlmError("llm_failed", "The chat model returned no text")
        reasoning = msg.get("reasoning_content") or ""
        log.info("studio: llm %s answered: %d chars, %d reasoning chars, finish=%s, usage=%s", model, len(out),
                 len(reasoning), data["choices"][0].get("finish_reason"), data.get("usage"))
        return out
