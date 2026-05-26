#!/bin/sh
# nemoclaw-brew-wrapper:v2
# Redirect steipete/tap/gogcli -> openclaw/tap/gogcli for openclaw config --section skills.
# Strips extra quotes OpenClaw sometimes passes (avoids ""openclaw/tap/gogcli"").
set -u
export HOMEBREW_PREFIX=/sandbox/.linuxbrew
export HOMEBREW_REPOSITORY=/sandbox/.linuxbrew/Homebrew
export HOMEBREW_CELLAR=/sandbox/.linuxbrew/Cellar
export HOMEBREW_NO_AUTO_UPDATE=1
export HOMEBREW_NO_ENV_HINTS=1
export HOMEBREW_NO_ANALYTICS=1
export HOMEBREW_NO_ENV_FILTERING=1
: "${HOMEBREW_TEMP:=/tmp/homebrew-tmp}"; export HOMEBREW_TEMP
: "${HOMEBREW_CACHE:=/tmp/homebrew-cache}"; export HOMEBREW_CACHE
: "${HOMEBREW_LOGS:=/tmp/homebrew-logs}"; export HOMEBREW_LOGS
: "${TMPDIR:=/tmp/homebrew-tmp}"; export TMPDIR
mkdir -p "$HOMEBREW_TEMP" "$HOMEBREW_CACHE" "$HOMEBREW_LOGS" 2>/dev/null || true

REAL=/sandbox/.linuxbrew/Homebrew/bin/brew

_nemoclaw_strip_quotes() {
  _v="$1"
  while [ "${#_v}" -ge 2 ] && [ "${_v#\"}" != "$_v" ] && [ "${_v%\"}" != "$_v" ]; do
    _v="${_v#\"}"
    _v="${_v%\"}"
  done
  printf '%s' "$_v"
}

_nemoclaw_map_gog_formula() {
  case "$1" in
    steipete/tap/gogcli|steipete/tap/gog|gogcli|openclaw/tap/gogcli) echo openclaw/tap/gogcli ;;
    *) echo "$1" ;;
  esac
}

_nemoclaw_map_tap() {
  case "$1" in
    steipete/tap|steipete/tap/gogcli|openclaw/tap|openclaw/tap/gogcli) echo openclaw/tap ;;
    *) echo "$1" ;;
  esac
}

if [ "$1" = "install" ]; then
  shift
  _tf="${TMPDIR:-/tmp}/nemoclaw-brew-wrap.$$"
  : > "$_tf"
  _need_tap=0
  for _a in "$@"; do
    _clean=$(_nemoclaw_strip_quotes "$_a")
    _mapped=$(_nemoclaw_map_gog_formula "$_clean")
    case "$_mapped" in
      openclaw/tap/gogcli) _need_tap=1 ;;
    esac
    printf '%s\n' "$_mapped" >> "$_tf"
  done
  set --
  while IFS= read -r _line || [ -n "$_line" ]; do
    [ -z "$_line" ] && continue
    set -- "$@" "$_line"
  done < "$_tf"
  rm -f "$_tf"
  if [ "$_need_tap" = "1" ]; then
    "$REAL" tap openclaw/tap 2>/dev/null || true
  fi
  exec "$REAL" install "$@"
fi

if [ "$1" = "tap" ]; then
  shift
  _tf="${TMPDIR:-/tmp}/nemoclaw-brew-wrap.$$"
  : > "$_tf"
  for _a in "$@"; do
    _clean=$(_nemoclaw_strip_quotes "$_a")
    _mapped=$(_nemoclaw_map_tap "$_clean")
    printf '%s\n' "$_mapped" >> "$_tf"
  done
  set --
  while IFS= read -r _line || [ -n "$_line" ]; do
    [ -z "$_line" ] && continue
    set -- "$@" "$_line"
  done < "$_tf"
  rm -f "$_tf"
  exec "$REAL" tap "$@"
fi

exec "$REAL" "$@"
