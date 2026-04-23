"""
Salvatore Nodes - Inpainting
Inpainting and mask generation nodes.
"""
import os
import numpy as np
import torch
from PIL import Image, ImageOps, ImageFilter

# Import utilities directly from the file
import importlib.util
_utils_spec = importlib.util.spec_from_file_location("salvatore_utils", os.path.join(os.path.dirname(__file__), "salvatore_utils.py"))
salvatore_utils = importlib.util.module_from_spec(_utils_spec)
_utils_spec.loader.exec_module(salvatore_utils)

tensor2pil = salvatore_utils.tensor2pil
pil2tensor = salvatore_utils.pil2tensor


class SalvatoreOutpaintToImage:
    """Outpaint image by adding transparent border."""
    
    directions = ["left", "right", "up", "down"]

    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "image": ("IMAGE",),
                              "direction": (s.directions,),
                              "pixels": ("INT", {"default": 128, "min": 32, "max": 512, "step": 32}),
                              "mask_padding": ("INT", {"default": 12, "min": 0, "max": 64, "step": 4})
                              }}
    
    RETURN_TYPES = ("IMAGE", "MASK")
    FUNCTION = "outpaint"
    CATEGORY = "Salvatore Nodes/inpainting"

    def convert_image(self, im, direction, mask_padding):
        width, height = im.size
        im = im.convert("RGBA")
        alpha = Image.new('L', (width, height), 255)
        im.putalpha(alpha)
        return im

    def outpaint(self, image, direction, mask_padding, pixels):
        image = tensor2pil(image)
        image = self.convert_image(image, direction, mask_padding)
        
        if direction == "right":
            border = (0, 0, pixels, 0)
            new_image = ImageOps.expand(image, border=border, fill=(0, 0, 0, 0))
        elif direction == "left":
            border = (pixels, 0, 0, 0)
            new_image = ImageOps.expand(image, border=border, fill=(0, 0, 0, 0))
        elif direction == "up":
            border = (0, pixels, 0, 0)
            new_image = ImageOps.expand(image, border=border, fill=(0, 0, 0, 0))
        elif direction == "down":
            border = (0, 0, 0, pixels)
            new_image = ImageOps.expand(image, border=border, fill=(0, 0, 0, 0))

        image = new_image.convert("RGB")
        image = np.array(image).astype(np.float32) / 255.0
        image = torch.from_numpy(image)[None,]
        
        if 'A' in new_image.getbands():
            mask = np.array(new_image.getchannel('A')).astype(np.float32) / 255.0
            mask = 1. - torch.from_numpy(mask)
        else:
            mask = torch.zeros((64, 64), dtype=torch.float32, device="cpu")

        return (image, mask)


class SalvatoreVAEEncodeForInpaintPadding:
    """Encode image for inpainting with mask padding."""
    
    def __init__(self, device="cpu"):
        self.device = device

    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "pixels": ("IMAGE", ), "vae": ("VAE", ), "mask": ("MASK", ),
                              "mask_padding": ("INT", {"default": 24, "min": 6, "max": 128, "step": 2})}}
    
    RETURN_TYPES = ("LATENT",)
    FUNCTION = "encode"
    CATEGORY = "Salvatore Nodes/inpainting"

    def encode(self, vae, pixels, mask, mask_padding=3):
        x = (pixels.shape[1] // 64) * 64
        y = (pixels.shape[2] // 64) * 64
        mask = torch.nn.functional.interpolate(mask[None, None,], size=(pixels.shape[1], pixels.shape[2]), 
                                              mode="bilinear")[0][0]

        pixels = pixels.clone()
        if pixels.shape[1] != x or pixels.shape[2] != y:
            pixels = pixels[:, :x, :y, :]
            mask = mask[:x, :y]

        # Grow mask by a few pixels to keep things seamless in latent space
        kernel_tensor = torch.ones((1, 1, mask_padding, mask_padding))
        mask_erosion = torch.clamp(torch.nn.functional.conv2d((mask.round())[None], kernel_tensor, padding=3), 0, 1)
        m = (1.0 - mask.round())
        
        for i in range(3):
            pixels[:, :, :, i] -= 0.5
            pixels[:, :, :, i] *= m
            pixels[:, :, :, i] += 0.5
        
        t = vae.encode(pixels)

        return ({"samples": t, "noise_mask": (mask_erosion[0][:x, :y].round())}, )


class SalvatoreGenerateEdgeMask:
    """Generate edge mask for outpainting."""
    
    directions = ["left", "right", "up", "down"]

    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "image": ("IMAGE",),
                              "direction": (s.directions,),
                              "pixels": ("INT", {"default": 128, "min": 32, "max": 512, "step": 32}),
                              "overlap": ("INT", {"default": 64, "min": 16, "max": 256, "step": 16})
                              }}
    
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "gen_second_mask"
    CATEGORY = "Salvatore Nodes/inpainting"

    def gen_second_mask(self, direction, image, pixels, overlap):
        image = tensor2pil(image)
        new_width, new_height = image.size

        # Generate new image fully un-masked
        mask2 = Image.new('RGBA', (new_width, new_height), (0, 0, 0, 255))
        mask_thickness = overlap
        
        if direction == "up":
            # Horizontal mask width of new image and height of 1/4 padding
            new_mask = Image.new('RGBA', (new_width, mask_thickness), (0, 122, 0, 255))
            mask2.paste(new_mask, (0, (pixels - int(mask_thickness / 2))))
        elif direction == "down":
            # Horizontal mask width of new image and height of 1/4 padding
            new_mask = Image.new('RGBA', (new_width, mask_thickness), (0, 122, 0, 255))
            mask2.paste(new_mask, (0, new_height - pixels - int(mask_thickness / 2)))
        elif direction == "left":
            # Vertical mask height of new image and width of 1/4 padding
            new_mask = Image.new('RGBA', (mask_thickness, new_height), (0, 122, 0, 255))
            mask2.paste(new_mask, (pixels - int(mask_thickness / 2), 0))
        elif direction == "right":
            # Vertical mask height of new image and width of 1/4 padding
            new_mask = Image.new('RGBA', (mask_thickness, new_height), (0, 122, 0, 255))
            mask2.paste(new_mask, (new_width - pixels - int(mask_thickness / 2), 0))
        
        mask2 = mask2.filter(ImageFilter.GaussianBlur(radius=5))
        mask2 = np.array(mask2).astype(np.float32) / 255.0
        mask2 = torch.from_numpy(mask2)[None,]
        
        return (mask2,)


NODE_CLASS_MAPPINGS = {
    "SalvatoreOutpaintToImage": SalvatoreOutpaintToImage,
    "SalvatoreVAEEncodeForInpaintPadding": SalvatoreVAEEncodeForInpaintPadding,
    "SalvatoreGenerateEdgeMask": SalvatoreGenerateEdgeMask,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SalvatoreOutpaintToImage": "Salvatore Outpaint to Image",
    "SalvatoreVAEEncodeForInpaintPadding": "Salvatore VAE Encode for Inpaint w/Padding",
    "SalvatoreGenerateEdgeMask": "Salvatore Generate Border Mask",
}
