# Jupyter Notebook ( jupyternotebook )

Jupyter Notebook V7 single-user interactive computing environment

- Image: `quay.io/jupyter/base-notebook:2025-12-31`
- Entrance port: `8888`

This is an Olares Application Chart (OAC) generated from `app-template`. To migrate, at minimum:

1. Fill in `OlaresManifest.yaml` (metadata / entrances / permission / spec).
2. Configure volume mounts and (optional) multiple containers in `templates/deployment.yaml`.
3. Run `scripts\validate-app.ps1 -AppId jupyternotebook` from the repo root to validate.
