#!/bin/sh
# Pin sandbox runtime OpenClaw to NEMOCLAW_OPENCLAW_VERSION (post-build npm upgrade).
# Canonical copy — also embedded as pin-openclaw-in-sandbox.sh in configmap-sandbox-bridge.yaml.
set -u

CLUSTER_CTR="${CLUSTER_CTR:-openshell-cluster-nemoclaw}"
NS="${NS:-openshell}"
SBX="${SBX:-my-assistant}"
LOG="${NEMOCLAW_PIN_LOG_PREFIX:-[openclaw-pin]}"
RESTART_GW="${NEMOCLAW_PIN_RESTART_GATEWAY:-0}"
VERBOSE="${NEMOCLAW_PIN_VERBOSE:-0}"

# Prefix log lines without sed (LOG may contain / | [ ] which break sed s///).
_pin_log_pipe() {
  _pfx="${1:-}"
  while IFS= read -r _ln || [ -n "$_ln" ]; do
    printf '%s %s\n' "$_pfx" "$_ln"
  done
}

_agent_container_running() {
  docker exec "$CLUSTER_CTR" kubectl -n "$NS" get pod "$SBX" \
    -o 'jsonpath={.status.containerStatuses[?(@.name=="agent")].state.running.startedAt}' 2>/dev/null \
    | grep -q .
}

_want="${NEMOCLAW_OPENCLAW_VERSION:-}"
_want="${_want#v}"
_sentinel=/workspace/.nemoclaw-openclaw-pin

if [ "${1:-}" = "--check-only" ]; then
  [ -z "$_want" ] && exit 0
  _have=""
  if [ -f "$_sentinel" ]; then
    _have=$(head -1 "$_sentinel" 2>/dev/null | tr -d '\r\n ')
  fi
  [ "$_have" = "$_want" ] || exit 1
  _agent_container_running || exit 1
  _kx="docker exec $CLUSTER_CTR kubectl -n $NS exec $SBX -c agent --"
  _live=$($_kx env PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/sandbox/.local/bin:/sandbox/.linuxbrew/Homebrew/bin:/sandbox/.linuxbrew/bin" \
    sh -c 'openclaw --version 2>/dev/null | head -1 | awk "{for(i=1;i<=NF;i++) if (\$i ~ /^v?[0-9]+\\.[0-9]+\\./) {print \$i; exit}}" | tr -d "v"' 2>/dev/null | tr -d '\r\n ')
  [ "$_live" = "$_want" ] && exit 0
  exit 1
fi

if [ ! -f /workspace/.nemoclaw-installed ]; then
  exit 0
fi

if ! _agent_container_running; then
  echo "${LOG} sandbox pod ${NS}/${SBX} agent container not running; skip pin this tick (sandbox may be creating or rebuilding)"
  exit 1
fi

if [ -z "$_want" ]; then
  docker exec "$CLUSTER_CTR" kubectl -n "$NS" exec "$SBX" -c agent -- \
    sh -c 'test -f /sandbox/.openclaw-pinned-marker && rm -f /sandbox/.openclaw-pinned-marker && echo "removed pin marker (env cleared)" || true' \
    2>/dev/null | _pin_log_pipe "$LOG" || true
  rm -f "$_sentinel" 2>/dev/null || true
  if [ "$VERBOSE" = "1" ]; then
    echo "${LOG} NEMOCLAW_OPENCLAW_VERSION unset — using sandbox build pin; no runtime upgrade"
  fi
  exit 0
fi

_have=""
if [ -f "$_sentinel" ]; then
  _have=$(head -1 "$_sentinel" 2>/dev/null | tr -d '\r\n ')
fi

_kx="docker exec $CLUSTER_CTR kubectl -n $NS exec $SBX -c agent --"
_live=$($_kx env PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/sandbox/.local/bin:/sandbox/.linuxbrew/Homebrew/bin:/sandbox/.linuxbrew/bin" \
  sh -c 'openclaw --version 2>/dev/null | head -1 | awk "{for(i=1;i<=NF;i++) if (\$i ~ /^v?[0-9]+\\.[0-9]+\\./) {print \$i; exit}}" | tr -d "v"' 2>/dev/null | tr -d '\r\n ')

if [ -n "$_live" ] && [ "$_live" = "$_want" ]; then
  if [ "$_have" != "$_want" ]; then
    mkdir -p /workspace 2>/dev/null || true
    printf "%s\n" "$_want" > "$_sentinel"
  fi
  $_kx python3 /sandbox/.nemoclaw/patch-openclaw-gog-skill.py 2>/dev/null \
    2>&1 | _pin_log_pipe "${LOG}:gog-skill" || true
  if [ "$VERBOSE" = "1" ]; then
    echo "${LOG} live sandbox openclaw=${_live} matches NEMOCLAW_OPENCLAW_VERSION=${_want}; no action"
  fi
  exit 0
fi

echo "${LOG} DRIFT: live sandbox openclaw=${_live:-<unknown>} vs NEMOCLAW_OPENCLAW_VERSION=${_want}; pinning via npm install -g openclaw@${_want}"

# Gateway holds dist/extensions open; npm global upgrade then hits ENOTEMPTY if we
# install while it is still running. Stop it before rm/npm (restart after success).
echo "${LOG} stopping sandbox gateway before npm upgrade"
docker exec "$CLUSTER_CTR" kubectl -n "$NS" exec "$SBX" -c agent -- \
  sh -c '
    pkill -9 -f "openclaw[- ]gateway" 2>/dev/null || true
    sleep 2
    pgrep -fa "openclaw[- ]gateway" 2>/dev/null && echo "WARN: gateway still alive after pkill -9" || echo "gateway stopped"
  ' 2>&1 | _pin_log_pipe "$LOG" || true

_ok=0
_log_capture=$($_kx sh -c "
    set -e
    VER=\"${_want}\"
    install_flags='--no-fund --no-audit --prefer-online --force'
    cleanup_targets='/usr/local/lib/node_modules/openclaw /sandbox/.local/lib/node_modules/openclaw /tmp/npm-global/lib/node_modules/openclaw'
    npm cache clean --force >/dev/null 2>&1 || true
    for d in \$cleanup_targets; do rm -rf \"\$d\" 2>/dev/null || true; done
    sleep 1
    if command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
      for d in \$cleanup_targets; do sudo rm -rf \"\$d\" 2>/dev/null || true; done
      sudo npm install -g \$install_flags \"openclaw@\$VER\" 2>&1
    elif [ -w /usr/local/lib ]; then
      npm install -g \$install_flags \"openclaw@\$VER\" 2>&1
    else
      echo 'system /usr/local not writable; falling back to /sandbox/.local prefix'
      rm -rf /sandbox/.local/lib/node_modules/openclaw /tmp/npm-global/lib/node_modules/openclaw 2>/dev/null || true
      mkdir -p /sandbox/.local
      NPM_CONFIG_PREFIX=/sandbox/.local npm install -g \$install_flags \"openclaw@\$VER\" 2>&1
      ln -sf /sandbox/.local/bin/openclaw /usr/local/bin/openclaw 2>/dev/null \
        || echo 'note: cannot symlink /usr/local/bin/openclaw (read-only); /sandbox/.local/bin/openclaw must come first in gateway PATH'
    fi
    _ver_out=\$(openclaw --version 2>&1 | head -1) || _ver_out='<exec failed>'
    echo \"post-install: \$_ver_out\"
    case \"\$_ver_out\" in
      *\"\$VER\"*) ;;
      *)
        echo \"FAIL: --version output does not contain \$VER (got: \$_ver_out)\"
        exit 11
        ;;
    esac
    _probe=\"const Module=require('module');const r=Module.createRequire('/usr/local/lib/node_modules/openclaw/');try{const p=r.resolve('openclaw');console.log('resolve OK:',p);}catch(e){if(e&&e.code==='MODULE_NOT_FOUND'){const r2=Module.createRequire('/sandbox/.local/lib/node_modules/openclaw/');try{const p=r2.resolve('openclaw');console.log('resolve OK:',p);}catch(e2){console.error('resolve FAIL:',e2&&e2.message);process.exit(12);}}else{console.error('resolve FAIL:',e&&e.message);process.exit(12);}}\"
    node -e \"\$_probe\"
  " 2>&1) && _ok=1

printf '%s\n' "$_log_capture" | _pin_log_pipe "$LOG"

if [ "$_ok" != "1" ]; then
  echo "${LOG} WARN: openclaw upgrade to ${_want} did NOT pass post-install verify; next tick will retry"
  exit 1
fi

mkdir -p /workspace 2>/dev/null || true
printf "%s\n" "$_want" > "$_sentinel"
docker exec "$CLUSTER_CTR" kubectl -n "$NS" exec "$SBX" -c agent -- \
  sh -c "printf '%s\n' '${_want}' > /sandbox/.openclaw-pinned-marker && chown sandbox:sandbox /sandbox/.openclaw-pinned-marker 2>/dev/null; ls -l /sandbox/.openclaw-pinned-marker 2>&1" \
  2>&1 | _pin_log_pipe "${LOG} marker:"
docker exec "$CLUSTER_CTR" kubectl -n "$NS" exec "$SBX" -c agent -- \
  python3 /sandbox/.nemoclaw/patch-openclaw-gog-skill.py 2>/dev/null \
  2>&1 | _pin_log_pipe "${LOG}:gog-skill" || true

if [ "$RESTART_GW" = "1" ]; then
  echo "${LOG} killing existing gateway so new openclaw binary launches"
  docker exec "$CLUSTER_CTR" kubectl -n "$NS" exec "$SBX" -c agent -- \
    sh -c '
      pkill -9 -f "openclaw[- ]gateway" 2>/dev/null
      sleep 1
      pgrep -fa "openclaw[- ]gateway" 2>/dev/null && echo "WARN: gateway still alive after pkill -9" || echo "gateway gone"
    ' 2>&1 | _pin_log_pipe "$LOG"
  echo "${LOG} forcing gateway restart"
  sh /opt/nemoclaw/sandbox-ensure-gateway.sh 2>&1 | _pin_log_pipe "${LOG} gw:"
fi

exit 0
