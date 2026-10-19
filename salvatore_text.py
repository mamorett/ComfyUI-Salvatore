"""
Salvatore Nodes - Text
String manipulation and text processing nodes.
"""
import os
import re
import random
from datetime import datetime

# Import utilities directly from the file
import importlib.util
_utils_spec = importlib.util.spec_from_file_location("salvatore_utils", os.path.join(os.path.dirname(__file__), "salvatore_utils.py"))
salvatore_utils = importlib.util.module_from_spec(_utils_spec)
_utils_spec.loader.exec_module(salvatore_utils)

make_filename = salvatore_utils.make_filename


class SalvatoreTimeString:
    """Generate timestamp string."""
    
    time_format = ["%Y%m%d%H%M%S", "%Y%m%d%H%M", "%Y%m%d", "%Y-%m-%d-%H%M%S", "%Y-%m-%d-%H%M", "%Y-%m-%d"]
    
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "style": (s.time_format,),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("time_format",)
    FUNCTION = "get_time"
    CATEGORY = "Salvatore Nodes/text"

    def get_time(self, style):
        now = datetime.now()
        timestamp = now.strftime(style)
        return (timestamp,)


class SalvatoreSimplePatternReplace:
    """Replace patterns in string with values from a list."""
    
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "input_string": ("STRING", {"multiline": True, "forceInput": True}),
                "list_string": ("STRING", {"default": ''}),
                "pattern": ("STRING", {"default": '$var'}),
                "delimiter": ("STRING", {"default": ','}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("string",)
    FUNCTION = "replace_string"
    CATEGORY = "Salvatore Nodes/text"

    def replace_string(self, input_string, list_string, pattern, delimiter, seed):
        # Escape special characters and strip whitespace from pattern
        pattern = re.escape(pattern).strip()

        # Find all pattern entries from input and create list
        regex = re.compile(pattern)
        matches = regex.findall(input_string)

        # Return input if nothing found
        if not matches:
            return (input_string,)

        if seed is not None:
            random.seed(seed)

        # If provided delimiter not present in input, will try to use whole list
        if delimiter not in list_string:
            raise ValueError("Delimiter not found in list_string")

        # If pattern appears more than once each entry will have a different random choice
        def replace(match):
            return random.choice(list_string.split(delimiter))

        new_string = regex.sub(replace, input_string)

        return (new_string,)


class SalvatoreStringAppend:
    """Append or prepend string with optional separator."""
    
    location = ["after", "before"]
    separator = ["comma", "space", "newline", "none"]

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "addition": ("STRING", {"multiline": True}),
                "placement": (s.location,),
                "separator": (s.separator,),
            },
            "optional": {
                "input_string": ("STRING", {"multiline": True, "forceInput": True}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("combined",)
    FUNCTION = "concat_string"
    CATEGORY = "Salvatore Nodes/text"

    def concat_string(self, placement, separator, addition="", input_string=""):
        sep = {"comma": ', ', "space": ' ', "newline": '\n', "none": ''}

        if input_string is None:
            return (addition,)

        if placement == "after":
            new_string = input_string + sep[separator] + addition
        else:
            new_string = addition + sep[separator] + input_string

        return (new_string,)


class SalvatorePromptWeight:
    """Add weight to prompt text."""
    
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "forceInput": True}),
                "weight": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 5.0, "step": 0.1}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    FUNCTION = "add_weight"
    CATEGORY = "Salvatore Nodes/text"

    def add_weight(self, prompt, weight):
        if weight == 1.0:
            new_string = prompt
        else:
            new_string = "(" + prompt + ":" + str(weight) + ")"

        return (new_string,)


class _SalvatoreAnyType(str):
    """Wildcard type that matches any ComfyUI socket type."""
    def __ne__(self, __value: object) -> bool:
        return False


ANY_TYPE = _SalvatoreAnyType("*")

# Store pending confirmation states keyed by node unique_id
_PENDING_CONFIRMATIONS = {}
_CONFIRM_LOCK = None

try:
    import threading
    _CONFIRM_LOCK = threading.Lock()
except ImportError:
    pass


def _register_confirm_routes():
    """Register PromptServer HTTP routes for the Salvatore Text Box confirm button."""
    try:
        from server import PromptServer
        from aiohttp import web

        if PromptServer.instance is None:
            return

        @PromptServer.instance.routes.post("/salvatore/text_confirm")
        async def salvatore_text_confirm(request):
            try:
                data = await request.json()
            except Exception as e:
                return web.json_response({"status": "error", "message": str(e)}, status=400)

            node_id = str(data.get("node_id", ""))
            confirmed_text = data.get("text", "")
            action = data.get("action", "confirm")

            if _CONFIRM_LOCK is not None:
                with _CONFIRM_LOCK:
                    entry = _PENDING_CONFIRMATIONS.get(node_id)
                    if entry is not None:
                        entry["text"] = confirmed_text
                        entry["action"] = action
                        entry["event"].set()
                        return web.json_response({"status": "ok", "node_id": node_id})

            return web.json_response({"status": "not_waiting", "node_id": node_id})

    except Exception:
        # PromptServer may not be initialized when importing outside ComfyUI runtime
        pass


_register_confirm_routes()


class SalvatoreTextBox:
    """
    Editable text box node that accepts any text as input, optionally renders Markdown,
    and optionally displays a Confirm ('Go') button that pauses execution until pressed.
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"default": "", "multiline": False}),
                "render_markdown": ("BOOLEAN", {"default": False}),
                "wait_for_confirmation": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "input_text": (ANY_TYPE, {"forceInput": True}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "process_text"
    OUTPUT_NODE = True
    CATEGORY = "Salvatore Nodes/text"

    @classmethod
    def IS_CHANGED(s, text="", render_markdown=False, wait_for_confirmation=False, input_text=None, unique_id=None):
        if wait_for_confirmation:
            return float("nan")
        return (text, render_markdown, wait_for_confirmation, str(input_text))

    @staticmethod
    def _to_text(val):
        if val is None:
            return ""
        if isinstance(val, str):
            return val
        if isinstance(val, (dict, list, tuple)):
            try:
                import json
                return json.dumps(val, indent=2, ensure_ascii=False)
            except Exception:
                return str(val)
        return str(val)

    @staticmethod
    def _send_ws_update(node_id, text, waiting, render_markdown):
        try:
            from server import PromptServer
            if PromptServer.instance is not None:
                PromptServer.instance.send_sync(
                    "salvatore.text_box.update",
                    {
                        "node_id": str(node_id),
                        "text": text,
                        "waiting": bool(waiting),
                        "render_markdown": bool(render_markdown),
                    },
                )
        except Exception:
            pass

    def process_text(self, text="", render_markdown=False, wait_for_confirmation=False, input_text=None, unique_id=None):
        import threading
        import time

        node_id = str(unique_id) if unique_id is not None else ""

        # If input_text is connected, show it in the text box; otherwise use the text box's own value
        if input_text is not None:
            current_text = self._to_text(input_text)
        else:
            current_text = self._to_text(text)

        if not wait_for_confirmation or not node_id:
            self._send_ws_update(node_id, current_text, False, render_markdown)
            return {"ui": {"text": [current_text]}, "result": (current_text,)}

        # Pause and wait for the user to press the Confirm ("Go") button
        event = threading.Event()
        entry = {
            "event": event,
            "text": current_text,
            "action": "confirm",
        }
        with _CONFIRM_LOCK:
            _PENDING_CONFIRMATIONS[node_id] = entry

        self._send_ws_update(node_id, current_text, True, render_markdown)

        try:
            import comfy.model_management as model_management
        except Exception:
            model_management = None

        try:
            while not event.is_set():
                if model_management is not None:
                    model_management.throw_exception_if_processing_interrupted()
                event.wait(timeout=0.1)
        except Exception:
            with _CONFIRM_LOCK:
                _PENDING_CONFIRMATIONS.pop(node_id, None)
            self._send_ws_update(node_id, current_text, False, render_markdown)
            raise

        with _CONFIRM_LOCK:
            finished_entry = _PENDING_CONFIRMATIONS.pop(node_id, entry)

        final_text = self._to_text(finished_entry.get("text", current_text))
        self._send_ws_update(node_id, final_text, False, render_markdown)

        return {"ui": {"text": [final_text]}, "result": (final_text,)}


NODE_CLASS_MAPPINGS = {
    "SalvatoreTimeString": SalvatoreTimeString,
    "SalvatoreSimplePatternReplace": SalvatoreSimplePatternReplace,
    "SalvatoreStringAppend": SalvatoreStringAppend,
    "SalvatorePromptWeight": SalvatorePromptWeight,
    "SalvatoreTextBox": SalvatoreTextBox,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SalvatoreTimeString": "Salvatore Time String",
    "SalvatoreSimplePatternReplace": "Salvatore Simple Pattern Replace",
    "SalvatoreStringAppend": "Salvatore Simple String Combine",
    "SalvatorePromptWeight": "Salvatore Prompt Weight",
    "SalvatoreTextBox": "Salvatore Text Box",
}

