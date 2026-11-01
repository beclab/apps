# Pool security rebuild

Derives from the fixed existing Olares toolbox index in Dockerfile, preserving
installed languages/tools. Upgrades every installed php8.3-* package and fails
unless the full Debian package version is at least 8.3.6-0ubuntu0.24.04.13.
Ubuntu24.04 backports the security fix while php -v remains 8.3.6.
Reference: https://ubuntu.com/security/notices/USN-8948-1 .

Pool binaries come from https://downloads.poolside.ai/pool/v1.0.16/ and are
checked against the vendor checksums.txt. Build both linux/amd64 and linux/arm64.
Source tag: harveyff/pool:v1.0.16-phpsec-20261023. Mirror tag:
beclab/harveyff-pool:v1.0.16-phpsec-20261023. Verify mirror content before deployment.
From this directory, reproduce the build with:

```sh
docker buildx build --platform linux/amd64,linux/arm64 --provenance=false --push -t harveyff/pool:v1.0.16-phpsec-20261023 .
```

Before upgrade back up the workspace, .config/poolside and local helpers. The
Chart's private config archive is supplementary, not a full workspace backup.
Upstream1.0.8 moved pool.json settings into settings.yaml; inspect custom agent
server/model defaults and migrate them according to the upstream reference.
The observed upstream1.0.15 Linux binary converts pool.json even on --version,
removes that legacy JSON and preserves existing YAML in settings.yaml.backup.
Back up before starting the new binary; inspect migrated agent/model defaults.
Use a dedicated model configuration for integration testing; do not reuse
unrelated app endpoints or credentials. Fresh-install testing verified a real
Router model response and permission-controlled workspace file write/read.
