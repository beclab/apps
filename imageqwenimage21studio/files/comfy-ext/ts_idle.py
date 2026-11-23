# In HAMi time slicing (CUDA_DEVICE_GPU_MODE_0=2) another app can only take
# memory this process holds as managed memory. comfy-aimdo's weights are VMM
# allocations and stay resident, so unload the models whenever the queue goes
# idle; the next prompt streams them back from pinned host memory.
# FLOWSTUDIO_TS_IDLE=0 turns this off.
import logging
import os
import time

if os.environ.get("CUDA_DEVICE_GPU_MODE_0") == "2" and os.environ.get("FLOWSTUDIO_TS_IDLE", "1") != "0":
    import comfy.model_management as mm
    import execution
    from server import PromptServer

    _execute = execution.PromptExecutor.execute

    def execute(self, *args, **kwargs):
        r = _execute(self, *args, **kwargs)
        try:
            q = PromptServer.instance.prompt_queue
            with q.mutex:
                idle = not q.queue
            if idle:
                t0 = time.perf_counter()
                mm.unload_all_models()
                mm.soft_empty_cache()
                logging.info("comfyapp: time slicing, unloaded models while idle in %.2fs", time.perf_counter() - t0)
        except Exception:
            logging.exception("comfyapp: unloading models while idle failed")
        return r

    execution.PromptExecutor.execute = execute
