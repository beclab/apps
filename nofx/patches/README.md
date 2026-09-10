# NOFX strategy market fix

The chart uses the public mirror
`beclab/harveyff-nofx-frontend:20260617-olares-20260910-multi2`.
Build commands below produce the source images in `harveyff/nofx-frontend`.

`strategy-market-external.patch` replaces the embedded VergeX strategy market
with an explicit new-tab link. It includes English, Chinese and Indonesian
copy and preserves the existing authenticated route. It also uses IPv4
loopback for the Docker health check, matching Nginx's listener.

The original `goai007/nofx-frontend:20260617` image's BuildKit provenance records:

- Source: https://github.com/leolianger/nofx
- Revision: `5a83b021a76e006165a91a8eccb1efdb832f9b51`
- Node base: `node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293`
- Nginx base: `nginx:alpine@sha256:8b1e78743a03dbb2c95171cc58639fef29abc8816598e27fb910ed2e621e589a`

Check out that revision, apply the patch with `git apply`, and build from the
source repository root. The following reproduces the amd64 test build:

```sh
docker buildx build --platform linux/amd64 --load \
  -f docker/Dockerfile.frontend \
  --build-arg NODE_VERSION=20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293 \
  --build-arg NGINX_VERSION=alpine@sha256:8b1e78743a03dbb2c95171cc58639fef29abc8816598e27fb910ed2e621e589a \
  -t harveyff/nofx-frontend:20260617-olares-20260910-r2-amd64 .
```

To build ARM64, use the same command with `--platform linux/arm64` and tag
`harveyff/nofx-frontend:20260617-olares-20260910-r2-arm64`. After inspecting and
smoke-testing each architecture, push both tags and combine them:

```sh
docker buildx imagetools create \
  -t harveyff/nofx-frontend:20260617-olares-20260910-multi2 \
  harveyff/nofx-frontend:20260617-olares-20260910-r2-amd64 \
  harveyff/nofx-frontend:20260617-olares-20260910-r2-arm64
```

Use a fresh image tag for subsequent builds. Verify both architectures appear
in the public manifest before declaring support for both architectures.

Changing `entrances[].openMethod` cannot fix an iframe created inside NOFX.
The external site sends `X-Frame-Options: SAMEORIGIN`; opening the link in a
new tab avoids embedding without modifying the site's security headers.
