"""
FastVideo ComfyUI Client Package — Architecture v0.2
"""
from .fastvideo_generate import (
    FastVideoGenerate,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    SIZE_PRESETS,
    TASK_OPTIONS,
    build_fastvideo_request,
)
from .fastvideo_http import (
    DEFAULT_BASE_URL,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_POLL_TIMEOUT,
    FastVideoHTTPError,
    FastVideoJobFailedError,
    FastVideoPollTimeoutError,
    download_video_content,
    generate_video_sync,
    get_models,
    get_video_job,
    normalize_base_url,
    poll_video_job,
    submit_video_job,
)
from .fastvideo_media import (
    encode_image_to_data_url,
    encode_images_to_references,
    mp4_bytes_to_comfy_video,
)

__all__ = [
    "FastVideoGenerate",
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "SIZE_PRESETS",
    "TASK_OPTIONS",
    "build_fastvideo_request",
    "DEFAULT_BASE_URL",
    "DEFAULT_POLL_INTERVAL",
    "DEFAULT_POLL_TIMEOUT",
    "FastVideoHTTPError",
    "FastVideoJobFailedError",
    "FastVideoPollTimeoutError",
    "download_video_content",
    "generate_video_sync",
    "get_models",
    "get_video_job",
    "normalize_base_url",
    "poll_video_job",
    "submit_video_job",
    "encode_image_to_data_url",
    "encode_images_to_references",
    "mp4_bytes_to_comfy_video",
]
