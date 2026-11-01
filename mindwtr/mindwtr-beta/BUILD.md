# 构建并推送 mindwtr-merged 镜像

## 前置条件

- Docker Desktop（支持 buildx 多架构构建）
- 已登录 GHCR：`docker login ghcr.io -u inverstar`（密码用 GitHub PAT，需要 `write:packages` 权限）

## 一键构建推送（推荐）

```bash
cd mindwtr-beta/mindwtr-merged

docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --build-arg CLOUD_IMAGE=ghcr.io/dongdongbh/mindwtr-cloud:1.3.7 \
  --build-arg APP_IMAGE=ghcr.io/dongdongbh/mindwtr-app:1.3.7 \
  --build-arg MCP_VERSION=1.1.13 \
  -t ghcr.io/inverstar/mindwtr-merged:1.3.7 \
  -t ghcr.io/inverstar/mindwtr-merged:latest \
  --push \
  .
```

## 构建成功的标志

日志中必须出现以下两行，否则说明 patch 失败：

```
BUILD: Cloud /mcp passthrough patch applied.
[patch-cloud] PATCH OK: 已在 .../server.ts 插入 /mcp 与 /healthz 转发分支。
```

## 本地冒烟测试（推送前可选）

```bash
# 先只构建 amd64 本地测试，不推送
docker buildx build \
  --platform linux/amd64 \
  --load \
  --build-arg CLOUD_IMAGE=ghcr.io/dongdongbh/mindwtr-cloud:1.3.7 \
  --build-arg APP_IMAGE=ghcr.io/dongdongbh/mindwtr-app:1.3.7 \
  --build-arg MCP_VERSION=1.1.13 \
  -t mindwtr-merged:test \
  .

# 生成两个测试 token
CLOUD_TOKEN=$(openssl rand -hex 32)
MCP_TOKEN=$(openssl rand -hex 32)

docker run -d --name mindwtr-test -p 8080:8080 \
  -e MINDWTR_CLOUD_AUTH_TOKENS="$CLOUD_TOKEN" \
  -e MINDWTR_MCP_HTTP_TOKEN="$MCP_TOKEN" \
  -e MINDWTR_MCP_CLOUD_TOKEN="$CLOUD_TOKEN" \
  mindwtr-merged:test

# 等约 15s 后验证
sleep 15
curl -s http://localhost:8080/health   # 应返回 ok 或 {"status":"ok"}
curl -s http://localhost:8080/healthz  # 应返回 ok
curl -s http://localhost:8080/ready    # 应返回 ok

# 清理
docker rm -f mindwtr-test
```

## 镜像内容说明

| 来源 | 内容 | 进程 | 端口（容器内） |
|------|------|------|----------------|
| `mindwtr-app:1.3.7` | nginx + PWA 静态文件 | nginx | 0.0.0.0:**8080**（唯一对外） |
| `mindwtr-cloud:1.3.7` | bun 运行时 + Cloud 源码 | bun | 127.0.0.1:8787 |
| `mindwtr-mcp@1.1.13`（npm） | MCP helper | node | 127.0.0.1:8723 |
| `patch-cloud.py` | 构建期给 server.ts 注入 /mcp 转发 | — | — |

与官方镜像的区别：
- 官方提供 `mindwtr-app` 和 `mindwtr-cloud` 两个独立镜像，没有提供合并版
- `mindwtr-merged` 是我们把这两个镜像 + npm MCP helper 拼装在一起的结果
- 额外在 Cloud 的 server.ts 中注入了 /mcp 路由转发（`patch-cloud.py`）
- 用 `start.sh` 管理三个进程的有序启动和监督

