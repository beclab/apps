---
title: "Mindwtr 三合一部署件：Cloud + MCP helper + PWA"
summary: "把 Mindwtr 的自托管同步服务、MCP helper 与网页端合并成一个镜像、一个对外端口的完整部署件：Dockerfile 拼装、nginx 路径分流、启动监督脚本、Cloud 的 /mcp 补丁脚本、参考 compose、Olares OAC chart，以及环境变量清单、构建与本地验证步骤、升级回滚与故障排查、现成方案调研结论，并逐条标注哪些环节尚未实测、哪些字段是按官方范例推断而非文档明文。"
---

# Mindwtr 三合一部署件

把 Mindwtr 的三个组件塞进**一个镜像、一个容器、一个对外端口**：

| 组件 | 作用 | 容器内监听 | 对外路径 |
| --- | --- | --- | --- |
| Mindwtr Cloud | 同步服务 + REST API | 127.0.0.1:8787 | `/v1/*`、`/health`、`/ready` |
| Mindwtr MCP helper | MCP 接口，让 AI 助手读写任务 | 127.0.0.1:8723 | `/mcp`、`/healthz` |
| PWA 网页端 | 浏览器里直接用 | nginx 0.0.0.0:8080 | 其余路径 |

两个后端进程只监听回环地址，公网上只有 nginx 的 8080。

## 目录内容

```
mindwtr-merged/
├── Dockerfile          # 单镜像：官方 cloud 镜像 + 官方 app 镜像 + npm 装 helper + 打补丁
├── nginx.conf          # 统一入口：/mcp、/healthz → 8723；/v1/ → 8787；其余 → PWA
├── start.sh            # 拉起三个进程、等就绪、任一进程退出则容器退出
├── patch-cloud.py      # 给上游 server.ts 插入 /mcp 转发分支（幂等）
└── compose.yaml        # 本地 / 自建服务器的参考编排
chart/                  # Olares OAC（Helm）chart，见 chart/README.md
README.md               # 本文件
```

## 前置条件

- Docker（含 buildx）与一个能拉 `ghcr.io` 的网络环境。
- 目标机：Olares（chart 方式）或任意一台能跑 Docker 的机器（compose 方式）。
- 生成两个 token（见下）。
- 上游仓库地址：`https://github.com/dongdongbh/Mindwtr`。

> 本方案**不需要**克隆上游仓库：`Dockerfile` 直接从两个官方镜像里 COPY 源码与静态产物。
> 只有要改 Cloud 源码细节时才需要 clone。

## 环境变量清单

全部通过环境变量注入，**不进镜像层**。

### Cloud 侧（上游 apps/cloud/src/server-config.ts / server-auth.ts）

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `MINDWTR_CLOUD_AUTH_TOKENS` | 是 | 允许的 Bearer token，逗号分隔。每个 token 20-512 字符，字符集 `[A-Za-z0-9._~+/=-]`。**不同 token 对应互相隔离的数据集**，共享实例时一人一个 token。 |
| `MINDWTR_CLOUD_CORS_ORIGIN` | 建议 | 浏览器打开 PWA 的完整地址（含 scheme 与端口），**只能设一个**。生产环境（`NODE_ENV=production`）不设会直接启动失败。 |
| `MINDWTR_CLOUD_TRUST_PROXY_HEADERS` | 否 | `true` 让 Cloud 采信 `X-Forwarded-For`。nginx 在前面时建议开。 |
| `MINDWTR_CLOUD_TRUSTED_PROXY_IPS` | 配合上一项 | 允许提供转发头的来源 IP，逗号分隔。容器内就是 `127.0.0.1`。 |
| `MINDWTR_CLOUD_DATA_DIR` | 否 | 数据目录，默认 `/app/cloud_data`（官方镜像就是这个路径）。 |

### MCP helper 侧（上游 apps/mcp-server/src/index.ts）

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `MINDWTR_MCP_HTTP` | 是 | `true` 启用 HTTP 传输（默认是 stdio）。 |
| `MINDWTR_MCP_HTTP_HOST` | 否 | 监听地址，默认 `127.0.0.1`。**保持 127.0.0.1**，别对外暴露。 |
| `MINDWTR_MCP_HTTP_PORT` | 否 | 监听端口，默认 `8722`（官方默认值）。本方案用 `8723`，与上游默认值不同以免与别的服务撞。 |
| `MINDWTR_MCP_HTTP_TOKEN` | 是 | MCP 客户端访问 `/mcp` 用的 Bearer token，**至少 16 字符**（16-19 字符只告警不拒绝，建议 20+）。 |
| `MINDWTR_MCP_CLOUD_URL` | 是 | helper 要访问的 Cloud 根地址（不带 `/v1`）。容器内是 `http://127.0.0.1:8787`。 |
| `MINDWTR_MCP_CLOUD_TOKEN` | 是 | helper 访问 Cloud 用的 token，必须是上面 `MINDWTR_CLOUD_AUTH_TOKENS` 里的某一个，否则 helper 看不到你的数据。 |
| `MINDWTR_MCP_CLOUD_ALLOW_INSECURE_HTTP` | 容器内必须 | 允许 helper 用 http:// 访问 Cloud。容器内走回环，所以设 `true`。 |
| `MINDWTR_MCP_WRITE` | 否 | 是否允许写入。官方默认 Cloud 模式**只读**，要 AI 助手改任务必须显式开。 |

### PWA 侧（上游 docker/app/*.sh）

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `MINDWTR_DEFAULT_CLOUD_URL` | 否 | 新浏览器首次打开时预填的 Cloud 地址。留空则同源自动探测。 |
| `MINDWTR_PWA_ENABLED` | 否 | `false` 时用只上线不拦截的 service worker（`sw-online.js`）。 |

### 生成 token

```bash
openssl rand -hex 32   # Cloud token 与 MCP token 各生成一个，不要复用
```

两套凭证是独立的：Cloud token 给手机/桌面 App 同步用，MCP token 给 MCP 客户端用。

## 构建

```bash
cd mindwtr-merged

# 默认拉上游 latest
docker build -t mindwtr-merged:1.0.0 .

# 或者指定上游版本（推荐，便于回滚）
docker build \
  --build-arg CLOUD_IMAGE=ghcr.io/dongdongbh/mindwtr-cloud:1.3.7 \
  --build-arg APP_IMAGE=ghcr.io/dongdongbh/mindwtr-app:1.3.7 \
  --build-arg MCP_VERSION=1.1.13 \
  -t mindwtr-merged:1.0.0 .
```

构建日志里会出现这三行，用来确认拼装与补丁都成功：

```
BUILD: Cloud /mcp passthrough patch applied.
[patch-cloud] target      : /app/apps/cloud/src/server.ts
[patch-cloud] anchor line : if (
```

**补丁失败即构建失败**（脚本以非零退出），不会出现「镜像构建出来了但 /mcp 是坏的」。

构建上下文必须是 `mindwtr-merged/` 目录本身（Dockerfile 要 COPY `patch-cloud.py`、`nginx.conf`、`start.sh`）。

## 本地验证

```bash
# 1) 起容器
docker run -d --name mindwtr -p 8080:8080 \
  -e MINDWTR_CLOUD_AUTH_TOKENS=your-cloud-token-here \
  -e MINDWTR_CLOUD_CORS_ORIGIN=http://localhost:8080 \
  -e MINDWTR_MCP_HTTP_TOKEN=your-mcp-token-here \
  -e MINDWTR_MCP_CLOUD_TOKEN=your-cloud-token-here \
  -v "$PWD/data:/app/cloud_data" \
  mindwtr-merged:1.0.0

# 2) helper 存活（免鉴权）
curl -fsS http://127.0.0.1:8080/healthz          # → ok

# 3) Cloud 存活与就绪
curl -fsS http://127.0.0.1:8080/health            # → {"ok":true}
curl -fsS http://127.0.0.1:8080/ready             # → {"ok":true}

# 4) MCP 握手（Bearer 用 MCP token，不是 Cloud token）
curl -i -X POST http://127.0.0.1:8080/mcp \
  -H "Authorization: Bearer your-mcp-token-here" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"curl","version":"1"}}}'

# 5) PWA 首页
curl -fsS http://127.0.0.1:8080/ | head -c 200
```

MCP 客户端配置（以支持 URL + Bearer 的客户端为例）：

```json
{
  "mcpServers": {
    "mindwtr": {
      "type": "http",
      "url": "https://now.inverstar.olares.cn/mcp",
      "headers": { "Authorization": "Bearer <你的 MCP token>" }
    }
  }
}
```

## 部署到 Olares

你现在的部署形态是 **Olares 商店 chart**。两条路：

**A. 用本目录的 chart（推荐）**

1. 先把镜像推到自己的镜像仓库（GHCR / Docker Hub）。
2. 改 `chart/values.yaml` 的 `image.repository` 与 `image.tag`。
3. 打 tar 包：`tar czf mindwtr.tar.gz chart/`
4. 在 Olares Studio 里「自定义安装 / 安装 chart」，上传 tar 包，按提示填两个 token。

细节、字段来源与未实测项见 [`chart/README.md`](chart/README.md)。

**B. 直接用 Studio 应用方式（不走 chart）**

在 Studio 里新建应用，镜像填你推的三合一镜像，端口映射填 **8080**，环境变量按上面的清单填。这样也能跑，只是不享受 chart 的版本管理与自动升级。

> 两种方式**都只有 8080 一个端口**。域名仍由 Olares 网关签发，不需要自建 Caddy/Nginx。

## 数据卷

- 容器内路径固定 `/app/cloud_data`（与官方 Cloud 镜像一致）。
- compose 用 `./data:/app/cloud_data`；chart 用 `.Values.userspace.appData` 下的 `cloud_data` 子目录（hostPath，`DirectoryOrCreate`）。
- Cloud 的数据集是纯 JSON 文件，备份就是把整个目录打包。
- 升级镜像、重新安装 chart **都不会清空它**；只有删除应用时勾选「删除应用数据」才会清掉——升级路径上不要勾。
- 目录属主：容器以 root 启动，`start.sh` 会把数据目录 chown 给 `bun` 用户（官方 Cloud 镜像也是 `bun:bun` 运行）。如果你的平台强制非 root 运行，chown 会失败并打警告，需要自己把目录属主改成容器内 Cloud 进程的 uid。

## 上游版本更新如何同步

上游 Mindwtr 的发版与镜像策略（依据见文末来源）：

- 上游用 GitHub Releases 发版，最近一版是 **v1.3.7（2026-10-22 发布）**，有 `v1.3.1-rc.1 / rc.2` 这类预发布。
- 官方镜像在 GHCR：`mindwtr-cloud` 与 `mindwtr-app`，tag 有 `latest`、版本号、`beta` 三种，amd64 与 arm64 都有。
- MCP helper 的 npm 版本线是独立的（当前 `mindwtr-mcp@1.1.13`），**不跟 app 版本号一起走**，需要单独盯。

同步步骤：

1. 改 Dockerfile 的 build-arg，把 `CLOUD_IMAGE` / `APP_IMAGE` 指到新的上游版本 tag。
2. 重新构建、推送三合一镜像，版本号 +1。
3. chart 侧：`values.yaml` 改 `image.tag`，`Chart.yaml` 的 `version` +1、`appVersion` 改成上游版本号。
4. 助手侧：MCP helper 版本如果也更新了，改 `--build-arg MCP_VERSION=...`（建议每次重建都显式写死，别用 `latest`，否则 npm 侧发新版会悄悄换掉 helper）。

上游改了 Cloud 的路由结构时，补丁会**故意失败**而不是打坏镜像：打开构建日志里的 `[patch-cloud] anchor line` 一行，对照新代码调整 `patch-cloud.py` 的锚点即可，补丁是幂等的。

## 回滚

- **镜像回滚**：`image.tag` 改回旧 tag 重建并重启。
- **数据回滚**：升级前把数据目录打包留底，新版本数据结构不兼容就解包覆盖回去再起旧镜像。
- **chart 回滚**：Olares 的应用更新是覆盖式的，回滚等于用旧 chart 再装一次，安装时不勾「删除应用数据」。

## 常见故障

| 现象 | 原因与处理 |
| --- | --- |
| `/mcp` 返回 404 | helper 的路径是精确匹配（`/mcp`、`/healthz`），`/mcp/` 之类的尾斜杠会 404。nginx 里必须用 `location = /mcp`。 |
| `/mcp` 返回 403 `forbidden_origin` | 请求带了 `Origin` 头且其 hostname 不等于 helper 绑定地址。nginx 已用 `proxy_set_header Origin "";` 摘掉；如果绕过 nginx 直连 Cloud 的 8787，靠 `patch-cloud.py` 插入的分支摘掉 origin。 |
| `/mcp` 返回 401 | 用了 Cloud token 而不是 MCP token。两套凭证独立。 |
| Cloud 启动就退出，日志说 auth is not configured | 没给 `MINDWTR_CLOUD_AUTH_TOKENS`（或 `MINDWTR_CLOUD_ALLOW_ANY_TOKEN`）。别用后者，它等于放开任意 token。 |
| Cloud 报 token 格式不对 | 规则是 20-512 字符、字符集 `[A-Za-z0-9._~+/=-]`。`openssl rand -hex 32` 出来的 64 位 hex 符合。 |
| helper 启动失败：token 至少 16 字符 | `MINDWTR_MCP_HTTP_TOKEN` 太短。 |
| helper 启动失败：HTTP mode requires --http-token | `MINDWTR_MCP_HTTP_TOKEN` 没传进容器。 |
| helper 报 Cloud 拒绝 | `MINDWTR_MCP_CLOUD_TOKEN` 不在 `MINDWTR_CLOUD_AUTH_TOKENS` 列表里，或漏了 `MINDWTR_MCP_CLOUD_ALLOW_INSECURE_HTTP=true`（容器内走 http 回环）。 |
| `/ready` 返回 503 | 数据目录不可写或被换成了软链接。Cloud 的 `/ready` 会做一次真实写 + fsync。看 `start.sh` 里 chown 的警告。 |
| PWA 打不开 / 一直跳同步设置 | `MINDWTR_CLOUD_CORS_ORIGIN` 没填或填的不是实际访问地址；生产模式下不填直接启动失败。 |
| PWA 资源 404 | `/assets/` 下缺 chunk 必须 404（上游刻意为之），不要改成回落 index.html。 |
| MCP 请求体超过 1MB 被拒 | helper 的 `MAX_HTTP_BODY_BYTES` 是 1 MiB，nginx 的 `/mcp` 段也按 1m 限制。要传大附件得改 helper。 |
| 容器反复重启 | `start.sh` 的设计是任一进程退出即整体退出。去看 Cloud 的日志（`docker logs`）。 |

## 另一条更轻的路：直接改官方 Market chart

本目录是「自建合并镜像」路线，完整自控，但需要你自己构建和推送镜像。

官方在 Olares 市场里已经有一个 Mindwtr chart（`github.com/beclab/apps/tree/main/mindwtr`），
它本身就已经把 **PWA（nginx 容器，5173）和 Cloud（8787）放在同一个 Deployment 的两个容器里**，
并且 nginx 已经做了 `/v1`、`/health`、`/ready` 的分流。

所以如果继续用官方 chart，加 MCP 的最小改动是：**再加第三个容器**跑 `mindwtr-mcp@1.1.13`，
并在 chart 的 nginx `default.conf` 里加一条 `location = /mcp { proxy_pass http://127.0.0.1:8723; }`
（要 `proxy_http_version 1.1`、`proxy_buffering off`、`proxy_set_header Origin "";` 支持 SSE 并绕开
helper 的 Origin 校验），Service 不需要新增端口，helper 只监听回环。

这条路的代价明显更小：不用自己构建镜像，上游更新跟着官方 chart 走。
代价是 chart 的改动要提到 `beclab/apps` 的 PR（官方 chart 的 owners 里包含你的账号，路径可行），
并且要走 Market 端的主动升级，而不是自己控制 tag。

选哪条：
- 想完全自控、以后不想再动 chart → 用本目录的合并镜像路线。
- 想少动手、上游更新自动跟随 → 走官方 chart 加容器的路线。

## 别人做过吗（避免重复造轮子）

截至 2026-10-27 的检索结论：

- **没有找到现成的「Mindwtr Cloud + MCP」合并镜像、Helm chart 或一键部署项目**。GitHub 仓库检索 `mindwtr` 与 `mindwtr docker OR olares OR chart` 的结果里，命中的都是上游仓库本身或第三方代码复刻（porom004/Mindwtr、seclution/Mindwtr 这类），没有打包好的镜像或部署方案。中文介绍页（kaiyuanbang.cn）也只讲桌面/移动端与各种同步方案，没提 MCP。
- **Olares 市场里没有现成的 Mindwtr chart**：抓取 `beclab/apps` 仓库根目录列表（2026-10-27）未见 Mindwtr 相关目录。
- **官方镜像只有两个**（`mindwtr-app`、`mindwtr-cloud`），官方 Docker 部署页描述的就是这两个服务的编排，没有 MCP 的部署拓扑。GHCR 包页面里也只有 `mindwtr-cloud` 一个容器包。
- **官方 MCP helper 只有 npm 包**，默认 stdio 传输，HTTP 传输是给自托管者的 opt-in 选项；官方文档没有推荐过 Nginx/反代/多容器承载 MCP 的拓扑。
- **上游 Cloud 本身目前没有 `/mcp` 路由**：我逐字核对了 `apps/cloud/src/server.ts`，全文没有 `mcp` 字样；GitHub issue 检索（`mcp in:title`、`mcp cloud`）也没看到上游把 MCP 挂进 Cloud 的条目。

结论：这个三合一目前没有现成方案可抄，本目录就是那个方案。

## 依据的官方来源

- 上游仓库：https://github.com/dongdongbh/Mindwtr
- Cloud 服务端源码（逐字核对）：https://raw.githubusercontent.com/dongdongbh/Mindwtr/main/apps/cloud/src/server.ts
- helper HTTP 传输实现（逐字核对）：https://raw.githubusercontent.com/dongdongbh/Mindwtr/main/apps/mcp-server/src/http-server.ts
- helper 入口与参数解析：https://raw.githubusercontent.com/dongdongbh/Mindwtr/main/apps/mcp-server/src/index.ts
- 官方 Cloud 镜像 Dockerfile：https://raw.githubusercontent.com/dongdongbh/Mindwtr/main/docker/cloud/Dockerfile
- 官方 PWA 镜像 Dockerfile 与 nginx 配置：https://raw.githubusercontent.com/dongdongbh/Mindwtr/main/docker/app/Dockerfile 、https://raw.githubusercontent.com/dongdongbh/Mindwtr/main/docker/app/nginx.conf
- 官方 compose：https://raw.githubusercontent.com/dongdongbh/Mindwtr/main/docker/compose.yaml
- 官方 Docker 部署文档：https://docs.mindwtr.app/power-users/docker-deployment
- 官方 MCP 文档：https://docs.mindwtr.app/power-users/mcp
- GHCR 包页面：https://github.com/dongdongbh/Mindwtr/pkgs/container/mindwtr-cloud
- npm 元数据：https://registry.npmjs.org/mindwtr-mcp
- OlaresManifest 规范：https://www.olares.com/docs/developer/develop/package/manifest
- OAC 目录结构：https://www.olares.com/docs/developer/develop/package/chart
- Olares Helm 扩展字段：https://www.olares.com/docs/developer/develop/package/extension
- 真实 chart 范例：https://github.com/beclab/apps/tree/main/jellyfin

## 尚未实测的部分（如实标注）

| 项 | 状态 |
| --- | --- |
| `patch-cloud.py` 在真实 `server.ts` 上插入 | ✅ 已实测。拉取 main 分支真实文件干跑，插入点定位在 `/ready` 之后、第一条 `withNamespace(...)` 包裹的 `/v1` 路由之前，缩进 16 空格；二次执行输出「ALREADY PATCHED」，幂等性成立。复现命令见下。 |
| 镜像构建 | ❌ 未实测。产出环境没有 docker 与 bun，无法执行 `docker build`；Dockerfile 里的 `COPY --from` 路径、`apk add` 包名、npm 安装步骤均按上游 Dockerfile 与 Alpine 包名推断，需你本机执行一次确认。 |
| 容器内三进程启动与探针 | ❌ 未实测（需要 docker）。 |
| `nginx.conf` 语法 | ❌ 未用 `nginx -t` 验证（产出环境无 nginx 二进制）。配置是以上游 `docker/app/nginx.conf` 为底稿改写，逐条 location 保留了上游的 CSP 与安全头。 |
| chart 渲染 | ❌ 未用 `helm template` 验证（产出环境无 helm）。`values.olaresEnv` 的取值写法参照官方 `beclab/apps/jellyfin` chart 的同名写法。 |
| Olares 上安装与入口域名 | ❌ 未实测。`entrances[].host: mindwtr-svc` 是按官方真实 chart 范例推断的：官方 chart 的 Service 名为 `{{ .Release.Name }}-svc`，entrance 的 host 与之同名。 |

复现补丁干跑：

```bash
mkdir -p /tmp/dryrun/apps/cloud
curl -fLo /tmp/dryrun/apps/cloud/src/server.ts \
  https://raw.githubusercontent.com/dongdongbh/Mindwtr/main/apps/cloud/src/server.ts
# 上面这个地址在你本机可能不通（本次产出环境被网关拦了 raw.githubusercontent.com），
# 备用镜像：
#   https://fastly.jsdelivr.net/gh/dongdongbh/Mindwtr@main/apps/cloud/src/server.ts

python3 mindwtr-merged/patch-cloud.py /tmp/dryrun/apps/cloud/src/server.ts
# 打印插入前后的真实带行号片段；再执行一次应输出 ALREADY PATCHED
```
