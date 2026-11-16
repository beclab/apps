# Tautulli for Olares

Tautulli is a monitoring and statistics dashboard for Plex Media Server.

This Olares app runs the official `tautulli/tautulli` container and persists Tautulli's configuration and database under `/config`.

## First Run

Open Tautulli from Olares. On a new installation, retrieve the generated username and password from the Tautulli container logs, as explained in the [official login instructions](https://github.com/Tautulli/Tautulli/wiki/Installation#tautulli-login). Then use the setup wizard to connect to your Plex Media Server.

Use your Plex server URL, for example:

```text
http://192.168.1.50:32400
```

Do not include `/web` in the Plex URL.

## Security

The app exposes Tautulli on port `8181`. Keep Tautulli authentication enabled and set your own username and password after the initial login.

## Data

Tautulli stores configuration, history, and its database in `/config`.

## Image

This chart uses the official Docker image:

```text
tautulli/tautulli:v2.19.1
```

## Packaging for Olares

Keep the application directory and the manifest name as `tautulli` (lowercase letters and digits only). Do not rename it to `tautulli-dev`: Olares rejects hyphens in application directory names.

From the repository root, build the upload archive with Helm:

```sh
helm lint ./tautulli
helm package ./tautulli --destination /tmp
```

The resulting archive must contain `tautulli/OlaresManifest.yaml` at its top application directory, without a `./charts/` prefix. Upload `/tmp/tautulli-2.19.1.tgz` in Olares Market.
