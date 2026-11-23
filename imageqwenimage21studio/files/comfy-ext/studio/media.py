"""Probe uploads, make posters and grab frames. PyAV and Pillow ship with
ComfyUI; ffmpeg is only needed to trim and as a HEIC fallback."""
import base64
import io
import os
import shutil
import subprocess

from PIL import Image, ImageOps

try:
    import av
except ImportError:  # pragma: no cover
    av = None

POSTER_EDGE = 640
IMAGE_MIME = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp", "GIF": "image/gif", "MPO": "image/jpeg"}
VIDEO_MIME = {"mov,mp4,m4a,3gp,3g2,mj2": "video/mp4", "matroska,webm": "video/webm"}
AUDIO_MIME = {"mp3": "audio/mpeg", "wav": "audio/wav", "flac": "audio/flac", "ogg": "audio/ogg",
              "mov,mp4,m4a,3gp,3g2,mj2": "audio/mp4", "aac": "audio/aac"}
HEIC_EXT = (".heic", ".heif")


class MediaError(Exception):
    pass


def ffmpeg():
    return shutil.which("ffmpeg")


def probe(path):
    """{kind, mime, ext, width, height, duration, has_audio, fps} or MediaError."""
    try:
        with Image.open(path) as im:
            fmt = im.format
            if fmt in IMAGE_MIME and not getattr(im, "is_animated", False):
                w, h = ImageOps.exif_transpose(im).size
                ext = {"JPEG": ".jpg", "MPO": ".jpg"}.get(fmt, "." + fmt.lower())
                return {"kind": "image", "mime": IMAGE_MIME[fmt], "ext": ext, "width": w, "height": h,
                        "duration": None, "has_audio": False, "fps": None}
    except Exception:
        pass
    if av is None:
        raise MediaError("unsupported_file")
    try:
        with av.open(path) as c:
            fmt = c.format.name
            v = next((s for s in c.streams.video if not _is_cover(s)), None)
            a = next(iter(c.streams.audio), None)
            dur = float(c.duration) / av.time_base if c.duration else None
            if v is not None:
                mime = VIDEO_MIME.get(fmt)
                if not mime:
                    raise MediaError("unsupported_video")
                w, h = v.codec_context.width, v.codec_context.height
                rot = _rotation(v)
                if rot in (90, 270):
                    w, h = h, w
                return {"kind": "video", "mime": mime, "ext": ".webm" if mime == "video/webm" else (".mov" if path.lower().endswith(".mov") else ".mp4"),
                        "width": w, "height": h, "duration": dur, "has_audio": a is not None,
                        "fps": float(v.average_rate) if v.average_rate else None}
            if a is not None:
                mime = AUDIO_MIME.get(fmt)
                if not mime:
                    raise MediaError("unsupported_audio")
                ext = {"audio/mpeg": ".mp3", "audio/wav": ".wav", "audio/flac": ".flac", "audio/ogg": ".ogg",
                       "audio/mp4": ".m4a", "audio/aac": ".aac"}[mime]
                return {"kind": "audio", "mime": mime, "ext": ext, "width": None, "height": None,
                        "duration": dur, "has_audio": True, "fps": None}
    except MediaError:
        raise
    except Exception:
        pass
    raise MediaError("unsupported_file")


def _is_cover(stream):
    return bool(getattr(stream, "disposition", 0) and "attached_pic" in str(stream.disposition))


def _rotation(stream):
    try:
        m = stream.side_data.get("DISPLAYMATRIX") if hasattr(stream, "side_data") else None
        if m is not None:
            return int(round(-float(m))) % 360
    except Exception:
        pass
    try:
        return int(stream.metadata.get("rotate", 0)) % 360
    except Exception:
        return 0


def heic_to_png(src, dst):
    try:
        import pillow_heif  # noqa: F401
        pillow_heif.register_heif_opener()
        with Image.open(src) as im:
            ImageOps.exif_transpose(im).convert("RGB").save(dst, "PNG")
        return
    except ImportError:
        pass
    except Exception as e:
        raise MediaError("bad_heic") from e
    if not ffmpeg():
        raise MediaError("heic_unsupported")
    r = subprocess.run([ffmpeg(), "-v", "error", "-y", "-i", src, "-frames:v", "1", dst], capture_output=True, timeout=120)
    if r.returncode != 0 or not os.path.exists(dst):
        raise MediaError("heic_unsupported")


def _save_poster(im, dst):
    im = ImageOps.exif_transpose(im)
    alpha = im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info)
    im = im.convert("RGBA" if alpha else "RGB")
    im.thumbnail((POSTER_EDGE, POSTER_EDGE))
    im.save(dst, "WEBP", quality=78, method=4)


def _frame_at(path, t=None, last=False):
    """A PIL image of the frame at t seconds (or the last frame)."""
    if av is None:
        raise MediaError("no_pyav")
    with av.open(path) as c:
        v = next(s for s in c.streams.video if not _is_cover(s))
        v.thread_type = "AUTO"
        dur = float(c.duration) / av.time_base if c.duration else None
        if last:
            t = max(0.0, (dur or 0) - 1.0)
        if t:
            c.seek(int(t * av.time_base), backward=True, any_frame=False)
        pick = None
        for frame in c.decode(v):
            ft = frame.time if frame.time is not None else 0
            if last:
                pick = frame
                continue
            pick = frame
            if t is None or ft >= t - 1e-3:
                break
        if pick is None:
            raise MediaError("no_frame")
        img = pick.to_image()
        rot = _rotation(v)
        if rot:
            img = img.rotate(-rot, expand=True)
        return img


def data_url(path, edge):
    """The image as a JPEG data URL, longest side at most edge."""
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info):
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im.convert("RGBA"), mask=im.convert("RGBA").getchannel("A"))
            im = bg
        im = im.convert("RGB")
        im.thumbnail((edge, edge))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def poster(path, kind, dst, duration=None):
    if kind == "image":
        with Image.open(path) as im:
            _save_poster(im, dst)
    elif kind == "video":
        t = min(0.5, (duration or 1) / 2)
        _save_poster(_frame_at(path, t), dst)
    else:
        return None
    return dst


def grab_frame(path, dst, t=None, last=False):
    img = _frame_at(path, t=t, last=last)
    img.save(dst, "PNG")
    return img.size


def needs_normalize(path, info):
    """Videos LoadVideo would read wrongly: rotated (phone portrait) or MOV."""
    if info["kind"] != "video" or not ffmpeg():
        return False
    if info["ext"] == ".mov":
        return True
    try:
        with av.open(path) as c:
            v = next(s for s in c.streams.video if not _is_cover(s))
            return _rotation(v) != 0
    except Exception:
        return False


def join(parts, source, dst, start, duration):
    """One video from segment results: parts are (path, skip, keep) frames
    to take from each (keep None for the rest), with the audio of source
    from start for duration seconds."""
    if not ffmpeg():
        raise MediaError("ffmpeg_missing")
    args = [ffmpeg(), "-v", "error", "-y"]
    for path, _, _ in parts:
        args += ["-i", path]
    args += ["-ss", "%.3f" % start, "-t", "%.3f" % duration, "-i", source]
    chains = []
    for i, (_, skip, keep) in enumerate(parts):
        end = ":end_frame=%d" % (skip + keep) if keep is not None else ""
        chains.append("[%d:v]trim=start_frame=%d%s,setpts=PTS-STARTPTS[v%d]" % (i, skip, end, i))
    graph = ";".join(chains) + ";" + "".join("[v%d]" % i for i in range(len(parts))) + "concat=n=%d:v=1:a=0[v]" % len(parts)
    args += ["-filter_complex", graph, "-map", "[v]", "-map", "%d:a:0?" % len(parts),
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", dst]
    r = subprocess.run(args, capture_output=True, timeout=max(600, duration * 120))
    if r.returncode != 0 or not os.path.exists(dst):
        raise MediaError("join_failed: " + r.stderr.decode(errors="replace")[-300:])


def trim(src, dst, start, end):
    if not ffmpeg():
        raise MediaError("ffmpeg_missing")
    args = [ffmpeg(), "-v", "error", "-y", "-ss", "%.3f" % start, "-i", src, "-t", "%.3f" % (end - start)]
    if dst.endswith(".mp4"):
        args += ["-map", "0:v:0?", "-map", "0:a:0?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                 "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
    else:
        args += ["-vn", "-c:a", "pcm_s16le"]
    r = subprocess.run(args + [dst], capture_output=True, timeout=600)
    if r.returncode != 0 or not os.path.exists(dst):
        raise MediaError("trim_failed: " + r.stderr.decode(errors="replace")[-300:])
