# Lares

Chat on Olares, wired to Router.

Current app version: **0.26.33** — `version` and `appVersion` in `Chart.yaml`, the
manifest version, and the image tag in `values.yaml` move together.

## Chart ownership (test / public index)

`owners` (no extension) must list the **GitHub login** used to open index PRs:

```yaml
owners:
- ffkijjkokok
```

## Requirements

| Item | Requirement |
|------|-------------|
| Olares | >= 1.12.7 |
| Dependency | Router (`>=1.0.0`) |
| Arch | `amd64`, `arm64` |

## Install

1. Install from Market (Chat test source URL: `https://appstore-server-test.bttcdn.com`).
2. Confirm Router is running.
3. Open the Lares entrance and chat.

Auth is the in-cluster app identity (`x-caller-appid`) plus the person logged
into this Lares (`x-bfl-user` / `OLARES_USERNAME`). Image jobs in FlowStudio
must belong to that person, not the shared FlowStudio chart owner.
