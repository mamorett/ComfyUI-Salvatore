"""
Salvatore Nodes - Numbers
Integer and resolution manipulation nodes.
"""


class SalvatoreSeedToNumber:
    """Convert seed to integer."""
    
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("SEED",),
            }
        }

    RETURN_TYPES = ("INT",)
    FUNCTION = "number_to_seed"
    CATEGORY = "Salvatore Nodes/numbers"

    def number_to_seed(self, seed):
        return (int(seed["seed"]), )


class SalvatoreSeedAndInt:
    """Convert integer to seed format."""
    
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff})
            }
        }

    RETURN_TYPES = ("INT", "SEED",)
    FUNCTION = "seed_and_int"
    CATEGORY = "Salvatore Nodes/numbers"

    def seed_and_int(self, seed):
        return (seed, {"seed": seed})


class SalvatoreSDXLSteps:
    """Set SDXL precondition/base/total steps."""
    
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "precondition": ("INT", {"default": 3, "min": 1, "max": 10000}),
                "base": ("INT", {"default": 12, "min": 1, "max": 10000}),
                "total": ("INT", {"default": 20, "min": 1, "max": 10000}),
            }
        }
    
    RETURN_TYPES = ("INT", "INT", "INT",)
    RETURN_NAMES = ("pre", "base", "total")
    FUNCTION = "set_steps"
    CATEGORY = "Salvatore Nodes/numbers"

    def set_steps(self, precondition, base, total):
        return (precondition, base, total)


class SalvatoreIntMultiply:
    """Multiply two integers."""
    
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "number": ("INT", {"default": 2, "min": 1, "max": 10000, "forceInput": True}),
                "multiplier": ("INT", {"default": 2, "min": 1, "max": 10000}),
            }
        }
    
    RETURN_TYPES = ("INT",)
    FUNCTION = "multiply"
    CATEGORY = "Salvatore Nodes/numbers"

    def multiply(self, number, multiplier):
        result = number * multiplier
        return (int(result),)


class SalvatoreResMultiply:
    """Multiply width and height by a factor."""
    
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "width": ("INT", {"default": 512, "min": 16, "max": 8192, "forceInput": True}),
                "height": ("INT", {"default": 512, "min": 16, "max": 8192, "forceInput": True}),
                "multiplier": ("INT", {"default": 2, "min": 1, "max": 10000}),
            }
        }
    
    RETURN_TYPES = ("INT", "INT",)
    RETURN_NAMES = ("width", "height",)
    FUNCTION = "multiply"
    CATEGORY = "Salvatore Nodes/numbers"

    def multiply(self, width, height, multiplier):
        adj_width = width * multiplier
        adj_height = height * multiplier
        return (int(adj_width), int(adj_height))


class SalvatoreResolutionsByRatio:
    """Generate resolution by aspect ratio and short side."""
    
    aspects = ["1:1", "6:5", "5:4", "4:3", "3:2", "16:10", "16:9", "19:9", "21:9", "43:18", "2:1", "3:1", "4:1"]
    direction = ["landscape", "portrait"]

    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "aspect": (s.aspects,),
                              "direction": (s.direction,),
                              "shortside": ("INT", {"default": 512, "min": 64, "max": 8192, "step": 64})}}
    
    RETURN_TYPES = ("INT", "INT",)
    RETURN_NAMES = ("width", "height",)
    FUNCTION = "get_resolutions"
    CATEGORY = "Salvatore Nodes/numbers"

    def get_resolutions(self, aspect, direction, shortside):
        x, y = aspect.split(':')
        x = int(x)
        y = int(y)
        ratio = x / y
        width = int(shortside * ratio)
        width = (width + 63) & (-64)
        height = shortside
        if direction == "portrait":
            width, height = height, width
        return (width, height)


class SalvatoreSDXLResolutions:
    """SDXL preset resolutions."""
    
    resolution = ["1024x1024|1:1", "1152x896|9:7", "1216x832|19:13", "1344x768|7:4", "1536x640|12:5"]
    direction = ["landscape", "portrait"]

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "resolution": (s.resolution,),
                "direction": (s.direction,),
            }
        }
    
    RETURN_TYPES = ("INT", "INT",)
    RETURN_NAMES = ("width", "height",)
    FUNCTION = "get_resolutions"
    CATEGORY = "Salvatore Nodes/numbers"

    def get_resolutions(self, resolution, direction):
        pixels = resolution.split('|')[0]
        width, height = pixels.split('x')
        width = int(width)
        height = int(height)
        if direction == "portrait":
            width, height = height, width
        return (width, height)


NODE_CLASS_MAPPINGS = {
    "SalvatoreSeedToNumber": SalvatoreSeedToNumber,
    "SalvatoreSeedAndInt": SalvatoreSeedAndInt,
    "SalvatoreSDXLSteps": SalvatoreSDXLSteps,
    "SalvatoreIntMultiply": SalvatoreIntMultiply,
    "SalvatoreResMultiply": SalvatoreResMultiply,
    "SalvatoreResolutionsByRatio": SalvatoreResolutionsByRatio,
    "SalvatoreSDXLResolutions": SalvatoreSDXLResolutions,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SalvatoreSeedToNumber": "Salvatore Seed to Number",
    "SalvatoreSeedAndInt": "Salvatore Seed and Int",
    "SalvatoreSDXLSteps": "Salvatore SDXL Steps",
    "SalvatoreIntMultiply": "Salvatore Multiply Integer",
    "SalvatoreResMultiply": "Salvatore Quick Resolution Multiply",
    "SalvatoreResolutionsByRatio": "Salvatore Resolutions by Ratio",
    "SalvatoreSDXLResolutions": "Salvatore SDXL Resolutions",
}
