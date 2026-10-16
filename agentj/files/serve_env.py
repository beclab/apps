"""Start `agentj serve` with the service environment file applied, the way systemd's EnvironmentFile= would.

The file (0600, written by Agent J's own secret cards) is parsed literally — never sourced by a shell, so a `$` or a
backtick inside a saved key stays text. Usage: serve_env.py <env file> <argv…>. Nothing is printed.

The file sits under $HOME, which the Agent may write, while serve runs outside the fence: only names shaped like what the
phone's secret cards save (…_API_KEY, …_TOKEN, …_BASE_URL …) are taken; anything that could change which code a process
loads or where it keeps its state (PATH, LD_*, PYTHON*, OPENSSL_*, GIT_*, XDG_*, *_PROXY, AGENTJ_* …) never is.
"""
import os
import re
import sys

ALLOWED = re.compile(r"[A-Z][A-Z0-9_]{0,62}_(?:API_KEY|KEY|TOKEN|SECRET|PASSWORD|BASE_URL|API_BASE|ENDPOINT|MODEL)")
DENIED_PREFIX = ("LD_", "PYTHON", "BASH_", "UV_", "AGENTJ_", "AGENTJARVIS_", "OPENSSL_", "GIT_", "XDG_", "SSL_", "NODE_",
                 "GLIBC_", "PERL", "RUBY", "NPM_", "CURL_", "REQUESTS_")


def allowed(k: str) -> bool:
    return bool(ALLOWED.fullmatch(k)) and not k.startswith(DENIED_PREFIX) and not k.endswith("_PROXY")


def unescape(v: str) -> str:
    r"""Inside double quotes: \\ → \ and \" → ", read left to right (the inverse of agentj's service.py quoting)."""
    out, i = [], 0
    while i < len(v):
        if v[i] == "\\" and i + 1 < len(v) and v[i + 1] in '\\"':
            out.append(v[i + 1])
            i += 2
        else:
            out.append(v[i])
            i += 1
    return "".join(out)


def parse(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line[0] in "#;" or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        if k.startswith("export "):
            k = k[7:].strip()
        if not allowed(k):
            continue
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] == '"':
            v = unescape(v[1:-1])
        elif len(v) >= 2 and v[0] == v[-1] == "'":
            v = v[1:-1]
        out[k] = v
    return out


def main() -> None:
    path, argv = sys.argv[1], sys.argv[2:]
    env = dict(os.environ)
    try:
        with open(path, encoding="utf-8") as f:
            env.update(parse(f.read()))
    except FileNotFoundError:
        pass
    os.execvpe(argv[0], argv, env)


if __name__ == "__main__":
    main()
