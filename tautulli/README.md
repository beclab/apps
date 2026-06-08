# Tautulli for Olares

Tautulli is a monitoring and statistics dashboard for Plex Media Server.

This Olares app runs the official `tautulli/tautulli` container and persists Tautulli's configuration and database under `/config`.

## First Run

Open Tautulli from Olares, then use Tautulli's setup wizard to connect to your Plex Media Server.

Use your Plex server URL, for example:

```text
http://192.168.1.50:32400
```

Do not include `/web` in the Plex URL.

## Security

The app exposes Tautulli on port `8181`. Configure a Tautulli username and password during setup.

## Data

Tautulli stores configuration, history, and its database in `/config`.

## Image

This chart uses the official Docker image:

```text
tautulli/tautulli:v2.17.1
```
