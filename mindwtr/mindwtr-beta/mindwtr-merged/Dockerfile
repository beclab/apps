# syntax=docker/dockerfile:1.7
#
# Mindwtr 三合一镜像：Cloud（同步服务 + REST API）+ MCP helper + PWA 网页端。
#
# 拼装思路：
#   1. 官方 mindwtr-cloud 镜像里已经带 /app 全部源码、bun 运行时和已装好的 node_modules，
#      直接 COPY 过来，天然跟随上游版本（改 ARG 的 tag 即可）。
#   2. 官方 mindwtr-app 镜像里已经带 PWA 静态产物、nginx、两个 /docker-entrypoint.d 注入脚本，
#      以它作为最终基底，nginx 就能直接用上。
#   3. MCP helper 官方没有镜像，只有 npm 包 mindwtr-mcp，这里用 npm 装进 /opt/mindwtr-mcp。
#
# 容器内进程（start.sh 负责拉起与监督）：
#   bun   → Cloud      127.0.0.1:8787   （只监听回环，不对外）
#   node  → MCP helper 127.0.0.1:8723   （只监听回环，不对外）
#   nginx → 统一入口    0.0.0.0:8080     （唯一对外端口）
#
# 路由分配（见 nginx.conf）：
#   /mcp    → helper 8723   （MCP Streamable HTTP，POST only）
#   /healthz→ helper 8723   （helper 存活探测，免鉴权）
#   /health /ready → Cloud 8787
#   /v1/*   → Cloud 8787    （同步 REST API）
#   其余    → PWA 静态（SPA 回落 index.html）
#
# 另有一层「可选补丁」：patch-cloud.py 会给 Cloud 的 server.ts 插入一条 /mcp 转发分支，
# 这样即使绕过 nginx 直连 Cloud 的 8787 也能用 MCP。该补丁是幂等的，构建日志会打印结果，
# 补丁失败即构建失败（RUN 步骤非零退出）。

ARG CLOUD_IMAGE=ghcr.io/dongdongbh/mindwtr-cloud:latest
ARG APP_IMAGE=ghcr.io/dongdongbh/mindwtr-app:latest
ARG MCP_VERSION=1.1.13

# 上游 Cloud 镜像：提供 /app 源码、bun 运行时、bun 用户家目录
FROM ${CLOUD_IMAGE} AS cloud
# 上游 App 镜像：提供 nginx + PWA 静态产物 + 注入脚本，作为最终基底
FROM ${APP_IMAGE} AS app

FROM app AS merged

# nodejs/npm：跑 MCP helper（官方要求 Node >= 20，Alpine 仓库里的 nodejs 为 22.x）
# su-exec：root 启动后降权到 bun 用户跑 Cloud（官方 Cloud 镜像也是 bun:bun 运行）
# curl   ：start.sh 等待 Cloud /ready，以及 Docker HEALTHCHECK
# python3：构建期跑 patch-cloud.py
RUN apk add --no-cache nodejs npm su-exec curl python3

# --- Cloud 运行时与源码 -------------------------------------------------------
COPY --from=cloud /usr/local/bin/bun /usr/local/bin/bun
COPY --from=cloud /home/bun /home/bun
COPY --from=cloud /app /app

# --- 给 Cloud 打 /mcp 转发补丁（幂等；失败即构建失败）-------------------------
COPY patch-cloud.py /usr/local/share/mindwtr-merged/patch-cloud.py
RUN python3 /usr/local/share/mindwtr-merged/patch-cloud.py /app/apps/cloud/src/server.ts \
 && echo "BUILD: Cloud /mcp passthrough patch applied."

# --- MCP helper（官方无镜像，用 npm 包）---------------------------------------
RUN mkdir -p /opt/mindwtr-mcp \
 && cd /opt/mindwtr-mcp \
 && npm init -y >/dev/null 2>&1 \
 && npm install --omit=optional --no-audit --no-fund "mindwtr-mcp@${MCP_VERSION}" \
 && npm cache clean --force \
 && test -x /opt/mindwtr-mcp/node_modules/.bin/mindwtr-mcp

# --- 统一入口与启动脚本 -------------------------------------------------------
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY start.sh /usr/local/bin/mindwtr-merged-start
RUN chmod +x /usr/local/bin/mindwtr-merged-start \
 && mkdir -p /app/cloud_data

# 默认值全部可以被运行时环境变量覆盖（密钥只走环境变量，不进镜像层）
ENV MINDWTR_CLOUD_DATA_DIR=/app/cloud_data \
    MINDWTR_CLOUD_HOST=127.0.0.1 \
    MINDWTR_CLOUD_PORT=8787 \
    MINDWTR_MCP_UPSTREAM=http://127.0.0.1:8723 \
    MINDWTR_MCP_HTTP=true \
    MINDWTR_MCP_HTTP_HOST=127.0.0.1 \
    MINDWTR_MCP_HTTP_PORT=8723 \
    MINDWTR_MCP_CLOUD_URL=http://127.0.0.1:8787 \
    MINDWTR_MCP_CLOUD_ALLOW_INSECURE_HTTP=true \
    MINDWTR_MCP_WRITE=true \
    MINDWTR_NGINX_PORT=8080 \
    NODE_ENV=production

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${MINDWTR_NGINX_PORT}/healthz" >/dev/null || exit 1

ENTRYPOINT ["/usr/local/bin/mindwtr-merged-start"]
