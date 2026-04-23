"""
Salvatore Nodes - Latent
Empty latent image generation nodes.
"""
import torch
import numpy as np
import comfy.model_management


MAX_RESOLUTION = 8192


class SalvatoreEmptyLatentImageByResolution:
    """Create empty latent by explicit width and height."""
    
    def __init__(self, device="cpu"):
        self.device = device

    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "width": ("INT", {"default": 512, "min": 16, "max": MAX_RESOLUTION, "step": 8}),
                              "height": ("INT", {"default": 512, "min": 16, "max": MAX_RESOLUTION, "step": 8}),
                              "batch_size": ("INT", {"default": 1, "min": 1, "max": 4096})}}
    
    RETURN_TYPES = ("LATENT", "INT", "INT",)
    RETURN_NAMES = ("latent", "width", "height",)
    FUNCTION = "generate"
    CATEGORY = "Salvatore Nodes/latent"

    def generate(self, width, height, batch_size=1):
        adj_width = width // 8
        adj_height = height // 8
        latent = torch.zeros([batch_size, 4, adj_height, adj_width])
        return ({"samples": latent}, adj_width * 8, adj_height * 8)


class SalvatoreEmptyLatentImageByRatio:
    """Create empty latent by aspect ratio and short side."""
    
    aspects = ["1:1", "6:5", "5:4", "4:3", "3:2", "16:10", "16:9", "19:9", "21:9", "43:18", "2:1", "3:1", "4:1"]
    direction = ["landscape", "portrait"]

    def __init__(self, device="cpu"):
        self.device = device

    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "aspect": (s.aspects,),
                              "direction": (s.direction,),
                              "shortside": ("INT", {"default": 512, "min": 64, "max": MAX_RESOLUTION, "step": 64}),
                              "batch_size": ("INT", {"default": 1, "min": 1, "max": 64})}}
    
    RETURN_TYPES = ("LATENT", "INT", "INT",)
    RETURN_NAMES = ("latent", "width", "height",)
    FUNCTION = "generate"
    CATEGORY = "Salvatore Nodes/latent"

    def generate(self, aspect, direction, shortside, batch_size=1):
        x, y = aspect.split(':')
        x = int(x)
        y = int(y)
        ratio = x / y
        width = int(shortside * ratio)
        width = (width + 63) & (-64)
        height = shortside
        if direction == "portrait":
            width, height = height, width
        adj_width = width // 8
        adj_height = height // 8
        latent = torch.zeros([batch_size, 4, adj_height, adj_width])
        return ({"samples": latent}, adj_width * 8, adj_height * 8)


class SalvatoreEmptyLatentImageByPixels:
    """Create empty latent by aspect ratio and megapixels."""
    
    aspects = ["1:1", "5:4", "4:3", "3:2", "16:10", "16:9", "19:9", "21:9", "43:18", "2:1", "3:1", "4:1"]
    direction = ["landscape", "portrait"]

    def __init__(self, device="cpu"):
        self.device = device

    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "aspect": (s.aspects,),
                              "direction": (s.direction,),
                              "megapixels": ("FLOAT", {"default": 1.0, "min": 0.01, "max": 16.0, "step": 0.01}),
                              "batch_size": ("INT", {"default": 1, "min": 1, "max": 64})}}
    
    RETURN_TYPES = ("LATENT", "INT", "INT",)
    RETURN_NAMES = ("latent", "width", "height",)
    FUNCTION = "generate"
    CATEGORY = "Salvatore Nodes/latent"

    def generate(self, aspect, direction, megapixels, batch_size=1):
        x, y = aspect.split(':')
        x = int(x)
        y = int(y)
        ratio = x / y

        total = int(megapixels * 1024 * 1024)

        width = int(np.sqrt(ratio * total))
        width = (width + 63) & (-64)
        height = int(np.sqrt(1 / ratio * total))
        height = (height + 63) & (-64)
        if direction == "portrait":
            width, height = height, width
        adj_width = width // 8
        adj_height = height // 8
        latent = torch.zeros([batch_size, 4, adj_height, adj_width])
        return ({"samples": latent}, adj_width * 8, adj_height * 8)


class SalvatoreSDXLQuickEmptyLatent:
    """Quick SDXL latent with preset resolutions."""
    
    resolution = ["1024x1024|1:1", "1152x896|9:7", "1216x832|19:13", "1344x768|7:4", "1536x640|12:5"]
    direction = ["landscape", "portrait"]

    def __init__(self, device="cpu"):
        self.device = device

    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "resolution": (s.resolution,),
                              "direction": (s.direction,),
                              "batch_size": ("INT", {"default": 1, "min": 1, "max": 64})}}
    
    RETURN_TYPES = ("LATENT", "INT", "INT",)
    RETURN_NAMES = ("latent", "width", "height",)
    FUNCTION = "generate"
    CATEGORY = "Salvatore Nodes/latent"

    def generate(self, resolution, direction, batch_size=1):
        pixels = resolution.split('|')[0]
        width, height = pixels.split('x')
        width = int(width)
        height = int(height)
        if direction == "portrait":
            width, height = height, width
        adj_width = width // 8
        adj_height = height // 8
        latent = torch.zeros([batch_size, 4, adj_height, adj_width])
        return ({"samples": latent}, adj_width * 8, adj_height * 8)


class SalvatoreSDXLResolutionMultiplier:
    """Multiply existing resolution by a factor."""
    
    def __init__(self, device="cpu"):
        self.device = device

    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "target_width": ("INT", {"default": 512, "min": 16, "max": MAX_RESOLUTION, "step": 8, "forceInput": True}),
                              "target_height": ("INT", {"default": 512, "min": 16, "max": MAX_RESOLUTION, "step": 8, "forceInput": True}),
                              "multiplier": ("INT", {"default": 2, "min": 1, "max": 12})}}
    
    RETURN_TYPES = ("INT", "INT",)
    RETURN_NAMES = ("width", "height",)
    FUNCTION = "multiply_res"
    CATEGORY = "Salvatore Nodes/latent"

    def multiply_res(self, target_width=1024, target_height=1024, multiplier=2):
        return (target_width * 2, target_height * 2)


NODE_CLASS_MAPPINGS = {
    "SalvatoreEmptyLatentImageByResolution": SalvatoreEmptyLatentImageByResolution,
    "SalvatoreEmptyLatentImageByRatio": SalvatoreEmptyLatentImageByRatio,
    "SalvatoreEmptyLatentImageByPixels": SalvatoreEmptyLatentImageByPixels,
    "SalvatoreSDXLQuickEmptyLatent": SalvatoreSDXLQuickEmptyLatent,
    "SalvatoreSDXLResolutionMultiplier": SalvatoreSDXLResolutionMultiplier,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SalvatoreEmptyLatentImageByResolution": "Salvatore Empty Latent by Size",
    "SalvatoreEmptyLatentImageByRatio": "Salvatore Empty Latent by Ratio",
    "SalvatoreEmptyLatentImageByPixels": "Salvatore Empty Latent by Pixels",
    "SalvatoreSDXLQuickEmptyLatent": "Salvatore SDXL Quick Empty Latent",
    "SalvatoreSDXLResolutionMultiplier": "Salvatore SDXL Resolution Multiplier",
}
