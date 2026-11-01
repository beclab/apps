---
title: "Mindwtr 三合一 Olares OAC Chart"
summary: "在 Olares 上安装 Mindwtr 三合一（Cloud 同步服务 + MCP helper + PWA 网页端）的 OAC chart 说明：目录结构与 OlaresManifest 每个字段的官方规范出处、安装与 Market 提交步骤、安装后自检命令、数据卷位置与备份、上游版本同步与补丁冲突处理、chart 升级与回滚路径，以及哪些字段是按官方真实 chart 范例推断、尚未在真机实测。"
---

# Mindwtr 三合一 · Olares OAC Chart

这个 chart 把 Mindwtr 的三个组件装成**一个容器、一个端口**：

| 组件 | 说明 | 容器内监听 |
| --- | --- | --- |
| Mindwtr Cloud | 同步服务 + REST API（`/v1/*`） | 127.0.0.1:8787 |
| Mindwtr MCP helper | MCP 接口（`/mcp`） | 127.0.0.1:8723 |
| PWA 网页端 | 浏览器端应用（其余路径） | 容器内 nginx 0.0.0.0:8080 |

对外只有 8080 一个端口，路径分流由容器内的 nginx 完成。

## 目录结构

```
chart/
├── Chart.yaml               # Helm chart 元信息
├── OlaresManifest.yaml      # Olares 应用清单（规范版本 0.12.0 / apiVersion v3）
├── values.yaml              # 默认值（镜像、端口、副本、资源、探针、环境变量默认值）
├── README.md                # 本文件
└── templates/
    ├── _helpers.tpl         # 命名与标签
    ├── deployment.yaml      # 单 Deployment、单容器、探针指向 8080/healthz
    └── service.yaml         # Service，名字为 <release>-svc
```

镜像本体由 `mindwtr-merged/` 目录里的 Dockerfile 构建，构建与部署细节见上一级目录的 `README.md`。

## 安装前准备

1. 构建并推送三合一镜像（示例）：

   ```bash
   cd mindwtr-merged
   docker build -t ghcr.io/<你的账号>/mindwtr-merged:1.0.0 .
   docker push ghcr.io/<你的账号>/mindwtr-merged:1.0.0
   ```

2. 把 `values.yaml` 里的 `image.repository` 改成你推的仓库地址。

3. 生成两个 token（各自独立，不要复用）：

   ```bash
   openssl rand -hex 32   # → MINDWTR_CLOUD_AUTH_TOKENS
   openssl rand -hex 32   # → MINDWTR_MCP_HTTP_TOKEN
   ```

   - Cloud token 规则来自上游 `BEARER_TOKEN_PATTERN`：20-512 字符，字符集 `[A-Za-z0-9._~+/=-]`。
   - MCP token 规则来自上游 `MIN_HTTP_TOKEN_LENGTH`：至少 16 字符，建议 20+（不足 20 只告警不拒绝）。

## 安装（Olares）

**方式一：Studio 自定义安装（推荐先走这条，验证镜像没问题再上架）**

1. 先把 chart 目录打包成 tar：`tar czf mindwtr.tar.gz chart/`
2. 在 Olares 的 Studio 里选择「自定义安装 / 安装 chart」，上传该 tar 包。
3. 按安装界面提示填写：
   - `MINDWTR_CLOUD_AUTH_TOKENS`（必填）
   - `MINDWTR_MCP_HTTP_TOKEN`（必填）
   - `MINDWTR_CLOUD_CORS_ORIGIN`（建议填入口域名，例如 `https://mindwtr-svc.<你的域名>`）
   - `MINDWTR_MCP_WRITE`（默认 true，允许 AI 助手改任务）
4. 安装完成后用 `https://<入口域名>/healthz` 验证，返回 `ok` 即三个进程都活着。

**方式二：提交到 Olares 市场**

把 `chart/` 提交到 `github.com/beclab/apps` 的 PR（市场收录需要额外的 `owners` 文件，列出允许维护该应用的 GitHub 账号——这个文件本目录没有提供，需要你自己补）。

**方式三：Studio 应用方式（不走 chart）**

如果只想要一个能跑的应用，不想维护 chart，可以直接在 Studio 里拉镜像、映射端口 8080，并在应用的环境变量里填同样的几个 token。这条路不依赖本 chart。

## 安装后的自检

```bash
# 1) 容器与端口
kubectl get pods,svc -l app=mindwtr -o wide

# 2) MCP helper 存活（nginx 转发到 8723，免鉴权）
curl -fsS https://mindwtr-svc.<你的域名>/healthz        # → ok

# 3) Cloud 存活与就绪
curl -fsS https://mindwtr-svc.<你的域名>/health          # → {"ok":true}
curl -fsS https://mindwtr-svc.<你的域名>/ready           # → {"ok":true}（会检查数据卷可写）

# 4) MCP 握手（Bearer 用 MINDWTR_MCP_HTTP_TOKEN）
curl -i -X POST https://mindwtr-svc.<你的域名>/mcp \
  -H "Authorization: Bearer <MCP_TOKEN>" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"curl","version":"1"}}}'
```

## 数据卷

- 位置：`<应用数据目录>/cloud_data`，由 `.Values.userspace.appData` 决定。
- 容器内挂载点：`/app/cloud_data`（与官方 Cloud 镜像一致）。
- 升级镜像、重新安装 chart **都不会动这个目录**。删除应用时如果勾选「删除应用数据」才会清掉——升级路径上不要勾。
- 备份：把该目录整个打包即可（Cloud 的数据集是纯 JSON 文件）。

## 升级与上游版本同步

1. 上游 Mindwtr 发新版本时，用新 tag 重新构建镜像：

   ```bash
   cd mindwtr-merged
   docker build \
     --build-arg CLOUD_IMAGE=ghcr.io/dongdongbh/mindwtr-cloud:1.3.8 \
     --build-arg APP_IMAGE=ghcr.io/dongdongbh/mindwtr-app:1.3.8 \
     -t ghcr.io/<你的账号>/mindwtr-merged:1.0.1 .
   docker push ghcr.io/<你的账号>/mindwtr-merged:1.0.1
   ```

2. 改 `values.yaml` 的 `image.tag`，把 `Chart.yaml` 的 `version` 加一、`appVersion` 改成上游版本号。
3. 在 Olares 里更新应用（拉新镜像重启 Pod）。

> 补丁风险：`mindwtr-merged/patch-cloud.py` 会改上游的 `apps/cloud/src/server.ts`。
> 上游改了插入点附近的代码时，补丁会**故意失败**（构建直接报错），不会打出一个半坏的镜像。
> 这时打开镜像构建日志里的 `[patch-cloud] anchor line` 一行，对着新代码调整锚点即可。
> 补丁是幂等的，重复构建不会重复插入。

## 字段来源与「按范例推断」的部分

以下是对应关系，`✅` 表示官方文档原文，`🟡` 表示按官方真实 chart 范例推断：

| 字段 | 取值 | 依据 |
| --- | --- | --- |
| `olaresManifest.version` | `0.12.0` | ✅ https://www.olares.com/docs/developer/develop/package/manifest（页面标注「Latest Olares Manifest version: 0.12.0」） |
| `apiVersion` | `v3` | ✅ 同上（0.12.0 起 v2 格式不再支持） |
| `workloadReplicas` | `mindwtr: 1` | ✅ 同上（0.12.0 新增字段） |
| `entrances[].host` | `mindwtr-svc` | 🟡 按官方真实 chart `beclab/apps/jellyfin` 的写法（entrance.host 与 `{{ .Release.Name }}-svc` 同名）推断；**未在真机实测** |
| `entrances[].authLevel` | `public` | ✅ 官方取值 public/private/internal；具体选 public 是本次交付的设定，不是文档要求 |
| `entrances[].invisible` | `true` | ✅ 官方字段，含义「不在 Olares 桌面显示该入口」 |
| `entrances[].openMethod` | `default` | ✅ 官方取值 default/iframe/window |
| `options.envs[]` | token 等 | ✅ 官方规范（0.10.0 新增 Envs；注入到 `.Values.olaresEnv.<NAME>`） |
| `permission.appData` | `true` | ✅ 官方字段；用于允许写应用数据目录 |
| `.Values.userspace.appData` | 数据卷路径 | ✅ https://www.olares.com/docs/developer/develop/package/extension（Helm 扩展字段表） |
| `spec.supportArch` | amd64 / arm64 | ✅ 官方字段；上游 GHCR 同时提供 amd64 与 arm64 镜像 |
| `metadata.icon` | 官方默认图标 | 🟡 占位，官方文档要求 256x256 PNG/WEBP、≤512KB，提交前应换掉 |
| `metadata.categories` / `tags` | `Utilities` 等 | 🟡 按规范给的枚举值推断，没有验证你的市场分类是否需要别的值 |
| `owners` 文件 | **未提供** | ✅ 官方 chart 结构文档说明市场提交需要该文件（本目录未生成，需自行补） |

官方参考：

- OlaresManifest 规范：https://www.olares.com/docs/developer/develop/package/manifest
- OAC 目录结构：https://www.olares.com/docs/developer/develop/package/chart
- Helm 扩展字段：https://www.olares.com/docs/developer/develop/package/extension
- 真实 chart 范例：https://github.com/beclab/apps/tree/main/jellyfin

## 回滚

- **镜像回滚**：把 `values.yaml` 的 `image.tag` 改回旧 tag（保持 `chart/Chart.yaml` 的 version 单调递增），再在 Olares 更新应用。
- **数据回滚**：升级前把 `<应用数据目录>/cloud_data` 打包留一份；万一新版本数据结构不兼容，解包覆盖回去再起旧镜像。
- **chart 回滚**：Olares 市场里的应用更新是覆盖式的，回滚等于「用旧 chart 再装一次」，安装时不要勾「删除应用数据」。
