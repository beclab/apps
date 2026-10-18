"""Agent J on Olares — the setup page behind the app's entrance (stdlib only).

The entrance is `authLevel: private`: Olares has already signed the owner in before a request reaches this port. The
page shows where the install stands, takes the seat setup code (ajt_…) or installation code (AJI-…) once, binds this
computer with `agentj login`, and then tells the owner how to add the phone from the account page. A setup code goes to
`agentj login --seat -` on stdin and never touches the disk; an installation code (the CLI only reads it from a file) is
written 0600 inside Agent J's state directory, which the fenced Agent cannot see, and deleted at once. Neither is logged,
echoed or kept. A code is taken only while no seat is bound — and while unbound the supervisor (entry.sh) keeps
`agentj serve`, and so the Agent, stopped. Writes need our own Origin, `application/json` of at most 4 KiB, one at a time.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

HOME = os.path.expanduser("~")
OLA = os.path.join(HOME, ".agentj-olares")
STATE = os.environ.get("AGENTJ_STATE_DIR") or os.path.join(HOME, ".local/state/agentj")
PORT = int(os.environ.get("AGENTJ_SETUP_PORT", "8080"))
ACCOUNT_URL = os.environ.get("AGENTJ_ACCOUNT_URL", "https://agentj.app/account")
CODE = re.compile(r"AJI-[a-f0-9]{32}|ajt_[A-Za-z0-9_-]{43}")
LOCK = threading.Lock()
_cache: dict = {"t": 0.0, "v": None}


def _run(argv: list[str], timeout: int = 30, stdin: str | None = None) -> tuple[int, str]:
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, input=stdin,
                           stdin=subprocess.DEVNULL if stdin is None else None)
        return r.returncode, (r.stdout + r.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, type(e).__name__


def _read(name: str) -> str:
    try:
        with open(os.path.join(OLA, name), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def status() -> dict:
    if time.time() - _cache["t"] < 3 and _cache["v"]:
        return _cache["v"]
    s = {"phase": _read("phase") or "starting", "router_model": _read("router-done"), "bound": False}
    rc, out = _run(["agentj", "--version"], 10)
    s["version"] = out.split()[-1] if rc == 0 and out else ""
    if s["version"] and os.path.isdir(STATE):
        ob = onboarding()
        s["onboarding"] = ob or {}
        s["bound"] = bool(ob and ob.get("seat"))
        if ob is not None:
            sync_bound(s["bound"])
        rc, out = _run(["agentj", "name"], 10)
        m = re.search(r"「([^」]{1,40})」", out) if rc == 0 else None
        s["agent_name"] = m.group(1) if m else ""
    _cache.update(t=time.time(), v=s)
    return s


def onboarding() -> dict | None:
    """`agentj onboarding --json`, or None when it could not be read (then nothing is concluded from it)."""
    rc, out = _run(["agentj", "onboarding", "--json"], 20)
    try:
        ob = json.loads(out.splitlines()[-1]) if rc == 0 and out else None
    except (ValueError, IndexError):
        return None
    return ob if isinstance(ob, dict) and "seat" in ob else None


def sync_bound(seat: bool) -> None:
    """Keep the supervisor's `bound` flag in step with the account: data kept from an earlier install starts serve at once;
    a seat that went away (unlink, transfer) stops serve before a new code can be taken."""
    flag = os.path.join(OLA, "bound")
    if seat and not os.path.exists(flag):
        _touch("bound")
    elif not seat and os.path.exists(flag):
        os.unlink(flag)
        _cache["t"] = 0


def _sync_loop() -> None:
    while True:
        time.sleep(30)
        if os.path.isdir(STATE):
            ob = onboarding()
            if ob is not None:
                sync_bound(bool(ob.get("seat")))


def _touch(name: str) -> None:
    with open(os.path.join(OLA, name), "w", encoding="utf-8") as f:
        f.write(str(int(time.time())) + "\n")


def login(body: dict) -> dict:
    text = body.get("code") if isinstance(body.get("code"), str) else ""
    m = CODE.search(text)
    if not m:
        return {"ok": False, "msg": "no_code"}
    code = m.group(0)
    if os.path.exists(os.path.join(OLA, "bound")):
        return {"ok": False, "msg": "already_bound"}
    ob = onboarding()
    if ob is None or ob.get("seat"):
        return {"ok": False, "msg": "already_bound" if ob else "not_ready"}
    name = body.get("name") if isinstance(body.get("name"), str) else ""
    name = name.strip()[:32]
    named = ["--name", name] if name else []
    if code.startswith("ajt_"):
        rc, out = _run(["agentj", "login", "--seat", "-"] + named, 90, stdin=code + "\n")
    else:
        d = os.path.join(STATE, "olares-setup")
        os.makedirs(d, mode=0o700, exist_ok=True)
        path = os.path.join(d, f"code-{os.getpid()}-{time.time_ns()}")
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(code + "\n")
            rc, out = _run(["agentj", "login", "--install-code-file", path] + named, 90)
        finally:
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass
    out = out.replace(code, "…")
    if rc == 0:
        _touch("bound")
        _touch("restart")
        _cache["t"] = 0
    lines = [ln for ln in out.splitlines() if ln.startswith(("✓", "✗", "拒绝", "连不上"))] or out.splitlines()[-3:]
    return {"ok": rc == 0, "exit": rc, "msg": "\n".join(lines)[:1200]}


PAGE = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent J</title><style>
:root{--bg:#faf9f5;--card:#f0eee6;--ink:#2c2b26;--mute:#858585;--line:#e3dacc;--acc:#629887;--soft:#dbf5ec;--bad:#a23b2a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 Ubuntu,"PingFang SC","Noto Sans CJK SC",system-ui,sans-serif}
main{max-width:560px;margin:0 auto;padding:28px 18px 48px}h1{font-size:22px;margin:0 0 4px}.sub{color:var(--mute);margin:0 0 20px}
.step{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin:12px 0}
.step h2{font-size:16px;margin:0 0 8px;display:flex;gap:8px;align-items:center}.dot{width:10px;height:10px;border-radius:50%;background:var(--line);flex:none}
.done .dot{background:var(--acc)}.now{border-color:var(--acc)}textarea,input{width:100%;font:inherit;padding:10px;border:1px solid var(--line);border-radius:10px;background:#faf9f5;color:var(--ink)}
.buyrow{display:flex;justify-content:flex-end;margin-top:12px}.buy{padding:10px 16px;border-radius:10px;background:var(--ink);color:var(--bg);text-decoration:none}.guide{display:block;width:100%;max-height:100px;margin:10px 0}textarea{height:86px;resize:vertical}button{margin-top:10px;font:inherit;font-weight:700;border:0;border-radius:10px;padding:10px 16px;background:var(--ink);color:var(--bg);cursor:pointer}
button:disabled{opacity:.5}.msg{white-space:pre-wrap;margin-top:10px;font-size:14px}.bad{color:var(--bad)}.ok{color:var(--acc)}a{color:var(--ink);text-decoration-color:#71bbde}
.mute{color:var(--mute);font-size:14px}ol{margin:6px 0 0;padding-left:20px}code{background:var(--soft);padding:1px 5px;border-radius:5px}
</style></head><body><main>
<h1>Agent J</h1><p class="sub" data-t="sub"></p>
<div class="step" id="s1"><h2><span class="dot"></span><span data-t="s1"></span></h2><div class="mute" id="s1d"></div></div>
<div class="step" id="s2"><h2><span class="dot"></span><span data-t="s2"></span></h2><div id="s2d">
<p class="mute" data-t="s2h"></p><p><a href="https://agentj.app/account" target="_blank" rel="noopener noreferrer">https://agentj.app/account</a></p><svg class="guide" role="img" aria-labelledby="guide-title" viewBox="0 0 480 80"><title id="guide-title"></title><rect x="1" y="1" width="478" height="78" rx="10" fill="#dbf5ec"/><text x="18" y="32" data-t="guide1" font-size="14"></text><text x="18" y="60" data-t="guide2" font-size="14"></text></svg><textarea id="code" autocomplete="off" spellcheck="false"></textarea>
<p class="mute" data-t="nameh" style="margin:10px 0 4px"></p><input id="name" maxlength="32" autocomplete="off">
<button id="go" data-t="go"></button><div class="msg" id="m2"></div><p class="mute" data-t="buyh"></p><div class="buyrow"><a class="buy" href="https://agentj.app/account?source=olares&amp;utm_source=olares&amp;utm_medium=setup" target="_blank" rel="noopener noreferrer" data-t="buy"></a></div></div></div>
<div class="step" id="s3"><h2><span class="dot"></span><span data-t="s3"></span></h2><div id="s3d" class="mute"></div></div>
<p class="mute" data-t="foot"></p>
</main><script>
const zh=(new URLSearchParams(location.search).get('lang')||navigator.language||'').toLowerCase().startsWith('zh');
const T=zh?{sub:'在你的 Olares 上运行的 Agent J：用手机指挥这台机器上的 AI Agent。',s1:'安装 Agent J',s2:'绑定你的席位',
s2h:'在下方账户页的空席位卡上点「复制安装提示词」。整段粘贴就行，不用挑出代码；设置码不会显示或保存。',
placeholder:'把复制的整段安装提示粘贴到这里',guide1:'① 空席位卡 → 复制安装提示词',guide2:'② 整段粘贴到下方 → 绑定',buyh:'还没有席位？先注册并购买一个，再回来粘贴。',buy:'购买席位',nameh:'给这个 Agent 起个名字（可不填）',go:'绑定',s3:'添加手机遥控器',foot:'这个页面只在你的 Olares 登录后可见。设置码只用一次，用完即删。',
ph:{starting:'正在启动…','error-image':'应用镜像不完整，已停止（请重新安装或联系我们）',ready:'已安装',serving:'已安装，正在运行'},
pair:a=>`<ol><li>手机打开 <a href="${a}" target="_blank" rel="noopener">${a}</a> 登录</li><li>找到这台 Agent J 主机「${N}」的席位卡，点「添加遥控器」</li><li>用通行密钥确认，按页面提示完成</li></ol>`,
paired:'手机已配对 ✓ 现在可以在手机上和 Agent 说话了。',model:m=>`模型：Olares Router 上的 ${m}（OpenCode）`,
no_code:'没找到设置码：请粘贴 ajt_ 或 AJI- 开头的码，或整段安装提示词。',already_bound:'这台 Olares 已经绑定了席位。要换席位，先在 Agent J Terminal 里运行 agentj unlink。',not_ready:'Agent J 还没准备好，请稍等再试。',wait:'正在绑定…',bound:'已绑定'}
:{sub:'Agent J on your Olares: direct the AI agent on this machine from your phone.',s1:'Install Agent J',s2:'Bind your seat',
s2h:'On the account page below, press “Copy installation prompt” on an empty seat card. Paste the entire prompt here; no need to pick out the code. The setup code is never shown or kept.',
placeholder:'Paste the entire copied installation prompt here',guide1:'1. Empty seat card → Copy installation prompt',guide2:'2. Paste all of it below → Bind',buyh:'No seat yet? Register and buy one, then come back to paste.',buy:'Buy a seat',nameh:'Name this Agent (optional)',go:'Bind',s3:'Add your phone as a remote',foot:'Only visible after you sign in to your Olares. The code is used once and deleted.',
ph:{starting:'Starting…','error-image':'The app image is incomplete; stopped (reinstall, or contact us)',ready:'Installed',serving:'Installed and running'},
pair:a=>`<ol><li>On your phone open <a href="${a}" target="_blank" rel="noopener">${a}</a> and sign in</li><li>On the seat card of “${N}” choose Add a remote</li><li>Confirm with your passkey and follow the page</li></ol>`,
paired:'Phone paired ✓ You can talk to the Agent from your phone now.',model:m=>`Model: ${m} on Olares Router (OpenCode)`,
no_code:'No setup code found: paste the code starting with ajt_ or AJI-, or the whole installation prompt.',already_bound:'This Olares is already bound to a seat. To change it, run agentj unlink in Agent J Terminal first.',not_ready:'Agent J is not ready yet; try again in a moment.',wait:'Binding…',bound:'Bound'};
let N='';const $=i=>document.getElementById(i);
document.documentElement.lang=zh?'zh-CN':'en';
document.querySelectorAll('[data-t]').forEach(e=>e.textContent=T[e.dataset.t]);
$('code').placeholder=T.placeholder;$('guide-title').textContent=T.guide1+'; '+T.guide2;
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function mark(id,state){$(id).classList.toggle('done',state==='done');$(id).classList.toggle('now',state==='now')}
async function tick(){let s;try{s=await (await fetch('api/status',{cache:'no-store'})).json()}catch{return}
N=esc(s.agent_name||'');const inst=!!s.version;mark('s1',inst?'done':'now');
$('s1d').textContent=(T.ph[s.phase]||s.phase)+(s.version?' · v'+s.version:'')+(s.router_model?' · '+T.model(s.router_model):'');
mark('s2',s.bound?'done':(inst?'now':''));$('go').disabled=!inst||s.bound;
if(s.bound){$('s2d').innerHTML='<p class="ok">'+T.bound+(N?' · '+N:'')+'</p>'}
const ob=s.onboarding||{};const paired=ob.phone||ob.computer;
mark('s3',paired?'done':(s.bound?'now':''));$('s3d').innerHTML=s.bound?(paired?'<p class="ok">'+T.paired+'</p>':T.pair(s.account_url||'%ACCOUNT%')):''}
$('go').onclick=async()=>{const code=$('code').value;$('code').value='';$('go').disabled=true;$('m2').className='msg';$('m2').textContent=T.wait;
let r;try{r=await (await fetch('api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code,name:$('name').value})})).json()}catch{r={ok:false,msg:'network'}}
$('m2').className='msg '+(r.ok?'ok':'bad');$('m2').textContent=T[r.msg]||r.msg;$('go').disabled=r.ok;tick()};
tick();setInterval(tick,4000);
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    server_version = "agentj-olares"

    def log_message(self, fmt, *args):          # method + path + status only; never a body
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        for k, v in (("Content-Type", ctype), ("Content-Length", str(len(body))), ("Cache-Control", "no-store"),
                     ("X-Content-Type-Options", "nosniff"), ("Referrer-Policy", "no-referrer"),
                     ("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
                                                "connect-src 'self'; frame-ancestors 'self' https:")):
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj: dict, code: int = 200) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def do_GET(self):
        p = urlparse(self.path).path
        if p in ("/", "/index.html"):
            self._send(200, PAGE.replace("%ACCOUNT%", ACCOUNT_URL).encode(), "text/html; charset=utf-8")
        elif p == "/api/status":
            self._json({**status(), "account_url": ACCOUNT_URL})
        elif p == "/healthz":
            self._send(200, b"ok", "text/plain")
        else:
            self._send(404, b"", "text/plain")

    def do_POST(self):
        if urlparse(self.path).path != "/api/login":
            return self._send(404, b"", "text/plain")
        origin = self.headers.get("Origin") or ""
        host = self.headers.get("X-Forwarded-Host") or self.headers.get("Host") or ""
        if not origin or urlparse(origin).netloc != host.split(",")[0].strip():
            return self._json({"ok": False, "msg": "origin"}, 403)
        try:
            n = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            n = -1
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if not 0 < n <= 4096 or ctype != "application/json":
            return self._json({"ok": False, "msg": "bad_request"}, 400)
        try:
            body = json.loads(self.rfile.read(n))
        except ValueError:
            return self._json({"ok": False, "msg": "bad_request"}, 400)
        if not isinstance(body, dict):
            return self._json({"ok": False, "msg": "bad_request"}, 400)
        if not LOCK.acquire(blocking=False):
            return self._json({"ok": False, "msg": "busy"}, 409)
        try:
            self._json(login(body))
        finally:
            LOCK.release()


if __name__ == "__main__":
    threading.Thread(target=_sync_loop, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
