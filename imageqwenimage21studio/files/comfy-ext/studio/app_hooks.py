"""Studio hooks for Qwen Image 2.1: seconds a job takes on Olares One.

From local-model-bench qwen-image-2.1 (One, ComfyUI, 1024x1024, second image
of a run): t2i measured with no image and edit with one. Each further image
adds what the first one did (its encode and the longer sampling step), which
is not measured. 2K is not measured either, so it gets no estimate. ref
(not measured) samples a 1 MP canvas with every image as a reference, as an
edit of the same images does, so it takes edit's numbers. The studio scales
the result by this install's own history."""

DEVICES = ("Olares One",)

# mode -> variant -> (seconds besides sampling, seconds per step, steps)
BASE = {
    "t2i": {"int8": (0.84, 0.365, 40), "nvfp4": (0.86, 0.298, 40)},
    "edit": {"int8": (3.76, 0.478, 40), "nvfp4": (3.73, 0.408, 40)},
    "edit_fast": {"int8": (3.74, 0.373, 8), "nvfp4": (3.86, 0.474, 8)},
}
# variant -> (seconds, seconds per step) one image adds
PER_IMAGE = {"int8": (2.9, 0.113), "nvfp4": (2.9, 0.110)}


def estimate(mode, variant, resolution, duration, aspect, items, prompt=""):
    if resolution not in ("", "1K"):
        return None
    row = BASE.get("edit" if mode == "ref" else mode, {}).get(variant)
    if row is None:
        return None
    fixed, step, steps = row
    extra = max(0, sum(1 for it in items if it["role"] == "ref_image") - (0 if mode == "t2i" else 1))
    add_fixed, add_step = PER_IMAGE[variant]
    return fixed + extra * add_fixed + steps * (step + extra * add_step)
