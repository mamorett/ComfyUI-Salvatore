"""
FastVideo ComfyUI Client — `FastVideo Generate` Node
Builds the canonical FastVideo OpenAI-compatible request, submits the job,
polls with truthful indeterminate progress, downloads the completed MP4,
and returns the native ComfyUI `VIDEO` type.
"""
import json
import re
import threading
from typing import Any, Dict, Optional, Tuple

from .fastvideo_http import (
    DEFAULT_BASE_URL,
    FastVideoHTTPError,
    FastVideoJobFailedError,
    FastVideoPollTimeoutError,
    download_video_content,
    get_models,
    normalize_base_url,
    poll_video_job,
    submit_video_job,
)
from .fastvideo_media import encode_images_to_references, mp4_bytes_to_comfy_video


VALID_TASKS = ("t2va", "fl2va", "ref2va")

TASK_OPTIONS = [
    "auto (server default)",
    "t2va",
    "fl2va",
    "ref2va",
]

SIZE_PRESETS = [
    "832x480 (16:9 Landscape 480p - Recommended)",
    "480x832 (9:16 Portrait 480p)",
    "640x640 (1:1 Square 480p)",
    "640x480 (4:3 Standard 480p)",
    "480x640 (3:4 Vertical 480p)",
    "1344x768 (16:9 Landscape 768p - High VRAM)",
    "768x1344 (9:16 Portrait 768p - High VRAM)",
    "960x960 (1:1 Square 768p - High VRAM)",
    "1024x768 (4:3 Standard 768p - High VRAM)",
    "768x1024 (3:4 Vertical 768p - High VRAM)",
    "server_default (use server config)",
    "custom (use width & height)",
]

PROGRESS_SUBMITTING = "Submitting job…"
PROGRESS_QUEUED = "Queued on FastVideo…"
PROGRESS_GENERATING = "Generating on FastVideo…"
PROGRESS_DOWNLOADING = "Downloading completed video…"

_GENERATION_LOCK = threading.Lock()
_SIZE_PATTERN = re.compile(r"^(\d+x\d+)\b")


def _parse_json_object(raw_json: str, field_name: str) -> Dict[str, Any]:
    """Parse a JSON string and ensure it is a JSON object (dict)."""
    text = (raw_json or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in '{field_name}': {e}") from None

    if not isinstance(parsed, dict):
        raise ValueError(
            f"'{field_name}' must be a JSON object (e.g. {{\"key\": \"value\"}}), got {type(parsed).__name__}."
        )
    return parsed


def _reject_file_id_references(payload: Dict[str, Any]) -> None:
    """
    Ensure `file_id` is never used in reference lists: FastVideo has no OpenAI Files store
    and returns HTTP 400 for it.
    """
    for ref_key in ("image_reference", "input_reference", "video_reference"):
        ref_val = payload.get(ref_key)
        if isinstance(ref_val, list):
            for idx, item in enumerate(ref_val):
                if isinstance(item, dict) and "file_id" in item:
                    raise ValueError(
                        f"'{ref_key}[{idx}].file_id' is not supported: FastVideo has no OpenAI Files store."
                    )
        elif isinstance(ref_val, dict) and "file_id" in ref_val:
            raise ValueError(f"'{ref_key}.file_id' is not supported: FastVideo has no OpenAI Files store.")


def _extract_size_token(size_value: Optional[str]) -> Tuple[str, Optional[str]]:
    """
    Interpret the `size` dropdown or string:
    Returns `(mode, size_str)` where `mode` is one of:
      - `"preset"`: `size_str` is `"WIDTHxHEIGHT"` (e.g. `"832x480"`)
      - `"custom"`: use `width` and `height` inputs
      - `"server_default"`: omit resolution fields so the server uses its YAML config
    """
    raw = (size_value or "").strip()
    if not raw or raw.lower().startswith("custom"):
        return ("custom", None)
    if raw.lower().startswith("server_default"):
        return ("server_default", None)

    match = _SIZE_PATTERN.match(raw)
    if match:
        return ("preset", match.group(1))

    raise ValueError(
        f"Invalid size value {size_value!r}. Expected 'WIDTHxHEIGHT' (e.g. '832x480'), "
        "'custom (use width & height)', or 'server_default (use server config)'."
    )


def build_fastvideo_request(
    *,
    model: str,
    prompt: str,
    task: str = "auto (server default)",
    seconds: Any = 5,
    size: str = SIZE_PRESETS[0],
    width: int = 832,
    height: int = 480,
    fps: int = 24,
    num_frames: int = 0,
    seed: int = 42,
    num_inference_steps: int = 8,
    guidance_scale: float = 1.0,
    images: Any = None,
    extra_params_json: str = "",
    advanced_request_json: str = "",
) -> Dict[str, Any]:
    """
    Construct the canonical top-level FastVideo request payload according to Architecture v0.2:
    - Emits only top-level canonical fields (never `video_params`).
    - `size` preset wins over `width` + `height`; when `size` is `'custom (use width & height)'`,
      top-level `width` and `height` are emitted; when `'server_default'`, resolution is omitted.
    - `seconds` (default 5s) is omitted when `num_frames > 0` explicitly controls duration.
    - `task` is sent only when explicitly selected (`t2va`, `fl2va`, `ref2va`).
    - `images` are encoded as `image_reference` base64 PNG data URLs.
    - `extra_params_json` maps to `extra_params`.
    - `advanced_request_json` merges into the top-level request body without silently overwriting
      any explicit widget value; a duplicate key with a different value raises ValueError.
    """
    model_str = (model or "").strip()
    if not model_str:
        raise ValueError("A FastVideo 'model' name is required (populate from GET /v1/models or enter manually).")

    prompt_str = str(prompt if prompt is not None else "").strip()
    if not prompt_str:
        raise ValueError("FastVideo 'prompt' must not be empty.")

    req: Dict[str, Any] = {
        "model": model_str,
        "prompt": prompt_str,
    }

    task_clean = (task or "").strip()
    if task_clean in VALID_TASKS:
        req["task"] = task_clean
    elif task_clean and not task_clean.lower().startswith(("auto", "none", "default")):
        req["task"] = task_clean

    # Resolution handling: preset `size` vs `custom (width & height)` vs `server_default`
    res_mode, size_token = _extract_size_token(size)
    if res_mode == "preset" and size_token:
        req["size"] = size_token
    elif res_mode == "custom":
        if width and int(width) > 0:
            req["width"] = int(width)
        if height and int(height) > 0:
            req["height"] = int(height)

    # Frame rate & duration: omit `seconds` when `num_frames > 0` explicitly controls duration
    if fps and int(fps) > 0:
        req["fps"] = int(fps)

    if num_frames and int(num_frames) > 0:
        req["num_frames"] = int(num_frames)
    else:
        if isinstance(seconds, str):
            sec_str = seconds.strip()
            if sec_str and sec_str not in ("0", "0.0"):
                req["seconds"] = int(float(sec_str)) if sec_str.replace(".", "", 1).isdigit() else sec_str
        elif seconds is not None:
            sec_int = int(round(float(seconds)))
            if sec_int > 0:
                req["seconds"] = sec_int

    if seed is not None:
        req["seed"] = int(seed)

    if num_inference_steps and int(num_inference_steps) > 0:
        req["num_inference_steps"] = int(num_inference_steps)

    if guidance_scale is not None and float(guidance_scale) > 0.0:
        req["guidance_scale"] = float(guidance_scale)

    # Encode ComfyUI IMAGE batch/list as PNG data URLs
    if images is not None:
        refs = encode_images_to_references(images, image_format="PNG")
        if refs:
            req["image_reference"] = refs

    # Parse `extra_params_json`
    extra_params = _parse_json_object(extra_params_json, "extra_params_json")
    if extra_params:
        req["extra_params"] = extra_params

    # Merge `advanced_request_json`
    advanced_obj = _parse_json_object(advanced_request_json, "advanced_request_json")
    if advanced_obj:
        for key, val in advanced_obj.items():
            if key in req:
                if req[key] != val:
                    raise ValueError(
                        f"advanced_request_json duplicate key '{key}' conflicts with explicit widget value: "
                        f"widget={req[key]!r} vs advanced_request_json={val!r}"
                    )
            else:
                req[key] = val

    _reject_file_id_references(req)

    # Validate reference requirement for OmniRef / Ref2VA / FL2VA before submitting to server
    has_any_ref = any(
        bool(req.get(k))
        for k in ("image_reference", "input_reference", "reference_url", "video_reference", "video_path", "video_url")
    )
    is_ref_model = "omniref" in model_str.lower() or "ref2va" in model_str.lower()
    if (is_ref_model or req.get("task") in ("ref2va", "fl2va")) and not has_any_ref:
        raise ValueError(
            f"Model '{model_str}' (or task '{req.get('task') or 'ref2va'}') requires at least one reference image "
            "connected to 'images' (or reference media passed via advanced_request_json)."
        )

    return req


def _register_fastvideo_routes() -> None:
    """Register a PromptServer endpoint so the frontend UI can refresh `model` via GET /v1/models."""
    try:
        from server import PromptServer  # type: ignore
        from aiohttp import web  # type: ignore

        if PromptServer.instance is None:
            return

        @PromptServer.instance.routes.post("/salvatore/fastvideo/models")
        async def salvatore_fastvideo_models(request):
            try:
                data = await request.json()
            except Exception:
                data = {}
            base_url = str(data.get("base_url") or DEFAULT_BASE_URL)
            api_key = str(data.get("api_key") or "")
            try:
                models, raw = get_models(base_url, api_key=api_key, timeout=10.0)
                return web.json_response({"status": "ok", "models": models, "raw": raw})
            except Exception as e:
                return web.json_response({"status": "error", "message": str(e)}, status=400)
    except Exception:
        pass


_register_fastvideo_routes()


class FastVideoGenerate:
    """
    Thin HTTP client node for an existing FastVideo server (`POST /v1/videos`).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_url": (
                    "STRING",
                    {
                        "default": DEFAULT_BASE_URL,
                        "multiline": False,
                        "tooltip": "Base URL of the FastVideo server, e.g. http://127.0.0.1:8000/v1",
                    },
                ),
                "api_key": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Optional Bearer token for a reverse proxy; leave empty for local FastVideo.",
                    },
                ),
                "model": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Served model ID (leave blank to auto-detect via GET /v1/models, or click Refresh Model).",
                    },
                ),
                "prompt": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": "Text prompt describing the video to generate.",
                    },
                ),
                "task": (
                    TASK_OPTIONS,
                    {
                        "default": "auto (server default)",
                        "tooltip": "Optional FastH3 task selector. Keep 'auto (server default)' unless explicitly needed.",
                    },
                ),
                "seconds": (
                    "INT",
                    {
                        "default": 5,
                        "min": 5,
                        "max": 15,
                        "step": 1,
                        "tooltip": "Video duration in seconds (FastH3 supports 5 to 15 seconds). Ignored when num_frames > 0.",
                    },
                ),
                "size": (
                    SIZE_PRESETS,
                    {
                        "default": SIZE_PRESETS[0],
                        "tooltip": (
                            "Output resolution & aspect ratio. "
                            "Select a recommended preset (width & height widgets are ignored), "
                            "'custom (use width & height)' to use manual width/height below, "
                            "or 'server_default' to use the server's YAML config."
                        ),
                    },
                ),
                "width": (
                    "INT",
                    {
                        "default": 832,
                        "min": 256,
                        "max": 1920,
                        "step": 32,
                        "tooltip": "Custom width (multiple of 32). Only active when size is 'custom (use width & height)'.",
                    },
                ),
                "height": (
                    "INT",
                    {
                        "default": 480,
                        "min": 256,
                        "max": 1920,
                        "step": 32,
                        "tooltip": "Custom height (multiple of 32). Only active when size is 'custom (use width & height)'.",
                    },
                ),
                "fps": (
                    "INT",
                    {
                        "default": 24,
                        "min": 1,
                        "max": 120,
                        "step": 1,
                        "tooltip": "Frames per second (FastH3 requires 24 fps).",
                    },
                ),
                "num_frames": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 362,
                        "step": 1,
                        "tooltip": (
                            "0 = Auto (calculated from seconds × fps on the server: 5s=124, 10s=243, 15s=362 frames). "
                            "Set > 0 (must be 17*n + 5) only to override 'seconds'."
                        ),
                    },
                ),
                "seed": (
                    "INT",
                    {
                        "default": 42,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "tooltip": "Generation seed.",
                    },
                ),
                "num_inference_steps": (
                    "INT",
                    {
                        "default": 8,
                        "min": 1,
                        "max": 100,
                        "step": 1,
                        "tooltip": "Sampling steps (default 8 for FastH3 OmniRef / FastH3 V2; 5 for FastH3 V1 4-step).",
                    },
                ),
                "guidance_scale": (
                    "FLOAT",
                    {
                        "default": 1.0,
                        "min": 0.0,
                        "max": 20.0,
                        "step": 0.1,
                        "tooltip": "Guidance scale (FastH3 requires 1.0).",
                    },
                ),
            },
            "optional": {
                "images": (
                    "IMAGE",
                    {
                        "tooltip": "Zero, one, or multiple reference images (encoded as PNG base64 data URLs in image_reference).",
                    },
                ),
                "extra_params_json": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": "Optional JSON object for extra_params (e.g. {\"vsa_mode\": \"exempt\"}).",
                    },
                ),
                "advanced_request_json": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": "Optional JSON object merged into the request body for advanced FastVideo fields.",
                    },
                ),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("VIDEO", "STRING", "STRING")
    RETURN_NAMES = ("video", "job_id", "status")
    FUNCTION = "generate"
    CATEGORY = "Salvatore Nodes/video"

    @staticmethod
    def _emit_status(unique_id: Optional[str], message: str, job_id: str = "", state: str = "running") -> None:
        """
        Emit truthful indeterminate progress messages (never fabricating percentage, ETA, or step count).
        """
        print(f"[FastVideo Generate] {message}" + (f" (job_id={job_id})" if job_id else ""))
        try:
            from server import PromptServer  # type: ignore

            if PromptServer.instance is not None:
                PromptServer.instance.send_sync(
                    "salvatore.fastvideo.status",
                    {
                        "node_id": str(unique_id or ""),
                        "message": message,
                        "job_id": job_id,
                        "state": state,
                    },
                )
        except Exception:
            pass

    @staticmethod
    def _check_interrupted() -> None:
        """Raise ComfyUI's ProcessingInterrupted exception if the user cancelled execution."""
        try:
            import comfy.model_management as model_management  # type: ignore

            model_management.throw_exception_if_processing_interrupted()
        except ImportError:
            pass

    def _resolve_model(self, base_url: str, api_key: str, model: str) -> str:
        """
        Confirm the advertised model via `GET /v1/models`.
        If `model` is empty, automatically select the first advertised model.
        """
        advertised_models, _ = get_models(base_url, api_key=api_key)
        chosen = (model or "").strip()
        if not chosen:
            if not advertised_models:
                raise RuntimeError(
                    f"GET {normalize_base_url(base_url)}/models returned no models; "
                    "please specify 'model' manually or verify the FastVideo server."
                )
            chosen = advertised_models[0]
        return chosen

    def generate(
        self,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str = "",
        model: str = "",
        prompt: str = "",
        task: str = "auto (server default)",
        seconds: Any = 5,
        size: str = SIZE_PRESETS[0],
        width: int = 832,
        height: int = 480,
        fps: int = 24,
        num_frames: int = 0,
        seed: int = 42,
        num_inference_steps: int = 8,
        guidance_scale: float = 1.0,
        images: Any = None,
        extra_params_json: str = "",
        advanced_request_json: str = "",
        unique_id: Optional[str] = None,
    ) -> Tuple[Any, str, str]:
        self._check_interrupted()

        with _GENERATION_LOCK:
            self._check_interrupted()

            resolved_model = self._resolve_model(base_url, api_key, model)
            request_body = build_fastvideo_request(
                model=resolved_model,
                prompt=prompt,
                task=task,
                seconds=seconds,
                size=size,
                width=width,
                height=height,
                fps=fps,
                num_frames=num_frames,
                seed=seed,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                images=images,
                extra_params_json=extra_params_json,
                advanced_request_json=advanced_request_json,
            )

            self._emit_status(unique_id, PROGRESS_SUBMITTING, state="submitting")
            job_resp = submit_video_job(base_url, request_body, api_key=api_key)
            job_id = str(job_resp.get("id") or job_resp.get("job_id") or "").strip()
            if not job_id:
                raise RuntimeError(f"FastVideo POST /v1/videos did not return a job id: {job_resp!r}")

            last_announced_msg = ""

            def _on_poll_status(status: str, _job_data: Dict[str, Any]) -> None:
                nonlocal last_announced_msg
                if status == "queued":
                    msg = PROGRESS_QUEUED
                elif status in ("in_progress", "running", "processing"):
                    msg = PROGRESS_GENERATING
                else:
                    msg = f"Status: {status}"
                if msg != last_announced_msg:
                    last_announced_msg = msg
                    self._emit_status(unique_id, msg, job_id=job_id, state=status)

            try:
                final_job = poll_video_job(
                    base_url,
                    job_id,
                    initial_job=job_resp,
                    api_key=api_key,
                    on_status=_on_poll_status,
                    check_interrupted=self._check_interrupted,
                )
            except (FastVideoJobFailedError, FastVideoPollTimeoutError, FastVideoHTTPError) as err:
                self._emit_status(unique_id, str(err), job_id=job_id, state="error")
                raise
            except Exception as err:
                self._emit_status(unique_id, f"Stopped ({job_id}): {err}", job_id=job_id, state="stopped")
                raise

            self._check_interrupted()
            self._emit_status(unique_id, PROGRESS_DOWNLOADING, job_id=job_id, state="downloading")
            mp4_bytes = download_video_content(base_url, job_id, api_key=api_key)
            video_obj = mp4_bytes_to_comfy_video(mp4_bytes, job_id=job_id)

            final_status = str(final_job.get("status") or "completed")
            self._emit_status(unique_id, f"Completed ({job_id})", job_id=job_id, state="completed")
            return (video_obj, job_id, final_status)


NODE_CLASS_MAPPINGS = {
    "FastVideoGenerate": FastVideoGenerate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FastVideoGenerate": "FastVideo Generate",
}
