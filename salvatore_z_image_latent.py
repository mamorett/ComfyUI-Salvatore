"""
Salvatore Z Image Latent Node
Integrates Z.py functionality for creating empty latents with preset aspect ratios.
"""
import torch
import comfy.model_management


class SalvatoreZImageLatent:
    """Create empty latent images with preset resolutions based on base sizes."""
    
    def __init__(self):
        self.device = comfy.model_management.intermediate_device()

    @classmethod
    def INPUT_TYPES(s):
        aspect_ratios_dict = {
            "1024": [
                "1024x1024 ( 1:1 )", "1152x896 ( 9:7 )", "896x1152 ( 7:9 )",
                "1152x864 ( 4:3 )", "864x1152 ( 3:4 )", "1248x832 ( 3:2 )",
                "832x1248 ( 2:3 )", "1280x720 ( 16:9 )", "720x1280 ( 9:16 )",
                "1344x576 ( 21:9 )", "576x1344 ( 9:21 )",
            ],
            "1280": [
                "1280x1280 ( 1:1 )", "1440x1120 ( 9:7 )", "1120x1440 ( 7:9 )",
                "1472x1104 ( 4:3 )", "1104x1472 ( 3:4 )", "1536x1024 ( 3:2 )",
                "1024x1536 ( 2:3 )", "1536x864 ( 16:9 )", "864x1536 ( 9:16 )",
                "1680x720 ( 21:9 )", "720x1680 ( 9:21 )",
            ],
            "1536": [
                "1536x1536 ( 1:1 )", "1728x1344 ( 9:7 )", "1344x1728 ( 7:9 )",
                "1728x1296 ( 4:3 )", "1296x1728 ( 3:4 )", "1872x1248 ( 3:2 )",
                "1248x1872 ( 2:3 )", "2048x1152 ( 16:9 )", "1152x2048 ( 9:16 )",
                "2016x864 ( 21:9 )", "864x2016 ( 9:21 )",
            ]
        }

        resolution_list = []
        for key in aspect_ratios_dict:
            resolution_list.extend(aspect_ratios_dict[key])

        return {"required": {
            "resolution": (resolution_list, ),
            "batch_size": ("INT", {"default": 1, "min": 1, "max": 64}),
        }}

    RETURN_NAMES = ("Latent", "Width", "Height")
    RETURN_TYPES = ("LATENT", "INT", "INT")
    FUNCTION = "generate"
    CATEGORY = "Salvatore Nodes/latent"

    def generate(self, resolution, batch_size=1):
        dimensions = resolution.split(' ')[0]
        width, height = map(int, dimensions.split('x'))

        # Ensure dimensions are divisible by 16
        width = int((width // 16) * 16)
        height = int((height // 16) * 16)

        latent = torch.zeros([batch_size, 4, height // 8, width // 8], device=self.device)

        return ({"samples": latent}, width, height)


NODE_CLASS_MAPPINGS = {
    "SalvatoreZImageLatent": SalvatoreZImageLatent,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SalvatoreZImageLatent": "Salvatore Z Image Latent",
}
