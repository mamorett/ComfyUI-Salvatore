"""
Salvatore Nodes - IO
Image and prompt file saving nodes.
"""
import os

# Import utilities directly from the file
import importlib.util
_utils_spec = importlib.util.spec_from_file_location("salvatore_utils", os.path.join(os.path.dirname(__file__), "salvatore_utils.py"))
salvatore_utils = importlib.util.module_from_spec(_utils_spec)
_utils_spec.loader.exec_module(salvatore_utils)

get_timestamp = salvatore_utils.get_timestamp
make_filename = salvatore_utils.make_filename
make_comment = salvatore_utils.make_comment
save_images_to_output = salvatore_utils.save_images_to_output
write_text_file = salvatore_utils.write_text_file


class SalvatoreImageSaveWithPrompt:
    """Save image with prompt metadata."""
    
    def __init__(self):
        self.type = "output"
        self.output_dir = folder_paths.output_directory

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", ),
                "filename": ("STRING", {"default": '%time_%seed', "multiline": False}),
                "path": ("STRING", {"default": '', "multiline": False}),
                "extension": (['png', 'jpeg', 'tiff', 'gif'], ),
                "quality": ("INT", {"default": 100, "min": 1, "max": 100, "step": 1}),
            },
            "optional": {
                "positive": ("STRING", {"multiline": True, "forceInput": True}),
                "negative": ("STRING", {"multiline": True, "forceInput": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "forceInput": True}),
                "modelname": ("STRING", {"default": '', "multiline": False, "forceInput": True}),
                "counter": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff }),
                "time_format": ("STRING", {"default": "%Y-%m-%d-%H%M%S", "multiline": False}),
            },
            "hidden": {
                "prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_files"
    OUTPUT_NODE = True
    CATEGORY = "Salvatore Nodes/IO"

    def save_files(self, images, positive="unknown", negative="unknown", seed=-1, 
                   modelname="unknown", counter=0, filename='', path="",
                   time_format="%Y-%m-%d-%H%M%S", extension='png', quality=100, 
                   prompt=None, extra_pnginfo=None):
        filename = make_filename(filename, seed, modelname, counter, time_format)
        comment = make_comment(positive, negative, modelname, seed, info=None)

        output_path = os.path.join(self.output_dir, path)

        # Create missing paths
        if output_path.strip() != '':
            if not os.path.exists(output_path.strip()):
                print(f'The path `{output_path.strip()}` specified doesn\'t exist! Creating directory.')
                os.makedirs(output_path, exist_ok=True)

        paths = save_images_to_output(
            images, output_path, path, filename, comment, extension, quality, 
            prompt, extra_pnginfo
        )

        return {"ui": {"images": paths}}


class SalvatoreImageSaveWithPromptInfo:
    """Save image with prompt and generation info metadata."""
    
    def __init__(self):
        self.type = "output"
        self.output_dir = folder_paths.output_directory

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", ),
                "filename": ("STRING", {"default": '%time_%seed', "multiline": False}),
                "path": ("STRING", {"default": '', "multiline": False}),
                "extension": (['png', 'jpeg', 'tiff', 'gif'], ),
                "quality": ("INT", {"default": 100, "min": 1, "max": 100, "step": 1}),
            },
            "optional": {
                "positive": ("STRING", {"multiline": True, "forceInput": True}),
                "negative": ("STRING", {"multiline": True, "forceInput": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "forceInput": True}),
                "modelname": ("STRING", {"default": '', "multiline": False, "forceInput": True}),
                "counter": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff }),
                "time_format": ("STRING", {"default": "%Y-%m-%d-%H%M%S", "multiline": False}),
                "info": ("INFO",)
            },
            "hidden": {
                "prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_files"
    OUTPUT_NODE = True
    CATEGORY = "Salvatore Nodes/IO"

    def save_files(self, images, positive="unknown", negative="unknown", seed=-1, 
                   modelname="unknown", info=None, counter=0, filename='', path="",
                   time_format="%Y-%m-%d-%H%M%S", extension='png', quality=100, 
                   prompt=None, extra_pnginfo=None):
        filename = make_filename(filename, seed, modelname, counter, time_format)
        comment = make_comment(positive, negative, modelname, seed, info)

        output_path = os.path.join(self.output_dir, path)

        # Create missing paths
        if output_path.strip() != '':
            if not os.path.exists(output_path.strip()):
                print(f'The path `{output_path.strip()}` specified doesn\'t exist! Creating directory.')
                os.makedirs(output_path, exist_ok=True)

        paths = save_images_to_output(
            images, output_path, path, filename, comment, extension, quality, 
            prompt, extra_pnginfo
        )

        return {"ui": {"images": paths}}


class SalvatoreImageSaveWithFile:
    """Save image and prompt to separate files."""
    
    def __init__(self):
        self.output_dir = folder_paths.output_directory
        self.type = "output"

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", ),
                "filename": ("STRING", {"default": '%time_%seed', "multiline": False}),
                "path": ("STRING", {"default": '', "multiline": False}),
                "extension": (['png', 'jpeg', 'tiff', 'gif'], ),
                "quality": ("INT", {"default": 100, "min": 1, "max": 100, "step": 1}),
            },
            "optional": {
                "positive": ("STRING", {"default": '', "multiline": True, "forceInput": True}),
                "negative": ("STRING", {"default": '', "multiline": True, "forceInput": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "forceInput": True}),
                "modelname": ("STRING", {"default": '', "multiline": False, "forceInput": True}),
                "counter": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff }),
                "time_format": ("STRING", {"default": "%Y-%m-%d-%H%M%S", "multiline": False}),
            },
            "hidden": {
                "prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_files"
    OUTPUT_NODE = True
    CATEGORY = "Salvatore Nodes/IO"

    def save_files(self, images, positive="unknown", negative="unknown", seed=-1, 
                   modelname="unknown", counter=0, filename='', path="",
                   time_format="%Y-%m-%d-%H%M%S", extension='png', quality=100, 
                   prompt=None, extra_pnginfo=None):
        filename = make_filename(filename, seed, modelname, counter, time_format)
        comment = make_comment(positive, negative, modelname, seed, info=None)
        
        output_path = os.path.join(self.output_dir, path)

        # Create missing paths
        if output_path.strip() != '':
            if not os.path.exists(output_path.strip()):
                print(f'The path `{output_path.strip()}` specified doesn\'t exist! Creating directory.')
                os.makedirs(output_path, exist_ok=True)

        paths = save_images_to_output(
            images, output_path, path, filename, comment, extension, quality, 
            prompt, extra_pnginfo
        )
        
        # Save text file
        write_text_file(os.path.join(output_path, filename + '.txt'), comment)
        
        return {"ui": {"images": paths}}


class SalvatoreImageSaveWithFileInfo:
    """Save image and prompt with info to separate files."""
    
    def __init__(self):
        self.output_dir = folder_paths.output_directory
        self.type = "output"

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", ),
                "filename": ("STRING", {"default": '%time_%seed', "multiline": False}),
                "path": ("STRING", {"default": '', "multiline": False}),
                "extension": (['png', 'jpeg', 'tiff', 'gif'], ),
                "quality": ("INT", {"default": 100, "min": 1, "max": 100, "step": 1}),
            },
            "optional": {
                "positive": ("STRING", {"default": '', "multiline": True, "forceInput": True}),
                "negative": ("STRING", {"default": '', "multiline": True, "forceInput": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "forceInput": True}),
                "modelname": ("STRING", {"default": '', "multiline": False, "forceInput": True}),
                "counter": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff }),
                "time_format": ("STRING", {"default": "%Y-%m-%d-%H%M%S", "multiline": False}),
                "info": ("INFO",)
            },
            "hidden": {
                "prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_files"
    OUTPUT_NODE = True
    CATEGORY = "Salvatore Nodes/IO"

    def save_files(self, images, positive="unknown", negative="unknown", seed=-1, 
                   modelname="unknown", info=None, counter=0, filename='', path="",
                   time_format="%Y-%m-%d-%H%M%S", extension='png', quality=100, 
                   prompt=None, extra_pnginfo=None):
        filename = make_filename(filename, seed, modelname, counter, time_format)
        comment = make_comment(positive, negative, modelname, seed, info)
        
        output_path = os.path.join(self.output_dir, path)

        # Create missing paths
        if output_path.strip() != '':
            if not os.path.exists(output_path.strip()):
                print(f'The path `{output_path.strip()}` specified doesn\'t exist! Creating directory.')
                os.makedirs(output_path, exist_ok=True)

        paths = save_images_to_output(
            images, output_path, path, filename, comment, extension, quality, 
            prompt, extra_pnginfo
        )
        
        # Save text file
        write_text_file(os.path.join(output_path, filename + '.txt'), comment)
        
        return {"ui": {"images": paths}}


class SalvatoreSavePromptFile:
    """Save prompt to text file."""
    
    def __init__(self):
        self.output_dir = folder_paths.output_directory

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "filename": ("STRING", {"default": 'info', "multiline": False}),
                "path": ("STRING", {"default": '', "multiline": False}),
                "positive": ("STRING", {"default": '', "multiline": True, "forceInput": True}),
            },
            "optional": {
                "negative": ("STRING", {"default": '', "multiline": True, "forceInput": True}),
                "modelname": ("STRING", {"default": '', "multiline": False, "forceInput": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "forceInput": True}),
                "counter": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff }),
                "time_format": ("STRING", {"default": "%Y-%m-%d-%H%M%S", "multiline": False}),
            }
        }

    OUTPUT_NODE = True
    RETURN_TYPES = ()
    FUNCTION = "save_text_file"
    CATEGORY = "Salvatore Nodes/IO"

    def save_text_file(self, positive="", negative="", seed=-1, modelname="unknown", 
                       path="", counter=0, time_format="%Y-%m-%d-%H%M%S", filename=""):
        output_path = os.path.join(self.output_dir, path)

        # Create missing paths
        if output_path.strip() != '':
            if not os.path.exists(output_path.strip()):
                print(f'The path `{output_path.strip()}` specified doesn\'t exist! Creating directory.')
                os.makedirs(output_path, exist_ok=True)

        text_data = make_comment(positive, negative, modelname, seed, info=None)

        filename = make_filename(filename, seed, modelname, counter, time_format)
        
        # Write text file
        write_text_file(os.path.join(output_path, filename + '.txt'), text_data)

        return (text_data,)


class SalvatoreSavePromptFileInfo:
    """Save prompt with info to text file."""
    
    def __init__(self):
        self.output_dir = folder_paths.output_directory

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "filename": ("STRING", {"default": 'info', "multiline": False}),
                "path": ("STRING", {"default": '', "multiline": False}),
                "positive": ("STRING", {"default": '', "multiline": True, "forceInput": True}),
            },
            "optional": {
                "negative": ("STRING", {"default": '', "multiline": True, "forceInput": True}),
                "modelname": ("STRING", {"default": '', "multiline": False, "forceInput": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "forceInput": True}),
                "counter": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff }),
                "time_format": ("STRING", {"default": "%Y-%m-%d-%H%M%S", "multiline": False}),
                "info": ("INFO",)
            }
        }

    OUTPUT_NODE = True
    RETURN_TYPES = ()
    FUNCTION = "save_text_file"
    CATEGORY = "Salvatore Nodes/IO"

    def save_text_file(self, positive="", negative="", seed=-1, modelname="unknown", 
                       info=None, path="", counter=0, time_format="%Y-%m-%d-%H%M%S", 
                       filename=""):
        output_path = os.path.join(self.output_dir, path)

        # Create missing paths
        if output_path.strip() != '':
            if not os.path.exists(output_path.strip()):
                print(f'The path `{output_path.strip()}` specified doesn\'t exist! Creating directory.')
                os.makedirs(output_path, exist_ok=True)

        text_data = make_comment(positive, negative, modelname, seed, info)

        filename = make_filename(filename, seed, modelname, counter, time_format)
        
        # Write text file
        write_text_file(os.path.join(output_path, filename + '.txt'), text_data)

        return (text_data,)


class SalvatoreSavePositivePromptFile:
    """Save positive prompt only to text file."""
    
    def __init__(self):
        self.output_dir = folder_paths.output_directory

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "filename": ("STRING", {"default": 'info', "multiline": False}),
                "path": ("STRING", {"default": '', "multiline": False}),
                "positive": ("STRING", {"default": '', "multiline": True, "forceInput": True}),
            }
        }

    OUTPUT_NODE = True
    RETURN_TYPES = ()
    FUNCTION = "save_text_file"
    CATEGORY = "Salvatore Nodes/IO"

    def save_text_file(self, positive="", path="", filename=""):
        output_path = os.path.join(self.output_dir, path)

        # Create missing paths
        if output_path.strip() != '':
            if not os.path.exists(output_path.strip()):
                print(f'The path `{output_path.strip()}` specified doesn\'t exist! Creating directory.')
                os.makedirs(output_path, exist_ok=True)

        # Ensure content to save, use timestamp if no name given
        if filename.strip() == '':
            print(f'Warning: There is no text specified to save! Text is empty. Saving file with timestamp')
            filename = get_timestamp('%Y%m%d%H%M%S')

        # Write text file after checking for empty prompt
        if positive == "":
            positive = "No prompt data"

        write_text_file(os.path.join(output_path, filename + '.txt'), positive)

        return (positive,)


# Import folder_paths here to avoid circular imports
import folder_paths


NODE_CLASS_MAPPINGS = {
    "SalvatoreImageSaveWithPrompt": SalvatoreImageSaveWithPrompt,
    "SalvatoreImageSaveWithPromptInfo": SalvatoreImageSaveWithPromptInfo,
    "SalvatoreImageSaveWithFile": SalvatoreImageSaveWithFile,
    "SalvatoreImageSaveWithFileInfo": SalvatoreImageSaveWithFileInfo,
    "SalvatoreSavePromptFile": SalvatoreSavePromptFile,
    "SalvatoreSavePromptFileInfo": SalvatoreSavePromptFileInfo,
    "SalvatoreSavePositivePromptFile": SalvatoreSavePositivePromptFile,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SalvatoreImageSaveWithPrompt": "Salvatore Image Save with Prompt",
    "SalvatoreImageSaveWithPromptInfo": "Salvatore Image Save with Prompt/Info",
    "SalvatoreImageSaveWithFile": "Salvatore Image Save with Prompt File",
    "SalvatoreImageSaveWithFileInfo": "Salvatore Image Save with Prompt/Info File",
    "SalvatoreSavePromptFile": "Salvatore Save Prompt",
    "SalvatoreSavePromptFileInfo": "Salvatore Save Prompt/Info",
    "SalvatoreSavePositivePromptFile": "Salvatore Save Positive Prompt",
}
