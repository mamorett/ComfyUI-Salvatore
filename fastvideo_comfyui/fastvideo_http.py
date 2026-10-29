"""
FastVideo ComfyUI Client — HTTP Transport
Standard-library HTTP client for the FastVideo OpenAI-compatible server contract:
  - GET /v1/models
  - POST /v1/videos
  - GET /v1/videos/{job_id}
  - GET /v1/videos/{job_id}/content
  - POST /v1/videos/sync
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple


DEFAULT_BASE_URL = "http://127.0.0.1:8000/v1"
DEFAULT_POLL_INTERVAL = 5.0
DEFAULT_POLL_TIMEOUT = 1800.0

# Direct opener that ignores ambient HTTP_PROXY/http_proxy environment variables
# so LAN/local FastVideo servers (e.g. 192.168.x.x, 127.0.0.1) are always reached directly.
_DIRECT_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class FastVideoHTTPError(RuntimeError):
    """Represents an HTTP error returned by the FastVideo server."""

    def __init__(
        self,
        status_code: int,
        message: str,
        *,
        error_type: Optional[str] = None,
        param: Optional[str] = None,
        code: Any = None,
        url: Optional[str] = None,
        raw_body: Optional[str] = None,
    ):
        self.status_code = status_code
        self.error_message = message
        self.error_type = error_type
        self.param = param
        self.code = code
        self.url = url
        self.raw_body = raw_body
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        details = []
        if self.error_type:
            details.append(f"type={self.error_type}")
        if self.param is not None:
            details.append(f"param={self.param}")
        if self.code is not None and str(self.code) != str(self.status_code):
            details.append(f"code={self.code}")
        detail_suffix = f" ({', '.join(details)})" if details else ""

        if self.status_code == 400:
            return f"FastVideo HTTP 400 Bad Request: {self.error_message}{detail_suffix}"
        if self.status_code == 404:
            return f"FastVideo HTTP 404 Not Found (job or model not found): {self.error_message}{detail_suffix}"
        return f"FastVideo HTTP {self.status_code}: {self.error_message}{detail_suffix}"


class FastVideoJobFailedError(RuntimeError):
    """Raised when an asynchronous FastVideo job reaches `failed` status."""

    def __init__(self, job_id: str, error_detail: str, job_data: Optional[Dict[str, Any]] = None):
        self.job_id = job_id
        self.error_detail = error_detail
        self.job_data = job_data or {}
        super().__init__(f"FastVideo job {job_id} failed: {error_detail}")


class FastVideoPollTimeoutError(TimeoutError):
    """Raised when local polling times out while the remote job is still non-terminal."""

    def __init__(self, job_id: str, last_status: str, elapsed_s: float):
        self.job_id = job_id
        self.last_status = last_status
        self.elapsed_s = elapsed_s
        super().__init__(
            f"FastVideo poll timed out after {elapsed_s:.1f}s waiting for job '{job_id}' "
            f"(last status: {last_status}). The job remains on the server and was not resubmitted."
        )


def normalize_base_url(base_url: str) -> str:
    """
    Normalize the FastVideo server base URL so endpoints resolve under `/v1`.
    Defaults to `http://127.0.0.1:8000/v1`.
    """
    url = (base_url or "").strip()
    if not url:
        url = DEFAULT_BASE_URL
    url = url.rstrip("/")

    parsed = urllib.parse.urlsplit(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid FastVideo base_url: {base_url!r}. Expected http(s)://host:port/v1")

    path = parsed.path.rstrip("/")
    if not path:
        path = "/v1"
    elif not path.endswith("/v1"):
        path = f"{path}/v1"

    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def _build_headers(
    api_key: str = "",
    content_type: Optional[str] = None,
    accept: str = "application/json",
) -> Dict[str, str]:
    headers: Dict[str, str] = {
        "Accept": accept,
        "Connection": "close",
        "User-Agent": "FastVideo-ComfyUI-Client/0.2",
    }
    if content_type:
        headers["Content-Type"] = content_type
    token = (api_key or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _parse_http_error(err: urllib.error.HTTPError, url: str) -> FastVideoHTTPError:
    raw_body = ""
    try:
        raw_bytes = err.read()
        if raw_bytes:
            raw_body = raw_bytes.decode("utf-8", errors="replace")
    except Exception:
        raw_body = ""

    message = err.reason or f"HTTP {err.code}"
    error_type = None
    param = None
    code = err.code

    if raw_body:
        try:
            parsed = json.loads(raw_body)
            if isinstance(parsed, dict):
                err_obj = parsed.get("error")
                if isinstance(err_obj, dict):
                    message = str(err_obj.get("message") or message)
                    error_type = err_obj.get("type")
                    param = err_obj.get("param")
                    code = err_obj.get("code", err.code)
                elif isinstance(err_obj, str):
                    message = err_obj
                elif "detail" in parsed:
                    message = str(parsed["detail"])
                elif "message" in parsed:
                    message = str(parsed["message"])
            else:
                message = raw_body.strip()
        except Exception:
            message = raw_body.strip() or message

    return FastVideoHTTPError(
        err.code,
        message,
        error_type=error_type,
        param=param,
        code=code,
        url=url,
        raw_body=raw_body,
    )


def _request_json(
    method: str,
    url: str,
    *,
    api_key: str = "",
    payload: Optional[Dict[str, Any]] = None,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    data_bytes = None
    content_type = None
    if payload is not None:
        data_bytes = json.dumps(payload).encode("utf-8")
        content_type = "application/json"

    headers = _build_headers(api_key=api_key, content_type=content_type, accept="application/json")
    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method.upper())

    try:
        with _DIRECT_OPENER.open(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            if not raw.strip():
                return {}
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise RuntimeError(f"Unexpected non-object JSON response from {url}: {data!r}")
            return data
    except urllib.error.HTTPError as e:
        raise _parse_http_error(e, url) from None
    except urllib.error.URLError as e:
        raise ConnectionError(f"Failed to connect to FastVideo server at {url}: {e.reason}") from None


def _request_bytes(
    method: str,
    url: str,
    *,
    api_key: str = "",
    payload: Optional[Dict[str, Any]] = None,
    timeout: float = 300.0,
) -> Tuple[bytes, Dict[str, str]]:
    data_bytes = None
    content_type = None
    if payload is not None:
        data_bytes = json.dumps(payload).encode("utf-8")
        content_type = "application/json"

    headers = _build_headers(
        api_key=api_key,
        content_type=content_type,
        accept="video/mp4, application/octet-stream, */*",
    )
    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method.upper())

    try:
        with _DIRECT_OPENER.open(req, timeout=timeout) as resp:
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            return resp.read(), resp_headers
    except urllib.error.HTTPError as e:
        raise _parse_http_error(e, url) from None
    except urllib.error.URLError as e:
        raise ConnectionError(f"Failed to connect to FastVideo server at {url}: {e.reason}") from None


def get_models(base_url: str, api_key: str = "", timeout: float = 15.0) -> Tuple[List[str], Dict[str, Any]]:
    """
    Call `GET /v1/models` to discover the served model(s).
    Returns `(model_ids, raw_response_dict)`.
    """
    norm_base = normalize_base_url(base_url)
    url = f"{norm_base}/models"
    resp = _request_json("GET", url, api_key=api_key, timeout=timeout)

    models: List[str] = []
    data_list = resp.get("data")
    if isinstance(data_list, list):
        for item in data_list:
            if isinstance(item, dict) and item.get("id"):
                models.append(str(item["id"]))
            elif isinstance(item, str) and item:
                models.append(item)
    return models, resp


def submit_video_job(
    base_url: str,
    payload: Dict[str, Any],
    api_key: str = "",
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """
    Call `POST /v1/videos` to submit an asynchronous video generation job.
    Transport retries are never performed on POST to avoid duplicate job submissions.
    """
    norm_base = normalize_base_url(base_url)
    url = f"{norm_base}/videos"
    return _request_json("POST", url, api_key=api_key, payload=payload, timeout=timeout)


def get_video_job(
    base_url: str,
    job_id: str,
    api_key: str = "",
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """
    Call `GET /v1/videos/{job_id}` to retrieve job status and metadata.
    """
    norm_base = normalize_base_url(base_url)
    encoded_id = urllib.parse.quote(str(job_id), safe="")
    url = f"{norm_base}/videos/{encoded_id}"
    return _request_json("GET", url, api_key=api_key, timeout=timeout)


def extract_job_error(job_data: Dict[str, Any]) -> str:
    """Extract a readable error description from a failed FastVideo job resource."""
    err = job_data.get("error")
    if isinstance(err, dict):
        msg = err.get("message") or err.get("code") or err.get("type")
        param = err.get("param")
        code = err.get("code")
        parts = [str(msg)] if msg else []
        if param:
            parts.append(f"param={param}")
        if code and str(code) != str(msg):
            parts.append(f"code={code}")
        if parts:
            return " ".join(parts)
    elif isinstance(err, str) and err.strip():
        return err.strip()

    for key in ("failure_reason", "message", "detail"):
        val = job_data.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()

    return "Unknown generation failure on FastVideo server"


def _interruptible_sleep(seconds: float, check_interrupted: Optional[Callable[[], None]] = None) -> None:
    """Sleep for `seconds` while checking ComfyUI interruption every 0.25s without network calls."""
    end_time = time.monotonic() + max(0.0, seconds)
    while time.monotonic() < end_time:
        if check_interrupted is not None:
            check_interrupted()
        remaining = end_time - time.monotonic()
        if remaining > 0:
            time.sleep(min(0.25, remaining))


def poll_video_job(
    base_url: str,
    job_id: str,
    *,
    initial_job: Optional[Dict[str, Any]] = None,
    api_key: str = "",
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    poll_timeout: float = DEFAULT_POLL_TIMEOUT,
    on_status: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    check_interrupted: Optional[Callable[[], None]] = None,
) -> Dict[str, Any]:
    """
    Poll `GET /v1/videos/{job_id}` until status is `completed` or `failed`.
    Matches FastVideo's official OpenAI client polling pattern:
    sleeps BEFORE each `retrieve` call so the server is never hammered immediately
    after job creation or flooded with tight-loop requests.
    """
    start_time = time.monotonic()
    deadline = start_time + poll_timeout if poll_timeout > 0 else float("inf")
    interval = max(2.0, float(poll_interval))

    job_data: Dict[str, Any] = dict(initial_job) if initial_job else {"id": job_id, "status": "queued"}
    status = str(job_data.get("status") or "queued").lower()

    if on_status is not None:
        on_status(status, job_data)

    consecutive_conn_errors = 0
    max_conn_retries = 3

    while status in ("queued", "in_progress", "running", "processing"):
        if check_interrupted is not None:
            check_interrupted()

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise FastVideoPollTimeoutError(job_id, status, time.monotonic() - start_time)

        # Always sleep BEFORE polling GET /v1/videos/{job_id}
        _interruptible_sleep(min(interval, remaining), check_interrupted=check_interrupted)

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise FastVideoPollTimeoutError(job_id, status, time.monotonic() - start_time)

        try:
            job_data = get_video_job(
                base_url,
                job_id,
                api_key=api_key,
                timeout=min(60.0, max(5.0, remaining)),
            )
            consecutive_conn_errors = 0
        except FastVideoHTTPError:
            raise
        except Exception as conn_err:
            consecutive_conn_errors += 1
            if consecutive_conn_errors > max_conn_retries:
                raise RuntimeError(
                    f"FastVideo server at {normalize_base_url(base_url)} stopped responding while executing "
                    f"job '{job_id}' ({conn_err}). The remote FastVideo server process likely crashed during "
                    f"GPU generation (e.g. Out-Of-Memory or worker error). Check the FastVideo server logs."
                ) from None
            _interruptible_sleep(3.0, check_interrupted=check_interrupted)
            continue

        status = str(job_data.get("status") or "queued").lower()
        if on_status is not None:
            on_status(status, job_data)

    if status == "completed":
        return job_data

    error_detail = extract_job_error(job_data)
    raise FastVideoJobFailedError(job_id, error_detail, job_data=job_data)


def download_video_content(
    base_url: str,
    job_id: str,
    api_key: str = "",
    timeout: float = 300.0,
) -> bytes:
    """
    Call `GET /v1/videos/{job_id}/content` to download the completed MP4 bytes.
    """
    norm_base = normalize_base_url(base_url)
    encoded_id = urllib.parse.quote(str(job_id), safe="")
    url = f"{norm_base}/videos/{encoded_id}/content"
    mp4_bytes, _ = _request_bytes("GET", url, api_key=api_key, timeout=timeout)
    return mp4_bytes


def generate_video_sync(
    base_url: str,
    payload: Dict[str, Any],
    api_key: str = "",
    timeout: float = 1800.0,
) -> Tuple[bytes, str]:
    """
    Call `POST /v1/videos/sync` to generate and download the MP4 in a single synchronous request
    with zero polling requests. Returns `(mp4_bytes, request_id)`.
    """
    norm_base = normalize_base_url(base_url)
    url = f"{norm_base}/videos/sync"
    mp4_bytes, headers = _request_bytes("POST", url, api_key=api_key, payload=payload, timeout=timeout)
    request_id = headers.get("x-request-id", "video_sync")
    return mp4_bytes, request_id
