"""
FastVideo ComfyUI Client — Media Encoding & Video Conversion
Encodes ComfyUI IMAGE batches/lists to PNG/JPEG data URLs and converts
downloaded MP4 bytes into the native ComfyUI VIDEO representation.
"""
import base64
import io
import os
import shutil
import tempfile
from typing import Any, Dict, List, Optional

import numpy as np
from PIL import Image


MAX_REFERENCE_IMAGES = 9


def _iter_single_images(images: Any):
    """Yield individual HWC image arrays/tensors/PIL images from a ComfyUI IMAGE input."""
    if images is None:
        return

    if isinstance(images, Image.Image):
        yield images
        return

    if isinstance(images, (list, tuple)):
        for item in images:
            yield from _iter_single_images(item)
        return

    # Duck-typed tensor or numpy array (avoids importing torch)
    if hasattr(images, "detach"):
        images = images.detach()
    if hasattr(images, "cpu"):
        images = images.cpu()
    if hasattr(images, "numpy"):
        arr = images.numpy()
    else:
        arr = np.asarray(images)

    if arr.ndim == 4:
        for i in range(arr.shape[0]):
            yield arr[i]
    elif arr.ndim in (2, 3):
        yield arr
    else:
        raise ValueError(f"Unsupported IMAGE tensor/array shape: {arr.shape}")


def _to_pil_image(img: Any) -> Image.Image:
    """Convert a single HWC float [0, 1] or uint8 array/PIL image to a PIL RGB Image."""
    if isinstance(img, Image.Image):
        return img.convert("RGB") if img.mode not in ("RGB", "RGBA") else img

    arr = np.asarray(img)
    if arr.dtype != np.uint8:
        arr = np.clip(arr * 255.0, 0.0, 255.0).astype(np.uint8)

    if arr.ndim == 3 and arr.shape[2] == 1:
        arr = arr[:, :, 0]

    pil_img = Image.fromarray(arr)
    if pil_img.mode not in ("RGB", "RGBA"):
        pil_img = pil_img.convert("RGB")
    return pil_img


def encode_image_to_data_url(img: Any, image_format: str = "PNG") -> str:
    """
    Encode a single image to a single-line base64 data URL:
      data:image/png;base64,<encoded-image>
    """
    fmt = image_format.upper()
    if fmt == "JPG":
        fmt = "JPEG"
    if fmt not in ("PNG", "JPEG"):
        raise ValueError(f"Unsupported image encoding format: {image_format}")

    pil_img = _to_pil_image(img)
    if fmt == "JPEG" and pil_img.mode == "RGBA":
        pil_img = pil_img.convert("RGB")

    buf = io.BytesIO()
    pil_img.save(buf, format=fmt)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    mime = "image/png" if fmt == "PNG" else "image/jpeg"
    return f"data:{mime};base64,{b64}"


def encode_images_to_references(images: Any, image_format: str = "PNG") -> List[Dict[str, str]]:
    """
    Convert a ComfyUI IMAGE batch or list into FastVideo `image_reference` entries:
      [{"image_url": "data:image/png;base64,..."}]
    """
    single_images = list(_iter_single_images(images))
    if len(single_images) > MAX_REFERENCE_IMAGES:
        raise ValueError(
            f"Received {len(single_images)} reference images, but FastVideo supports at most "
            f"{MAX_REFERENCE_IMAGES} image references per request."
        )

    references: List[Dict[str, str]] = []
    for single_img in single_images:
        data_url = encode_image_to_data_url(single_img, image_format=image_format)
        references.append({"image_url": data_url})
    return references


class _FallbackVideoFromFile:
    """
    Fallback VIDEO representation matching ComfyUI's VideoInput / VideoFromFile interface
    when running outside the ComfyUI runtime environment.
    """

    def __init__(self, file_path: str):
        self._file_path = file_path

    @property
    def path(self) -> str:
        return self._file_path

    def get_stream_source(self) -> str:
        return self._file_path

    def get_container_format(self) -> str:
        return "mp4"

    def get_dimensions(self) -> tuple[int, int]:
        return (0, 0)

    def save_to(self, output_path: str, **kwargs) -> bool:
        shutil.copyfile(self._file_path, output_path)
        return True

    def __fspath__(self) -> str:
        return self._file_path

    def __str__(self) -> str:
        return self._file_path

    def __repr__(self) -> str:
        return f"VideoFromFile({self._file_path!r})"


def mp4_bytes_to_comfy_video(mp4_bytes: bytes, job_id: Optional[str] = None) -> Any:
    """
    Persist downloaded MP4 bytes to ComfyUI's temp directory (or system temp) and wrap
    in the native ComfyUI `VIDEO` type (`VideoFromFile`).
    """
    if not mp4_bytes:
        raise ValueError("Downloaded video content is empty (0 bytes).")

    temp_dir = None
    try:
        import folder_paths  # type: ignore

        if hasattr(folder_paths, "get_temp_directory"):
            temp_dir = folder_paths.get_temp_directory()
    except Exception:
        temp_dir = None

    if not temp_dir:
        temp_dir = tempfile.gettempdir()

    os.makedirs(temp_dir, exist_ok=True)

    safe_id = "".join(c if (c.isalnum() or c in "-_") else "_" for c in (job_id or "video"))
    fd, file_path = tempfile.mkstemp(prefix=f"fastvideo_{safe_id}_", suffix=".mp4", dir=temp_dir)
    with os.fdopen(fd, "wb") as f:
        f.write(mp4_bytes)

    for module_path in (
        "comfy_api.input_impl.video_types",
        "comfy_api.latest._input_impl.video_types",
        "comfy_api.input.video_types",
    ):
        try:
            mod = __import__(module_path, fromlist=["VideoFromFile"])
            video_cls = getattr(mod, "VideoFromFile", None)
            if video_cls is not None:
                return video_cls(file_path)
        except Exception:
            continue

    try:
        from comfy_api.latest import InputImpl  # type: ignore

        if hasattr(InputImpl, "VideoFromFile"):
            return InputImpl.VideoFromFile(file_path)
    except Exception:
        pass

    return _FallbackVideoFromFile(file_path)
