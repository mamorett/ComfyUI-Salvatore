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


NODE_CLASS_MAPPINGS = {
    "SalvatoreTimeString": SalvatoreTimeString,
    "SalvatoreSimplePatternReplace": SalvatoreSimplePatternReplace,
    "SalvatoreStringAppend": SalvatoreStringAppend,
    "SalvatorePromptWeight": SalvatorePromptWeight,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SalvatoreTimeString": "Salvatore Time String",
    "SalvatoreSimplePatternReplace": "Salvatore Simple Pattern Replace",
    "SalvatoreStringAppend": "Salvatore Simple String Combine",
    "SalvatorePromptWeight": "Salvatore Prompt Weight",
}
