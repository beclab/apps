# comfyapp studio extension: no nodes. Registers the studio backend's routes
# (/studio/api/...) on ComfyUI's server, and web/comfyapp.js opens a studio
# flow in the ComfyUI editor.
from . import ts_idle  # noqa: F401
from .studio import setup

setup()

NODE_CLASS_MAPPINGS = {}
WEB_DIRECTORY = "./web"
