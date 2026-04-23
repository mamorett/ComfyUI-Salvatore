"""
Salvatore Nodes - Image
Image processing and I/O nodes.
"""
import os
import json
import hashlib
import re
import numpy as np
import torch
from PIL import Image, ImageOps
from PIL.PngImagePlugin import PngInfo
import piexif
import piexif.helper
import folder_paths

# Import utilities directly from the file
import importlib.util
_utils_spec = importlib.util.spec_from_file_location("salvatore_utils", os.path.join(os.path.dirname(__file__), "salvatore_utils.py"))
salvatore_utils = importlib.util.module_from_spec(_utils_spec)
_utils_spec.loader.exec_module(salvatore_utils)

tensor2pil = salvatore_utils.tensor2pil
pil2tensor = salvatore_utils.pil2tensor
save_images_to_output = salvatore_utils.save_images_to_output
write_text_file = salvatore_utils.write_text_file
make_filename = salvatore_utils.make_filename


class SalvatoreImageGrayscale:
    """Convert image to grayscale."""
    
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "original": ("IMAGE",), }}
    
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("grayscale",)
    FUNCTION = "make_grayscale"
    CATEGORY = "Salvatore Nodes/image"

    def make_grayscale(self, original):
        image = tensor2pil(original)
        image = ImageOps.grayscale(image)
        image = image.convert("RGB")
        image = np.array(image).astype(np.float32) / 255.0
        image = torch.from_numpy(image)[None,]
        return (image,)


class SalvatoreReadPrompt:
    """Load image and extract prompt metadata."""
    
    @classmethod
    def INPUT_TYPES(s):
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        return {"required": {
                    "verbose": (["true", "false"],),
                    "image": (sorted(files), {"image_upload": True}),
                },
            }
    
    CATEGORY = "Salvatore Nodes/image"
    
    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "INT", "INT", "FLOAT", "INT", "INT", "STRING")
    RETURN_NAMES = ("image", "positive", "negative", "seed", "steps", "cfg", "width", "height", "positive_magic")
    FUNCTION = "get_image_data"

    def get_image_data(self, image, verbose):
        image_path = folder_paths.get_annotated_filepath(image)
        with open(image_path, 'rb') as file:
            img = Image.open(file)
            extension = image_path.split('.')[-1]
            image = img.convert("RGB")
            image = np.array(image).astype(np.float32) / 255.0
            image = torch.from_numpy(image)[None,]

        parameters = ""
        comfy = False
        
        if extension.lower() == 'png':
            try:
                parameters = img.info['parameters']
                if not parameters.startswith("Positive prompt"):
                    parameters = "Positive prompt: " + parameters
            except:
                parameters = ""
                print("Error loading prompt info from png")
        elif extension.lower() in ("jpg", "jpeg", "webp"):
            try:
                exif = piexif.load(img.info["exif"])
                parameters = (exif or {}).get("Exif", {}).get(piexif.ExifIFD.UserComment, b'')
                parameters = piexif.helper.UserComment.load(parameters)
                if not parameters.startswith("Positive prompt"):
                    parameters = "Positive prompt: " + parameters
            except:
                try:
                    parameters = str(img.info['comment'])
                    comfy = True
                    # Legacy fixes
                    parameters = parameters.replace("Positive Prompt", "Positive prompt")
                    parameters = parameters.replace("Negative Prompt", "Negative prompt")
                    parameters = parameters.replace("Start at Step", "Start at step")
                    parameters = parameters.replace("End at Step", "End at step")
                    parameters = parameters.replace("Denoising Strength", "Denoising strength")
                except:
                    parameters = ""
                    print("Error loading prompt info from jpeg")

        if comfy and extension.lower() == 'jpeg':
            parameters = parameters.replace('\\n', ' ')
        else:
            parameters = parameters.replace('\n', ' ')

        patterns = [
            "Positive prompt: ", "Negative prompt: ", "Steps: ", "Start at step: ",
            "End at step: ", "Sampler: ", "Scheduler: ", "CFG scale: ", "Seed: ",
            "Size: ", "Model: ", "Model hash: ", "Denoising strength: ", "Version: ",
            "ControlNet 0", "Controlnet 1", "Batch size: ", "Batch pos: ",
            "Hires upscale: ", "Hires steps: ", "Hires upscaler: ", "Template: ",
            "Negative Template: ",
        ]
        
        if comfy and extension.lower() == 'jpeg':
            parameters = parameters[2:]
            parameters = parameters[:-1]

        keys = re.findall("|".join(patterns), parameters)
        values = re.split("|".join(patterns), parameters)
        values = [x for x in values if x]
        results = {}
        result_string = ""
        
        for item in range(len(keys)):
            result_string += keys[item] + values[item].rstrip(', ')
            result_string += "\n"
            results[keys[item].replace(": ", "")] = values[item].rstrip(', ')

        if verbose == "true":
            print(result_string)

        try:
            positive = results['Positive prompt']
        except:
            positive = ""
        try:
            negative = results['Negative prompt']
        except:
            negative = ""
        try:
            seed = int(results['Seed'])
        except:
            seed = -1
        try:
            steps = int(results['Steps'])
        except:
            steps = 20
        try:
            cfg = float(results['CFG scale'])
        except:
            cfg = 8.0
        try:
            width, height = img.size
        except:
            width, height = 512, 512

        # Extract positive prompt using workflow metadata (magic extraction)
        positive_magic = ""
        if extension.lower() == 'png':
            try:
                metadata = img.info
                if 'workflow' in metadata:
                    workflow_data = json.loads(metadata['workflow'])
                    processed_nodes = set()
                    prompts = self.extract_positive_from_workflow(workflow_data, processed_nodes)
                    if prompts:
                        positive_magic = "\n".join([p.get('text', '') for p in prompts])
            except Exception as e:
                if verbose == "true":
                    print(f"Error extracting workflow prompts: {e}")

        return (image, positive, negative, seed, steps, cfg, width, height, positive_magic)

    def extract_positive_from_workflow(self, workflow_data, processed_nodes):
        """Extract positive prompts from workflow nodes."""
        positive_prompts = []
        nodes = workflow_data.get('nodes', [])

        for node in nodes:
            node_id = node.get('id')
            node_type = node.get('type', '')
            title = node.get('properties', {}).get('Node name for S&R', '')

            if node_id in processed_nodes:
                continue

            if (node_type == 'CLIPTextEncode' or
                'cliptext' in node_type.lower() or
                title == 'CLIPTextEncode'):

                widgets_values = node.get('widgets_values', [])

                if widgets_values and len(widgets_values) > 0:
                    prompt_text = widgets_values[0]
                    title_lower = node.get('title', '').lower()

                    is_positive = (
                        'positive' in title_lower or
                        'pos' in title_lower or
                        (title_lower == 'untitled' and isinstance(prompt_text, str) and 
                         prompt_text.strip() != '' and 'negative' not in prompt_text.lower()[:50])
                    )

                    is_negative = (
                        'negative' in title_lower or
                        'neg' in title_lower or
                        (isinstance(prompt_text, str) and (prompt_text.strip() == '' or 
                         prompt_text.lower().strip().startswith('negative')))
                    )

                    if isinstance(prompt_text, list):
                        prompt_text = '\n'.join(str(x) for x in prompt_text)

                    if is_positive and not is_negative and isinstance(prompt_text, (str, int, float)):
                        prompt_info = {
                            'text': str(prompt_text),
                            'node_id': node_id,
                            'node_type': node_type,
                            'title': node.get('title', 'Untitled'),
                            'source': 'workflow'
                        }
                        positive_prompts.append(prompt_info)
                        processed_nodes.add(node_id)

        return positive_prompts

    @classmethod
    def IS_CHANGED(s, image, verbose):
        image_path = folder_paths.get_annotated_filepath(image)
        m = hashlib.sha256()
        with open(image_path, 'rb') as f:
            m.update(f.read())
        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(s, image, verbose):
        if not folder_paths.exists_annotated_filepath(image):
            return "Invalid image file: {}".format(image)
        return True


class SalvatoreBuildFilenameString:
    """Build filename from format string and inputs."""
    
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
                    "required": {
                        "filename": ("STRING", {"default": "%time_%seed", "multiline": False}),
                    },
                    "optional": {
                        "modelname": ("STRING", {"default": '', "multiline": False}),
                        "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff }),
                        "counter": ("SEED", {"default": 0}),
                        "time_format": ("STRING", {"default": "%Y-%m-%d-%H%M%S", "multiline": False}),
                    }
                }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("filename",)
    FUNCTION = "build_filename"
    CATEGORY = "Salvatore Nodes/image"

    def build_filename(self, filename="%time_%seed", modelname="model", time_format="%Y-%m-%d-%H%M%S", 
                       seed=0, counter=0):
        filename = make_filename(filename, seed, modelname, counter, time_format)
        return (filename,)


NODE_CLASS_MAPPINGS = {
    "SalvatoreImageGrayscale": SalvatoreImageGrayscale,
    "SalvatoreReadPrompt": SalvatoreReadPrompt,
    "SalvatoreBuildFilenameString": SalvatoreBuildFilenameString,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SalvatoreImageGrayscale": "Salvatore Grayscale Image",
    "SalvatoreReadPrompt": "Salvatore Image Load with Metadata",
    "SalvatoreBuildFilenameString": "Salvatore Build Filename String",
}
