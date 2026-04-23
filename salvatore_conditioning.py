"""
Salvatore Nodes - Conditioning
CLIP encoding and prompt conditioning nodes.
"""
import comfy.samplers
from nodes import common_ksampler
import re
import folder_paths


class SalvatoreCLIPPositiveNegative:
    """Encode positive and negative prompts from text."""
    
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "clip": ("CLIP", ),
            "positive_text": ("STRING", {"default": '', "multiline": True}),
            "negative_text": ("STRING", {"default": '', "multiline": True})
            }}
    
    RETURN_TYPES = ("CONDITIONING", "CONDITIONING",)
    RETURN_NAMES = ("positive", "negative",)
    FUNCTION = "encode"
    CATEGORY = "Salvatore Nodes/conditioning"

    def encode(self, clip, positive_text, negative_text):
        return ([[clip.encode(positive_text), {}]], [[clip.encode(negative_text), {}]] )


class SalvatoreCLIPTextPositiveNegative:
    """Encode positive and negative prompts and return text as well."""
    
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"positive": ("STRING", {"multiline": True}),
             "negative": ("STRING", {"multiline": True}),
             "clip": ("CLIP", )}}
    
    RETURN_TYPES = ("CONDITIONING", "CONDITIONING", "STRING", "STRING")
    RETURN_NAMES = ("positive", "negative", "positive_text", "negative_text")
    FUNCTION = "encode"
    CATEGORY = "Salvatore Nodes/conditioning"

    def encode(self, clip, positive, negative):
        return ([[clip.encode(positive), {}]], [[clip.encode(negative), {}]], positive, negative)


class SalvatoreCLIPPositiveNegativeXL:
    """SDXL-compatible CLIP encoding with crop/target coordinates."""
    
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "width": ("INT", {"default": 1024.0, "min": 0, "max": 8192}),
            "height": ("INT", {"default": 1024.0, "min": 0, "max": 8192}),
            "crop_w": ("INT", {"default": 0, "min": 0, "max": 8192}),
            "crop_h": ("INT", {"default": 0, "min": 0, "max": 8192}),
            "target_width": ("INT", {"default": 1024.0, "min": 0, "max": 8192}),
            "target_height": ("INT", {"default": 1024.0, "min": 0, "max": 8192}),
            "positive_g": ("STRING", {"multiline": True, "default": "POS_G"}),
            "positive_l": ("STRING", {"multiline": True, "default": "POS_L"}),
            "negative_g": ("STRING", {"multiline": True, "default": "NEG_G"}),
            "negative_l": ("STRING", {"multiline": True, "default": "NEG_L"}),
            "clip": ("CLIP", ),
            }}

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING",)
    RETURN_NAMES = ("positive", "negative",)
    FUNCTION = "encode"
    CATEGORY = "Salvatore Nodes/conditioning"

    def encode(self, clip, width, height, crop_w, crop_h, target_width, target_height, 
               positive_g, positive_l, negative_g, negative_l):
        tokens = clip.tokenize(positive_g)
        tokens["l"] = clip.tokenize(positive_l)["l"]
        if len(tokens["l"]) != len(tokens["g"]):
            empty = clip.tokenize("")
            while len(tokens["l"]) < len(tokens["g"]):
                tokens["l"] += empty["l"]
            while len(tokens["l"]) > len(tokens["g"]):
                tokens["g"] += empty["g"]
        condP, pooledP = clip.encode_from_tokens(tokens, return_pooled=True)
        
        tokensN = clip.tokenize(negative_g)
        tokensN["l"] = clip.tokenize(negative_l)["l"]
        if len(tokensN["l"]) != len(tokensN["g"]):
            empty = clip.tokenize("")
            while len(tokensN["l"]) < len(tokensN["g"]):
                tokensN["l"] += empty["l"]
            while len(tokensN["l"]) > len(tokensN["g"]):
                tokensN["g"] += empty["g"]
        condN, pooledN = clip.encode_from_tokens(tokensN, return_pooled=True)
        
        return ([[condP, {"pooled_output": pooledP, "width": width, "height": height, 
                          "crop_w": crop_w, "crop_h": crop_h, "target_width": target_width, 
                          "target_height": target_height}]],
                [[condN, {"pooled_output": pooledP, "width": width, "height": height, 
                          "crop_w": crop_w, "crop_h": crop_h, "target_width": target_width, 
                          "target_height": target_height}]])


class SalvatoreCLIPTextPositiveNegativeXL:
    """SDXL-compatible CLIP encoding with text output."""
    
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "width": ("INT", {"default": 1024.0, "min": 0, "max": 8192}),
            "height": ("INT", {"default": 1024.0, "min": 0, "max": 8192}),
            "crop_w": ("INT", {"default": 0, "min": 0, "max": 8192}),
            "crop_h": ("INT", {"default": 0, "min": 0, "max": 8192}),
            "target_width": ("INT", {"default": 1024.0, "min": 0, "max": 8192}),
            "target_height": ("INT", {"default": 1024.0, "min": 0, "max": 8192}),
            "positive_g": ("STRING", {"multiline": True, "default": "POS_G"}),
            "positive_l": ("STRING", {"multiline": True, "default": "POS_L"}),
            "negative_g": ("STRING", {"multiline": True, "default": "NEG_G"}),
            "negative_l": ("STRING", {"multiline": True, "default": "NEG_L"}),
            "clip": ("CLIP", ),
            }}

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING", "STRING", "STRING")
    RETURN_NAMES = ("positive", "negative", "positive_text", "negative_text")
    FUNCTION = "encode"
    CATEGORY = "Salvatore Nodes/conditioning"

    def encode(self, clip, width, height, crop_w, crop_h, target_width, target_height, 
               positive_g, positive_l, negative_g, negative_l):
        tokens = clip.tokenize(positive_g)
        tokens["l"] = clip.tokenize(positive_l)["l"]
        if len(tokens["l"]) != len(tokens["g"]):
            empty = clip.tokenize("")
            while len(tokens["l"]) < len(tokens["g"]):
                tokens["l"] += empty["l"]
            while len(tokens["l"]) > len(tokens["g"]):
                tokens["g"] += empty["g"]
        condP, pooledP = clip.encode_from_tokens(tokens, return_pooled=True)
        
        tokensN = clip.tokenize(negative_g)
        tokensN["l"] = clip.tokenize(negative_l)["l"]
        if len(tokensN["l"]) != len(tokensN["g"]):
            empty = clip.tokenize("")
            while len(tokensN["l"]) < len(tokensN["g"]):
                tokensN["l"] += empty["l"]
            while len(tokensN["l"]) > len(tokensN["g"]):
                tokensN["g"] += empty["g"]
        condN, pooledN = clip.encode_from_tokens(tokensN, return_pooled=True)

        positive_text = positive_g + ", " + positive_l
        negative_text = negative_g + ", " + negative_l
        
        return ([[condP, {"pooled_output": pooledP, "width": width, "height": height, 
                          "crop_w": crop_w, "crop_h": crop_h, "target_width": target_width, 
                          "target_height": target_height}]],
                [[condN, {"pooled_output": pooledP, "width": width, "height": height, 
                          "crop_w": crop_w, "crop_h": crop_h, "target_width": target_width, 
                          "target_height": target_height}]], 
                positive_text, negative_text)


class SalvatoreCLIPTextUnified:
    """Unified CLIP text encoder supporting SD1.5 and SDXL."""
    
    conditioners = ["SD1.5", "SDXL"]
    
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "positive": ("STRING", {"multiline": True, "default": ""}),
            "negative": ("STRING", {"multiline": True, "default": ""}),
            "clip": ("CLIP", ),
            "conditioner": (s.conditioners,),
            },
            "optional": {
                "width": ("INT", {"default": 1024.0, "min": 0, "max": 8192}),
                "height": ("INT", {"default": 1024.0, "min": 0, "max": 8192}),
            }}

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING", "STRING", "STRING")
    RETURN_NAMES = ("positive", "negative", "positive_text", "negative_text")
    FUNCTION = "encode"
    CATEGORY = "Salvatore Nodes/conditioning"

    def encode(self, clip, positive, negative, conditioner, width=1024, height=1024):
        if conditioner == "SDXL":
            # Double height for target
            target_width = 2 * width
            target_height = 2 * height

            # No crop
            crop_w = 0
            crop_h = 0

            # Duplicate pos_g as pos_l
            tokens = clip.tokenize(positive)
            tokens["l"] = clip.tokenize(positive)["l"]
            if len(tokens["l"]) != len(tokens["g"]):
                empty = clip.tokenize("")
                while len(tokens["l"]) < len(tokens["g"]):
                    tokens["l"] += empty["l"]
                while len(tokens["l"]) > len(tokens["g"]):
                    tokens["g"] += empty["g"]
            condP, pooledP = clip.encode_from_tokens(tokens, return_pooled=True)

            # Duplicate neg_g as neg_l
            tokensN = clip.tokenize(negative)
            tokensN["l"] = clip.tokenize(negative)["l"]
            if len(tokensN["l"]) != len(tokensN["g"]):
                empty = clip.tokenize("")
                while len(tokensN["l"]) < len(tokensN["g"]):
                    tokensN["l"] += empty["l"]
                while len(tokensN["l"]) > len(tokensN["g"]):
                    tokensN["g"] += empty["g"]
            condN, pooledN = clip.encode_from_tokens(tokensN, return_pooled=True)

            positive_text = positive
            negative_text = negative
            
            return ([[condP, {"pooled_output": pooledP, "width": width, "height": height, 
                              "crop_w": crop_w, "crop_h": crop_h, "target_width": target_width, 
                              "target_height": target_height}]],
                    [[condN, {"pooled_output": pooledP, "width": width, "height": height, 
                              "crop_w": crop_w, "crop_h": crop_h, "target_width": target_width, 
                              "target_height": target_height}]], 
                    positive_text, negative_text)
        elif conditioner == "SD1.5":
            return ([[clip.encode(positive), {}]], [[clip.encode(negative), {}]], positive, negative)


NODE_CLASS_MAPPINGS = {
    "SalvatoreCLIPPositiveNegative": SalvatoreCLIPPositiveNegative,
    "SalvatoreCLIPTextPositiveNegative": SalvatoreCLIPTextPositiveNegative,
    "SalvatoreCLIPPositiveNegativeXL": SalvatoreCLIPPositiveNegativeXL,
    "SalvatoreCLIPTextPositiveNegativeXL": SalvatoreCLIPTextPositiveNegativeXL,
    "SalvatoreCLIPTextUnified": SalvatoreCLIPTextUnified,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SalvatoreCLIPPositiveNegative": "Salvatore CLIP Positive-Negative",
    "SalvatoreCLIPTextPositiveNegative": "Salvatore CLIP Positive-Negative w/Text",
    "SalvatoreCLIPPositiveNegativeXL": "Salvatore CLIP Positive-Negative XL",
    "SalvatoreCLIPTextPositiveNegativeXL": "Salvatore CLIP Positive-Negative XL w/Text",
    "SalvatoreCLIPTextUnified": "Salvatore CLIP +/- w/Text Unified",
}
