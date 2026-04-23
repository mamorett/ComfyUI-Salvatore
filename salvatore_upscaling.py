"""
Salvatore Nodes - Upscaling
Image upscaling nodes.
"""
import os
import comfy.model_management
import comfy.utils

# Import utilities directly from the file
import importlib.util
_utils_spec = importlib.util.spec_from_file_location("salvatore_utils", os.path.join(os.path.dirname(__file__), "salvatore_utils.py"))
salvatore_utils = importlib.util.module_from_spec(_utils_spec)
_utils_spec.loader.exec_module(salvatore_utils)

tensor2pil = salvatore_utils.tensor2pil
pil2tensor = salvatore_utils.pil2tensor


class SalvatoreImageScaleByFactor:
    """Scale image by a factor."""
    
    upscale_methods = ["nearest-exact", "bilinear", "area"]

    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "original": ("IMAGE",),
                              "upscale_method": (s.upscale_methods,),
                              "factor": ("FLOAT", {"default": 2.0, "min": 0.1, "max": 8.0, "step": 0.1})
                              }}
    
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "upscale"
    CATEGORY = "Salvatore Nodes/upscaling"

    def upscale(self, original, upscale_method, factor):
        old_width = original.shape[2]
        old_height = original.shape[1]
        new_width = int(old_width * factor)
        new_height = int(old_height * factor)
        print(f"Processing image with shape: {old_width}x{old_height} to {new_width}x{new_height}")
        
        samples = original.movedim(-1, 1)
        s = comfy.utils.common_upscale(samples, new_width, new_height, upscale_method, crop="disabled")
        s = s.movedim(1, -1)
        
        return (s,)


class SalvatoreImageScaleByShortside:
    """Scale image to match short side dimension."""
    
    upscale_methods = ["nearest-exact", "bilinear", "area"]

    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "original": ("IMAGE",),
                              "upscale_method": (s.upscale_methods,),
                              "shortside": ("INT", {"default": 512, "min": 32, "max": 4096, "step": 32})
                              }}
    
    RETURN_TYPES = ("IMAGE", "INT", "INT",)
    RETURN_NAMES = ("IMAGE", "width", "height",)
    FUNCTION = "upscale"
    CATEGORY = "Salvatore Nodes/upscaling"

    def upscale(self, original, upscale_method, shortside):
        old_width = original.shape[2]
        old_height = original.shape[1]
        old_shortside = min(old_width, old_height)
        factor = shortside / max(1, old_shortside)
        new_width = int(old_width * factor)
        new_height = int(old_height * factor)
        
        print(f"Processing image with shape: {old_width}x{old_height} to {new_width}x{new_height}")
        
        samples = original.movedim(-1, 1)
        s = comfy.utils.common_upscale(samples, new_width, new_height, upscale_method, crop="disabled")
        s = s.movedim(1, -1)
        
        return (s, new_width, new_height)


class SalvatoreSDXLQuickImageScale:
    """Quick SDXL image scaling with preset resolutions."""
    
    upscale_methods = ["nearest-exact", "bilinear", "area"]
    resolution = ["1024x1024|1:1", "1152x896|9:7", "1216x832|19:13", "1344x768|7:4", "1536x640|12:5"]
    direction = ["landscape", "portrait"]
    crop_methods = ["disabled", "center"]
    
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "original": ("IMAGE",),
                              "upscale_method": (s.upscale_methods,),
                              "resolution": (s.resolution,),
                              "direction": (s.direction,),
                              "crop": (s.crop_methods,),
                              }}
    
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "upscale"
    CATEGORY = "Salvatore Nodes/upscaling"

    def upscale(self, original, upscale_method, resolution, direction, crop):
        pixels = resolution.split('|')[0]
        width, height = pixels.split('x')
        new_width = int(width)
        new_height = int(height)
        if direction == "portrait":
            new_width, new_height = new_height, new_width
        
        old_width = original.shape[2]
        old_height = original.shape[1]
        
        samples = original.movedim(-1, 1)
        s = comfy.utils.common_upscale(samples, new_width, new_height, upscale_method, crop)
        s = s.movedim(1, -1)
        
        return (s,)


class SalvatoreUpscaleByFactorWithModel:
    """Upscale image using upscaling model."""
    
    upscale_methods = ["nearest-exact", "bilinear", "area"]

    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "upscale_model": ("UPSCALE_MODEL",), "image": ("IMAGE",),
                              "upscale_method": (s.upscale_methods,),
                              "factor": ("FLOAT", {"default": 2.0, "min": 0.1, "max": 8.0, "step": 0.1})
                              }}
    
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "upscale"
    CATEGORY = "Salvatore Nodes/upscaling"

    def upscale(self, image, upscale_model, upscale_method, factor):
        # Upscale image using upscaling model
        device = comfy.model_management.get_torch_device()
        upscale_model.to(device)
        in_img = image.movedim(-1, -3).to(device)
        
        s = comfy.utils.tiled_scale(
            in_img, 
            lambda a: upscale_model(a), 
            tile_x=128 + 64, 
            tile_y=128 + 64, 
            overlap=8, 
            upscale_amount=upscale_model.scale
        )
        
        upscale_model.cpu()
        upscaled = torch.clamp(s.movedim(-3, -1), min=0, max=1.0)

        # Get dimensions of original image
        old_width = image.shape[2]
        old_height = image.shape[1]

        # Scale dimensions by provided factor
        new_width = int(old_width * factor)
        new_height = int(old_height * factor)
        
        print(f"Processing image with shape: {old_width}x{old_height} to {new_width}x{new_height}")

        # Apply simple scaling to image
        samples = upscaled.movedim(-1, 1)
        s = comfy.utils.common_upscale(samples, new_width, new_height, upscale_method, crop="disabled")
        s = s.movedim(1, -1)

        return (s,)


NODE_CLASS_MAPPINGS = {
    "SalvatoreImageScaleByFactor": SalvatoreImageScaleByFactor,
    "SalvatoreImageScaleByShortside": SalvatoreImageScaleByShortside,
    "SalvatoreSDXLQuickImageScale": SalvatoreSDXLQuickImageScale,
    "SalvatoreUpscaleByFactorWithModel": SalvatoreUpscaleByFactorWithModel,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SalvatoreImageScaleByFactor": "Salvatore Image Scale By Factor",
    "SalvatoreImageScaleByShortside": "Salvatore Image Scale by Shortside",
    "SalvatoreSDXLQuickImageScale": "Salvatore SDXL Quick Image Scale",
    "SalvatoreUpscaleByFactorWithModel": "Salvatore Upscale by Factor with Model",
}
