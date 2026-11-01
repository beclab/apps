#!/bin/sh
# Mindwtr 三合一启动脚本：拉起 Cloud、MCP helper、nginx 三个进程并监督它们。
#
# 进程拓扑：
#   bun   Cloud       127.0.0.1:8787
#   node  MCP helper  127.0.0.1:8723
#   nginx 统一入口     0.0.0.0:8080   ← 唯一对外端口
#
# 行为约定：
#   1. 先起 Cloud，等到 /ready 返回 200 再起 helper（helper 依赖 Cloud 的 /v1）。
#   2. 再等 helper 的 /healthz 返回 200，最后起 nginx。
#   3. 任何一个进程退出，容器整体退出（编排层负责重启），避免"外壳活着但功能已残"。
#   4. 收到 SIGTERM/SIGINT 时优雅停掉三个进程。
#
# 用法：ENTRYPOINT 直接执行本脚本；也可以在本机手动跑本脚本做冒烟测试。

set -eu

CLOUD_HOST="${MINDWTR_CLOUD_HOST:-127.0.0.1}"
CLOUD_PORT="${MINDWTR_CLOUD_PORT:-8787}"
MCP_HOST="${MINDWTR_MCP_HTTP_HOST:-127.0.0.1}"
MCP_PORT="${MINDWTR_MCP_HTTP_PORT:-8723}"
NGINX_PORT="${MINDWTR_NGINX_PORT:-8080}"
DATA_DIR="${MINDWTR_CLOUD_DATA_DIR:-/app/cloud_data}"
MCP_BIN="${MINDWTR_MCP_BIN:-/opt/mindwtr-mcp/node_modules/.bin/mindwtr-mcp}"
CLOUD_READY_TIMEOUT="${MINDWTR_CLOUD_READY_TIMEOUT:-120}"
MCP_READY_TIMEOUT="${MINDWTR_MCP_READY_TIMEOUT:-60}"

log() { echo "[mindwtr-merged] $*"; }

# --- 前置检查：密钥必须由环境变量注入 ----------------------------------------
: "${MINDWTR_CLOUD_AUTH_TOKENS:?MINDWTR_CLOUD_AUTH_TOKENS 未设置。Cloud 不允许匿名访问，请注入至少一个 20-512 字符的 token。}"
: "${MINDWTR_MCP_HTTP_TOKEN:?MINDWTR_MCP_HTTP_TOKEN 未设置。helper 需要至少 16 字符的 Bearer token。}"
: "${MINDWTR_MCP_CLOUD_TOKEN:?MINDWTR_MCP_CLOUD_TOKEN 未设置。helper 需要一个能访问 Cloud 的 token。}"

# helper 默认只读；置 MINDWTR_MCP_WRITE=true 打开写权限（官方默认 Cloud 模式是只读）。
if [ "${MINDWTR_MCP_WRITE:-true}" = "true" ]; then
    MCP_WRITE_FLAG="--write"
else
    MCP_WRITE_FLAG=""
fi

# --- 数据目录：保证存在，并在以 root 运行时把属主交给 bun --------------------
mkdir -p "$DATA_DIR"
if [ "$(id -u)" = "0" ] && id bun >/dev/null 2>&1; then
    chown bun:bun "$DATA_DIR" 2>/dev/null || log "警告：无法 chown $DATA_DIR（继续尝试启动）"
fi

# 以某个用户运行命令；root 时降权到 bun，行为与官方 Cloud 镜像一致。
as_cloud_user() {
    if [ "$(id -u)" = "0" ] && id bun >/dev/null 2>&1; then
        su-exec bun:bun env HOME=/home/bun "$@"
    else
        "$@"
    fi
}

# --- 生成 PWA 的运行时配置与 service worker ---------------------------------
# 官方 app 镜像把这两个脚本放在 /docker-entrypoint.d/，正常由 nginx 官方 entrypoint 执行；
# 我们替换掉了 entrypoint，所以在这里手动执行，行为保持一致。
for script in /docker-entrypoint.d/10-runtime-config.sh /docker-entrypoint.d/20-service-worker.sh; do
    if [ -x "$script" ]; then
        log "执行 $script"
        sh "$script"
    fi
done

# --- 启动 Cloud -------------------------------------------------------------
log "启动 Cloud：bun run --filter mindwtr-cloud start -- --host $CLOUD_HOST --port $CLOUD_PORT"
as_cloud_user bun run --filter mindwtr-cloud start -- --host "$CLOUD_HOST" --port "$CLOUD_PORT" &
CLOUD_PID=$!

# --- 等待 Cloud 就绪 --------------------------------------------------------
log "等待 Cloud /ready ..."
waited=0
while :; do
    if ! kill -0 "$CLOUD_PID" 2>/dev/null; then
        log "Cloud 进程已退出，启动失败。"
        exit 1
    fi
    if curl -fsS "http://$CLOUD_HOST:$CLOUD_PORT/ready" >/dev/null 2>&1; then
        log "Cloud 就绪。"
        break
    fi
    waited=$((waited + 1))
    if [ "$waited" -ge "$((CLOUD_READY_TIMEOUT * 2))" ]; then
        log "等待 Cloud /ready 超时（${CLOUD_READY_TIMEOUT}s）。"
        exit 1
    fi
    sleep 0.5
done

# --- 启动 MCP helper --------------------------------------------------------
# helper 的所有参数都可用环境变量给（apps/mcp-server/src/index.ts 的 resolveHttpConfig /
# resolveServerConfig 会读 MINDWTR_MCP_* ），只有 --write 是纯 CLI 开关。
log "启动 MCP helper：node $MCP_BIN（http://$MCP_HOST:$MCP_PORT/mcp）"
# shellcheck disable=SC2086
as_cloud_user node "$MCP_BIN" $MCP_WRITE_FLAG &
MCP_PID=$!

# --- 等待 helper 就绪 --------------------------------------------------------
log "等待 helper /healthz ..."
waited=0
while :; do
    if ! kill -0 "$MCP_PID" 2>/dev/null; then
        log "MCP helper 进程已退出，启动失败。"
        exit 1
    fi
    if curl -fsS "http://$MCP_HOST:$MCP_PORT/healthz" >/dev/null 2>&1; then
        log "helper 就绪。"
        break
    fi
    waited=$((waited + 1))
    if [ "$waited" -ge "$((MCP_READY_TIMEOUT * 2))" ]; then
        log "等待 helper /healthz 超时（${MCP_READY_TIMEOUT}s）。"
        exit 1
    fi
    sleep 0.5
done

# --- 启动 nginx（唯一对外端口）----------------------------------------------
log "启动 nginx：监听 0.0.0.0:$NGINX_PORT"
nginx -g 'daemon off;' &
NGINX_PID=$!

# --- 监督 -------------------------------------------------------------------
CHILD_PIDS="$CLOUD_PID $MCP_PID $NGINX_PID"

shutdown() {
    code="${1:-0}"
    log "收到停止信号，正在关闭子进程 ..."
    for pid in $CHILD_PIDS; do
        kill "$pid" 2>/dev/null || true
    done
    sleep 1
    for pid in $CHILD_PIDS; do
        kill -9 "$pid" 2>/dev/null || true
    done
    exit "$code"
}

trap 'shutdown 0' TERM INT

log "全部就绪，对外入口端口 $NGINX_PORT。"
while :; do
    for pid in $CHILD_PIDS; do
        if ! kill -0 "$pid" 2>/dev/null; then
            log "子进程 $pid 已退出，容器随之退出以便编排层重启。"
            shutdown 1
        fi
    done
    sleep 2
done
