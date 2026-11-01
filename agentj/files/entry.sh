#!/bin/bash
# Agent J on Olares — the one process the pod runs (uid 1000, HOME = the app's Data folder). Agent J, OpenCode, uv and
# bubblewrap come with the app's own image, in its read-only root-owned layer: nothing is downloaded or installed at boot.
# First boot: create this computer's identity, link the bundled skills, switch Agent J's own upgrades off (on Olares a new
# version arrives as an app upgrade with a new image), point OpenCode at the owner's Olares Router. Every boot: start the
# setup page (the entrance) and, while a seat is bound, keep `agentj serve` running — systemd's job on an ordinary host.
# No secret is ever written by this script or printed to the pod log.
set -u
umask 077
OLA="$HOME/.agentj-olares"
mkdir -p "$OLA" "$HOME/coding"
# The image's system directories stay first, so nothing the Agent writes under $HOME can stand in for agentj, uv, opencode,
# bwrap or the six names serve calls that this container has no use for (systemctl … sudo answer from the image). Other
# names resolve under $HOME, after them — the owner's harnesses live there (the same as on any Linux host, DESIGN.md). Every python3 here runs isolated (-I): no user site-packages
# under $HOME, no PYTHON* variables. Temporary files and the runtime dir stay out of
# $HOME: the fence hides /tmp from the Agent, not $HOME.
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin:$HOME/.opencode/bin"
export XDG_RUNTIME_DIR="/tmp/agentj-run-$(id -u)"
mkdir -p -m 700 "$XDG_RUNTIME_DIR"
phase() { printf '%s\n' "$1" > "$OLA/phase"; echo "[agentj-olares] $(date -u +%FT%TZ) $1"; }

# The setup page comes first so the entrance answers at once.
( while true; do python3 -I /opt/agentj-olares/setup_page.py; sleep 2; done ) &

for t in agentj opencode bwrap; do
  case "$(command -v "$t")" in /usr/local/bin/*|/usr/bin/*) ;; *) phase "error-image"; sleep infinity ;; esac
done

route_router() {
  # OpenCode → the owner's Olares Router. In-cluster calls need no key (Olares vouches for this app at the edge), so the
  # key variable holds a fixed non-secret placeholder. Only once, and only if the owner has not chosen a route yet.
  [ -n "${OLARES_ROUTER_URL:-}" ] || return 0
  [ -f "$OLA/router-done" ] && return 0
  local models model ctx
  models=$(curl -fsS -m 20 "$OLARES_ROUTER_URL/models") || { phase "router-unreachable"; return 0; }
  read -r model ctx < <(printf '%s' "$models" | python3 -I -c '
import json, sys
ms = [m for m in json.load(sys.stdin).get("data", []) if m.get("mode", "chat") == "chat"]
ms.sort(key=lambda m: m.get("readiness") != "ready")
print(ms[0]["id"], int(ms[0].get("context_size") or 0)) if ms else print("", 0)' 2>/dev/null)
  [ -n "${model:-}" ] || { phase "router-no-model"; return 0; }
  local extra=()
  [ "${ctx:-0}" -gt 0 ] 2>/dev/null && extra=(--max-output 16384 --context "$ctx")
  agentj provider add olares --base-url "$OLARES_ROUTER_URL" --model "$model" --name "Olares Router" "${extra[@]}" \
    >"$OLA/router.log" 2>&1 &&
    agentj agent opencode --model "olares/$model" >>"$OLA/router.log" 2>&1 &&
    printf '%s\n' "$model" > "$OLA/router-done"
}

[ -d "$HOME/.local/state/agentj" ] || agentj init --working-root "$HOME/coding" </dev/null >"$OLA/init.log" 2>&1
# The bundled skills (agentj-pair, agentj-update, …) are linked once, as the standard install does.
[ -f "$OLA/skills-done" ] || { agentj skill install </dev/null >"$OLA/skills.log" 2>&1 && : > "$OLA/skills-done"; }
# Upgrades come with the app (Market → upgrade, a new image): Agent J's daily check and nightly install are switched off
# once — they would write a second copy under $HOME, which the Agent can rewrite.
[ -f "$OLA/upgrades-off" ] || { agentj update auto off </dev/null >"$OLA/upgrades.log" 2>&1 &&
  agentj config auto-update off </dev/null >>"$OLA/upgrades.log" 2>&1 && : > "$OLA/upgrades-off"; }
route_router
phase "ready"

# serve supervisor. serve runs only while a seat is bound (the setup page keeps `bound` in step with the account), so no
# Agent is running while the setup page would accept a new seat code. It is restarted when it exits, when the service
# environment file changes (a key saved from the phone's secret card) or when the setup page asks.
ENVF="$HOME/.config/systemd/user/agentj.env"
stamp() { stat -c %Y "$ENVF" 2>/dev/null; }
while true; do
  if [ ! -f "$OLA/bound" ]; then sleep 3; continue; fi
  phase "serving"
  rm -f "$OLA/restart"
  python3 -I /opt/agentj-olares/serve_env.py "$ENVF" agentj serve --events quiet --no-stdin &
  pid=$! seen=$(stamp)
  while kill -0 "$pid" 2>/dev/null; do
    sleep 3
    if [ "$(stamp)" != "$seen" ] || [ -f "$OLA/restart" ] || [ ! -f "$OLA/bound" ]; then
      kill "$pid" 2>/dev/null; wait "$pid"; break
    fi
  done
  wait "$pid" 2>/dev/null
  [ -f "$OLA/bound" ] || phase "ready"
  sleep 3
done
